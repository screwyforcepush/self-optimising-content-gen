from typing_extensions import Annotated
import os
import autogen
import arxiv
import json
from typing import List
import emoji
import requests
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
       
script_dir = os.path.dirname(os.path.abspath(__file__))
posted_path = os.path.join(script_dir, 'data', 'posted.json')
consumed_path = os.path.join(script_dir, 'data', 'consumed_research.json')
unposted_path = os.path.join(script_dir, 'data', 'unposted.json')

def fetch_latest_ai_papers()-> List[arxiv.Result]:
    # Load consumed titles from JSON
    with open(consumed_path, 'r') as file:
        consumed_data = json.load(file)
            # Convert each dictionary in data to an arxiv.Result object   
    client = arxiv.Client()

    # Define the search query and parameters
    search = arxiv.Search(
        query="cat:cs.AI",  # Search in the Artificial Intelligence category
        max_results=20,     # Limit to the 10 most recent results
        sort_by=arxiv.SortCriterion.SubmittedDate,  # Sort by submission date
        sort_order=arxiv.SortOrder.Descending       # Get the latest papers first
    )

    # Initialize a list to hold non-consumed papers
    non_consumed_papers = []
    
    results = client.results(search)


    # Fetch the papers and filter out consumed ones
    for result in results:
        if result.entry_id not in consumed_data:
            print(f"Title: {result.title}")
            print(f"URL: {result.entry_id}")
            print("--------------------------------------------------")
            non_consumed_papers.append(result)

    return non_consumed_papers

def mark_paper_as_consumed(entry_id: str):    
    with open(consumed_path, 'r') as file:
        consumed_data = json.load(file)
    
   
    consumed_data.append(entry_id)
    
    with open(consumed_path, 'w') as file:
        json.dump(consumed_data, file, indent=4)


def custom_serializer(obj):
    if isinstance(obj, str) and any(char in emoji.UNICODE_EMOJI for char in obj):
        return obj
    return str(obj)

def save_workflow_output(post, unposted_arr):
    with open(posted_path, 'r') as file:
        post_data = json.load(file)
    post_data.append(post)
    with open(posted_path, 'w') as file:
        json.dump(post_data, file, indent=4, default=custom_serializer, sort_keys=True, ensure_ascii=False)
    
        
    with open(unposted_path, 'r') as file:
        unposted_data = json.load(file)
    for item in unposted_arr:
        unposted_data.append(item)
    with open(unposted_path, 'w') as file:
        json.dump(unposted_data, file, indent=4, default=custom_serializer, sort_keys=True, ensure_ascii=False)


# Set up the OpenAI API key from environment variable
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("API key not found. Set the OPENAI_API_KEY environment variable.")

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def gen_img_save(prompt,title):
    # Define the prompt for the image generation

    # Generate the image using DALL-E 3
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="hd",
        n=1
    )

    # Check if 'data' is not empty and contains at least one image
    if response.data and isinstance(response.data, list):
        image_url = response.data[0].url  # Access the URL of the first image
    else:
        raise ValueError("No data found in the API response or 'data' is not a list")


    # Download the image using the URL
    image_data = requests.get(image_url).content
    # Remove spaces from the title and limit its length to 100 characters
    title = title.replace(' ', '_')[:100]
    # Save the image to a file
    path = os.path.join(script_dir, 'images', f'{title}.png')
    with open(path, 'wb') as file:
        file.write(image_data)

    print(f"Image has been saved as '{title}.png'")
    return path


class Tool:
    def __init__(self, name, description, function):
        self.name = name
        self.description = description
        self.function = function
        
            
ALL_TOOLS = {
    "fetch_latest_ai_papers": Tool("fetch_latest_ai_papers", "Pull latest AI papers from arxiv.org.", fetch_latest_ai_papers),
}

def register_tool(executor: autogen.UserProxyAgent, assistant: autogen.AssistantAgent, tool_obj: Tool):
    # Register the tool signature with the assistant agent.
    assistant.register_for_llm(name=tool_obj.name, description=tool_obj.description)(tool_obj.function)

    # Register the tool function with the user proxy agent.
    executor.register_for_execution(name=tool_obj.name)(tool_obj.function)

