import sys
from storage import get_connection
from retriever import retrieve


def main():
    if len(sys.argv) < 2:
        print("Usage: python ask.py \"your question here\"")
        sys.exit(1)

    question = sys.argv[1]
    conn = get_connection("codebase.db")

    results = retrieve(conn, question, top_k=3)

    print(f"\nQuestion: {question}\n")
    print("Top matching code:\n")
    for r in results:
        print(f"[{r['type']}] {r['name']}  ({r['file_path']}, lines {r['start_line']}-{r['end_line']})")
        print(f"   distance: {r['distance']:.3f}")
        print()


if __name__ == "__main__":
    main()