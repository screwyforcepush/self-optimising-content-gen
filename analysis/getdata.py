import json
import re
import dspy
from dspy.teleprompt import Ensemble
import pickle
from dspy.evaluate import Evaluate
from dspy.teleprompt import BootstrapFewShotWithRandomSearch
from dspy.primitives.assertions import assert_transform_module, backtrack_handler
from dspy.teleprompt import COPRO
import ast
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import random
from dotenv import load_dotenv
import os

load_dotenv()

os.environ["OPENAI_API_KEY"] = os.getenv('OPENAI_API_KEY')

# Set up the LM
turbo = dspy.OpenAI(model='gpt-3.5-turbo', max_tokens=1000)
dspy.settings.configure(lm=turbo, trace=[])
gpt4T = dspy.OpenAI(model='gpt-4-turbo-preview', max_tokens=1000, model_type='chat')


class ExtractData(dspy.Signature):
    """Extract the hashtags, reaction count, comment count, share count from the social post context"""

    context = dspy.InputField()
    hashtags = dspy.OutputField(desc="['Array', 'of', '#hashtags']")
    reaction_count = dspy.OutputField(desc="int. Total likes, insightfuls, etc. or 0")
    comment_count = dspy.OutputField(desc="int. Number of comments or 0")
    share_count = dspy.OutputField(desc="int. Number of shares or 0")
    impression_count = dspy.OutputField(desc="int. Number of impressions")


extract = dspy.Predict(ExtractData, n=3)

# %%

# Assume a list of programs
programs = [extract]

# Define Ensemble teleprompter
teleprompter = Ensemble(reduce_fn=dspy.majority)

# Compile to get the EnsembledProgram
ensembled_program = teleprompter.compile(programs)



def extract_text_after_first(input_text):
    # Define a regular expression pattern to match the required text
    # The pattern captures lines starting from the second line after the bullet point with identifier up to the line before "hashtag#"
    pattern = r'•.*?\n(.*?)\nhashtag#'

    # Find the first match in the input text
    match = re.search(pattern, input_text, re.DOTALL)

    # If a match is found, return it, otherwise return None
    if match:
        return match.group(1).strip()
    else:
        return None

# %%
def parse_data(data):
    chunked_data=data.split("Alex Savage posted this")
    json_array=[]
    for i in chunked_data:
        var2 = ensembled_program(context=i)
        hashtag_string = var2.hashtags.replace("#", "")
        try:
            hashtags = ast.literal_eval(hashtags)
        except Exception as e:
            hashtags = hashtag_string.split(" ")
            # remove square brackets and commas
            hashtags = [x.replace("[", "").replace("]", "").replace(",", "") for x in hashtags]
            print(f"not an array: {hashtag_string}")
        json_array.append({
            "content": extract_text_after_first(i), 
            "hashtags": hashtags, 
            "impression_count": int(var2.impression_count.replace(",", "")), 
            "reaction_count": int(var2.reaction_count),
            "comment_count": int(var2.comment_count),
            "share_count": int(var2.share_count)
        })    
    return json_array


# %%



# %%
def clasify_chart(arr):

    AlphaFold = 0
    Quantum_AI = 0
    Other = 0

    for i in arr:
        content = i['content']
        classify = dspy.Predict(Topic)
        var2=classify(content=content)
        print(var2.topic)
        if var2.topic == "AlphaFold":
            AlphaFold += 1
        elif var2.topic == "Quantum AI":
            Quantum_AI += 1
        else:
            Other += 1

    print(AlphaFold, Quantum_AI, Other)


    # The sizes of each section of the pie chart
    sizes = [AlphaFold, Quantum_AI, Other]  # These values represent the three variables

    # The labels for each section
    labels = ['AlphaFold', 'Quantum AI', 'Other']

    # The colors for each section
    colors = ['gold', 'lightcoral', 'lightskyblue']

    # To separate a section from the others, use the explode option.
    explode = (0.1, 0, 0)  # This will only explode the 1st slice (i.e., 'Category A')

    plt.figure(figsize=(8, 6))  # Set the figure size
    plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', shadow=True, startangle=140)
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

    plt.title('Topic Distribution of Posts')
    plt.show()
# %%


def histpot(structured_data):
    # For the demonstration, creating a normally distributed array
    # Our original NumPy array
    number_array = np.array([])
    for i in structured_data:
        push = i['engagement_count']/i['impression_count']*100
        if (push>0 and push<4):
            number_array = np.append(number_array, push)
        if(push>4):
            print(i)

    # Setting the stage for our spell
    plt.figure(figsize=(10, 6))  # Telling the canvas the desired size

    # With the grace of seaborn's histplot, let's craft the distribution
    sns.histplot(number_array, kde=True, color='darkblue', bins=5,
                line_kws={'linewidth': 3}, 
                edgecolor="k", linewidth=1)

    # Calculating the cauldron's brew: Mean and Standard Deviation
    mean = np.mean(number_array)
    std_dev = np.std(number_array)

    # Weaving in the tapestry: Standard Deviation Lines
    plt.axvline(mean, color='k', linestyle='--', linewidth=2)  # The line for mean
    plt.axvline(mean + std_dev, color='red', linestyle='--', linewidth=2)  # +1 SD
    plt.axvline(mean - std_dev, color='red', linestyle='--', linewidth=2)  # -1 SD


    # Final charms: Titles and Labels
    plt.title('LN post engagement rate distribution')
    plt.xlabel('Engagement Rate')
    plt.ylabel('Density')

    # The grand reveal
    plt.show()

    weakposts = []
    strongposts = []
    for i in structured_data:
        push = i['engagement_count']/i['impression_count']*100
        if (push>(mean + std_dev)):
            strongposts.append(i)
        if(push<(mean - std_dev)):
            weakposts.append(i)


# %%
def etl():
    struc = parse_data(postdata)
    with open('data/post_engagement.json', 'w') as f:
        json.dump(struc, f, indent=4, sort_keys=True)


# %%

class ClasifyCategorySignature(dspy.Signature):
    """Ponder the content through the lense of the Category, then accuratly Classify the Content by awarding the most fitting Label(s) as per the defined Classification Label guidelines"""

    content = dspy.InputField()
    name = dspy.InputField(prefix="Category Name")
    definition = dspy.InputField(prefix="Category Definition")
    label_options = dspy.InputField(desc="Available Clasification Labels for the category", prefix="Label Options:")
    label_exclusive = dspy.InputField(desc="Indicates Label mutual exclusivity. Assign one label only if True, one or more if False.", prefix="Label Mutually Exclusive:")
    classification = dspy.OutputField(desc="Array of one or more Label Options assigned to the Content", prefix="Content Clasification:")



def build_metadata(program):
    with open('data/categories.json', 'r') as f:
        categories = json.load(f)
    with open('data/post_engagement.json', 'r') as f:
        post_engagement_data = json.load(f)
    engagement_metadata = []
    for post in post_engagement_data:   
        post['labels']= {}
        for category in categories:
            post['labels'][category['name']] = {}
            for sub_category in category['subcategories']:
                response = program(content=post['content'], name=category['name']+ ": "+ sub_category['name'], definition=sub_category['definition'], label_options=str(sub_category['label_options']), label_exclusive=str(sub_category['label_exclusive']))
                classification = response.classification

                try:
                    # Try to parse the string as python literal
                    classification = ast.literal_eval(classification)
                    if sub_category['label_exclusive'] and len(classification) > 1:
                        print("Error: Only one label can be assigned to the content.")
                    if sub_category['label_exclusive'] and len(classification) == 1:
                        classification = classification[0]
                except (SyntaxError, ValueError):
                    # The string could not be parsed as a Python literal
                    print("Error: The string could not be parsed as a Python literal.")
                post['labels'][category['name']][sub_category['name']]= classification
        engagement_metadata.append(post)
    
    return engagement_metadata

def populate_metadata_file(program):
    classified_data = build_metadata(program)

    with open('data/labeled.json', 'w') as f:
        json.dump(classified_data, f, indent=4, sort_keys=True)
    return classified_data

# %%
def is_string_array(string):
    try:
        # Try to parse the string as python literal
        arr = ast.literal_eval(string)
        return True
    except (SyntaxError, ValueError):
        # The string could not be parsed as a Python literal
        return False
        
        
        
class ClasifyCategory(dspy.Module):
    def __init__(self):
        super().__init__()
        self.signature = ClasifyCategorySignature
        self.clasify = dspy.ChainOfThought(self.signature)

        
    def forward(self, content, name, definition, label_options, label_exclusive):
        response = self.clasify(content=content, name=name, definition=definition, label_options=label_options, label_exclusive=label_exclusive)
        
        dspy.Suggest(
            not is_string_array(response.classification),
            "literal_eval error: classification must only contain an array of label strings",
        )
        
        return dspy.Prediction(classification=response.classification)



run_classify = ClasifyCategory().activate_assertions()


#%%

def read_file_data():
    with open('data/labeled.json', 'r') as f:
        labeled = json.load(f)
    with open('data/categories.json', 'r') as f:
        categories = json.load(f)
    with open('data/post_engagement.json', 'r') as f:
        post_engagement_data = json.load(f)
    return {"labeled": labeled, "categories": categories, "post_engagement_data": post_engagement_data}



def generate_random_triplets(num_samples=100):
    data = read_file_data()
    categories = data["categories"]
    post_engagement_data = data["post_engagement_data"]
    array1_length = len(post_engagement_data)
    array2_lengths = [len(category['subcategories']) for category in categories]
    
    # Generate all possible triplets
    all_triplets = []
    for i in range(array1_length):
        for j in range(len(categories)):
            for k in range(array2_lengths[j]):
                all_triplets.append((i, j, k))
    
    # Randomly sample unique triplets
    if num_samples > len(all_triplets):
        raise ValueError("Number of samples requested exceeds the number of unique triplets possible.")
    unique_triplets = random.sample(all_triplets, num_samples)
    
    # returns (post,categories,subcategories)
    return unique_triplets



def gen_training_examples():
    data = read_file_data()
    categories = data["categories"]
    post_engagement_data = data["post_engagement_data"]
    unique_triplets = generate_random_triplets()
    trainset = []
    for triplet in unique_triplets:
        print("example", len(trainset))
        i, j, k = triplet
        post = post_engagement_data[i]
        sub_category = categories[j]['subcategories'][k]

        with dspy.context(lm=gpt4T):
            response = run_classify(content=post['content'], name=categories[j]['name']+ ": "+ sub_category['name'], definition=sub_category['definition'], label_options=str(sub_category['label_options']), label_exclusive=str(sub_category['label_exclusive']))
            classification = response.classification
            trainset.append(dspy.Example({    "content": post['content'],
                                          "name": categories[j]['name'] + ": " + sub_category['name'], 
                                        "definition": sub_category['definition'], 
                                        "label_options": str(sub_category['label_options']), 
                                        "label_exclusive": str(sub_category['label_exclusive']), 
                                        "classification": classification}).with_inputs('content', 'name', 'definition', 'label_options', 'label_exclusive'))
    with open('data/labeled_training.pkl', 'wb') as f:
        pickle.dump(trainset, f)
    return trainset

def validate_answer(example, pred, trace=None):
    return example.classification.lower() == pred.classification.lower()
    
# %%

def train_model(trainset):
    evaluate = Evaluate(devset=trainset, num_threads=1, display_progress=True, display_table=5)
    classify_baseline = ClasifyCategory()
    evaluate(classify_baseline, metric=validate_answer)
    config = dict(max_bootstrapped_demos=3, max_labeled_demos=3, num_candidate_programs=10, num_threads=4)
    teleprompter = BootstrapFewShotWithRandomSearch(metric=validate_answer, **config)
    optimized_program = teleprompter.compile(classify_baseline, trainset=trainset)
    optimized_program.save('./compiled/classify.json')
    return optimized_program


# %%


def evaluate_model(program, trainset):
    # Set up the evaluator, which can be re-used in your code.
    evaluate = Evaluate(devset=trainset, num_threads=1, display_progress=True, display_table=5)
    # Launch evaluation.
    evaluate(program, metric=validate_answer)

# %%

def optimise_program_instruction(program, trainset):
    teleprompter = COPRO(
        metric=validate_answer,
        verbose=True,
    )
    kwargs = dict(num_threads=64, display_progress=True, display_table=0) # Used in Evaluate class in the optimization process
    compiled_prompt_opt = teleprompter.compile(program, trainset=trainset, eval_kwargs=kwargs)
    return compiled_prompt_opt
# %%

def optimise_program_fewshot(program, trainset):
    # Set up the optimizer: we want to "bootstrap" (i.e., self-generate) 8-shot examples of your program's steps.
    # The optimizer will repeat this 10 times (plus some initial attempts) before selecting its best attempt on the devset.
    config = dict(max_bootstrapped_demos=3, max_labeled_demos=3, num_candidate_programs=10, num_threads=4)
    teleprompter = BootstrapFewShotWithRandomSearch(metric=validate_answer, **config)
    optimized_program = teleprompter.compile(program, trainset=trainset)
    optimized_program.save('./compiled/classify.json')
    return optimized_program


#%%
trainset = gen_training_examples()
#%%
evaluate_model(run_classify, trainset)
#%%
instruction = optimise_program_instruction(run_classify, trainset)
#%%
optimised_program = optimise_program_fewshot(run_classify, trainset)
#%%
populate_metadata_file(optimised_program)

# %%
