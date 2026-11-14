> **📦 ARCHIVED 2026-08-20 — SUPERSEDED.** Early informal design capture (no version, no owner). The authoritative voice/conversation design lives in `dev-docs/architecture-design/mvp-arch.md` (§6 voice sections) and the SD-9 batch design (`dev-docs/architecture-design/batch-designs/batch-sd9-design.md`). Archived per Tom's decision. **Frozen reference — do not update.**

---

## AI Chat DB Schema Functional Design

Here is how your current architecture is designed to handle this, avoiding a bloated table full of sparse, empty columns:

1. The Raw Transcript: conversation_message & conversation_session

Instead of a standalone "transcript" table, your schema uses a conversational model.
- The Session: When a user starts speaking, it creates a conversation_session linked directly to their user_id and tenant_id.
- The Transcript: The exact Whisper transcription is saved in conversation_message.content_text (with role = 'user'), completely independent of whatever business object it might eventually create. It also stores the S3 link to the raw audio (audio_object_key) and a vector embedding for semantic search.

2. The Link to Entities: context_window_json

Instead of hardcoding foreign keys (like quote_id or job_id) directly onto the transcript message, your schema uses a context_window_json field on the conversation_session.
- As the AI parses intents, it updates this JSON object with active_quote_id, active_job_id, or active_customer_id.
- This is brilliant for multi-turn conversations because the AI knows that if the user says, "Log 4 hours on it," "it" refers to the active_job_id currently in the context window.

3. The Execution Record: voice_command_log

When a transcript actually results in an action (like creating a quote or sending a text), your schema logs that relationship in the voice_command_log table.
- This table acts as the bridge. It ties the message_id (the transcript) to the intent_detected and the action_executed.
- It also stores the exact extracted entities (like the customer's name or the materials requested).

4. The Final Product: Entity-Specific Audio Links

When the voice command successfully creates a business record, your schema often stores a reference to the audio directly on that new record. For example, the job_notes table has its own audio_object_key column alongside the generated text note.

## AI Chat Interface Design

Since our field technicians will primarily be using the Expo mobile app—often with work gloves on or while walking the job site—how they navigate this historical chat list is important and here is our thinking right now:

We would show them session history, like a list, which they could then "rename" similar to how most of the frontier LLMs provide a chat interface with history of their chats on the lef sidebar. The UI design should include a similar chat interface so that the user has an iterative discussion on whatever topic they want, allowing the ai model to "confirm" a task before executing it, as well as allowing the user to "fix" any terms that were not "heard" correctly by the ai engine, and other similar use cases.


Here is how our existing architecture seamlessly maps to this chat-interface design:

1. The "Renameable" Sidebar List

In our conversation_session table, we included a context_summary column.
- This is tailor-made to act as the "Chat Title" in your sidebar.
- When a new session starts, we can have Ollama generate a quick 3-4 word summary (e.g., "Johnson Panel Upgrade") and save it here. If the user decides to rename it manually, we just UPDATE that specific column.

2. The Iterative Chat UI

Our conversation_message table is structured exactly like standard LLM chat history.
- Because it tracks the role (user, assistant, or system) alongside the content_text, rendering the chat bubbles in our UI is just a simple SELECT * FROM conversation_message WHERE session_id = XYZ ORDER BY created_at ASC.
- When the AI mishears something, the user can just tap the microphone again and say, "No, I meant copper wire, not aluminum," and the AI will use the prior conversation_message context to correct the active intent.

3. The "Confirm Before Execute" Loop

Our architecture defines a context_window_json that carries session state across multiple turns.
- If the technician says, "Add 100 feet of 10 AWG to the quote," the AI doesn't have to blindly execute it.
- It can push an assistant message back saying: "I have 100 feet of 10 AWG wire ready to add to Tom's quote. Should I execute?"
- The system simply waits for the next user message to validate before our backend voice_action_router.py actually calls the add_quote_line handler.