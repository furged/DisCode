import sqlite3
import json
import sqlite_vec

EMBEDDING_SIZE = 3072


def get_connection(db_path="codebase.db"):
    """
    Opens a connection to our SQLite database file and loads the sqlite-vec
    extension, which adds the ability to search by embedding similarity.
    """
    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn


def init_db(conn):
    """
    Creates the tables we need, if they don't already exist.
    - chunks: the actual code + metadata (name, file, line numbers)
    - chunk_vectors: a special sqlite-vec table just for fast similarity search
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY,
            type TEXT,
            name TEXT,
            code TEXT,
            start_line INTEGER,
            end_line INTEGER,
            file_path TEXT
        )
    """)

    # NOTE: sqlite-vec's virtual table syntax (`FLOAT[N]`) doesn't support
    # parameterized column definitions the way normal SQL values do, so
    # EMBEDDING_SIZE has to be interpolated directly rather than passed
    # as a "?" placeholder. This is safe ONLY because EMBEDDING_SIZE is a
    # hardcoded int constant defined at the top of this file, not
    # user-controlled input - if that ever changes, this needs to go
    # back to being parameterized.
    conn.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS chunk_vectors USING vec0("
        "chunk_id INTEGER PRIMARY KEY, "
        f"embedding FLOAT[{EMBEDDING_SIZE}])"
    )

    conn.commit()


def clear_chunks(conn):
    """
    Wipes all existing chunks/vectors so a re-index replaces the old data
    instead of stacking on top of it. Without this, running run.py twice
    on the same repo silently doubles everything in the db (found this
    the hard way testing the chunker changes - update() showed up twice
    with identical distances because the old 20-chunk run was never
    cleared before the new 25-chunk run added its own copies).
    """
    conn.execute("DELETE FROM chunk_vectors")
    conn.execute("DELETE FROM chunks")
    conn.commit()


def save_chunks(conn, chunks):
    """
    Saves a list of embedded chunks (with an "embedding" field already on
    each one) into the database - both the readable info and the vector
    for similarity search.
    """
    for chunk in chunks:
        cursor = conn.execute(
            """
            INSERT INTO chunks (type, name, code, start_line, end_line, file_path)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                chunk["type"],
                chunk["name"],
                chunk["code"],
                chunk["start_line"],
                chunk["end_line"],
                chunk["file_path"],
            ),
        )
        chunk_id = cursor.lastrowid

        # sqlite-vec wants the embedding as a JSON array string
        embedding_json = json.dumps(chunk["embedding"])
        conn.execute(
            "INSERT INTO chunk_vectors (chunk_id, embedding) VALUES (?, ?)",
            (chunk_id, embedding_json),
        )

    conn.commit()


def search_similar_chunks(conn, query_embedding, top_k=5):
    """
    Given a query embedding (e.g. from a user's question), finds the
    most similar code chunks already stored in the database.
    Returns the top_k closest matches, most similar first.
    """
    query_json = json.dumps(query_embedding)

    rows = conn.execute(
        """
        SELECT chunks.name, chunks.type, chunks.code, chunks.file_path,
               chunks.start_line, chunks.end_line, chunk_vectors.distance
        FROM chunk_vectors
        JOIN chunks ON chunks.id = chunk_vectors.chunk_id
        WHERE chunk_vectors.embedding MATCH ?
          AND k = ?
        ORDER BY chunk_vectors.distance
        """,
        (query_json, top_k),
    ).fetchall()

    results = []
    for row in rows:
        results.append({
            "name": row[0],
            "type": row[1],
            "code": row[2],
            "file_path": row[3],
            "start_line": row[4],
            "end_line": row[5],
            "distance": row[6],  # lower distance = more similar
        })
    return results