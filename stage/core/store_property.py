"""Path utilities for the right-click -> Store Property feature.

Three responsibilities, all working off the textual data_path strings the
right-click context produces:

  - resolve_value(path)         -> read current value of the path
  - apply_value(path, value)    -> walk to the parent, setattr the leaf
  - encode_value / decode_value -> serialize values to a (str, type-tag) pair
                                   so they round-trip through Studio.custom_paths

These are deliberately conservative for v1.0: handle int, float, bool,
string, enum, and (vector / color) tuples. Skip pointer-to-datablock and
nested custom-property dictionaries — those land in v1.x once the simple
path covers the common case.

Path strings come from the right-click context (see ops.store_property)
and look like one of:
    bpy.context.scene.render.engine
    bpy.data.objects["Cube"].modifiers["Subsurf"].levels
"""

from __future__ import annotations

import ast

import bpy

from ..utils.logger import get_logger


_log = get_logger()


# Type tags must round-trip via StoredProp.value_type's enum
INT = 'INT'
FLOAT = 'FLOAT'
BOOL = 'BOOL'
STRING = 'STRING'
ENUM = 'ENUM'
VECTOR = 'VECTOR'
COLOR = 'COLOR'


class UnsafePathError(ValueError):
    """Raised when a stored data_path contains constructs we don't allow."""


# Allowed AST nodes for a constrained path expression. Notably absent:
# Call (no function calls), BinOp/Compare/BoolOp (no expressions), Lambda /
# Comprehension / GeneratorExp / IfExp / Starred / FormattedValue / JoinedStr
# (no fancy syntax). The only things needed for real RNA paths are attribute
# access and constant subscripts.
_ALLOWED_NODES: tuple[type, ...] = (
    ast.Expression, ast.Name, ast.Attribute, ast.Subscript, ast.Constant,
    ast.Load, ast.Index,  # Index is for older Python AST shapes; harmless on 3.9+
)

# Only `bpy` is permitted as a root identifier. Everything else (e.g.
# `__import__`, builtins, captured names) is refused outright.
_ALLOWED_ROOTS: frozenset[str] = frozenset({"bpy"})


def _validate_ast(node: ast.AST) -> None:
    """Walk the parsed expression and raise on anything not in the allowlist.

    Constrains the path to attribute access (`a.b.c`) and constant subscripts
    (`a["key"]`, `a[3]`). Refuses calls, comprehensions, arithmetic, etc.
    This is the security boundary — once an AST passes here, eval() can be
    used safely on the original source string because we've proven it has
    no executable parts.
    """
    for child in ast.walk(node):
        if not isinstance(child, _ALLOWED_NODES):
            raise UnsafePathError(
                f"Disallowed AST node {type(child).__name__} in stored data_path"
            )
        if isinstance(child, ast.Subscript):
            # Subscript index must be a constant string or int. (On Python
            # 3.9+ the slice is the value directly; older Pythons wrap in
            # ast.Index which we permit above.)
            slice_node = getattr(child, "slice", None)
            if isinstance(slice_node, ast.Index):  # pre-3.9 compat
                slice_node = slice_node.value
            if not isinstance(slice_node, ast.Constant):
                raise UnsafePathError(
                    "Subscript index must be a literal string or int"
                )
            if not isinstance(slice_node.value, (str, int)):
                raise UnsafePathError(
                    f"Subscript index must be str or int, got {type(slice_node.value).__name__}"
                )
        if isinstance(child, ast.Name):
            if child.id not in _ALLOWED_ROOTS:
                raise UnsafePathError(
                    f"Disallowed root identifier {child.id!r} — only {sorted(_ALLOWED_ROOTS)} are permitted"
                )


def _eval_path(path: str):
    """Evaluate a stored 'bpy.*' path string into a runtime object.

    Hardened against malicious .blend files that ship a poisoned
    ``Studio.custom_paths[*].data_path`` aimed at executing arbitrary
    Python on Apply Studio. We parse the expression, walk the AST to
    confirm it's only attribute access + constant subscripts rooted in
    `bpy`, and only then evaluate. Anything more exotic raises
    UnsafePathError.
    """
    try:
        tree = ast.parse(path, mode="eval")
    except SyntaxError as e:
        raise UnsafePathError(f"Invalid path syntax: {e}") from e
    _validate_ast(tree)
    # eval is safe here — we've proven the AST has no executable parts.
    # Empty __builtins__ is belt-and-braces; the AST validator already blocks
    # everything dangerous.
    return eval(  # noqa: S307 — input is AST-validated above
        compile(tree, "<stage-data-path>", "eval"),
        {"bpy": bpy, "__builtins__": {}},
    )


def resolve_value(path: str):
    """Read the current value at `path`. Raises on bad or unsafe path."""
    return _eval_path(path)


def split_parent_and_attr(path: str) -> tuple[str, str]:
    """Split 'bpy.context.scene.render.engine' -> ('bpy.context.scene.render', 'engine').

    Handles bracket-suffixed paths too:
       'bpy.data.objects["Cube"]' -> ('bpy.data.objects', '"Cube"')
       'bpy.data.objects["Cube"].modifiers["Subsurf"].levels'
           -> ('bpy.data.objects["Cube"].modifiers["Subsurf"]', 'levels')
    """
    last_dot = path.rfind(".")
    last_bracket = path.rfind("[")
    if last_dot > last_bracket:
        return path[:last_dot], path[last_dot + 1:]
    if last_bracket > last_dot and path.endswith("]"):
        return path[:last_bracket], path[last_bracket + 1:-1]
    raise ValueError(f"Cannot split path: {path!r}")


def apply_value(path: str, value) -> None:
    """Walk to the parent object then setattr/setitem on the leaf segment."""
    parent_path, attr = split_parent_and_attr(path)
    parent = _eval_path(parent_path)
    if attr.startswith(("'", '"')) and attr.endswith(("'", '"')):
        # Bracket-style index (rare for our use, but be safe)
        key = ast.literal_eval(attr)
        parent[key] = value
    else:
        setattr(parent, attr, value)


def detect_type(value) -> str:
    """Map a Python value to a StoredProp.value_type tag."""
    if isinstance(value, bool):
        return BOOL
    if isinstance(value, int):
        return INT
    if isinstance(value, float):
        return FLOAT
    if isinstance(value, str):
        return STRING
    if hasattr(value, "__iter__"):
        # mathutils.Vector, Color, list, tuple of floats
        try:
            items = list(value)
            if items and all(isinstance(x, float) for x in items):
                return COLOR if len(items) in (3, 4) else VECTOR
        except TypeError:
            pass
    return STRING  # fallback — encoded as repr


def encode_value(value, type_tag: str | None = None) -> tuple[str, str]:
    """Return (string-encoded value, type tag) suitable for StoredProp."""
    if type_tag is None:
        type_tag = detect_type(value)

    if type_tag == BOOL:
        return ("True" if value else "False"), BOOL
    if type_tag in (INT, FLOAT, STRING, ENUM):
        return str(value), type_tag
    if type_tag in (VECTOR, COLOR):
        return repr(list(value)), type_tag
    return repr(value), type_tag


def decode_value(value_repr: str, type_tag: str):
    """Inverse of encode_value."""
    if type_tag == BOOL:
        return value_repr == "True"
    if type_tag == INT:
        return int(value_repr)
    if type_tag == FLOAT:
        return float(value_repr)
    if type_tag in (STRING, ENUM):
        return value_repr
    if type_tag in (VECTOR, COLOR):
        return ast.literal_eval(value_repr)
    return value_repr


def get_button_data_path(context) -> str | None:
    """Extract the full RNA path of a right-clicked property.

    Returns None if the context doesn't have a button_pointer / button_prop
    (i.e. user right-clicked something other than a property). Skips paths
    Blender can't fully resolve (containing "...").
    """
    button_pointer = getattr(context, "button_pointer", None)
    button_prop = getattr(context, "button_prop", None)
    if button_pointer is None or button_prop is None:
        return None
    if not hasattr(button_prop, "identifier"):
        return None

    pointer_path = button_pointer.__repr__()
    # Some UI items render with "..." in their repr — Blender can't fully
    # path-resolve them. Skip rather than store a broken path.
    if "..." in pointer_path:
        return None
    pointer_path = pointer_path.replace('"', "'")

    if hasattr(button_pointer, button_prop.identifier):
        full = f"{pointer_path}.{button_prop.identifier}"
    elif button_prop.identifier in button_pointer:
        full = f"{pointer_path}['{button_prop.identifier}']"
    else:
        return None

    # Normalize bpy.data.scenes['Scene'].x -> bpy.context.scene.x so the path
    # follows whichever scene is currently active.
    prefix = "bpy.data.scenes["
    if full.startswith(prefix) and "]." in full:
        idx = full.index("].")
        return "bpy.context.scene." + full[idx + len("]."):]
    return full
