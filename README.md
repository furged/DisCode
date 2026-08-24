# DisCode

Semantic codebase search engine. Ask questions about your code in plain English, get real answers grounded in your actual codebase.

## What it does

Input: "How does the ball speed increase in this game?"
Output: The actual code functions that implement that behavior, ranked by relevance to your question.

DisCode uses RAG (Retrieval-Augmented Generation) to search codebases by meaning, not keywords. Instead of an AI guessing from general knowledge, it finds real code chunks from your repo first, then explains based on that evidence. It automatically retries weak searches with rewritten queries instead of answering with low-confidence results.

## How it works

1. Walker — finds real source files, skips junk (node_modules, build artifacts, etc.)
2. Chunker — parses code using tree-sitter, breaks it into whole functions/classes
3. Embedder — converts each chunk to a vector (list of numbers representing meaning)
4. Storage — saves chunks and vectors to SQLite database
5. Retriever — takes user questions, embeds them, searches for closest-meaning chunks
6. Self-correction — checks if results are weak, retries with better query if needed
7. API — FastAPI backend exposing search as HTTP endpoints
8. MCP Server — same logic exposed as tools for Claude Desktop / other AI apps

## Status

Completed:
- Indexing pipeline (walk, chunk, embed)
- Vector storage (SQLite + sqlite-vec)
- Semantic search with self-correction
- MCP server
- Backend API

In progress:
- Frontend web app

## Setup

Prerequisites: Python 3.12, Gemini API key (free at https://aistudio.google.com/)

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo "GEMINI_API_KEY=your_key_here" > .env
```

## Usage

Index a repo:
```bash
python indexer/run.py /path/to/repo
```

Ask questions from CLI:
```bash
python indexer/ask.py "how does the paddle move"
```

Run the backend API:
```bash
python indexer/api.py
# Runs on localhost:8000
```

Query the API:
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"question": "how does collision detection work"}'
```

## Architecture

Core files:
- walker.py — finds code files worth indexing
- chunker.py — uses tree-sitter to parse and chunk by function/class
- embedder.py — calls Gemini API to convert chunks to vectors
- storage.py — SQLite database with vector search extension
- retriever.py — semantic search with auto-retry on weak results
- server.py — MCP server exposing search_codebase tool
- api.py — FastAPI backend with /api/search endpoint

Key design decisions:
- No local model inference (learned from earlier project that hit hardware limits)
- Code-aware chunking preserves meaning better than blind text-splitting
- Self-correction detects weak results and retries instead of answering poorly
- Threshold for "weak" result tuned empirically on real test data (0.85 distance)

## Tech Stack

- Python 3.12
- tree-sitter (code parsing)
- Google Gemini API (embeddings)
- SQLite + sqlite-vec (storage and vector search)
- FastAPI (backend)
- MCP SDK (protocol for AI tools)

## Concepts

RAG — finding real data first before generating answers, grounding responses in truth instead of AI memory.

Embeddings — converting text/code to vectors where similar meaning lives close together geometrically. Enables "search by meaning" not just keywords.

Tree-sitter — parser that understands code structure (functions, classes) so chunking respects code boundaries instead of slicing randomly.

Self-correcting retrieval — when top results aren't close enough in meaning (high distance), automatically rewrite the question and retry instead of answering with weak context.

Vector similarity — finding the closest points in vector space (lowest distance) to locate semantically related code.

## Limitations

- Currently indexes JavaScript/TypeScript only. Other languages require adding tree-sitter grammars (architecture supports this, just not built yet).
- v1 works on local workspaces. Remote repos are planned for later.
- Self-correction threshold was tuned on one small repo (Pong game) and may need adjustment for other codebases.

## Next

Frontend web chat interface, multi-language support, final evaluation and report.