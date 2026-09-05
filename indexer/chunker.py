import os
from tree_sitter_languages import get_parser

# --- Language support -------------------------------------------------
#
# Every language has a different grammar, and different grammars name
# their "this is a function" / "this is a class" nodes differently, and
# expose the name differently too. So instead of one hardcoded set of
# node types (which only worked for JS), each language gets its own
# small config: which node types count as one whole chunk, and (for the
# odd ones out) how to dig out the name.
#
# This is the single source of truth for "which languages does DisCode
# understand" — walker.py imports EXTENSION_TO_LANGUAGE from here so the
# two can never drift apart the way JS/TS support did before.

EXTENSION_TO_LANGUAGE = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".py": "python",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
}

# Node types that should become one whole chunk in each language, i.e.
# "don't look inside this, treat it as one unit". Verified against real
# tree-sitter parses for each language, not guessed.
LANGUAGE_CONTAINER_TYPES = {
    "javascript": {"function_declaration", "class_declaration"},
    "typescript": {"function_declaration", "class_declaration"},
    "tsx": {"function_declaration", "class_declaration"},
    "python": {"function_definition", "class_definition"},
    "go": {"function_declaration", "method_declaration", "type_declaration"},
    "rust": {"function_item", "struct_item", "enum_item", "trait_item"},
    "java": {"class_declaration", "interface_declaration"},
    "ruby": {"method", "class", "module"},
    "c": {"function_definition", "struct_specifier"},
    "cpp": {"function_definition", "class_specifier", "struct_specifier"},
}

# Only JS/TS/TSX get the special "const foo = () => {}" handling, since
# arrow functions assigned to a variable are a JS/TS-specific pattern.
LANGUAGES_WITH_ARROW_FUNCTIONS = {"javascript", "typescript", "tsx"}

# Human-readable labels for chunk["type"], keyed by node type. Falls
# back to the raw node type if not listed here.
NODE_TYPE_LABELS = {
    "function_declaration": "function",
    "function_definition": "function",
    "function_item": "function",
    "method_declaration": "method",
    "method": "method",
    "class_declaration": "class",
    "class_definition": "class",
    "class_specifier": "class",
    "class": "class",
    "module": "module",
    "struct_specifier": "struct",
    "struct_item": "struct",
    "type_declaration": "type",
    "interface_declaration": "interface",
    "trait_item": "trait",
    "enum_item": "enum",
}

# tree-sitter needs a "parser" set up before it can read any code.
# We build one parser per language and reuse it, instead of rebuilding
# for every file.
_parsers = {}


def _get_parser_for(language):
    if language not in _parsers:
        _parsers[language] = get_parser(language)
    return _parsers[language]


def _find_first_identifier(node):
    """
    Fallback name-finder for languages where the name isn't exposed via
    a clean "name" field on the container node itself — e.g. in C/C++,
    `function_definition` wraps its name inside a `function_declarator`
    (or several nested declarators for pointer returns), so we walk
    down looking for the first identifier token instead of guessing a
    fixed field path.
    """
    if node.type in ("identifier", "field_identifier"):
        return node.text.decode("utf-8")
    for child in node.children:
        found = _find_first_identifier(child)
        if found:
            return found
    return None


def _extract_name(node):
    """
    Pulls a human-readable name off a declaration node. Tries the
    straightforward case first (a "name" field, which covers most
    languages), then falls back to language-specific quirks.
    """
    name_node = node.child_by_field_name("name")
    if name_node:
        return name_node.text.decode("utf-8")

    # C/C++ function_definition: the name is nested inside the
    # "declarator" field (function_declarator -> identifier), not
    # exposed directly on the function_definition node.
    declarator = node.child_by_field_name("declarator")
    if declarator:
        found = _find_first_identifier(declarator)
        if found:
            return found

    # Go type_declaration (e.g. `type Vector struct {...}`): the name
    # lives on the child type_spec node, not on type_declaration itself.
    for child in node.children:
        if child.type == "type_spec":
            inner_name = child.child_by_field_name("name")
            if inner_name:
                return inner_name.text.decode("utf-8")

    return "anonymous"


def _make_chunk(node, chunk_type, name, file_path):
    return {
        "type": chunk_type,
        "name": name,
        "code": node.text.decode("utf-8"),
        "start_line": node.start_point[0] + 1,  # tree-sitter counts lines from 0
        "end_line": node.end_point[0] + 1,
        "file_path": file_path,
    }


def chunk_file(file_path):
    """
    Parses one file's code and pulls out each function/class (or the
    closest equivalent in that language) as a separate chunk, instead
    of just splitting the text every N characters (which would cut
    functions in half). Returns a list of dicts, one per chunk.

    Supports JS, TS, TSX, Python, Go, Rust, Java, Ruby, C, and C++.
    Unrecognized extensions fall back to the JavaScript grammar, which
    will produce poor (likely empty) results — callers should check
    EXTENSION_TO_LANGUAGE before indexing a file if they need to know
    ahead of time whether it's actually supported.
    """
    ext = os.path.splitext(file_path)[1]
    language = EXTENSION_TO_LANGUAGE.get(ext, "javascript")
    container_types = LANGUAGE_CONTAINER_TYPES.get(language, set())
    supports_arrow_functions = language in LANGUAGES_WITH_ARROW_FUNCTIONS

    parser = _get_parser_for(language)

    with open(file_path, "r", encoding="utf-8") as f:
        source_code = f.read()

    # tree-sitter works on raw bytes, not Python strings, so we encode it first.
    source_bytes = source_code.encode("utf-8")
    tree = parser.parse(source_bytes)

    chunks = []

    # "node" here means one piece of the parsed code structure (e.g. one function),
    # not Node.js the runtime.
    def visit(node):
        if node.type in container_types:
            label = NODE_TYPE_LABELS.get(node.type, node.type)
            chunks.append(_make_chunk(node, label, _extract_name(node), file_path))
            return  # don't look inside — already captured as one whole unit

        # Arrow functions assigned to a variable, e.g.
        #   const increaseSpeed = (ball) => { ... }
        #   export const Button = () => { ... }
        # JS/TS-only: extremely common (especially React) and not a
        # named declaration type the way function_declaration is.
        if supports_arrow_functions and node.type == "variable_declarator":
            value_node = node.child_by_field_name("value")
            if value_node is not None and value_node.type in ("arrow_function", "function"):
                name_node = node.child_by_field_name("name")
                name = name_node.text.decode("utf-8") if name_node else "anonymous"
                # Use the enclosing declaration's span (not just the arrow
                # function's) so the chunk includes "const foo = " for
                # readability, and "export" if present.
                # Tree shape: [export_statement ->] (lexical_declaration | variable_declaration)
                #   -> variable_declarator (this node)
                target = node
                declaration = node.parent
                if declaration is not None and declaration.type in (
                    "lexical_declaration", "variable_declaration"
                ):
                    target = declaration
                    if declaration.parent is not None and declaration.parent.type == "export_statement":
                        target = declaration.parent
                chunks.append(_make_chunk(target, "function", name, file_path))
            return  # don't recurse into the arrow function body looking for nested chunks

        # keep looking through children for more functions/classes
        for child in node.children:
            visit(child)

    visit(tree.root_node)
    return chunks