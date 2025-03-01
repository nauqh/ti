# Questions Extension Documentation

## Overview
The `questions.py` extension implements a forum-based Q&A system for the Discord bot, providing automated responses to student questions across different course forums. This extension connects Discord's forum threads with the OpenAI-powered assistant to deliver contextually relevant answers.

## Core Features
1. Forum Integration
- Monitors designated question forums for new threads
- Automatically responds to new questions with AI-powered answers
- Supports follow-up questions with conversation continuity
2. Multi-Course Support
- Configurable forum mapping for different courses (Data Science, Full Stack Web, CS50)
- Course-specific TA role identification
- Custom notification channels for each course
3. Attachment Handling
- Processes both image and file attachments
- Routes images to visual context for the AI
- Handles code files, PDFs, and other documents
4. Feedback Collection
- Interactive rating system through emoji reactions (1-5 scale)
- Automatic feedback prompt after each response
- Centralized feedback logging to staff channels
5. TA Integration
- TA role detection to avoid conflicting with human TAs
- Automatic forum routing based on course categories
- Staff notification system for assistance needs

## Implementation Details
**Configuration**
```python
QUESTION_CENTERS = {
    "DS": {"forum_id": 1081063200377806899, "ta_id": 1194665960376901773, "staff_channel": 1237424754739253279},
    "FSW": {"forum_id": 1326478786274922568, "ta_id": 912553106124972083},
    "CS50": {"forum_id": 1343930405702865037, "ta_id": 1233260164233297942},
}
```
The extension uses a mapping dictionary to track forum IDs, TA role IDs, and staff channels for different courses.

**Initialization**
```python
@plugin.listener(hikari.StartingEvent)
async def on_starting(event: hikari.StartingEvent) -> None:
    bot = Assistant([f"docs/{filename}" for filename in os.listdir('docs')])
    plugin.app.d.bot = bot
```
On startup, the extension initializes the `Assistant` with all documents from the `docs` directory, setting up the knowledge base for responses.

**Thread Creation Flow**
1. The extension listens for new forum threads in designated forums
2. When detected, it extracts message content and attachments
3. Creates a corresponding AI thread via the Assistant
4. Maps the Discord thread ID to the OpenAI thread ID for continuity
5. Sends the AI's response back to the Discord thread

**Follow-up Question Handling**
The extension handles follow-up questions by:
```python
async def handle_follow_up(post: hikari.GuildThreadChannel, message: hikari.Message) -> None:
    # Process follow-up questions and collect feedback
```

1. Continuing the existing AI thread using the stored mapping
2. Preventing duplicate responses with history checks
3. Adding feedback collection after each response
4. IMPORTANT: Limiting responses to **2 per thread** to avoid excessive replies

**Feedback Collection**
```python
@plugin.listener(hikari.ReactionAddEvent)
async def on_reaction_add(event: hikari.ReactionAddEvent) -> None:
    # Handle feedback reactions (1-5 scale)
```
The feedback system:
1. Monitors reactions on feedback messages
2. Identifies numeric ratings (1-5)
3. Logs ratings to a designated staff channel with user information
4. Creates a clickable thread link for staff follow-up


## Usage Workflow
1. Student creates a new question in a course forum
2. Bot automatically processes the question and responds
3. Student can ask one follow-up question for clarification
4. Student can rate the helpfulness of the responses
5. TAs can step in at any point to provide additional help


# Questions Extension Workflow

The following diagram illustrates the workflow of the components in the Questions extension:

```mermaid
graph TD
    %% Initialization
    A[Bot Starts] --> B[Initialize Assistant with docs]
    
    %% Thread Creation Flow
    C[New Forum Thread Created] --> D{Is in Question Forum?}
    D -->|Yes| E[Extract Message & Attachments]
    D -->|No| Z[Ignore]
    E --> F[Create AI Thread]
    F --> G[Store Discord-OpenAI Thread Mapping]
    G --> H[Generate & Send Response]
    
    %% Follow-up Question Flow
    I[New Message in Thread] --> J{Is Author Bot?}
    J -->|Yes| Z
    J -->|No| K{Is TA Role?}
    K -->|Yes| Z
    K -->|No| L{Response Count Check}
    L -->|First Response| M[Process Follow-up Question]
    L -->|2+ Responses| N[Stop Following Up]
    M --> O[Continue AI Thread]
    O --> P[Check Last Message Author]
    P -->|Is Bot| Z
    P -->|Not Bot| Q[Send AI Response]
    Q --> R[Send Feedback Request]
    R --> S[Add Reaction Emojis]
    
    %% Feedback Collection Flow
    T[Reaction Added] --> U{Is Rating Emoji?}
    U -->|No| Z
    U -->|Yes| V[Extract Rating Score]
    V --> W[Log User Feedback]
    W --> X[Send to Staff Channel]
    
    %% Legend
    style A fill:#d4f1f9,stroke:#05445E
    style B fill:#d4f1f9,stroke:#05445E
    style Z fill:#F8D7DA,stroke:#842029
    style R fill:#D1E7DD,stroke:#0F5132
    style S fill:#D1E7DD,stroke:#0F5132
    style X fill:#FFF3CD,stroke:#664D03
```

## Component Legend

### Event Listeners
- `on_starting`: Initializes the Assistant with documents 
- `on_thread_create`: Handles new forum threads
- `on_message_create`: Processes follow-up messages
- `on_reaction_add`: Collects user feedback

### Core Functions
- `handle_post_creation`: Processes initial questions
- `handle_follow_up`: Manages follow-up interactions
- `QUESTION_CENTERS`: Maps course forums to TA roles

### Limitations
- Maximum of 2 bot responses per thread
- TA messages prevent bot responses
- Only specific forum channels are monitored
