from embedder import client
from storage import search_similar_chunks

# If the closest match's distance is above this number, we consider the
# retrieval "weak" and worth retrying with a better query.
# (This threshold was picked by eyeballing real results - lower distance
# is more similar. Tune this later once we have more real questions to test.)
DISTANCE_THRESHOLD = 0.85


def embed_query(question):
    """
    Turns a plain-text question into an embedding, the same way we embed
    code chunks - so we can compare "meaning" between the question and
    the stored code.
    """
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=question,
    )
    return result.embeddings[0].values


def rewrite_query(original_question):
    """
    Asks the LLM to rewrite a weak question into one more likely to match
    real code - e.g. adding likely function/variable names, rephrasing
    vague wording into more code-like terms.
    """
    prompt = f"""You are helping search a codebase using semantic search.
The following question got weak search results. Rewrite it as a short,
more specific search query that's more likely to match real code
(e.g. likely function names, technical terms). Reply with ONLY the
rewritten query, nothing else.

Original question: {original_question}"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text.strip()


def retrieve(conn, question, top_k=5):
    """
    Given a plain-text question, finds the most relevant code chunks.
    If the first search comes back weak (nothing close enough in meaning),
    automatically rewrites the query and tries again once.

    Returns a dict with the results AND whether self-correction happened,
    so the UI can show that to the user later.
    """
    query_embedding = embed_query(question)
    results = search_similar_chunks(conn, query_embedding, top_k=top_k)

    was_corrected = False
    used_query = question

    # Check if even the BEST result is too far away to be a real match
    if not results or results[0]["distance"] > DISTANCE_THRESHOLD:
        rewritten = rewrite_query(question)
        rewritten_embedding = embed_query(rewritten)
        retried_results = search_similar_chunks(conn, rewritten_embedding, top_k=top_k)

        # Only actually use the retry if it's genuinely better than the first attempt
        if retried_results and (not results or retried_results[0]["distance"] < results[0]["distance"]):
            results = retried_results
            was_corrected = True
            used_query = rewritten

    return {
        "results": results,
        "was_corrected": was_corrected,
        "final_query": used_query,
    }