from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
import re
import os

from utils.github_fetcher import fetch_files
from utils.summarizer import summarize_file, summarize_project

# Load .env
load_dotenv()

app = FastAPI(title="AI GitHub Analyzer")

# Regex to match GitHub repo URLs like https://github.com/username/projectname
GITHUB_REGEX = r"^https://github\.com/([\w\-]+)/([\w\-]+)(/)?$"


@app.get("/")
def home():
    return {"message": "Welcome to the AI GitHub Analyzer"}


@app.get("/analyze_repo")
def analyze_repo(url: str):
    """
    Analyze a GitHub repository and summarize all files.

    Query param:
    - url: Full GitHub repo URL (e.g., https://github.com/username/projectname)
    """
    # Validate GitHub URL
    match = re.match(GITHUB_REGEX, url)
    if not match:
        raise HTTPException(
            status_code=400,
            detail="Invalid GitHub URL. Must be of the form https://github.com/username/projectname"
        )

    owner, repo = match.group(1), match.group(2)

    # Fetch all files from the repo
    try:
        files = fetch_files(owner, repo)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching files: {e}")

    if not files:
        raise HTTPException(status_code=404, detail="No readable files found.")

    # Summarize each file
    summaries = []
    for path, content in files.items():
        summaries.append(f"{path}:\n{summarize_file(path, content)}")

    # Summarize the whole project
    try:
        project_summary = summarize_project(summaries)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating project summary: {e}")

    return {
        "repo": f"{owner}/{repo}",
        "file_count": len(files),
        "project_summary": project_summary
    }
