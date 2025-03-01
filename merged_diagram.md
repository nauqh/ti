# Merged Workflow Diagram

The following diagram illustrates the complete workflow of the T.i chatbot system, including both the core AI assistant functionality and the Questions extension integration:

```mermaid
graph TD
    %% Main Entry Points
    UserMsg((New Message)) --> CheckThread{Check if Thread Exists}
    CheckThread -->|Yes| AddMsg[Add Message to Thread]
    CheckThread -->|No| CreateThread[Create Thread]
    CreateThread --> AddMsg
    
    %% Core Assistant Flow - Main Section
    subgraph CoreAssistant [Core Assistant Flow]
        AddMsg --> CreateRun[Create Run]
        CreateRun --> ProcessRun[Process Run]
        ProcessRun --> RunStatus{Run Status Check}
        RunStatus -->|completed| RetrieveMsg[Retrieve Response Messages]
        RunStatus -->|requires_action| ProcessTools[Process Required Tool Calls]
        RunStatus -->|failed| LogError[Log Error and Exit]
        
        %% Tool Handling Section
        ProcessTools --> ToolType{Tool Type}
        ToolType -->|GitHub| FetchRepo[Fetch Repository Code]
        ToolType -->|YouTube| SearchVids[Search Videos]
        ToolType -->|Document| SearchDB[Search ChromaDB]
        ToolType -->|TA Role| GetRole[Get TA Role for Forum]
        FetchRepo --> ProcessRun
        SearchVids --> ProcessRun
        SearchDB --> ProcessRun
        GetRole --> ProcessRun
        
        %% Response Processing Section
        RetrieveMsg --> CheckCitations{Check Citations}
        CheckCitations -->|Yes| AddFiles[Add Referenced Files]
        CheckCitations -->|No| DisplayResp[Display Response to User]
        AddFiles --> DisplayResp
    end
    
    %% Questions Extension Flow - Can be displayed separately
    subgraph QuestionsExtension [Questions Extension Flow]
        %% Thread Creation Flow
        ThreadCreated[New Forum Thread Created] --> ForumCheck{Is in Question Forum?}
        ForumCheck -->|Yes| ExtractMsg[Extract Message & Attachments]
        ForumCheck -->|No| Ignore((Ignore))
        ExtractMsg --> InitThread[Create AI Thread]
        InitThread --> StoreMapping[Store Discord-OpenAI Thread Mapping]
        StoreMapping --> GenerateResp[Generate & Send Response]
        
        %% Follow-up Question Flow
        NewMsg[New Message in Thread] --> BotCheck{Is Author Bot?}
        BotCheck -->|Yes| Ignore
        BotCheck -->|No| TARoleCheck{Is TA Role?}
        TARoleCheck -->|Yes| Ignore
        TARoleCheck -->|No| ResponseCountCheck{Response Count Check}
        ResponseCountCheck -->|First Response| ProcessFollowup[Process Follow-up Question]
        ResponseCountCheck -->|2+ Responses| StopFollowing[Stop Following Up]
        ProcessFollowup --> ContinueThread[Continue AI Thread]
        ContinueThread --> LastAuthorCheck{Check Last Message Author}
        LastAuthorCheck -->|Is Bot| Ignore
        LastAuthorCheck -->|Not Bot| SendResp[Send AI Response]
        SendResp --> SendFeedback[Send Feedback Request]
        SendFeedback --> AddReactions[Add Rating Emojis]
        
        %% Feedback Collection Flow
        ReactionAdded[Reaction Added] --> RatingCheck{Is Rating Emoji?}
        RatingCheck -->|No| Ignore
        RatingCheck -->|Yes| ExtractScore[Extract Rating Score]
        ExtractScore --> LogFeedback[Log User Feedback]
        LogFeedback --> SendToStaff[Send to Staff Channel]
    end
    
    %% Connections between subgraphs
    GenerateResp -.-> CreateRun
    ContinueThread -.-> ProcessRun
    
    %% Legend styling
    classDef startEvent fill:#d4f1f9,stroke:#05445E
    classDef errorEvent fill:#F8D7DA,stroke:#842029
    classDef feedbackEvent fill:#D1E7DD,stroke:#0F5132
    classDef staffEvent fill:#FFF3CD,stroke:#664D03
    
    class UserMsg,ThreadCreated,ReactionAdded startEvent
    class LogError,Ignore errorEvent
    class SendFeedback,AddReactions feedbackEvent
    class SendToStaff staffEvent
```

## Creating Partial Diagrams

This unified diagram has been designed to allow for displaying partial views in different documentation files:

### 1. Complete Diagram (for README.md)
The complete diagram shown above includes both the Core Assistant flow and the Questions Extension flow, with clear connections between them.

### 2. Questions Extension Only (for questions.md)
To display only the Questions Extension portion of the diagram, you can extract just that subgraph section and add a reference to the Core Assistant like this:

```mermaid
graph TD
    %% Questions Extension Flow - Specific to this module
    %% Thread Creation Flow
    ThreadCreated[New Forum Thread Created] --> ForumCheck{Is in Question Forum?}
    ForumCheck -->|Yes| ExtractMsg[Extract Message & Attachments]
    ForumCheck -->|No| Ignore((Ignore))
    ExtractMsg --> InitThread[Create AI Thread]
    InitThread --> StoreMapping[Store Discord-OpenAI Thread Mapping]
    StoreMapping --> GenerateResp[Generate & Send Response]
    
    %% Follow-up Question Flow
    NewMsg[New Message in Thread] --> BotCheck{Is Author Bot?}
    BotCheck -->|Yes| Ignore
    BotCheck -->|No| TARoleCheck{Is TA Role?}
    TARoleCheck -->|Yes| Ignore
    TARoleCheck -->|No| ResponseCountCheck{Response Count Check}
    ResponseCountCheck -->|First Response| ProcessFollowup[Process Follow-up Question]
    ResponseCountCheck -->|2+ Responses| StopFollowing[Stop Following Up]
    ProcessFollowup --> ContinueThread[Continue AI Thread]
    ContinueThread --> LastAuthorCheck{Check Last Message Author}
    LastAuthorCheck -->|Is Bot| Ignore
    LastAuthorCheck -->|Not Bot| SendResp[Send AI Response]
    SendResp --> SendFeedback[Send Feedback Request]
    SendFeedback --> AddReactions[Add Rating Emojis]
    
    %% Feedback Collection Flow
    ReactionAdded[Reaction Added] --> RatingCheck{Is Rating Emoji?}
    RatingCheck -->|No| Ignore
    RatingCheck -->|Yes| ExtractScore[Extract Rating Score]
    ExtractScore --> LogFeedback[Log User Feedback]
    LogFeedback --> SendToStaff[Send to Staff Channel]
    
    %% This subgraph connects to the Core Assistant
    GenerateResp -.-> CoreAssistant[Send to Core Assistant]
    ContinueThread -.-> CoreAssistant
    
    %% Legend styling 
    classDef startEvent fill:#d4f1f9,stroke:#05445E
    classDef errorEvent fill:#F8D7DA,stroke:#842029
    classDef feedbackEvent fill:#D1E7DD,stroke:#0F5132
    classDef staffEvent fill:#FFF3CD,stroke:#664D03
    classDef coreRef fill:#f0f0f0,stroke:#707070,stroke-dasharray: 5 5
    
    class ThreadCreated,ReactionAdded startEvent
    class Ignore errorEvent
    class SendFeedback,AddReactions feedbackEvent
    class SendToStaff staffEvent
    class CoreAssistant coreRef
```

### 3. Core Assistant Only
Similarly, you could create a view showing only the Core Assistant flow:

```mermaid
graph TD
    %% Main Entry Points
    UserMsg((New Message)) --> CheckThread{Check if Thread Exists}
    CheckThread -->|Yes| AddMsg[Add Message to Thread]
    CheckThread -->|No| CreateThread[Create Thread]
    CreateThread --> AddMsg
    
    %% Core Assistant Flow - Main Section
    AddMsg --> CreateRun[Create Run]
    CreateRun --> ProcessRun[Process Run]
    ProcessRun --> RunStatus{Run Status Check}
    RunStatus -->|completed| RetrieveMsg[Retrieve Response Messages]
    RunStatus -->|requires_action| ProcessTools[Process Required Tool Calls]
    RunStatus -->|failed| LogError[Log Error and Exit]
    
    %% Tool Handling Section
    ProcessTools --> ToolType{Tool Type}
    ToolType -->|GitHub| FetchRepo[Fetch Repository Code]
    ToolType -->|YouTube| SearchVids[Search Videos]
    ToolType -->|Document| SearchDB[Search ChromaDB]
    ToolType -->|TA Role| GetRole[Get TA Role for Forum]
    FetchRepo --> ProcessRun
    SearchVids --> ProcessRun
    SearchDB --> ProcessRun
    GetRole --> ProcessRun
    
    %% Response Processing Section
    RetrieveMsg --> CheckCitations{Check Citations}
    CheckCitations -->|Yes| AddFiles[Add Referenced Files]
    CheckCitations -->|No| DisplayResp[Display Response to User]
    AddFiles --> DisplayResp
    
    %% Legend styling
    classDef startEvent fill:#d4f1f9,stroke:#05445E
    classDef errorEvent fill:#F8D7DA,stroke:#842029
    
    class UserMsg startEvent
    class LogError errorEvent
```

## Maintainability Note

The diagrams have been organized with consistent node naming and structure so that changes to the unified diagram can be easily propagated to partial views. When updating the workflow:

1. First update the complete diagram in this file
2. Then update the partial diagrams in their respective documentation files
3. Maintain consistent node IDs and naming conventions
4. Keep section comments (like `%% Thread Creation Flow`) to make extraction easier
