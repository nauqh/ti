from .tools import fetch_all_code_from_repo, extract_owner, extract_repo
from openai import OpenAI
import requests
import tempfile
from loguru import logger
import json
import time


class DataScienceAssistant:
    def __init__(self, file_paths=None):
        self.client = OpenAI()
        self.posts = {}  # Maps Discord post IDs to OpenAI thread IDs

        self.create_vector_store(file_paths)
        with open("instructions.txt", "r") as file:
            instructions = file.read()
        self.create_assistant(instructions)

    def create_vector_store(self, file_paths):
        """Creates a vector store and uploads files to it."""
        self.vector_store = self.client.beta.vector_stores.create(
            name="DS Course")

        file_streams = [open(path, "rb") for path in file_paths]
        logger.info("Adding files to vector store")
        self.client.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=self.vector_store.id, files=file_streams
        )

        for file_stream in file_streams:
            file_stream.close()

    def create_assistant(self, instructions, model="gpt-4o"):
        """Creates an assistant using the newly created vector store."""
        if not self.vector_store:
            raise ValueError(
                "Vector store must be created before initializing an assistant."
            )

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
                                    "description": "The owner of the GitHub repository.",
                                },
                                "repo": {
                                    "type": "string",
                                    "description": "The name of the GitHub repository.",
                                },
                                "path": {
                                    "type": "string",
                                    "description": "The directory path within the repository to fetch files from. Defaults to the root directory.",
                                },
                            },
                            "required": ["owner", "repo"],
                        },
                    },
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
                                    "description": "The input text to extract the repository owner from.",
                                }
                            },
                            "required": ["text"],
                        },
                    },
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
                                    "description": "The input text to extract the repository name from.",
                                }
                            },
                            "required": ["text"],
                        },
                    },
                },
            ],
            tool_resources={
                "file_search": {"vector_store_ids": [self.vector_store.id]}
            },
        )

    def upload_file(self, file_path):
        """Uploads a file to OpenAI."""
        try:
            if file_path.startswith("http"):
                response = requests.get(file_path, stream=True)
                response.raise_for_status()

                file_name = file_path.split("/")[-1].split("?")[0]

                with tempfile.NamedTemporaryFile(
                    suffix=f"_{file_name}", delete=False
                ) as temp:
                    for chunk in response.iter_content(chunk_size=1024):
                        temp.write(chunk)
                    file_path = temp.name

            with open(file_path, "rb") as file:
                return self.client.files.create(file=file, purpose="assistants")
        except requests.RequestException as e:
            print(f"Error downloading the file from URL: {e}")
            raise
        except OSError as e:
            print(f"Error handling the file: {e}")
            raise
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            raise

    def _prepare_attachments(self, file_paths):
        """Utility method to prepare file attachments."""
        attachments = []
        if file_paths:
            for path in file_paths:
                message_file = self.upload_file(path)
                attachments.append({
                    "file_id": message_file.id,
                    "tools": [
                        {"type": "file_search"},
                        {"type": "code_interpreter"},
                    ],
                })
        return attachments

    def _prepare_content(self, message, image_urls=None):
        """Utility method to prepare message content."""
        content = [{"type": "text", "text": message}]
        if image_urls:
            content.extend(
                {"type": "image_url", "image_url": {"url": url}}
                for url in image_urls
            )
        return content

    def _handle_run(self, thread_id, run):
        """Common method to handle run status and responses."""
        while True:
            run_status = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id, run_id=run.id
            )

            if run_status.status == "completed":
                logger.info("Run completed successfully.")
                messages = list(
                    self.client.beta.threads.messages.list(
                        thread_id=thread_id, run_id=run.id
                    )
                )
                return messages
            elif run_status.status == "requires_action":
                logger.info(
                    "Run requires action. Processing required tool calls...")
                self.call_required_functions(
                    run=run,
                    required_actions=run_status.required_action.submit_tool_outputs.model_dump(),
                    thread_id=thread_id
                )
            elif run_status.status == "failed":
                logger.error(f"Run failed: {run_status.last_error.code}")
                if run_status.last_error.code == 'rate_limit_exceeded':
                    error_msg = "Your GitHub link is too general. Please specify a specific folder in your GitHub repository."
                    self.client.beta.threads.messages.create(
                        thread_id=thread_id,
                        role="assistant",
                        content=error_msg
                    )
                    return error_msg
                raise RuntimeError("The assistant run has failed.")
            else:
                logger.info(
                    "Run is in progress. Waiting for the next update...")
                time.sleep(5)

    def create_thread(self, message, files=None, images=None):
        """Creates an OpenAI thread from a Discord post."""
        attachments = self._prepare_attachments(files)
        content = self._prepare_content(message, images)

        return self.client.beta.threads.create(
            messages=[{
                "role": "user",
                "content": content,
                "attachments": attachments,
            }]
        )

    def add_message(self, role, content, post_id, files=None, images=None):
        """Adds a message to an OpenAI thread."""
        if post_id not in self.posts:
            raise ValueError(
                f"No thread found for post: {post_id}")

        thread_id = self.posts[post_id]
        attachments = self._prepare_attachments(files)
        content = self._prepare_content(content, images)

        self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role=role,
            content=content,
            attachments=attachments
        )

    def call_required_functions(self, run, required_actions: dict, thread_id):
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

                tool_outputs.append(
                    {"tool_call_id": action["id"], "output": output})

            except Exception as e:
                logger.error(f"Error calling function {func_name}: {e}")
                tool_outputs.append(
                    {"tool_call_id": action["id"], "output": f"Error: {e}"}
                )

        if tool_outputs:
            logger.info("Submitting tool outputs back to the assistant...")
            self.client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id, run_id=run.id, tool_outputs=tool_outputs
            )

    def create_and_run_thread(self, thread):
        """Creates a run for the thread and processes it."""
        run = self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistant.id
        )
        return self._handle_run(thread.id, run)

    def extract_response(self, messages):
        """Processes and extracts the assistant's response."""
        if not isinstance(messages, list):
            return messages, None
        message_content = messages[0].content[0].text
        annotations = message_content.annotations
        citations = set()

        for annotation in annotations:
            message_content.value = message_content.value.replace(
                annotation.text, "")
            if file_citation := getattr(annotation, "file_citation", None):
                citations.add(
                    self.client.files.retrieve(file_citation.file_id).filename
                )

        return message_content.value, list(citations)

    def continue_thread(self, message, post_id, files=None, images=None):
        """Continues conversation in an OpenAI thread."""
        self.add_message(
            role="user",
            content=message,
            post_id=post_id,
            files=files,
            images=images
        )

        thread_id = self.posts[post_id]
        run = self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=self.assistant.id
        )

        messages = self._handle_run(thread_id, run)
        return self.extract_response(messages)


if __name__ == "__main__":
    # Initialize the assistant with documentation files
    assistant = DataScienceAssistant([
        "docs/instructions.pdf",
        "docs/user_manual.pdf"
    ])

    # Create a new thread for a post
    openai_thread = assistant.create_thread(
        message="Can you help me understand how to use pandas for data analysis?",
        images=[
            "https://jalammar.github.io/images/pandas-intro/0%20excel-to-pandas.png"],
    )

    # Run the initial conversation
    messages = assistant.create_and_run_thread(openai_thread)
    response, citations = assistant.extract_response(messages)
    print(response)
    if citations:
        print("Citations:", citations)

    # Continue the conversation with a follow-up question
    post_id = 123456789  # Example Discord post ID
    assistant.posts[post_id] = openai_thread.id

    follow_up_response, follow_up_citations = assistant.continue_thread(
        "How can I handle missing values in my dataset?",
        post_id
    )
    print(follow_up_response)
    if follow_up_citations:
        print("Citations:", follow_up_citations)
