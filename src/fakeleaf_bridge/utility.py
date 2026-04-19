from pprint import pprint
import sys
import json
import hashlib

def _get_tty_path() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1]
    return "/dev/stderr"

def compute_doc_hash(lines: list[str]) -> str:
    content = "\n".join(lines)
    return hashlib.sha1(content.encode("utf-8")).hexdigest()

def cookies_to_header(cookie_jar) -> str:
    key = ""
    for c in cookie_jar:
         key += f"{c.name}={c.value}; "
    return key

def print_other_terminal(arg,debug = True) -> None:
    if not debug:
        return
    tty_path = _get_tty_path()
    if tty_path == "/dev/stderr":
        pprint(arg)
    with open(tty_path, "w") as tty:
        pprint(arg, tty)


def parse_sharejs_ot(raw: str) -> dict:
    inner = raw.strip("()'")

    bracket_idx = inner.find("[")

    if bracket_idx == -1:
        try:
            return {
                "operation_type": "retain",
                "count": int(inner),
            }
        except ValueError:
            raise ValueError(f"Unrecognized ShareJS OT format: {inner!r}")

    prefix = inner[:bracket_idx]       # e.g. "2+"
    json_str = inner[bracket_idx:]     # e.g. "[null, [...], 30, ...]"

    data = json.loads(json_str)

    return {
        "operation_type": prefix,
        "null_field":     data[0],
        "lines":          data[1],
        "revision":       data[2],
        "extra_ops":      data[3],
        "metadata":       data[4],
        "ot_type":        data[5],
    }


