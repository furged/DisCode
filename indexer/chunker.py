
from tree_sitter_languages import get_parser

# tree-sitter needs a "parser" set up before it can read any code.
# We only want to build this once and reuse it, not redo it for every file.
_parser = None


def _get_parser():
    global _parser
    if _parser is None:
        _parser = get_parser("javascript")
    return _parser


def chunk_file(file_path):
    """
    Parses one file's code and pulls out each function/class as a separate chunk,
    instead of just splitting the text every N characters (which would cut functions in half).
    Returns a list of dicts, one per chunk.
    """
    parser = _get_parser()

    with open(file_path, "r", encoding="utf-8") as f:
        source_code = f.read()

    # tree-sitter works on raw bytes, not Python strings, so we encode it first.
    source_bytes = source_code.encode("utf-8")
    tree = parser.parse(source_bytes)

    chunks = []

    # "node" here means one piece of the parsed code structure (e.g. one function),
    # not Node.js the runtime.
    def visit(node):
        if node.type == "function_declaration":
            name_node = node.child_by_field_name("name")
            chunks.append({
                "type": "function",
                "name": name_node.text.decode("utf-8") if name_node else "anonymous",
                "code": node.text.decode("utf-8"),
                "start_line": node.start_point[0] + 1,  # tree-sitter counts lines from 0
                "end_line": node.end_point[0] + 1,
                "file_path": file_path,
            })
            return  # don't look inside this function for nested chunks, it's already one whole unit

        if node.type == "class_declaration":
            name_node = node.child_by_field_name("name")
            chunks.append({
                "type": "class",
                "name": name_node.text.decode("utf-8") if name_node else "anonymous",
                "code": node.text.decode("utf-8"),
                "start_line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1,
                "file_path": file_path,
            })
            return  # treat the whole class (including its methods) as one chunk for now

        # keep looking through children for more functions/classes
        for child in node.children:
            visit(child)

    visit(tree.root_node)
    return chunks