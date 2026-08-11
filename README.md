# DisCode

## What this project actually is

I'm building a tool that lets someone ask questions about a codebase in plain
English (like "what does this function do?") and get a real answer based on
the actual code — not the AI just guessing from general knowledge.

It's now planned as a **web app** (not a VS Code extension like I originally
thought) — a chat interface in the browser, backed by an MCP server that
does the real work.

The core idea is called RAG (Retrieval-Augmented Generation):
instead of asking an AI "explain this codebase" and hoping it doesn't make
stuff up, I first FIND the actual relevant pieces of code, THEN hand those
real pieces to the AI and say "explain based on this." This keeps answers
grounded in truth instead of guesses.

## Why I made the choices I did

- **No local AI models on my laptop, ever.** This is a permanent rule, not
  just a "for now" thing — it's what killed my earlier NativeRAG project.
  All AI work (embeddings, generating answers) happens through API calls.

- **Python, not TypeScript.** I originally picked TypeScript because VS Code
  extensions require it. But I changed my mind — I dropped the VS Code
  extension idea (going web app instead), and I genuinely find Python easier
  and want to learn it more. So I rewrote the indexing pipeline in Python.
  The frontend (the actual chat webpage) will still be JS/TypeScript, since
  browsers only understand that — but the "brain" (indexing, MCP server,
  backend) is all Python now.

- **SQLite, not PostgreSQL.** Considered Postgres to learn something new,
  but decided it wasn't worth the extra moving part (it needs to run
  constantly as a background process). SQLite is just a single file, way
  simpler.

- **Web app, not VS Code extension.** Originally planned as a VS Code
  extension. Changed my mind because: (1) nobody looking at my project would
  necessarily have VS Code extension dev tools set up to try it, (2) it's a
  lot of new API to learn on top of everything else, (3) a web app means
  anyone can just click a link and try it — way lower friction for a
  recruiter or examiner checking it out.

- **No accounts/login.** Decided against this — it would mean building auth
  (signup, passwords, sessions) which has nothing to do with AI/RAG and
  would just eat time. Anyone can open the link and use it directly.

- **Free embedding API (Google Gemini), not OpenAI.** I don't have a way to
  pay for OpenAI's API right now (it's not covered by ChatGPT Plus — totally
  separate product/billing). Gemini's API has a genuine free tier, no card
  needed, so I'm using that instead for now.

## What's actually been built so far

### Phase 1: Indexing Pipeline — DONE (rebuilt in Python)

The "indexing pipeline" = the part that reads a codebase and organizes it
into clean, searchable pieces. Lives in the `indexer/` folder.

**`walker.py`** — finds the right files. Goes through a project folder,
skips junk (`node_modules`, `.git`, build folders), only picks up
`.js/.ts/.jsx/.tsx` files, skips anything over 500kb (probably not
hand-written code).

**`chunker.py`** — breaks files into meaningful pieces using **tree-sitter**
(a tool that understands code's real structure), so it cuts along whole
functions/classes instead of blindly slicing text. This means a chunk is
never "half a function" — always a complete, meaningful unit.

**`run.py`** — just a test script to run the above two and print results.

Originally built and tested in TypeScript first (proved the logic works,
tested on my real Pong game — correctly found 20 real functions). Then
fully rewritten in Python, tested again on the same Pong repo — **identical
results**: same 20 functions, same line numbers. So the rewrite is confirmed
correct, not just "probably fine."

### Phase 2: Embeddings — JUST STARTED, connection confirmed working

An "embedding" is a list of numbers that represents what a piece of text or
code *means* — similar meaning = similar numbers. This is what will let me
later search code by meaning (e.g. asking "how does the ball move" and
finding the right function, even if the words don't match exactly).

Today I:
- Set up a Google Gemini API key (their free tier, no card needed)
- Stored it safely in a `.env` file (a special file for secrets — never
  gets uploaded to GitHub, `.gitignore` blocks it automatically)
- Installed `python-dotenv` (reads the `.env` file) and `google-genai`
  (Google's official library for calling their AI models)
- Wrote a small test script (`indexer/test_embed.py`) that sends one line
  of code to Gemini's embedding model and prints back the result
- **It worked** — got back an embedding with 3072 numbers for a simple test
  function. This confirms the whole chain works: my key is valid, the API
  call works, and I'm getting real embeddings back.

This was just a connection test, not the real embedding pipeline yet. Next
step is to actually run this on ALL my code chunks (not just one test
string) and figure out where to store the results.

## Concepts I now understand (or should be able to explain if asked)

- **RAG (Retrieval-Augmented Generation)** — find real relevant data first,
  then have the AI answer using that data, instead of trusting it to just
  "know" the answer
- **Embeddings** — turning text/code into a list of numbers, where similar
  meaning = similar numbers. Confirmed this works for me today, with real
  output (3072 numbers for one code snippet)
- **AST parsing** — reading code as its real grammatical structure (this is
  a function, this is a class) instead of treating it like plain text
- **tree-sitter** — the specific library used to do AST parsing
- **Code-aware chunking** — splitting code along real function/class
  boundaries instead of blind character-count cuts
- **MCP (Model Context Protocol)** — NOT the smart part of the system. It's
  just the shared "language"/format that lets an AI app (like Claude) ask my
  server for help and understand what it sends back. Think of it like a
  walkie-talkie standard — my server is the one doing the real work (finding
  code, searching it), MCP is just how it talks to the AI.
- **Self-correcting / reflective RAG** — the AI checking its own retrieval
  quality, and if it's weak, trying again with a better search instead of
  answering anyway with bad info (planned, not built yet)
- **Virtual environment (venv)** — a way to keep one project's Python
  version + installed packages completely separate from other projects or
  my system's default Python. Doesn't touch my actual files, just controls
  which Python/packages get used when I run something inside it. Had to
  learn this today because my system has Python 3.14, but the
  code-chunking library only supports up to 3.12 — so I installed 3.12
  separately and made a venv that uses it specifically.
- **.env file** — a special file just for secret values like API keys.
  Never gets committed to GitHub (blocked via `.gitignore`), so my key stays
  private even though my code is public.

## Tech stack so far

- **Python** — main language now (indexing pipeline, and soon the MCP
  server + backend)
- **tree-sitter** (`tree-sitter` + `tree-sitter-languages` Python packages)
  — for reading code structure and chunking
- **Google Gemini API** (`google-genai` package) — for generating
  embeddings (and later, possibly generating answers too)
- **python-dotenv** — for safely loading my API key from a `.env` file
- **SQLite** (planned next) — lightweight database, will store chunks +
  their embeddings
- **sqlite-vec** (planned next) — add-on for SQLite that allows searching by
  embedding similarity
- **JavaScript/TypeScript** — will be used for the frontend web app only
- **Git/GitHub** — version control
- **Python venv** — isolates this project's Python version (3.12) from my
  system's default (3.14)

## What's done vs. what's left

**Done:**
- [x] Indexing pipeline — file walker (finds real code files, skips junk)
- [x] Indexing pipeline — code-aware chunker using tree-sitter
- [x] Tested indexing pipeline on real code (Pong game) — first in
      TypeScript, then rebuilt and re-tested in Python with identical results
- [x] Switched project language decision: Python for backend/MCP server,
      JS/TS for frontend only
- [x] Set up Python 3.12 + venv locally (system has 3.14, which isn't
      compatible with the chunking library yet)
- [x] Got a free Gemini API key, stored safely in `.env`
- [x] Confirmed the embedding API connection actually works (real test,
      real output)
- [x] All of the above pushed to GitHub

**Not done yet:**
- [ ] Run embeddings on ALL real code chunks (not just one test string)
- [ ] Storage — saving chunks + their embeddings into a SQLite database
- [ ] Search/retrieval — given a question, find the most relevant chunks
      from storage
- [ ] MCP server — wrapping this into actual "tools" (like
      `search_codebase`, `explain_function`) that an AI can call
- [ ] Self-correction logic — detecting when retrieval was weak and
      retrying with a better search instead of answering with bad info
- [ ] Backend API — connects the frontend to the MCP server
- [ ] Frontend web app — the actual chat interface (dark/terminal style),
      needs to show: the answer, the real retrieved code chunks used, and a
      visible indicator when self-correction kicks in. Remembers
      conversation within a session only, no permanent history/accounts.
- [ ] Support for more languages beyond JS/TS (chunker currently only
      understands JavaScript/TypeScript files)
- [ ] Eval plan — how I'll prove/measure this works well, for my final year
      project report (retrieval precision/recall, answer faithfulness)

## Rough timeline
Estimated 6-8 weeks total at 2-3 hours/day, started today's real coding
session. Will keep tracking pace here as I go.

## Immediate next step
Actually run the embedding step on all the real code chunks from a repo
(not just a single test string), and figure out where/how to temporarily
hold those results before we build proper storage.