# import time
# from selenium.webdriver.common.keys import Keys
# from selenium.webdriver.common.by import By
# from selenium import webdriver
import json
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

# NOTE: This function is not used in the current implementation of the bot
# def search_youtube():
#     driver = webdriver.Chrome()

#     try:
#         driver.get("https://www.youtube.com")

#         time.sleep(2)

#         # If there's a "Consent" or "Accept Cookies" button, you might need to click it:
#         # Example (may vary by region):
#         # accept_button = driver.find_element(By.XPATH, "//button[@aria-label='Accept the use of cookies and other data']")
#         # accept_button.click()
#         # time.sleep(2)

#         search_box = driver.find_element(By.NAME, "search_query")

#         search_box.send_keys("python tutorial")
#         search_box.send_keys(Keys.ENTER)

#         # Wait for the results page to load
#         time.sleep(3)

#         video_links = driver.find_elements(By.ID, "video-title")

#         return [link.get_attribute("href") for link in video_links[:5]]

#     finally:
#         driver.quit()


def search_youtube(query, max_results=5):
    """
    Search YouTube and retrieve video links based on a search query.

    Args:
        query (str): The search term or phrase to look up on YouTube
        max_results (int, optional): Maximum number of video links to return. Defaults to 5.

    Returns:
        list[str]: A list of YouTube video URLs matching the search query.
                  Returns an empty list if no results are found or if there's an error.

    Example:
        >>> get_youtube_search_results("python tutorial")
        ['https://www.youtube.com/watch?v=hVzlmOomLRU,'https://www.youtube.com/watch?v=Zq5fmkH0T78']
    """
    # Build search URL (replace spaces with '+')
    url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"

    # Basic desktop User-Agent to reduce chance of blocks or alternate HTML
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers)

    # 1. Extract JSON from 'ytInitialData'
    match = re.search(r"var ytInitialData = ({.*?});", response.text)
    if not match:
        return []

    data = json.loads(match.group(1))

    # 2. Traverse JSON to find videoRenderer -> videoId
    try:
        sections = data["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"]["sectionListRenderer"]["contents"]
    except KeyError:
        return []

    video_links = []
    for section in sections:
        items = section.get("itemSectionRenderer", {}).get("contents", [])
        for item in items:
            video_data = item.get("videoRenderer")
            if video_data and "videoId" in video_data:
                video_id = video_data["videoId"]
                video_links.append(
                    f"https://www.youtube.com/watch?v={video_id}")
                if len(video_links) >= max_results:
                    return video_links[0]

    return video_links


if __name__ == "__main__":
    print(search_youtube("python tutorial"))
