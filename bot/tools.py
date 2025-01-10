import re
import requests
import os
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


def get_ta_role_for_forum(forum_id: int) -> str:
    """Get TA role ID for a specific forum channel"""
    from .extensions.questions import QUESTION_CENTERS
    for center in QUESTION_CENTERS.values():
        if center["forum_id"] == forum_id:
            return str(center["ta_id"])
    return None


def extract_owner(text: str) -> str:
    """
    Extracts GitHub repository owner from a thread post
    """
    pattern = r"https?://github\.com/([^/]+)/([^/\s]+)"
    match = re.search(pattern, text)
    return match.group(1) if match else None


def extract_repo(text: str) -> str:
    """
    Extracts GitHub repository name from a thread post
    """
    pattern = r"https?://github\.com/([^/]+)/([^/\s]+)"
    match = re.search(pattern, text)
    return match.group(2) if match else None


def fetch_all_code_from_repo(owner: str, repo: str, path: str = "") -> str:
    """
    Fetches all code files from a specified GitHub repository path.
    If the path is empty, starts from the repository's root.

    Args:
        owner: The owner of the GitHub repository.
        repo: The name of the GitHub repository.
        path: The directory path within the repository to fetch files from. Defaults to the root directory.

    Returns:
        str: A concatenated string containing the content of all relevant code files in the repository.

    Example:
        Fetch all code files from the root of the repository:
        ```python
        code = fetch_all_code_from_repo("example-owner", "example-repo")
        ```

        Fetch all code files from a specific directory in the repository:
        ```python
        code = fetch_all_code_from_repo("example-owner", "example-repo", "src")
        ```
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Accept": "application/vnd.github+json",
    }
    headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    contents = response.json()
    logger.info(f"Fetching {len(contents)} files from {url}")
    all_code = ""

    for item in contents:
        if item["type"] == "file" and item["name"].endswith(
            (".py", ".js", ".jsx", "tsx", "ts", "html", "css")
        ):
            file_response = requests.get(item["download_url"])
            all_code += f"\n\n# File: {item['path']}\n" + file_response.text
        elif item["type"] == "dir":
            all_code += fetch_all_code_from_repo(owner, repo, item["path"])

    return all_code
