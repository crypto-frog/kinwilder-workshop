"""Resident-owned, opt-in exhibits for a small Internet commons.

No resident code is imported or executed by the publisher. Files must be bounded,
regular, world-readable and owned by the resident whose name will be displayed.
This module is also usable outside Outpost; collect() accepts simple resident objects
with name, uid and home attributes. See README.md and LICENSE.
"""
from __future__ import annotations

import html
import json
import os
import re
import stat
import time
from itertools import islice
from pathlib import Path
from urllib.parse import urlsplit

SLUG = re.compile(r"^[a-z][a-z0-9-]{1,23}$")
FILE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
MAX_BYTES, MAX_WORKS, PER_RESIDENT = 32768, 256, 8
KINDS = ("ascii", "note", "sound", "tool")
LICENSES = ("All rights reserved", "CC0-1.0", "CC-BY-4.0", "MIT")
CONTROL = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(\x07|\x1b\\)?|[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def clean(text, limit=1000):
    return CONTROL.sub("", str(text)).replace("\r", "")[:limit]


def read_owned(path, uid, limit=MAX_BYTES):
    """Read public data without following the final symlink or opening a FIFO."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != uid or not info.st_mode & stat.S_IROTH or info.st_size > limit:
                return None
            data = os.read(fd, limit + 1)
            return data if len(data) <= limit else None
        finally:
            os.close(fd)
    except OSError:
        return None


def public_file(path, uid, limit):
    """Check download metadata without reading megabytes just to list a link."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            info = os.fstat(fd)
            return stat.S_ISREG(info.st_mode) and info.st_uid == uid and bool(info.st_mode & stat.S_IROTH) and info.st_size <= limit
        finally:
            os.close(fd)
    except OSError:
        return False


def text(value, name, limit, required=False):
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError(f"{name} must be text, at most {limit} characters")
    value = clean(value, limit).strip()
    if required and not value:
        raise ValueError(f"{name} is required")
    return value


def validate(data):
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("outpost.json must have version: 1")
    kind = data.get("kind", "ascii")
    if kind not in KINDS:
        raise ValueError("kind must be ascii, note, sound or tool")
    license_name = data.get("license", LICENSES[0])
    if license_name not in LICENSES:
        raise ValueError("choose a supported licence, or All rights reserved")
    result = dict(version=1, kind=kind, license=license_name,
                  title=text(data.get("title", ""), "title", 80, True),
                  summary=text(data.get("summary", ""), "summary", 400),
                  note=text(data.get("note", ""), "note", 5000))
    frames = data.get("frames", [])
    if not isinstance(frames, list) or len(frames) > 4:
        raise ValueError("use at most four ASCII frames")
    if kind == "ascii" and not frames:
        raise ValueError("an ASCII exhibit needs at least one frame")
    for frame in frames:
        if not isinstance(frame, list) or not 1 <= len(frame) <= 10:
            raise ValueError("each frame needs 1-10 rows")
        if not all(isinstance(row, str) and len(row) <= 32 and re.fullmatch(r"[ -~]*", row) for row in frame):
            raise ValueError("art uses printable ASCII, at most 32 columns")
    width = max((len(row) for frame in frames for row in frame), default=0)
    height = max((len(frame) for frame in frames), default=0)
    result["frames"] = [[row.ljust(width) for row in frame] + [" " * width] * (height - len(frame)) for frame in frames]
    colors = data.get("colors", [])
    if colors and (not isinstance(colors, list) or len(colors) != len(frames)):
        raise ValueError("colors must have one mask per frame")
    masks = []
    for i, frame in enumerate(result["frames"]):
        mask = colors[i] if colors else []
        if not isinstance(mask, list) or len(mask) > height or not all(isinstance(row, str) and len(row) <= width and re.fullmatch(r"[ abcd]*", row) for row in mask):
            raise ValueError("color masks use only space and a/b/c/d")
        if mask:
            masks.append([row.ljust(width) for row in mask] + [" " * width] * (height - len(mask)))
        else:
            masks.append(["".join("b" if c in "*+o[]" else "a" if c in "~_-/\\|" else "c" if c in "()^" else " " for c in row) for row in frame])
    result["colors"] = masks
    interval = data.get("interval_ms", 1000)
    if isinstance(interval, bool) or not isinstance(interval, int) or not 500 <= interval <= 4000:
        raise ValueError("interval_ms must be 500-4000")
    result["interval_ms"] = interval
    files = data.get("files", ["README.md"])
    if not isinstance(files, list) or len(files) > 12 or not all(isinstance(f, str) and FILE.fullmatch(f) and f != "outpost.json" for f in files):
        raise ValueError("files must be up to 12 plain filenames (no paths or dotfiles)")
    result["files"] = list(dict.fromkeys(files))
    links = data.get("links", [])
    if not isinstance(links, list) or len(links) > 4:
        raise ValueError("include at most four trail links")
    result["links"] = []
    for link in links:
        if not isinstance(link, dict):
            raise ValueError("each link needs a title, url and note")
        url = text(link.get("url", ""), "url", 400, True)
        parsed = urlsplit(url)
        if parsed.scheme not in ("https", "http", "gemini", "gopher") or not parsed.hostname or parsed.username or parsed.password or any(c.isspace() for c in url):
            raise ValueError("trail links must be ordinary web, Gemini or Gopher URLs")
        result["links"].append(dict(url=url, title=text(link.get("title", ""), "link title", 80, True), note=text(link.get("note", ""), "link note", 300)))
    return result


def collect(people):
    works = []
    for resident in sorted(people, key=lambda r: r.name):
        if not re.fullmatch(r"[a-z][a-z0-9]{1,15}", resident.name):
            continue
        folder = Path(resident.home) / "public_html/workshop"
        try:
            children = sorted(islice(folder.iterdir(), 64), key=lambda p: p.name)
        except OSError:
            continue
        count = 0
        for child in children:
            if count >= PER_RESIDENT or len(works) >= MAX_WORKS:
                break
            if not SLUG.fullmatch(child.name) or child.is_symlink():
                continue
            raw = read_owned(child / "outpost.json", resident.uid)
            if raw is None:
                continue
            try:
                data = validate(json.loads(raw))
            except (ValueError, TypeError, UnicodeError, RecursionError):
                continue
            # Only list downloads that satisfy the same public ownership rule.
            downloads = [name for name in data["files"] if public_file(child / name, resident.uid, 8 * 1024 * 1024)]
            archive = public_file(child / "source.zip", resident.uid, 8 * 1024 * 1024)
            try:
                updated = int((child / "outpost.json").stat().st_mtime)
            except OSError:
                continue
            works.append(dict(data, author=resident.name, slug=child.name,
                              id=f"{resident.name}/{child.name}",
                              url=f"/~{resident.name}/workshop/{child.name}/",
                              updated=updated, downloads=downloads, archive=archive))
            count += 1
    return works


def painted(frame, colors):
    """Fixed class names only, with HTML-escaped resident text."""
    output = []
    for y, row in enumerate(frame):
        line, run, previous = [], [], None
        for x, glyph in enumerate(row):
            color = colors[y][x]
            if color != previous and run:
                line.append(f'<span class="ink-{previous.strip() or "plain"}">{html.escape("".join(run))}</span>')
                run = []
            previous = color
            run.append(glyph)
        if run:
            line.append(f'<span class="ink-{previous.strip() or "plain"}">{html.escape("".join(run))}</span>')
        output.append("".join(line))
    return "\n".join(output)


def project_page(work, author, slug):
    """A resident's publication is independently readable outside the shared index."""
    esc = html.escape
    art = painted(work["frames"][0], work["colors"][0]) if work["frames"] else ""
    links = " ".join(f'<a href="{esc(name, quote=True)}">[ {esc(name)} ]</a>' for name in work["files"])
    return f'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(work['title'])}</title>
<script src="/appearance.js?v=ascii1"></script><link rel="stylesheet" href="/tints.css?v=ascii1">
<link rel="stylesheet" href="/style.css?v=ascii1"><link rel="stylesheet" href="/commons.css?v=workshop1">
<main><p><a href="/commons/">[ the Commons ]</a> / <a href="/~{author}/">~{author}</a></p>
<h1>{esc(work['title'])}</h1><p>{esc(work['summary'])}</p><pre>{art}</pre>
<pre class="work-note">{esc(work['note'])}</pre><p>Licence: {esc(work['license'])}</p>
<p><a href="source.zip">[ portable source ]</a> {links}</p>
<p><code>workshop fork {author}/{slug} my-version</code> (when its licence permits)</p></main></html>'''


PROMPTS = (
    "Write a small program that makes an ordinary job less annoying.",
    "Give a place that does not exist a sound, a sign, or a field note.",
    "Build an unnecessary contraption and document its mechanism.",
    "Find an obscure corner of Gemini or Gopher worth investigating. Leave a trail.",
    "Tell a story in four ASCII frames.",
    "Fork a permitted work and take it somewhere its author did not expect.",
)


def prompt(when=None):
    stamp = time.gmtime(when if when is not None else time.time())
    return PROMPTS[(int(time.strftime("%G", stamp)) * 53 + int(time.strftime("%V", stamp))) % len(PROMPTS)]
