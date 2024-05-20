import autogen
from system_messages import system_messages

#%%
agents = [
    {
        "name": "AI_Researcher",
        "description": "AI Expert research and breakthroughs."
    },
    {
        "name": "Extractor",
        "description": "Extracts requested information from text."
    },
    {
        "name": "Socials",
        "description": "Master in all things social media. Creates copy."
    },
    {
        "name": "Critique",
        "description": "Critiques social post content."
    },
    {
        "name": "Idea_Challenge",
        "description": "Challenges the idea and assumptions."
    },
    {
        "name": "Editor",
        "description": "Edits content."
    },
    {
        "name": "img_prompt",
        "description": "Crafts image gen prompts."
    }
    

]

def get_agent(agent_name, llm_config):
    # Find the agent by name
    agent = next((agent for agent in agents if agent['name'] == agent_name), None)
    if agent is None:
        raise ValueError(f"Agent {agent_name} not found")
    
    # Return the agent with the llm_config added
    return autogen.AssistantAgent(name=agent['name'],llm_config=llm_config,system_message=system_messages[agent_name],description=agent['description'])
    
#%%