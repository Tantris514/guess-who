"""Shared helpers for the level-agent editor scripts (imported inside the editor)."""
import json
import os
import re

ROOT = r"J:\Projets\Unreal_Projects\Guess Who"
MANIFEST = os.path.join(ROOT, "AssetGen", "manifest.json")
LAYOUT = os.path.join(ROOT, "Tools", "manor_layout.json")
LEVEL_DIR = os.path.join(ROOT, "Tools", "level")


def norm_name(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def load_manifest():
    """Approved manifest assets keyed by normalised name (empty dict if no manifest yet)."""
    try:
        with open(MANIFEST, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    out = {}
    for a in data.get("assets", []):
        if a.get("status", "approved") != "approved":
            continue
        out[norm_name(a.get("name", ""))] = a
    return out


def find_asset(manifest, *names):
    """First approved asset whose normalised name equals (or ends with / starts with) one of names."""
    for n in names:
        n = norm_name(n)
        if n in manifest:
            return manifest[n]
    for n in names:
        n = norm_name(n)
        for k, a in manifest.items():
            if k.endswith(n) or k.startswith(n) or n.endswith(k):
                return a
    return None


def file_of(asset, *keys):
    files = asset.get("files", {}) if asset else {}
    for k in keys:
        p = files.get(k)
        if p and os.path.exists(p):
            return p
    return None


def load_layout():
    with open(LAYOUT, encoding="utf-8") as fh:
        return json.load(fh)
