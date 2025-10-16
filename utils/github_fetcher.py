import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
GITHUB_API_URL = "https://api.github.com/repos/{owner}/{repo}/contents/{path}"


async def fetch_file(client, url):
    """Fetch individual file content asynchronously"""
    try:
        resp = await client.get(url, headers=HEADERS)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"[WARN] Failed to fetch {url}: {e}")
        return None


async def fetch_dir(client, owner: str, repo: str, path=""):
    """Recursively fetch all files in a directory"""
    url = GITHUB_API_URL.format(owner=owner, repo=repo, path=path)
    resp = await client.get(url, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()

    files = {}

    # If a single file
    if isinstance(data, dict) and data.get("type") == "file":
        content = await fetch_file(client, data["download_url"])
        if content:
            files[data["path"]] = content
        return files

    # If a directory
    tasks = []
    for item in data:
        if item["type"] == "file":
            # Skip large/binary files
            if item["name"].lower().endswith(
                (".png", ".jpg", ".jpeg", ".gif", ".ico", ".exe", ".dll", ".zip", ".tar")
            ):
                print(f"[SKIP] Skipping binary file {item['path']}")
                continue
            tasks.append(
                fetch_file(client, item["download_url"])
            )
            files[item["path"]] = None  # placeholder for later assignment
        elif item["type"] == "dir":
            # Recursively fetch subdirectory
            sub_files = await fetch_dir(client, owner, repo, item["path"])
            files.update(sub_files)

    # Wait for all file fetch tasks
    if tasks:
        results = await asyncio.gather(*tasks)
        # Assign results to correct paths
        i = 0
        for key in files:
            if files[key] is None:
                files[key] = results[i]
                i += 1

    return files


def fetch_files(owner: str, repo: str):
    """
    Entry point to fetch all files from a GitHub repo.
    This function runs the async fetcher synchronously.
    """
    async def runner():
        async with httpx.AsyncClient() as client:
            return await fetch_dir(client, owner, repo)

    print(f"[INFO] Fetching files for {owner}/{repo}...")
    files = asyncio.run(runner())
    print(f"[INFO] Fetched {len(files)} files.")
    return files
