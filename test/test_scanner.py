# test_scanner.py - Simple code scanner for comments and functions

import ast

def extract_comments_and_functions(file_path: str):
    """Extract comments and function definitions from a Python file."""
    with open(file_path, 'r') as f:
        tree = ast.parse(f.read())

    functions = []
    comments = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.append(node.name)
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Str):
            comments.append(node.value.s.strip())

    return {
        "functions": functions,
        "comments": comments
    }

if __name__ == "__main__":
    print(extract_comments_and_functions(__file__))