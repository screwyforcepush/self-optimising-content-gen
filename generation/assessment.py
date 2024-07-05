
import dspy
from dotenv import load_dotenv
import os

load_dotenv()

os.environ["OPENAI_API_KEY"] = os.getenv('OPENAI_API_KEY')
# Set up the LM
turbo = dspy.OpenAI(model='gpt-3.5-turbo', max_tokens=1000)
dspy.settings.configure(lm=turbo, trace=[])

post_components_str="""1. Hook → Grab attention
2. Re-hook → Add curiosity
3. Lead → Why it's important
4. The rule of three → Powerful
5. Proof → Expertise adds a layer of trust. The technical how.
6. Body → The answer to your hook. Include reference to the source research title.
7. Listicles → Descending or ascending
8. Power-ending → Summary for impact
9. CTA/CTE → Invite your reader to engage
10. Hashtags → 3 relevant hashtags for SEO"""


example_post="""
# Example Post:{{
I use this framework for every post.
And there's a reason for it...

It's called the Cognitive Fluency Effect:
The easier it is to understand,
the more trust you will get!

→ More trust means:
1. More engagement
2. More authority
3. More $$$

Copy the framework:
1. Hook → Grab attention
2. Re-hook → Add curiosity
3. Lead → Why it's important
4. The rule of three → Powerful
5. Proof → It adds a layer of trust
6. Body → The answer to your hook
7. Listicles → Descending / ascending
8. Power-ending → Summary for impact
9. CTA/CTE → Invite your reader to engage
10. Hashtags → 3 relevant hashtags for SEO

Follow these steps and see what happens.
Trust me 🤝

Do you use a framework for your posts?

#Three #Hash #Tags}}"""

post_components_arr = post_components_str.splitlines()
# Define the signature for automatic assessments.

blacklist_words = """["Delve", "Imagine a world", "in the realm of", "powerhouse", "revolutionize", "transformative", "leap", "new era", "paradim shift", "unprecedented", "cataclysmic", "groundbreaking", "evolution", "underpinned", "spearhead"]"""

def assess_content_length(content):
    content_length = len(content)
    if content_length < 1000:
        return 2.0
    elif content_length < 1500:
        return 1
    elif content_length < 2000:
        return 0.5
    else:
        return 0


class Assess_Structure(dspy.Signature):
    f"""Given the Expected Structure as context, assess the quality of a linkedin post along the specified Structure Component dimension.
    
    # Expected Structure:
    {post_components_str}
    """

    linkedin_post = dspy.InputField()
    structure_component = dspy.InputField()
    assessment_answer = dspy.OutputField(desc="Yes or No")
    
    


class Assess(dspy.Signature):
    """Assess the quality of a social post along the specified dimension."""

    assessed_text = dspy.InputField()
    assessment_question = dspy.InputField()
    assessment_answer = dspy.OutputField(desc="Yes or No")
    
    

# def content_metric(gold, pred, trace=None):
#     paper_title, answer, tweet = gold.paper_title, gold.answer, pred.output

def content_metric(post, title, summary):
    print("Assessing post: ", post)
    engaging = "Does the assessed text make for a self-contained, engaging linkedin post?"
    reference = f"Does the assessed text reference this source: `{title}`?"
    no_blacklist = f"Does the assessed text contain any of the following words/phrases: `{blacklist_words}`?"
    no_emojis = "Does the assessed text contain any emojis?"
    no_signature = "Does the Author introduce themselves, sign off, or mention their name?"
    factually_relevant = f"Is the assessed text factually relevant to the research: `{summary}`?"
    formated = f"Is the assessed text formatted as per example: `{example_post}`?"
    
    component_grade_arr = []
    component_score = 0
    for component in post_components_arr:
        component_used = f"Does the linkedin post contain a fit fur purpose Component: `{component}`?"
        component_grade =  dspy.ChainOfThought(Assess_Structure)(linkedin_post=post, structure_component=component_used)
        component_grade = component_grade.assessment_answer.lower() == 'yes'
        component_score += component_grade
        component_grade_arr.append({component:component_grade})

    reference = dspy.ChainOfThought(Assess)(assessed_text=post, assessment_question=reference)
    no_blacklist = dspy.ChainOfThought(Assess)(assessed_text=post, assessment_question=no_blacklist)
    no_emojis = dspy.ChainOfThought(Assess)(assessed_text=post, assessment_question=no_emojis)
    no_signature = dspy.ChainOfThought(Assess)(assessed_text=post, assessment_question=no_signature)
    factually_relevant = dspy.ChainOfThought(Assess)(assessed_text=post, assessment_question=factually_relevant)
    engaging = dspy.ChainOfThought(Assess)(assessed_text=post, assessment_question=engaging) 
    formated = dspy.ChainOfThought(Assess)(assessed_text=post, assessment_question=formated)
    

    reference, engaging, factually_relevant, formated = [m.assessment_answer.lower() == 'yes' for m in [reference, engaging, factually_relevant, formated]]
    no_blacklist, no_emojis, no_signature = [m.assessment_answer.lower() == 'no' for m in [no_blacklist, no_emojis, no_signature]]
    is_short_content = assess_content_length(post)
    
    score = (((reference + engaging + no_emojis + factually_relevant + formated)/5.0) + (component_score / len(component_grade_arr)) + no_signature + is_short_content + no_blacklist)/5.0

    return score, {
        "reference":reference, 
        "engaging":engaging, 
        "no_blacklist":no_blacklist, 
        "no_emojis":no_emojis, 
        "no_signature":no_signature, 
        "factually_relevant":factually_relevant, 
        "component_grade_arr":component_grade_arr, 
        "formated":formated, 
        "is_short_content":is_short_content
        }