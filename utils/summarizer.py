import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini API key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Models (configured via .env, fallback to defaults)
MODEL_FILE = os.getenv("AI_MODEL_FILE", "models/gemini-2.5-flash")         # for individual file summaries
MODEL_PROJECT = os.getenv("AI_MODEL_PROJECT", "models/gemini-pro-latest")  # for full project summary

# Create Gemini model instances
model_file = genai.GenerativeModel(MODEL_FILE)
model_project = genai.GenerativeModel(MODEL_PROJECT)


def summarize_file(path: str, content: str) -> str:
    """
    Summarize a single code or text file using Gemini.
    
    Args:
        path (str): File path (for context)
        content (str): File content to summarize

    Returns:
        str: Summary of the file
    """
    prompt = f"""
You are an expert software developer. 
Summarize the purpose, functionality, and key details of this code file clearly and concisely.

File path: {path}

Content:
{content}
"""
    try:
        response = model_file.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error summarizing {path}: {e}"


def summarize_project(file_summaries: list[str]) -> str:
    """
    Summarize an entire GitHub repository from individual file summaries.
    
    Args:
        file_summaries (list[str]): List of file summary strings

    Returns:
        str: Combined project-level summary
    """
    joined_summaries = "\n\n".join(file_summaries)
    prompt = f"""
You are an AI assistant analyzing a GitHub repository.
Here are summaries of individual files:

{joined_summaries}

Please provide:
1. A high-level overview of the project.
2. Key modules and folder structure.
3. Technologies, frameworks, or libraries used.
4. Main purpose or domain of the project.

Provide a clear and concise summary suitable for documentation.
"""
    try:
        response = model_project.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error generating project summary: {e}"
