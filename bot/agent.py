import re
from openai import OpenAI
import requests
import tempfile
from loguru import logger
from dotenv import load_dotenv
import json
import time
import os

load_dotenv()


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
        if item['type'] == 'file' and item['name'].endswith(('.py', '.js', '.jsx', 'tsx', 'ts', '.html', '.css')):
            file_response = requests.get(item['download_url'])
            all_code += f"\n\n# File: {item['path']}\n" + \
                file_response.text
        elif item['type'] == 'dir':
            all_code += fetch_all_code_from_repo(owner, repo, item['path'])

    return all_code


class DataScienceAssistant:
    def __init__(self):
        self.client = OpenAI()
        self.vector_store = None
        self.assistant = None
        self.thread = None

    def create_vector_store(self, file_paths):
        """Creates a vector store and uploads files to it."""
        self.vector_store = self.client.beta.vector_stores.create(
            name='DS Course'
        )

        file_streams = [open(path, "rb") for path in file_paths]
        logger.info("Adding files to vector store")
        self.client.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=self.vector_store.id,
            files=file_streams
        )

        for file_stream in file_streams:
            file_stream.close()

    def create_assistant(self, instructions, model="gpt-4o"):
        """Creates an assistant using the newly created vector store."""
        if not self.vector_store:
            raise ValueError(
                "Vector store must be created before initializing an assistant.")

        self.assistant = self.client.beta.assistants.create(
            name="Data Science Teaching Assistant",
            instructions=instructions,
            model=model,
            tools=[
                {"type": "file_search"},
                {"type": "code_interpreter"},
                {
                    "type": "function",
                    "function": {
                        "name": "fetch_all_code_from_repo",
                        "description": "Fetches all code files from a GitHub repository.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "owner": {
                                    "type": "string",
                                    "description": "The owner of the GitHub repository."
                                },
                                "repo": {
                                    "type": "string",
                                    "description": "The name of the GitHub repository."
                                },
                                "path": {
                                    "type": "string",
                                    "description": "The directory path within the repository to fetch files from. Defaults to the root directory."
                                }
                            },
                            "required": ["owner", "repo"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "extract_owner",
                        "description": "Extracts GitHub repository owner from a thread post.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "text": {
                                    "type": "string",
                                    "description": "The input text to extract the repository owner from."
                                }
                            },
                            "required": ["text"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "extract_repo",
                        "description": "Extracts GitHub repository name from a thread post.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "text": {
                                    "type": "string",
                                    "description": "The input text to extract the repository name from."
                                }
                            },
                            "required": ["text"]
                        }
                    }
                }
            ],
            tool_resources={
                "file_search": {"vector_store_ids": [self.vector_store.id]}
            }
        )

    def upload_file(self, file_path):
        """Uploads a file to OpenAI."""
        try:
            if file_path.startswith("http"):
                response = requests.get(file_path, stream=True)
                response.raise_for_status()

                file_name = file_path.split("/")[-1].split("?")[0]

                with tempfile.NamedTemporaryFile(suffix=f"_{file_name}", delete=False) as temp:
                    for chunk in response.iter_content(chunk_size=1024):
                        temp.write(chunk)
                    file_path = temp.name

            with open(file_path, "rb") as file:
                return self.client.files.create(
                    file=file, purpose="assistants")
        except requests.RequestException as e:
            print(f"Error downloading the file from URL: {e}")
            raise
        except OSError as e:
            print(f"Error handling the file: {e}")
            raise
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            raise

    def create_thread(self, user_message, file_paths=None, image_urls=None):
        """Creates a thread and optionally attaches a file to the user's message."""
        attachments = []
        if file_paths:
            for path in file_paths:
                message_file = self.upload_file(path)
                attachments.append(
                    {
                        "file_id": message_file.id,
                        "tools": [{"type": "file_search"}, {"type": "code_interpreter"}]
                    }
                )

        content = [{"type": "text", "text": user_message}]

        if image_urls:
            for url in image_urls:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": url}
                })

        self.thread = self.client.beta.threads.create(
            messages=[
                {
                    "role": "user",
                    "content": content,
                    "attachments": attachments,
                }
            ]
        )
        return self.thread

    def call_required_functions(self, run, required_actions: dict):
        """
        Handles required tool calls and submits outputs back to the assistant.
        """
        tool_outputs = []

        for action in required_actions.get("tool_calls", []):
            func_name = action["function"]["name"]
            args = json.loads(action["function"]["arguments"])

            logger.info(
                f"Calling function: {func_name} with arguments: {args}")

            try:
                if func_name == "fetch_all_code_from_repo":
                    owner = args["owner"]
                    repo = args["repo"]
                    path = args.get("path", "")
                    output = fetch_all_code_from_repo(owner, repo, path)
                elif func_name == "extract_owner":
                    text = args["text"]
                    output = extract_owner(text)
                elif func_name == "extract_repo":
                    text = args["text"]
                    output = extract_repo(text)
                else:
                    raise ValueError(f"Unknown function: {func_name}")

                tool_outputs.append({
                    "tool_call_id": action["id"],
                    "output": output
                })

            except Exception as e:
                logger.error(f"Error calling function {func_name}: {e}")
                tool_outputs.append({
                    "tool_call_id": action["id"],
                    "output": f"Error: {e}"
                })

        if tool_outputs:
            logger.info("Submitting tool outputs back to the assistant...")
            self.client.beta.threads.runs.submit_tool_outputs(
                thread_id=self.thread.id,
                run_id=run.id,
                tool_outputs=tool_outputs
            )

    def create_and_run_thread(self, thread):
        """
        Creates a run for the thread, processes required actions, and retrieves the response.
        """
        run = self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistant.id
        )

        while True:
            run_status = self.client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )

            logger.info(f"Run status: {run_status.status}")

            if run_status.status == "completed":
                logger.info("Run completed successfully.")
                messages = self.client.beta.threads.messages.list(
                    thread_id=thread.id,
                    run_id=run.id
                )
                return list(messages)
            elif run_status.status == "requires_action":
                logger.info(
                    "Run requires action. Processing required tool calls...")
                self.call_required_functions(
                    run=run,
                    required_actions=run_status.required_action.submit_tool_outputs.model_dump()
                )
            elif run_status.status == "failed":
                logger.error("Run failed.")
                raise RuntimeError("The assistant run has failed.")
            else:
                logger.info(
                    "Run is in progress. Waiting for the next update...")
                time.sleep(5)

    def extract_response(self, messages):
        """Processes and extracts the assistant's response."""
        message_content = messages[0].content[0].text
        annotations = message_content.annotations
        citations = set()

        for annotation in annotations:
            message_content.value = message_content.value.replace(
                annotation.text, "")
            if file_citation := getattr(annotation, "file_citation", None):
                citations.add(self.client.files.retrieve(
                    file_citation.file_id).filename)

        return message_content.value, list(citations)

    def add_message_to_thread(self, role, content):
        """Adds a new message to an existing thread."""
        if not self.thread:
            raise ValueError("Thread must be created before adding messages.")

        self.client.beta.threads.messages.create(
            thread_id=self.thread.id, role=role, content=content
        )

    def continue_conversation(self, new_message):
        """Adds a new user message to the thread, creates a run, and retrieves the response."""
        self.add_message_to_thread(role="user", content=new_message)

        run = self.client.beta.threads.runs.create_and_poll(
            thread_id=self.thread.id,
            assistant_id=self.assistant.id
        )

        messages = list(self.client.beta.threads.messages.list(
            thread_id=self.thread.id,
            run_id=run.id
        ))

        return self.extract_response(messages)


if __name__ == "__main__":
    bot = DataScienceAssistant()
    with open("instructions.txt", "r") as file:
        instructions = file.read()
    bot.create_vector_store(["docs/instructions.pdf", "docs/user_manual.pdf"])
    bot.create_assistant(
        instructions=instructions
    )
    thread = bot.create_thread(
        "What does my code do? https://github.com/nauqh/csautograde")
    messages = bot.create_and_run_thread(thread)
    response, citations = bot.extract_response(messages)
    print(response)
    if citations:
        logger.info(f"Referenced files: {', '.join(citations)}")

    # Continuing the conversation
    # new_message = "Làm sao để reschedule mentor session?"
    # print("\nNew Message:", new_message)
    # response, citations = bot.continue_conversation(new_message)
    # print(response)
    # if citations:
    #     logger.info(f"Referenced files: {', '.join(citations)}")
