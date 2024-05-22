from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from operator import itemgetter
from dotenv import load_dotenv
from system_messages import system_messages
from tools import fetch_latest_ai_papers
from langchain_core.globals import set_verbose
from assessment import content_metric, blacklist_words
from linkedin_integration import post_image_and_text, post_comment_on_linkedin
from tools import gen_img_save, fetch_latest_ai_papers, save_workflow_output, mark_paper_as_consumed
import json
import ast
from datetime import datetime
from typing import List

load_dotenv(override=True)
set_verbose(True)


gpt4 = ChatOpenAI(model="gpt-4", temperature=1)
gpt4TExtract = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0)

ai_expert = SystemMessage(system_messages["AI_Researcher"])
extractor = SystemMessage(system_messages["Extractor"])
socials = SystemMessage(system_messages["Socials"])
critique = SystemMessage(system_messages["Critique"])
challenge = SystemMessage(system_messages["Idea_Challenge"])
img_prompt_gen = SystemMessage(system_messages["img_prompt"])

def fill_paper_metadata(paper_part, papers_arr):
    title = paper_part['title']
    paper = next((paper for paper in papers_arr if paper.title == title), None)
    
    # If the paper was found, append it to consumed_data
    if paper is not None:
        return paper.__dict__
    else:
        # If the paper was not found, raise an error
        raise ValueError(f"No paper found with title {title}")

def parse_titles_for_summary(titles_str, latest_papers) -> List[dict]:
    title_array = ast.literal_eval(titles_str)
    paper_summary_array = [{"title":paper.title,"summary":paper.summary} for paper in latest_papers if paper.title in title_array]
    return paper_summary_array


shortlist_agent = (
    ChatPromptTemplate.from_messages(
        [extractor,
            ("human", "Shortlist 5 reasearch papers that seem most insteresting, GenAI/LLM relevent, and applicable to digital tech.\n\nTitles: [\"{titles}\"]"),
            
        ]
    )
    | gpt4 
    | StrOutputParser()
    | {"titles_shortlist": RunnablePassthrough()}
)
extract_titles_agent = (
    ChatPromptTemplate.from_messages(
        [ai_expert,
            ("human", "Extract the paper titles from Context into an string list.\nResponse Format: List[str]. Start response with [ and end with ]\n\nContext:{titles_shortlist}"),
            
        ]
    )
    | gpt4TExtract | StrOutputParser()
)

paper_condensed_summary_agent = (
    ChatPromptTemplate.from_messages(
        [ai_expert,
            ("human", "Generate a MAXIMALLY COMPRESSED Description of the NOVEL breakthrough, advancement, discovery, technique, framework, or finding that is presented in the Research Paper. Your response must be distilled to a single line that represents the essense of your MAXIMALLY COMPRESSED Description.\n\n# Research Paper:\n{paper_raw}"),
             
        ]
    )
    | gpt4
    | StrOutputParser()
    | {"paper_condensed_summary": RunnablePassthrough()}
)
            
            
brainstorm_idea_agent = (
    ChatPromptTemplate.from_messages(
        [ai_expert,
            ("human", "Ponder the research and the implications in the real world. Think of a novel application for this research within the context of a business. buseinss domains with the vibe of data, tech, digital product, startup, etc. Research: {paper_raw}"),
            
        ]
    )
    | gpt4 
    | StrOutputParser()
    | {"brainstorm_idea": RunnablePassthrough()}
)

brainstorm_twist_agent = (
    ChatPromptTemplate.from_messages(
        [challenge,

            ("human", "Ponder the research and the implications in the real world. Think of a novel application for this research within the context of a business. buseinss domains with the vibe of data, tech, digital product, startup, etc. Research: {paper_raw}"),
                        ("human", "Challenge my thinking: {brainstorm_idea}"),
        ]
    )
    | gpt4 
    | StrOutputParser()
    | {"brainstorm_twist": RunnablePassthrough()}
)

socials_draft_agent = (
    ChatPromptTemplate.from_messages(
        [socials,
            ("human", "Review the Source Research, Idea, and Twist that have been provided for context.\n\nLeverage your myriad skills to draft a linkedin post as per your Post Framework.\n\n# Source Research:\n{paper}\n{paper_condensed_summary}\n\n# Idea:\n{brainstorm_idea}\n\n# Twist:\n{brainstorm_twist}"),
            
        ]
    )
    | gpt4 
    | StrOutputParser()
    | {"socials_draft": RunnablePassthrough()}
)


critique_agent = (
    ChatPromptTemplate.from_messages(
        [critique,
           
            ("human", "# Source Research:\n{paper}\n{paper_condensed_summary}\n\n# Idea:\n{brainstorm_idea}"),
             ("human", "PROVIDE CRITICAL FEEDBACK on the Linkedin Post Content across the Dimensions and Framework.\n\n# Content: {socials_draft}"),
        ]
    )
    | gpt4 
    | StrOutputParser()
    | {"critique": RunnablePassthrough()}
)

socials_edit_agent = (
    ChatPromptTemplate.from_messages(
        [    socials,
                   ("human", "# Source Research:\n{paper}\n{paper_condensed_summary}\n\n# Idea:\n{brainstorm_idea}\n\n# Twist:\n{brainstorm_twist}"),
            ("ai", "{socials_draft}"),
     
        ("human", "Reflect on the Critique given on the Linkedin Post. Edit the Post Draft accordingly while adhering to the Post Framework\n\n# Critique:\n{critique}"),
        ]
    )
    | gpt4 
    | StrOutputParser()
    | {"socials_edit": RunnablePassthrough()}
)

socials_final_edit_agent = (
    ChatPromptTemplate.from_messages(
        [ socials,
            ("human", "Generate the final edit of the Linkedin Post Draft. Respond only with the final edit.\nThis edit is a minor polishing of the Post Draft based on the following guide:\n- **Exclusion of Certain Terms:** Edit out ALL OCCURANCES of the following *blacklisted* words and phrases: {blacklist_words}\n- **Awareness of Common Words:** Ensure low frequency of common words such as \"the\", \"it\", and \"is\".\n- **Post Framework:** The post should adhere to the Post Framework format without specific mention of the framework. Remove any labeling of sections such as Hook, Rehook, Twist, Flip etc...\n\nSource Research has been provided for aditional context.\n\n# Source Research:\n'{paper}'\n{paper_condensed_summary}\n\n# Post Draft:\n{socials_edit}"),
           
        ]
    )
    | gpt4 
    | StrOutputParser()
    | {"socials_final_edit": RunnablePassthrough()}
)

post_extractor_agent = (
    ChatPromptTemplate.from_messages(
        [  extractor,
            ("human", "Extract the linkedin post content from the Context. The post content should start with a hook and end with hashtags. Respond only with the extraction\n\n# Content: {socials_final_edit}"),
          
        ]
    )
    | gpt4TExtract
    | StrOutputParser()
    | {"post_extractor": RunnablePassthrough()}
)

img_prompt_agent = (
    ChatPromptTemplate.from_messages(
        [ img_prompt_gen,
            ("human", "# Linkedin Post:\n{top_post}\n\n[REFLECT] -> [OMNISKILL] -> [IMGGEN]"),
           
        ]
    )
    | gpt4
    | StrOutputParser()
    | {"img_prompt_gen": RunnablePassthrough()}
)

img_prompt_extract_agent = (
    ChatPromptTemplate.from_messages(
        [ extractor,
            ("human", "Extract [IMGGEN] Image Prompt from the Context. Respond only with the exact image prompt including technical details of photography equipment and style.\n\n# Context:\n{context}"),
           
        ]
    )
    | gpt4TExtract
    | StrOutputParser()
    | {"img_prompt_extracted": RunnablePassthrough()}
)

chain = (
 shortlist_agent
    | {
        "titles_array": extract_titles_agent,
        "titles_shortlist": itemgetter("titles_shortlist"),
    }
)

latest_papers = fetch_latest_ai_papers()
titles = [paper.title for paper in latest_papers]
paperarrstr = chain.invoke({"titles": "\", \"".join(titles)})['titles_array']

paper_summary_array = parse_titles_for_summary(paperarrstr, latest_papers)


now = datetime.now()
timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

post_options=[]
for paper in paper_summary_array:
    
    # Tried a chain but it was not pasisng variables properly. probably need some state management var TODO for now
    papertitle=paper['title']
    papertitle
    inputs = {
        "paper": papertitle, 
        "paper_raw": json.dumps(paper), 
        "blacklist_words": blacklist_words
    }
    inputs['paper_condensed_summary'] = paper_condensed_summary_agent.invoke(inputs)["paper_condensed_summary"]
    inputs['brainstorm_idea'] = brainstorm_idea_agent.invoke(inputs)['brainstorm_idea']
    inputs['brainstorm_twist'] = brainstorm_twist_agent.invoke(inputs)['brainstorm_twist']
    inputs['socials_draft'] = socials_draft_agent.invoke(inputs)['socials_draft']
    inputs['critique'] = critique_agent.invoke(inputs)['critique']
    inputs['socials_edit'] = socials_edit_agent.invoke(inputs)['socials_edit']
    inputs['socials_final_edit'] = socials_final_edit_agent.invoke(inputs)['socials_final_edit']
    post = post_extractor_agent.invoke(inputs)['post_extractor']


    parsed_content = post.replace("**", "") 
    parsed_content = post.replace("#### ", "") 
    parsed_content = post.replace("### ", "") 
    parsed_content = post.replace("## ", "") 
    score, assessment_obj = content_metric(post=parsed_content, title=paper['title'], summary=paper['summary'])
    paper = fill_paper_metadata(paper, latest_papers)
    post_options.append({"content":parsed_content, "paper":paper, "compressed_paper": inputs['paper_condensed_summary'], "assessment_score": score, "assessment_obj": assessment_obj, "timestamp": timestamp})
    
top_post = max(post_options, key=lambda x: x['assessment_score'])
non_top_posts = [post for post in post_options if post != top_post]

img_prompt_agent_res = img_prompt_agent.invoke({"top_post":top_post})["img_prompt_gen"]
img_prompt = img_prompt_extract_agent.invoke({"context": img_prompt_agent_res})["img_prompt_extracted"]

img_path = gen_img_save(img_prompt, top_post['paper']['title'])

share_urn = post_image_and_text(img_path, top_post['content'])
top_post['share_urn']= share_urn
# Save the workflow output
save_workflow_output(top_post, non_top_posts)
mark_paper_as_consumed(top_post['paper']['entry_id'])

post_comment_on_linkedin(share_urn, f"arXiv: {top_post['paper']['entry_id']}")

