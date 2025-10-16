import os
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
import textwrap
import openai  # pip install openai>=1.0.0

load_dotenv()

# Gemini configuration
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_FILE = os.getenv("AI_MODEL_FILE", "models/gemini-2.5-flash")
MODEL_PROJECT = os.getenv("AI_MODEL_PROJECT", "models/gemini-pro-latest")
model_file = genai.GenerativeModel(MODEL_FILE)
model_project = genai.GenerativeModel(MODEL_PROJECT)

# OpenAI fallback configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY
OPENAI_MODEL = "gpt-3.5-turbo"

CHUNK_SIZE = 4000
BATCH_SIZE = 5


def chunk_content(content: str, chunk_size: int = CHUNK_SIZE):
    return textwrap.wrap(content, width=chunk_size, break_long_words=False, replace_whitespace=False)


def summarize_with_openai(prompt: str) -> str:
    """Fallback to OpenAI API using modern v1.0+ interface"""
    try:
        response = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"OpenAI fallback error: {e}"


def summarize_file(path: str, content: str) -> str:
    chunks = chunk_content(content)
    summaries = []

    for i, chunk in enumerate(chunks, start=1):
        prompt = f"""
You are an expert software engineer and architect.
Analyze this code chunk and provide a detailed, structured summary:

File: {path} (chunk {i}/{len(chunks)})

Instructions:
- Purpose of the code
- Main classes/functions and responsibilities
- Relationships between classes/functions
- Design patterns used
- Notable logic
- Frameworks/libraries used

Content:
{chunk}
"""
        try:
            response = model_file.generate_content(prompt)
            summaries.append(response.text.strip())
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e):
                # Fallback to OpenAI
                summaries.append(summarize_with_openai(prompt))
            else:
                summaries.append(f"Error summarizing chunk {i} of {path}: {e}")

    return "\n\n".join(summaries)


def summarize_project(file_summaries: list[str], project_name: str = "Project") -> str:
    markdown_content = f"# {project_name} - Comprehensive Summary\n\n"
    markdown_content += f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    for i in range(0, len(file_summaries), BATCH_SIZE):
        batch = file_summaries[i:i + BATCH_SIZE]
        joined_summaries = "\n\n".join(batch)

        prompt = f"""
You are an expert software architect analyzing a GitHub repository.
Here are summaries of several files:

{joined_summaries}

Please produce a detailed, structured project-level summary including:
1. High-level architecture and main modules
2. Module/folder structure
3. Relationships between classes/functions
4. Design patterns
5. Technologies, frameworks, libraries used
6. Suggested diagrams (UML class/sequence style)
7. Any notable logic or dependencies

Format output in Markdown with headings, bullet points, and code blocks where appropriate.
"""
        try:
            response = model_project.generate_content(prompt)
            markdown_content += response.text.strip() + "\n\n"
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e):
                # Fallback to OpenAI
                markdown_content += summarize_with_openai(prompt) + "\n\n"
            else:
                markdown_content += f"Error summarizing batch {i // BATCH_SIZE + 1}: {e}\n\n"

    report_filename = f"{project_name.replace(' ', '_')}_summary.md"
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    return report_filename
