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
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

load_dotenv()


def get_ta_role_for_forum(forum_id: int) -> str:
    """Get TA role ID for a specific forum channel"""
    # from .extensions.questions import QUESTION_CENTERS
    QUESTION_CENTERS = {
        "DS": {"forum_id": 1081063200377806899, "ta_id": 1194665960376901773, "staff_channel": 1237424754739253279},
        "FSW": {"forum_id": 1077118780523679787, "ta_id": 912553106124972083},
        "CS50": {"forum_id": 1318582941667819683, "ta_id": 1233260164233297942},
        # "MOENASH": {"forum_id": 1195747557335375907, "ta_id": 947046253609508945},
    }
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


def search_db(query: str, k: int = 5) -> str:
    """
    Search the Chroma database for documents related to the query.

    Args:
        query (str): The search query to find relevant documents
        k (int, optional): Maximum number of documents to return. Defaults to 5.

    Returns:
        str: A formatted string containing the most relevant document excerpts

    Example:
        >>> search_db("What are the rules for Monopoly?")
        'Document 1: From data/monopoly.pdf, page 2: In Monopoly, players start with $1500...'
    """
    try:
        # Initialize the embedding function
        embedding_function = OpenAIEmbeddings(model="text-embedding-3-large")

        # Initialize Chroma DB
        CHROMA_PATH = "chroma"
        if not os.path.exists(CHROMA_PATH):
            logger.error(f"Chroma DB path {CHROMA_PATH} does not exist")
            return "Error: The database has not been initialized. Please contact an administrator."

        db = Chroma(persist_directory=CHROMA_PATH,
                    embedding_function=embedding_function)

        # Search the DB
        results = db.similarity_search_with_score(query, k=k)

        if not results:
            return "No relevant information found in the database."

        # Format the results
        formatted_results = []
        for i, (doc, score) in enumerate(results, 1):
            source = doc.metadata.get("source", "Unknown source")
            page = doc.metadata.get("page", "Unknown page")
            content = doc.page_content.strip()

            formatted_result = f"Document {i}: From {source}"
            if page != "Unknown page":
                formatted_result += f", page {page}"
            formatted_result += f" (relevance: {score:.2f}):\n{content}\n"

            formatted_results.append(formatted_result)

        return "\n\n".join(formatted_results)

    except Exception as e:
        logger.error(f"Error searching database: {str(e)}")
        return f"Error searching database: {str(e)}"


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
