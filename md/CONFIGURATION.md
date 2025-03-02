# T.i. - The Informationist: Configuration Documentation

This document provides detailed technical configuration information for the T.i. chatbot system. It expands on the implementation details from the main documentation and provides specific configuration guidelines.

## Environment Configuration

### Required Environment Variables

The application requires the following environment variables to be properly configured:

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | API key for OpenAI services | `sk-abcdef123456...` |
| `DISCORD_TOKEN` | Authentication token for the Discord bot | `MTAwMDAwMDAwMDAwMDAwMDAw...` |
| `GITHUB_TOKEN` | GitHub personal access token for repository access | `ghp_abcdefghijklmno...` |
| `GUILD_ID` | Discord server (guild) ID for bot initialization | `1081063200377806899` |

**Security Note**: Store these environment variables in a `.env` file which should be added to `.gitignore` to prevent exposing sensitive information.

## Vector Store Configuration

### ChromaDB Setup

The application uses ChromaDB as its vector database with the following configuration parameters:

```python
self.vector_store = Chroma(
    persist_directory=self.CHROMA_PATH,  # "chroma/" directory
    embedding_function=embedding_function  # OpenAI embeddings
)
```

### Document Processing Parameters

Documents are processed with the following parameters:

| Parameter | Value | Description |
|-----------|-------|-------------|
| Chunk Size | 800 characters | Size of each document chunk |
| Chunk Overlap | 80 characters | Overlap between consecutive chunks |
| Embedding Model | `text-embedding-3-large` | OpenAI model used for generating embeddings |
| Storage Location | `chroma/` directory | Local persistent storage for the vector database |

### Document Loading Pipeline

The system processes documents through the following pipeline:

1. **File Collection**:
   - PDF files are collected and processed using `PyPDFDirectoryLoader`
   - Non-PDF text files are read directly

2. **Document Splitting**:
   ```python
   text_splitter = RecursiveCharacterTextSplitter(
       chunk_size=800,
       chunk_overlap=80,
       length_function=len,
       is_separator_regex=False,
   )
   chunks = text_splitter.split_documents(documents)
   ```

3. **ID Generation**:
   - Unique IDs are generated for each chunk using `_calculate_chunk_ids`
   - Format: `{source}:{page}:{chunk_index}`

4. **Vector Store Addition**:
   - Chunks with IDs are added to the ChromaDB store
   - Storage is persisted to disk in the `chroma/` directory

## Discord Bot Configuration

### Core Configuration

The Discord bot is implemented using the Hikari and Lightbulb libraries with the following configuration:

```python
# Bot initialization with all intents
bot = lightbulb.BotApp(
    token=os.environ["DISCORD_TOKEN"],
    prefix="!",
    intents=hikari.Intents.ALL,
    help_class=None,
    banner=None,
)
```

### Extension Architecture

The bot uses an extension-based architecture with the following plugins:

1. **Questions Plugin** (`questions.py`):
   - Handles forum monitoring and thread responses
   - Maps specific forum IDs to TA roles:
     ```python
     QUESTION_CENTERS = {
         "DS": {"forum_id": 1081063200377806899, "ta_id": 1194665960376901773, "staff_channel": 1237424754739253279},
         "FSW": {"forum_id": 1326478786274922568, "ta_id": 912553106124972083},
         "CS50": {"forum_id": 1343930405702865037, "ta_id": 1233260164233297942},
     }
     ```

2. **Submission Plugin** (`submission.py`):
   - Handles assignment submission review

### Event Handler Configuration

The bot is configured with the following event handlers:

| Event | Handler | Purpose |
|-------|---------|---------|
| `hikari.GuildThreadCreateEvent` | `on_thread_create` | Handles new forum threads and initializes AI responses |
| `hikari.GuildMessageCreateEvent` | `on_message_create` | Processes new messages in existing threads |
| `hikari.ReactionAddEvent` | `on_reaction_add` | Manages feedback collection through reactions |
| `hikari.StartingEvent` | `on_starting` | Initializes components like the Assistant object |

## OpenAI Assistant Configuration

### Assistant Creation

The OpenAI assistant is created with the following configuration:

```python
self.assistant = self.client.beta.assistants.create(
    name="Data Science Teaching Assistant",
    instructions=instructions,  # Loaded from instructions.txt
    model=model,  # Default: "gpt-4o"
    tools=tool_schemas["tools"],  # Loaded from tool_schemas.json
)
```

### Tool Schema Configuration

Tool schemas are defined in `bot/schemas/tool_schemas.json` with the following structure:

```json
{
  "tools": [
    {
      "type": "code_interpreter"
    },
    {
      "type": "function",
      "function": {
        "name": "function_name",
        "description": "Function description",
        "parameters": {
          "type": "object",
          "properties": {
            "param1": {
              "type": "string",
              "description": "Parameter description"
            }
          },
          "required": ["param1"]
        }
      }
    }
  ]
}
```

### Available Assistant Tools

The assistant is configured with the following tools:

1. **Code Interpreter Tool**:
   - Enables code execution for demonstrations
   - Built-in OpenAI capability

2. **GitHub Repository Tool** (`fetch_all_code_from_repo`):
   - Purpose: Fetches code from GitHub repositories for analysis
   - Parameters:
     - `owner`: The GitHub repository owner
     - `repo`: The repository name
     - `path`: Optional path within the repository (defaults to root)
   - Implementation: Makes GitHub API requests using the `GITHUB_TOKEN`

3. **Knowledge Base Search Tool** (`search_db`):
   - Purpose: Queries the ChromaDB vector database
   - Parameters:
     - `query`: The search query to find relevant documents
     - `k`: Maximum number of documents to return (default: 5)
   - Implementation: Uses ChromaDB's similarity search capabilities

4. **GitHub URL Parsing Tools**:
   - `extract_owner`: Extracts repository owner from GitHub URLs
   - `extract_repo`: Extracts repository name from GitHub URLs
   - Implementation: Uses regex pattern matching

5. **TA Role Identification Tool** (`get_ta_role_for_forum`):
   - Purpose: Maps forum IDs to TA role IDs
   - Parameters: 
     - `forum_id`: The Discord forum channel ID
   - Implementation: Lookup in the `QUESTION_CENTERS` dictionary

6. **YouTube Search Tool** (`search_youtube`):
   - Purpose: Finds educational videos on YouTube
   - Parameters:
     - `query`: The search query for YouTube
   - Implementation: Uses YouTube API or web scraping

## Message and Thread Management

### Thread Mapping System

Discord threads are mapped to OpenAI threads using a dictionary:

```python
self.posts = {}  # Maps Discord post IDs to OpenAI thread IDs
```

This enables:
- Persistence of conversation context across multiple messages
- Multi-turn conversations with history
- Proper handling of follow-up questions

### Attachment Handling Configuration

Attachments from Discord messages are processed as follows:

1. **Image Attachments**:
   - Identified by MIME type starting with "image"
   - Included in OpenAI messages using the `image_url` content type

2. **File Attachments**:
   - Any non-image attachments
   - Downloaded and uploaded to OpenAI
   - Made accessible to the code interpreter

### Run Processing Configuration

The system processes OpenAI assistant runs with the following configuration:

1. **Status Polling**:
   - Initial delay: Configurable, typically 1-2 seconds
   - Exponential backoff: Increases delay on rate limiting
   - Maximum retries: Configurable, typically 10-20 attempts

2. **Status Handling**:
   - `completed`: Extracts and formats the response
   - `requires_action`: Processes required tool calls
   - `failed`: Handles errors and provides fallback responses

3. **Tool Call Processing**:
   - Parses required actions from the assistant
   - Matches function names to implementation functions
   - Executes appropriate tools with provided arguments
   - Submits outputs back to the assistant

## Integration Points

### Discord Integration

The system integrates with Discord through:
- Forum thread monitoring
- Message event handlers
- Thread creation and management
- Attachment processing

### OpenAI Integration

The system integrates with OpenAI through:
- Assistant API for message handling
- Embeddings API for vector database
- Files API for attachment handling
- Beta features for advanced capabilities

### GitHub Integration

Repository access is configured through:
- GitHub API with personal access token
- Repository content retrieval
- Code analysis capabilities

## Deployment Configuration

The deployment is configured with the following files:

1. **Procfile**:
   - Contains commands for process managers like Heroku
   - Example: `worker: python -m bot`

2. **requirements.txt**:
   - Lists all Python dependencies with versions
   - Core dependencies include:
     - `openai`
     - `hikari`
     - `lightbulb`
     - `langchain`
     - `chromadb`

3. **runtime.txt**:
   - Specifies Python runtime version
   - Example: `python-3.11.x`

## Security Considerations

1. **API Key Management**:
   - All API keys stored in environment variables
   - No hardcoded credentials in the codebase

2. **Permission Scopes**:
   - Discord bot requires specific intents
   - GitHub token requires minimal necessary permissions

3. **Rate Limiting**:
   - Implements exponential backoff for API calls
   - Handles rate limit errors gracefully

4. **Error Handling**:
   - Logs errors without exposing sensitive information
   - Provides user-friendly fallback responses

## Monitoring and Logging

Logging is configured using the Loguru library:

```python
from loguru import logger

# Log important events
logger.info("Starting bot...")
logger.error("Error occurred: {error}")
```

Key logging points include:
- Bot startup and initialization
- Thread and message creation
- API call successes and failures
- Document processing status
