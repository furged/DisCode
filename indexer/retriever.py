from embedder import client


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


def retrieve(conn, question, top_k=5):
    """
    Given a plain-text question, finds the most relevant code chunks
    already stored in the database.
    """
    from storage import search_similar_chunks

    query_embedding = embed_query(question)
    results = search_similar_chunks(conn, query_embedding, top_k=top_k)
    return results