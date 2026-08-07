# DisCode

# Codebase Explainer 

## What this project actually is

A tool that lets someone ask questions about a codebase in plain English (like "what does this function do?") and get a real answer based on the actual code, not the AI just guessing from general knowledge.

Two parts:
1. An MCP server (a backend that an AI tool like Claude/VS Code can talk to)
2. A VS Code extension 

The core idea is called RAG (Retrieval-Augmented Generation): instead of asking an AI "explain this codebase" and hoping it doesn't make stuff up, I first FIND the actual relevant pieces of code, THEN hand those real pieces to the AI and say "explain based on this." This keeps answers grounded in truth instead of guesses.

## Built so far (Phase 1: Indexing Pipeline)

The "indexing pipeline" = the part of the project that reads a codebase and breaks it into clean, searchable pieces. This has to happen before any "asking questions" stuff can work. You can't search something that hasn't been organized yet.

It has 3 files, all inside the `indexer/` folder:

### 1. `walker.ts` (finds the right files)
Goes through a project folder and makes a list of files worth reading.
- Skips junk folders like `node_modules`, `.git`, `dist` (these aren't "my code", they're installed libraries or generated files)
- Only picks up `.js`, `.ts`, `.jsx`, `.tsx` files for now
- Skips any file bigger than 500kb (probably not hand-written code if it's that big, likely a generated/minified file)

### 2. `chunker.ts` (breaks files into meaningful pieces)
Takes one file and splits it into pieces — but NOT by blindly cutting every X characters (that could slice a function in half and make it useless).

Instead it uses a tool called **tree-sitter**, which actually understands code's real structure, it can tell "this exact block of text, start to end, is one whole function called `movePaddle`." So it cuts along the natural boundaries of the code: one function = one piece, one class = one piece.

Tested this on my real Pong game's `script.js`. It correctly found all 20 real functions in the file, with the correct starting and ending line number for each one.

### 3. `run.ts` (glues the two above together)
Just a script that says: "walk this folder → chunk every file you found → print out what you got." Used it purely to test and see real results on screen. Not part of the final product itself, just a testing tool.

## Concepts 

- **RAG (Retrieval-Augmented Generation)**: find real relevant data first, then have the AI answer using that data, instead of trusting it to just "know" the answer
- **Embeddings**: turning text/code into a list of numbers, in a way where similar meaning = similar numbers. This is what makes "search by meaning" possible later, instead of just matching exact keywords
- **AST parsing**: reading code as its real grammatical structure (this is a function, this is a class) instead of treating it like plain text
- **tree-sitter**: the specific library I used to do AST parsing
- **Code-aware chunking**: splitting code along real function/class boundaries instead of blind character-count cuts
- **MCP (Model Context Protocol)**: a standard way for AI tools (Claude Desktop, Cursor, VS Code) to call outside tools/servers. My project will expose itself as an MCP server so any MCP-compatible AI tool can use it, not just my own extension
- **Self-correcting / reflective RAG**: the AI checking its own retrieval quality, and if it's weak, trying again with a better search instead of just answering anyway with bad information (planned, not built yet)

## Tech so far

- **TypeScript** 
- **Node.js** 
- **ts-node** 
- **tree-sitter (web-tree-sitter + tree-sitter-wasms)** 
- **SQLite** 
- **sqlite-vec** 
- **GitHub Codespaces** 
- **Git/GitHub**

## Progress

- [x] Project folder set up (TypeScript + Node.js configured)
- [x] File walker (finds real code files, skips junk)
- [x] Code-aware chunker using tree-sitter (splits code into whole functions/classes, not blind cuts)
- [x] Tested successfully on real code (my Pong game, found 20 real functions correctly)
- [x] Pushed to GitHub
- [ ] Embeddings - turning each code chunk into a list of numbers representing its meaning (needs an API key from OpenAI or similar, haven't set this up yet)
- [ ] Storage - saving chunks + their embeddings into a SQLite database so they can be searched later
- [ ] Search/retrieval - given a question, find the most relevant chunks from storage
- [ ] MCP server - wrapping all of this into actual "tools" (like `search_codebase`, `explain_function`) that an AI can call
- [ ] Self-correction logic - detecting when retrieval was weak and retrying with a better search instead of answering with bad info
- [ ] VS Code extension - the actual chat window / UI piece
- [ ] Support for more languages beyond JS/TS (my chunker currently only understands JavaScript/TypeScript files)
- [ ] Deciding on eval plan (how I'll prove/measure this actually works well, for my final year project report)

## Immediate next step
Set up an API key (OpenAI or similar) so I can start turning code chunks
into embeddings, the next real building block after this one.
