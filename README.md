# Self-Optimising Content Generation

## Overview

This repository contains various Python scripts and JSON files related to AI research and content generation. The purpose of this repository is to automate the generation and posting of content based on AI research.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/screwyforcepush/self-optimising-content-gen.git
   cd self-optimising-content-gen
   ```

2. Create a virtual environment and activate it:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Main Scripts

- `generation/workflow.py`: This script handles the workflow for generating and posting content based on AI research.
- `analysis/getdata.py`: This script is used for data analysis and extraction.

### Running the Workflow

To run the content generation workflow, execute the following command:
```bash
python generation/workflow.py
```

### Running Data Analysis

To run the data analysis script, execute the following command:
```bash
python analysis/getdata.py
```

## Dependencies

The project dependencies are listed in the `requirements.txt` file. They include:
- openai
- dspy-ai
- langchain-core
- langchain_openai
- arxiv
- python-dotenv
- emoji

## Environment Variables

The project uses environment variables for configuration. You need to set up a `.env` file in the root directory of the project with the following variables:

```
OPENAI_API_KEY=your_openai_api_key
LK_OWNER=your_linkedin_owner_urn
LK_TOKEN=your_linkedin_access_token
```

These variables are used in various scripts, such as `generation/tools.py`, to configure API keys and other settings.
