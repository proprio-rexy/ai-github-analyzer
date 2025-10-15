import requests
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Optional, needed for private repos
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

GITHUB_API_URL = "https://api.github.com/repos/{owner}/{repo}/contents/{path}"


def fetch_files(owner: str, repo: str, path="") -> dict:
    """
    Fetch all files in a GitHub repository recursively.
    Returns a dict: {file_path: content}
    """
    files = {}
    url = GITHUB_API_URL.format(owner=owner, repo=repo, path=path)
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 404:
        raise Exception("404: Repo not found or access denied")

    if response.status_code != 200:
        raise Exception(f"{response.status_code}: {response.text}")

    data = response.json()

    # If it's a single file
    if isinstance(data, dict) and data.get("type") == "file":
        files[data["path"]] = requests.get(data["download_url"], headers=HEADERS).text
        return files

    # If it's a directory (list of items)
    for item in data:
        if item["type"] == "file":
            files[item["path"]] = requests.get(item["download_url"], headers=HEADERS).text
        elif item["type"] == "dir":
            # Recursively fetch subdirectory
            sub_files = fetch_files(owner, repo, item["path"])
            files.update(sub_files)

    return files
