# My Understanding Notes — DisCode

This file is just for me to actually understand what we're building and why.
Not meant to explain the project to anyone else.

## The big picture

I'm building a tool that lets someone ask questions about a codebase in
plain English and get a real answer based on the actual code — not the AI
guessing from general knowledge.

It's a **web app** (chat interface in the browser), backed by an **MCP
server** that does the real retrieval work.

The core idea is called **RAG (Retrieval-Augmented Generation)**: find the
actual relevant pieces of code first, THEN hand those real pieces to an AI
to explain — instead of trusting the AI to just "know" the answer.

## Why I made the choices I did

- **No local AI models on my laptop, ever.** Permanent rule, not just
  "for now." This is what killed my earlier NativeRAG project (4GB RAM
  couldn't handle local model inference). All AI work happens through API
  calls instead.

- **Python, not TypeScript**, for the backend/MCP server. Originally chose
  TypeScript because VS Code extensions require it. Dropped that plan (going
  web app instead), and genuinely prefer Python + want to learn it more. The
  frontend (actual webpage) is still JS/TypeScript, since browsers only
  understand that.

- **SQLite, not PostgreSQL.** Considered Postgres to learn something new,
  decided against it — didn't want a constantly-running background service
  to manage. SQLite is a single file, simpler.

- **Web app, not VS Code extension.** Changed my mind because: recruiters/
  examiners likely don't have VS Code extension dev tools set up, it's a lot
  of new API to learn on top of everything else left to build, and a web app
  means "click a link and try it" — way lower friction for anyone checking
  it out.

- **No accounts/login.** Would mean building auth (signup, passwords,
  sessions) — none of that demonstrates AI/ML skill, just eats time. Anyone
  can open the link and use it directly.

- **Google Gemini API, not OpenAI.** Don't have a way to pay for OpenAI's
  API (not covered by ChatGPT Plus — totally separate product/billing).
  Gemini has a genuine free tier, no card needed.

- **JS/TS only for now, more languages later (planned, not forgotten).**
  Chunker currently only understands JavaScript/TypeScript. Proving the full
  pipeline works end-to-end on one language first, before adding more
  grammars. Architecture is designed to make this a small addition later
  (load another tree-sitter grammar, add its node types, add its file
  extensions to the walker) — not a redesign.

## Concepts I now understand (or should be able to explain if asked)

- **RAG (Retrieval-Augmented Generation)** — find real relevant data first,
  then have the AI answer using that data, instead of trusting it to "know"
  the answer.

- **Embeddings** — turning text/code into a list of numbers, where similar
  meaning = similar numbers. This is what makes "search by meaning"
  possible, not just exact keyword matching. Confirmed this works — got a
  real 3072-number embedding back from Gemini for a test code snippet.

- **AST parsing** — reading code as its real grammatical structure (this is
  a function, this is a class) instead of treating it like plain text.

- **tree-sitter** — the specific library used to do AST parsing. Understands
  code structure across languages (currently only using its JS grammar).

- **Code-aware chunking** — splitting code along real function/class
  boundaries instead of blind character-count cuts, so a chunk is always a
  complete, meaningful unit.

- **MCP (Model Context Protocol)** — NOT the smart part of the system. It's
  the shared "language"/format that lets an AI app (like Claude) ask my
  server for help and understand what it sends back. My server does the real
  work (finding code, searching it); MCP is just how it talks to the AI.

- **Self-correcting / reflective RAG** — the AI checking its own retrieval
  quality, and if it's weak, trying again with a better search instead of
  answering anyway with bad info. Planned, not built yet.

- **Vector / similarity search** — comparing embeddings to find the
  "closest" match by meaning. Lower "distance" = more similar. Tested this
  today with fake data — searching using one chunk's own embedding correctly
  found itself as the closest match (distance 0.0).

- **Virtual environment (venv)** — keeps one project's Python version +
  installed packages separate from other projects or my system's default.
  Had to learn this because my system has Python 3.14, but the code-chunking
  library only supports up to 3.12 — so I installed 3.12 separately and made
  a venv using it specifically. Doesn't touch my actual files, just controls
  which Python/packages get used when I run something inside that venv.

- **.env file** — a special file just for secret values like API keys.
  Never gets committed to GitHub (blocked via `.gitignore`), so my key stays
  private even though my code is public.

- **SQLite + sqlite-vec** — SQLite is a lightweight, single-file database
  (no separate server process to run). sqlite-vec is an add-on that gives it
  the ability to search by embedding similarity, which plain SQLite can't do
  on its own.

## How the pieces fit together (mental model)

1. **Walker** — goes through a codebase, finds real code files, skips junk
   (`node_modules`, `.git`, huge files)
2. **Chunker** — reads each file's real structure via tree-sitter, breaks it
   into whole functions/classes (never half-cut)
3. **Embedder** — sends each chunk's code to Gemini's API, gets back a list
   of numbers representing its meaning
4. **Storage** — saves each chunk (readable code + metadata) and its
   embedding into SQLite, linked by an ID
5. **Retrieval** (next step) — takes a real question, embeds it the same
   way, searches storage for the closest-meaning chunks
6. **Self-correction** (later) — if retrieval results are weak, rewrite the
   query and try again instead of answering with bad context
7. **MCP server** (later) — wraps steps 1-6 into tools an AI can call
   (`search_codebase`, `explain_function`, etc.)
8. **Backend + frontend web app** (later) — the actual chat interface a
   person interacts with, which talks to the MCP server behind the scenes

## Things I had to debug/learn the hard way (so I remember why)

- Hit real version-mismatch bugs getting tree-sitter working in both
  TypeScript and Python — had to pin specific package versions that are
  known to work together, rather than always installing "latest."
- Default TypeScript config was too strict/modern for this simple use case
  — had to simplify it manually.
- My system's Python (3.14) is too new for some libraries (`tree-sitter-
  languages`) — solved by installing Python 3.12 separately via a venv,
  without needing to uninstall or replace 3.14.
- OpenAI's API needs separate billing from ChatGPT Plus — they are NOT the
  same account/product for this purpose. Switched to Gemini's free tier
  instead.