from embedder import client, EmbeddingError, MAX_RETRIES, RETRY_BACKOFF_SECONDS
from google.genai import errors as genai_errors
from storage import search_similar_chunks
import time

# If the closest match's distance is above this number, we consider the
# retrieval "weak" and worth retrying with a better query.
# (This threshold was picked by eyeballing real results - lower distance
# is more similar. Tune this later once we have more real questions to test.)
DISTANCE_THRESHOLD = 0.85


class RetrievalError(Exception):
    """Raised when a search request can't be completed (e.g. the
    embedding API is down or exhausted its retries)."""


def embed_query(question):
    """
    Turns a plain-text question into an embedding, the same way we embed
    code chunks - so we can compare "meaning" between the question and
    the stored code.
    Raises RetrievalError if the API call fails after retries.
    """
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = client.models.embed_content(
                model="gemini-embedding-001",
                contents=question,
            )
            return result.embeddings[0].values
        except genai_errors.APIError as e:
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1)))
        except (ConnectionError, TimeoutError) as e:
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1)))

    raise RetrievalError(f"Couldn't embed the question after {MAX_RETRIES} attempts: {last_error}")


def rewrite_query(original_question):
    """
    Asks the LLM to rewrite a weak question into one more likely to match
    real code - e.g. adding likely function/variable names, rephrasing
    vague wording into more code-like terms.

    If the rewrite call fails, we don't want to blow up the whole search
    (the original results are still usable) - so this returns the
    original question unchanged and lets the caller proceed without
    self-correction.
    """
    prompt = f"""You are helping search a codebase using semantic search.
The following question got weak search results. Rewrite it as a short,
more specific search query that's more likely to match real code
(e.g. likely function names, technical terms). Reply with ONLY the
rewritten query, nothing else.

Original question: {original_question}"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text.strip()
    except genai_errors.APIError as e:
        print(f"Query rewrite failed, using original question instead: {e}")
        return original_question


MAX_CODE_CHARS_PER_CHUNK = 2000  # keep the synthesis prompt from ballooning on huge functions


def synthesize_answer(question, results):
    """
    Turns raw retrieved code chunks into an actual written answer to the
    user's question, instead of making them read grep-style output
    themselves. This is a separate, best-effort step on top of retrieve()
    - if it fails (LLM outage, etc), the caller should still have the raw
    results to fall back on, so this never raises: it returns None on
    failure instead of blowing up a search that otherwise worked fine.
    """
    if not results:
        return None

    context_blocks = []
    for i, r in enumerate(results, start=1):
        code = r["code"]
        if len(code) > MAX_CODE_CHARS_PER_CHUNK:
            code = code[:MAX_CODE_CHARS_PER_CHUNK] + "\n... (truncated)"
        context_blocks.append(
            f"[{i}] {r['type']} {r['name']} ({r['file_path']}:{r['start_line']}-{r['end_line']})\n{code}"
        )

    prompt = f"""You are explaining a codebase to a developer who just asked a question about it.
Below are code chunks retrieved via semantic search that are likely relevant.
Write a short, direct explanation (2-4 sentences) of how the code answers
their question, referencing specific function/class names. If the
retrieved code only partially answers it, say so honestly instead of
guessing at behavior that isn't shown. Do not repeat the raw code back
verbatim - explain it.

Write in plain prose only - this renders as plain text in a terminal-style
UI, so do NOT use markdown formatting of any kind: no **bold**, no
numbered or bulleted lists, no headers, no backtick code spans. Just
normal sentences, the way you'd explain it out loud to a coworker.

Question: {question}

Retrieved code:
{chr(10).join(context_blocks)}

Answer:"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text.strip()
    except genai_errors.APIError as e:
        print(f"Answer synthesis failed, falling back to raw results only: {e}")
        return None


def retrieve(conn, question, top_k=5):
    """
    Given a plain-text question, finds the most relevant code chunks.
    If the first search comes back weak (nothing close enough in meaning),
    automatically rewrites the query and tries again once.

    Returns a dict with the results AND whether self-correction happened,
    so the UI can show that to the user later.

    Raises RetrievalError if the initial embedding call fails outright
    (there's nothing useful to return at that point) - callers (e.g. the
    API layer) should catch this and return a clean error to the user
    instead of a raw 500.
    """
    query_embedding = embed_query(question)  # raises RetrievalError on failure
    results = search_similar_chunks(conn, query_embedding, top_k=top_k)

    was_corrected = False
    used_query = question

    # Check if even the BEST result is too far away to be a real match.
    # (Also handles the empty-database case: no results at all counts
    # as "weak" and triggers a retry, which will also come back empty -
    # that's fine, the function still returns cleanly with results: [].)
    if not results or results[0]["distance"] > DISTANCE_THRESHOLD:
        rewritten = rewrite_query(question)
        if rewritten != question:  # rewrite_query only differs on success
            try:
                rewritten_embedding = embed_query(rewritten)
                retried_results = search_similar_chunks(conn, rewritten_embedding, top_k=top_k)

                # Only actually use the retry if it's genuinely better than the first attempt
                if retried_results and (not results or retried_results[0]["distance"] < results[0]["distance"]):
                    results = retried_results
                    was_corrected = True
                    used_query = rewritten
            except RetrievalError as e:
                # The original (weak) results are still better than nothing.
                print(f"Self-correction retry failed, keeping original results: {e}")

    return {
        "results": results,
        "was_corrected": was_corrected,
        "final_query": used_query,
    }