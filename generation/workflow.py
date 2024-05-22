import os
from dotenv import load_dotenv
import autogen
from tools import ALL_TOOLS, gen_img_save, fetch_latest_ai_papers, save_workflow_output, mark_paper_as_consumed
from agents import get_agent
from assessment import content_metric, blacklist_words
from linkedin_integration import post_image_and_text, post_comment_on_linkedin
import json
import ast
from datetime import datetime
load_dotenv(override=True)


config_list = [{"model": "gpt-4", "api_key": os.getenv("OPENAI_API_KEY")}]
config_list_turbo = [{"model": "gpt-4-turbo-preview", "api_key": os.getenv("OPENAI_API_KEY")}]

llm_config = {
    "temperature": 1,
    "config_list": config_list,
}

llm_config_turbo = {
    "temperature": 1,
    "config_list": config_list_turbo,
}

user_proxy = autogen.UserProxyAgent(
    name="Admin",
    code_execution_config=False,
    human_input_mode="NEVER",
)

researcher = get_agent("AI_Researcher", llm_config)
extractor = get_agent("Extractor", llm_config_turbo)
ai_expert = get_agent("AI_Researcher", llm_config)
socials = get_agent("Socials", llm_config)
critique = get_agent("Critique", llm_config)
challenge = get_agent("Idea_Challenge", llm_config)
img_prompt = get_agent("img_prompt", llm_config)



latest_papers = fetch_latest_ai_papers()
titles = [paper.title for paper in latest_papers]


def fill_paper_metadata(paper_part, papers_arr):
    title = paper_part['title']
    paper = next((paper for paper in papers_arr if paper.title == title), None)
    
    # If the paper was found, append it to consumed_data
    if paper is not None:
        return paper.__dict__
    else:
        # If the paper was not found, raise an error
        raise ValueError(f"No paper found with title {title}")


research = user_proxy.initiate_chats(
    [
        {"recipient": researcher, "message": "Shortlist 5 reasearch papers that seem most insteresting, GenAI/LLM relevent, and applicable to digital tech.\n\nTitles: [\""+"\", \"".join(titles)+"\"]", "max_turns": 1, "summary_method": "last_msg"},
        {"recipient": extractor, "message": "Extract the paper titles into an string list. Response Format: List[str]. Start response with [ and end with ]", "max_turns": 1, "summary_method": "last_msg"},
    ]
)
    

title_array = ast.literal_eval(research[1].summary)
paper_summary_array = [{"title":paper.title,"summary":paper.summary} for paper in latest_papers if paper.title in title_array]


brainstrom = autogen.GroupChat(
    agents=[ai_expert, challenge, user_proxy],
    messages=[],
    max_round=3,
    speaker_selection_method="round_robin",
    enable_clear_history=True,
)

content = autogen.GroupChat(
    agents=[socials, critique],
    messages=[],
    max_round=4,
    speaker_selection_method="round_robin",
    enable_clear_history=True,
)

brainstorm_manager = autogen.GroupChatManager(
    groupchat=brainstrom,
    name="brainstorm_manager",
    llm_config=llm_config_turbo,
)
content_manager = autogen.GroupChatManager(
    groupchat=content,
    name="content_manager",
    llm_config=llm_config_turbo,
)

def get_brainstorm_messages(one, two, three):
    idea = two.chat_messages_for_summary(user_proxy)[1]
    twist = two.chat_messages_for_summary(user_proxy)[2]
    summary = '# Idea :\n'+idea['content']+'\n\n# Twist: \n'+twist['content']
    return summary

def extract_post_message(sender, recipient, context: dict):
    carryover = content_manager.last_message(socials)
    final_msg = "Extract the linkedin post content from the Context. The post content should start with a hook and end with hashtags. Respond only with the extraction" + "\nContent: \n" + carryover['content']
    return final_msg

now = datetime.now()
timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

post_options=[]
for paper in paper_summary_array:

    paper_condensed_summary = user_proxy.initiate_chat(
        recipient = ai_expert, 
        message= "Generate a MAXIMALLY COMPRESSED Description of the NOVEL breakthrough, advancement, discovery, technique, framework, or finding that is presented in the Research Paper. Your response must be distilled to a single line that represents the essense of your MAXIMALLY COMPRESSED Description.\n\n# Research Paper:\n"+ json.dumps(paper), 
        max_turns= 1, 
        summary_method= "last_msg"
    )
    # This works but the autogen framework is so restrictive, it is getting unwieldly to conform. 
    # content_gen = user_proxy.initiate_chats(
    #     [
    #         {"recipient": brainstorm_manager, "message": "Ponder the research and the implications in the real world. Think of a novel application for this research within the context of a business. buseinss domains with the vibe of data, tech, digital product, startup, etc. Research: "+ json.dumps(paper), "max_turns": 1, "summary_method": get_brainstorm_messages},
    #         {"recipient": content_manager, "message": f"Think through the application of the Post Framework. Itterate and apply Critiques provided.\nSource Research, Idea, and Twist have been provided for context.\n\n# Source Research:\n'{paper['title']}'\n{paper_condensed_summary.summary}", "max_turns": 1, "summary_method": "last_msg"},
    #         {"recipient": extractor, "message": extract_post_message, "max_turns": 1, "summary_method": "last_msg"},
    #     ]
    # )
    
    draft_gen = user_proxy.initiate_chats(
        [
            {"recipient": brainstorm_manager, "message": "Ponder the research and the implications in the real world. Think of a novel application for this research within the context of a business. buseinss domains with the vibe of data, tech, digital product, startup, etc. Research: "+ json.dumps(paper), "max_turns": 1, "summary_method": get_brainstorm_messages},
            {"recipient": socials, "message": f"Review the Source Research, Idea, and Twist that have been provided for context.\n\nLeverage your myriad skills to draft a linkedin post as per your Post Framework.\n\n# Source Research:\n'{paper['title']}'\n{paper_condensed_summary.summary}", "max_turns": 1, "summary_method": "last_msg"},
            {"recipient": critique, "message": f"PROVIDE CRITICAL FEEDBACK on the Linkedin Post Content across the Dimensions and Framework.", "max_turns": 1, "summary_method": "last_msg"},
            {"recipient": socials, "message": f"Reflect on the Critique given on the Linkedin Post. Edit the post accordingly while adhering to the Post Framework", "max_turns": 1, "summary_method": "last_msg"},
        ]
    )
    
    
    final_edit = user_proxy.initiate_chats(
        [
            {"recipient" : socials, 
            "message": f"Generate the final edit of the Linkedin Post Draft. Respond only with the final edit.\nThis edit is a minor polishing of the Post Draft based on the following guide:\n- **Exclusion of Certain Terms:** Edit out ALL OCCURANCES of the following *blacklisted* words and phrases: {blacklist_words}\n- **Awareness of Common Words:** Ensure low frequency of common words such as \"the\", \"it\", and \"is\".\n- **Post Framework:** The post should adhere to the Post Framework format without specific mention of the framework. Remove any labeling of sections such as Hook, Rehook, Twist, Flip etc...\n\nSource Research has been provided for aditional context.\n\n# Source Research:\n'{paper['title']}'\n{paper_condensed_summary.summary}\n\n# Post Draft:\n{draft_gen[3].summary}", 
            "max_turns": 1, 
            "summary_method": "last_msg"},
            {"recipient": extractor, "message": "Extract the linkedin post content from the Context. The post content should start with a hook and end with hashtags. Respond only with the extraction", "max_turns": 1, "summary_method": "last_msg"},
        ]
    )

    parsed_content = final_edit[1].summary.replace("**", "") 
    parsed_content = final_edit[1].summary.replace("#### ", "") 
    parsed_content = final_edit[1].summary.replace("### ", "") 
    parsed_content = final_edit[1].summary.replace("## ", "") 
    score, assessment_obj = content_metric(post=parsed_content, title=paper['title'], summary=paper['summary'])
    paper = fill_paper_metadata(paper, latest_papers)
    post_options.append({"content":parsed_content, "paper":paper, "compressed_paper": paper_condensed_summary.summary, "assessment_score": score, "assessment_obj": assessment_obj, "timestamp": timestamp})
    
top_post = max(post_options, key=lambda x: x['assessment_score'])
non_top_posts = [post for post in post_options if post != top_post]

img_gen = user_proxy.initiate_chats(
    [
        {"recipient": img_prompt, "message": "# Linkedin Post:\n"+top_post['content']+"\n\n[REFLECT] -> [OMNISKILL] -> [IMGGEN]", "max_turns": 1, "summary_method": "last_msg"},
        {"recipient": extractor, "message": "Extract [IMGGEN] Image Prompt from the Context. Respond only with the exact image prompt including technical details of photography equipment and style", "max_turns": 1, "summary_method": "last_msg"},
    ]
)

img_path = gen_img_save(img_gen[1].summary, top_post['paper']['title'])

share_urn = post_image_and_text(img_path, top_post['content'])
top_post['share_urn']= share_urn
# Save the workflow output
save_workflow_output(top_post, non_top_posts)
mark_paper_as_consumed(top_post['paper']['entry_id'])

post_comment_on_linkedin(share_urn, f"arXiv: {top_post['paper']['entry_id']}")


