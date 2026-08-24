from mcp.server.mcpserver import MCPServer
from storage import get_connection
from retriever import retrieve

# This creates the actual MCP server - the "walkie-talkie" that lets an
# AI app talk to your retrieval pipeline using the MCP standard.
server = MCPServer("codebase-explainer")

# Open one shared database connection when the server starts, reused for
# every question instead of reopening the file each time.
conn = get_connection("codebase.db")


@server.tool()
def search_codebase(question: str) -> str:
    """
    Search the indexed codebase for code relevant to a natural-language
    question. Automatically retries with a refined query if the first
    search comes back weak.
    """
    outcome = retrieve(conn, question, top_k=3)

    lines = []
    if outcome["was_corrected"]:
        lines.append(f"(Search was refined to: \"{outcome['final_query']}\")")

    for r in outcome["results"]:
        lines.append(
            f"[{r['type']}] {r['name']} "
            f"({r['file_path']}, lines {r['start_line']}-{r['end_line']}, "
            f"distance {r['distance']:.3f})"
        )
        lines.append(r["code"])
        lines.append("")  # blank line between chunks for readability

    return "\n".join(lines)


if __name__ == "__main__":
    # "stdio" means it talks to whatever launches it (like Claude Desktop)
    # through direct input/output text, not over the internet.
    server.run(transport="stdio")