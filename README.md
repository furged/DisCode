# DisCode

**"what dis code sayin?"** — semantic search over a codebase, with actual written answers instead of raw grep-style output.

Ask a plain-English question about a codebase and get back a real explanation grounded in the actual code, plus the specific functions/classes it's based on — not a hallucinated guess, and not just a dump of matching text.

## What it does

DisCode indexes a codebase (a local folder or a public GitHub repo), breaks it into meaningful chunks (whole functions/classes, not arbitrary line splits), embeds those chunks for semantic search, and answers natural-language questions by retrieving the most relevant chunks and having an LLM explain them — with self-correcting retrieval that automatically rewrites a query if the first search comes back weak.

It's usable three ways: a web frontend, a CLI, or an MCP server (so Claude Desktop or another MCP-compatible AI tool can query your codebase directly).

## Features

- **Multi-language chunking** — JavaScript, JSX, TypeScript, TSX, Python, Go, Rust, Java, Ruby, C, and C++, via language-aware tree-sitter parsing (not naive text splitting, and not just a JS-only tool with other extensions bolted on)
- **Self-correcting retrieval** — if the best match for a query is too weak (above a tuned distance threshold), the query is automatically rewritten and retried once, and the better of the two results is kept
- **Synthesized answers** — retrieved code is explained in plain written prose referencing real function/class names, not just handed back as raw chunks
- **Index a local path or a GitHub URL** — paste `github.com/owner/repo` directly; it's downloaded and indexed without needing git installed locally (public repos only)
- **Background indexing with live progress** — indexing runs as a background job with a pollable status (fetching → walking → chunking → embedding → saving), so the UI never blocks on a multi-minute run
- **Resilient to API failures** — retry-with-backoff on embedding calls, failed chunks are skipped rather than aborting the whole run, and re-indexing a repo replaces the previous index instead of silently duplicating it
- **MCP server** — exposes a `search_codebase` tool for use from Claude Desktop or any other MCP client
- **Terminal-styled web frontend** — a single self-contained HTML file (no build step) with real syntax-highlighted code, a dedicated indexing panel separate from the chat, and collapsible code references under each answer

## Architecture

```
Walker → Chunker → Embedder → Storage → Retriever → (MCP server / FastAPI backend)
```

1. **Walker** (`walker.py`) — finds source files by extension, skips dependency/build folders (`node_modules`, `.git`, `dist`, `build`, `target`, `__pycache__`, `venv`, `vendor`, etc.) and anything over 500KB
2. **Chunker** (`chunker.py`) — parses each file with the correct tree-sitter grammar for its language and extracts whole functions/classes/structs (never a half-cut function) as chunks, with per-language rules for how names are found (most languages expose a clean `name` field; C/C++ requires walking the declarator chain; Go structs pull the name from a nested `type_spec`)
3. **Embedder** (`embedder.py`) — sends each chunk to Gemini's `gemini-embedding-001` for a 3072-dimensional embedding, with retry-with-backoff and graceful per-chunk failure handling
4. **Storage** (`storage.py`) — SQLite + the `sqlite-vec` extension for vector similarity search; re-indexing clears the previous index first so results never silently double up
5. **Retriever** (`retriever.py`) — embeds the question, searches for the closest chunks, and if the best match is weak (distance > 0.85), rewrites the query via `gemini-2.5-flash` and retries once, keeping whichever result is actually better; also synthesizes a plain-prose answer from the retrieved chunks
6. **Repo source resolver** (`repo_source.py`) — accepts either a local path or a GitHub URL; for GitHub, downloads the repo as a zip via `codeload.github.com` (no git or auth needed for public repos) and extracts it before handing off to the walker
7. **MCP server** (`server.py`) — wraps retrieval as a `search_codebase` tool over stdio
8. **API** (`api.py`) — FastAPI backend with search, background indexing, and job-status endpoints (see below)
9. **Frontend** (`discode-frontend.html`) — a standalone HTML/CSS/JS page that talks to the API

No local model inference happens anywhere in this pipeline — every AI call goes through the Gemini API, since local embedding/inference isn't practical on a 4GB-RAM laptop.

## Project structure

```
DisCode/
├── indexer/
│   ├── walker.py          # file discovery
│   ├── chunker.py         # tree-sitter parsing + chunking, multi-language
│   ├── embedder.py        # Gemini embedding calls, retry/backoff
│   ├── storage.py         # SQLite + sqlite-vec
│   ├── retriever.py       # semantic search, self-correction, answer synthesis
│   ├── repo_source.py     # local path / GitHub URL resolution
│   ├── run.py              # CLI: batch index a repo
│   ├── ask.py               # CLI: ask a question against the indexed db
│   ├── server.py           # MCP server (search_codebase tool)
│   └── api.py                # FastAPI backend
├── discode-frontend.html  # standalone web UI (no build step)
├── requirements.txt
├── .env                     # GEMINI_API_KEY (not committed)
├── .gitignore
└── README.md
```

## Setup

**Requirements:** Python 3.12 specifically. `tree-sitter==0.21.3` is version-locked to `tree-sitter-languages==1.10.2` and doesn't work with newer Python (3.13+) or newer tree-sitter releases — if your system Python is newer, create the venv with a Python 3.12 install explicitly (e.g. `py -3.12 -m venv venv` on Windows).

```bash
python -m venv venv
# Windows: venv\Scripts\Activate.ps1
# macOS/Linux: source venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
GEMINI_API_KEY=your_key_here
```

Get a free-tier key at [aistudio.google.com](https://aistudio.google.com/) — no card required. Never commit this file (it's already in `.gitignore`).

## Usage

### Option A — Web UI (recommended)

```bash
cd indexer
python api.py
```

Then open `discode-frontend.html` directly in a browser (just double-click it — no server needed for the frontend itself). Paste a local path or a `github.com/owner/repo` URL into the index panel at the top, then ask questions in the chat below once indexing finishes.

### Option B — CLI

```bash
cd indexer
python run.py /path/to/some/repo    # index a local folder
python ask.py "how does the ball bounce"   # ask a question
```

### Option C — MCP server (Claude Desktop, etc.)

```bash
cd indexer
python server.py
```

Point your MCP client at this process over stdio to expose the `search_codebase` tool.

### API reference

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Liveness check |
| `/api/search` | POST | `{"question": "..."}` → synthesized answer + matched code chunks |
| `/api/index` | POST | `{"repo_path": "local/path or github.com/owner/repo"}` → starts a background indexing job, returns `{"job_id": "..."}` |
| `/api/index/{job_id}` | GET | Poll indexing progress/status |
| `/api/status` | GET | Info about the most recently completed index (for showing "indexed: X, N chunks" without re-running anything) |

## Supported languages

| Language | Extensions |
|---|---|
| JavaScript | `.js`, `.jsx` |
| TypeScript | `.ts`, `.tsx` |
| Python | `.py` |
| Go | `.go` |
| Rust | `.rs` |
| Java | `.java` |
| Ruby | `.rb` |
| C | `.c`, `.h` |
| C++ | `.cpp`, `.cc`, `.cxx`, `.hpp`, `.hh` |

## Tuned parameters

- `DISTANCE_THRESHOLD = 0.85` (`retriever.py`) — above this, a result is considered weak enough to trigger self-correction
- `MAX_RETRIES = 3`, `RETRY_BACKOFF_SECONDS = 2` (doubling: 2s/4s/8s) (`embedder.py`) — retry behavior for embedding API calls
- `MAX_FILE_SIZE_BYTES = 500_000` (`walker.py`) — files larger than this are assumed generated/minified and skipped
- `MAX_QUESTION_LENGTH = 500` (`api.py`) — input validation on `/api/search`

## Known limitations

- GitHub indexing only supports **public** repos (no auth flow for private repos)
- The indexing job store is in-memory — it resets if the API server restarts mid-job
- The API has no auth and CORS is wide open — this is meant for local single-user dev use only, not for deploying anywhere reachable from the internet
- Free-tier Gemini API rate limits apply to both embedding and answer synthesis calls
- No automated test suite yet — testing so far has been manual, across real repos in each supported language

## Tech stack

Python, FastAPI, tree-sitter (+ `tree-sitter-languages`), SQLite + `sqlite-vec`, Google Gemini API (`gemini-embedding-001` for embeddings, `gemini-2.5-flash` for query rewriting and answer synthesis), MCP, and a dependency-free HTML/CSS/vanilla-JS frontend (syntax highlighting via `highlight.js` loaded from a CDN).