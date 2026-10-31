# 17. Frontend Architecture, Streaming & UX

## 1. Paced Word Streaming Buffer (`components/chat/chat-interface.tsx`)

```mermaid
flowchart TD
    RESPONSE[Full LLM Answer Payload Arrives] --> SPLIT[Split into Words Array]
    SPLIT --> EVAL{Total Words > 150?}
    EVAL -->|Yes: Long Response| BATCH_3[Batch Window: 3 Words]
    EVAL -->|No: Short Response| BATCH_1[Batch Window: 1 Word]
    
    BATCH_3 --> LOOP[Append Batch to currentText]
    BATCH_1 --> LOOP
    
    LOOP --> UPDATE_STATE[React setMessages State Dispatch]
    UPDATE_STATE --> DELAY[Paced Delay: await sleep 20ms]
    DELAY --> MORE_WORDS{Remaining Words?}
    MORE_WORDS -->|Yes| LOOP
    MORE_WORDS -->|No| COMMIT_FINAL[Commit Full String & Sanitize]
    COMMIT_FINAL --> MD_RENDER[Custom Markdown Parser]
```

---

## 2. Custom Markdown Parser (`MarkdownText`)

Avoids heavy external markdown libraries, parsing directly in React:
- **GFM Tables**: Detects lines starting with `|`, accumulates rows, and renders inside responsive, horizontally-scrollable `<table>` wrappers.
- **Hierarchical Lists**: Dynamically aggregates unordered bullet points (`- `) and numbered lists (`1. `).
- **Blockquotes**: Parses lines starting with `> `, rendering an italic block with an indigo accent border.
