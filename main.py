import re
import os
import asyncio
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

# Import your helpers
from utils.github_fetcher import fetch_files
from utils.summarizer import summarize_file, summarize_project

load_dotenv()

app = FastAPI(title="AI GitHub Analyzer (Async Streaming & Classic)")

# Regex for GitHub repo URLs
GITHUB_REGEX = r"^https://github\.com/([\w\-]+)/([\w\-]+)(/)?$"

# Text file extensions to process
TEXT_EXTENSIONS = [".py", ".js", ".ts", ".json", ".md", ".yaml", ".yml", ".html", ".css"]


@app.get("/")
async def home():
    return {"message": "Welcome to the AI GitHub Analyzer"}


# ----------------------------
# Classic endpoint (JSON)
# ----------------------------
@app.get("/analyze_repo")
async def analyze_repo(url: str):
    # Validate GitHub URL
    match = re.match(GITHUB_REGEX, url)
    if not match:
        raise HTTPException(
            status_code=400,
            detail="Invalid GitHub URL. Must be of the form https://github.com/username/projectname"
        )

    owner, repo = match.group(1), match.group(2)

    # Fetch all files asynchronously
    try:
        files = await asyncio.to_thread(fetch_files, owner, repo)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching files: {e}")

    if not files:
        raise HTTPException(status_code=404, detail="No readable files found.")

    # Summarize files asynchronously using threads
    async def summarize_path(path, content):
        return f"{path}:\n{await asyncio.to_thread(summarize_file, path, content)}"

    tasks = [summarize_path(p, c) for p, c in files.items() if any(p.endswith(ext) for ext in TEXT_EXTENSIONS)]
    summaries = await asyncio.gather(*tasks)

    # Summarize the whole project
    try:
        project_summary = await asyncio.to_thread(summarize_project, summaries)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating project summary: {e}")

    return {
        "repo": f"{owner}/{repo}",
        "file_count": len(files),
        "project_summary": project_summary
    }


# ----------------------------
# Streaming endpoint (SSE)
# ----------------------------
async def summarize_files_stream(url: str):
    # Validate GitHub URL
    match = re.match(GITHUB_REGEX, url)
    if not match:
        yield f"data: {json.dumps({'error': 'Invalid GitHub URL'})}\n\n"
        return

    owner, repo = match.group(1), match.group(2)

    # Fetch files
    try:
        files = await asyncio.to_thread(fetch_files, owner, repo)
    except Exception as e:
        yield f"data: {json.dumps({'error': f'Error fetching files: {e}'})}\n\n"
        return

    if not files:
        yield f"data: {json.dumps({'error': 'No readable files found.'})}\n\n"
        return

    file_summaries = []

    for idx, (path, content) in enumerate(files.items(), start=1):
        if not any(path.endswith(ext) for ext in TEXT_EXTENSIONS):
            yield f"data: {json.dumps({'skip': path})}\n\n"
            continue

        yield f"data: {json.dumps({'status': f'Summarizing {path} ({idx}/{len(files)})...'})}\n\n"
        await asyncio.sleep(0.1)  # allow client to process the message

        summary = await asyncio.to_thread(summarize_file, path, content)
        file_summaries.append(f"### {path}\n{summary}\n")

        # Stream partial summary for this file
        yield f"data: {json.dumps({'file_summary': {path: summary}})}\n\n"

    # Project-level summary
    yield f"data: {json.dumps({'status': 'Generating full project summary...'})}\n\n"
    await asyncio.sleep(0.1)

    try:
        report_file = await asyncio.to_thread(summarize_project, file_summaries)
        yield f"data: {json.dumps({'project_summary_file': report_file})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': f'Error generating project summary: {e}'})}\n\n"

    yield f"data: {json.dumps({'status': 'Completed'})}\n\n"


@app.get("/analyze_repo_stream")
async def analyze_repo_stream(url: str):
    """
    Stream GitHub repo analysis progress using Server-Sent Events (SSE)
    """
    return StreamingResponse(summarize_files_stream(url), media_type="text/event-stream")
