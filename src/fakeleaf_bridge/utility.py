import json
import hashlib
import html
from bs4 import BeautifulSoup


def get_doc_path(structure, target_id, current_path=""):
    for doc in structure["docs"]:
        if doc["id"] == target_id:
            return current_path + doc["name"]

    for sub in structure["folders"]:
        result = get_doc_path(sub, target_id, current_path + sub["name"] + "/")
        if result:
            return result

def get_doc_id(structure, path):
    parts = path.split("/", 1)

    if len(parts) == 1:
        for doc in structure["docs"]:
            if doc["name"] == parts[0]:
                return doc["id"]
    else:
        folder_name, rest = parts
        for sub in structure["folders"]:
            if sub["name"] == folder_name:
                return get_doc_id(sub, rest)

def extract_structure(folder):
    result = {
        "id": folder["_id"],
        "name": folder["name"],
        "docs": [{"id": doc["_id"], "name": doc["name"]} for doc in folder.get("docs", [])],
        "folders": [extract_structure(sub) for sub in folder.get("folders", [])]
    }
    return result

def parse_project(args):
    root_folder = args[0]["project"]["rootFolder"][0]
    return extract_structure(root_folder)

def compute_doc_hash(lines: list[str]) -> str:
    content = "\n".join(lines)
    return hashlib.sha1(content.encode("utf-8")).hexdigest()

def cookies_to_header(cookie_jar) -> str:
    key = ""
    for c in cookie_jar:
         key += f"{c.name}={c.value}; "
    return key

def parse_sharejs_ot(raw: str) -> dict:
    inner = raw.strip("()'")
    bracket_idx = inner.find("[")
    if bracket_idx == -1:
        try:
            return {"operation_type": "retain", "count": int(inner)}
        except ValueError:
            raise ValueError(f"Unrecognized ShareJS OT format: {inner!r}")

    prefix = inner[:bracket_idx]
    data = json.loads(inner[bracket_idx:])

    if len(data) < 6:
        return {"operation_type": prefix, "raw": data}

    return {
        "operation_type": prefix,
        "null_field":     data[0],
        "lines":          data[1],
        "revision":       data[2],
        "extra_ops":      data[3],
        "metadata":       data[4],
        "ot_type":        data[5],
    }
def _parse_project_names(response):
    soup = BeautifulSoup(response.text, "html.parser")
    meta = soup.find("meta", {"name": "ol-prefetchedProjectsBlob"})
    if meta is None:
        raise Exception("No content")
    data = json.loads(html.unescape(str(meta["content"])))
    return data
