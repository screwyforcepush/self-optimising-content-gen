import requests
from dotenv import load_dotenv
import os

load_dotenv()


llm_config = {
    "config_list": [{"model": "gpt-4-turbo-preview", "api_key": os.getenv('OPENAI_API_KEY')}],
}