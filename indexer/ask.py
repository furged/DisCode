import sys
from storage import get_connection
from retriever import retrieve


def main():
    if len(sys.argv) < 2:
        print("Usage: python ask.py \"your question here\"")
        sys.exit(1)

    question = sys.argv[1]
    conn = get_connection("codebase.db")

    outcome = retrieve(conn, question, top_k=3)

    print(f"\nQuestion: {question}")
    if outcome["was_corrected"]:
        print(f"(Initial search was weak - retried with: \"{outcome['final_query']}\")")
    print()

    for r in outcome["results"]:
        print(f"[{r['type']}] {r['name']}  ({r['file_path']}, lines {r['start_line']}-{r['end_line']})")
        print(f"   distance: {r['distance']:.3f}")
        print()


if __name__ == "__main__":
    main()