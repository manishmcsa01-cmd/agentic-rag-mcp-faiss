"""
MCP server for EAGV3 Session 7.

Eleven tools, stdio transport:
    web_search, fetch_url, get_time, currency_convert,
    read_file, list_dir, create_file, update_file, edit_file,
    index_document, search_knowledge

web_search:        Tavily primary, DuckDuckGo fallback. Hard-capped at 5 results.
fetch_url:         crawl4ai only. Clean markdown via headless Chromium.
index_document:    Chunks a sandbox file or artifact and writes the chunks as
                   fact records into Memory, where they become FAISS-searchable.
search_knowledge:  Vector search over indexed facts. Same backend as
                   memory.read but exposed to the model as a tool.

Usage for tavily and duckduckgo is logged to ./usage.json with monthly
rollover and a soft cap of 950/1000 on Tavily.

File tools are sandboxed under ./sandbox/. Run:  python mcp_server.py
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from ddgs import DDGS
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Same-directory imports for the Memory and Artifact services so that the
# new index_document / search_knowledge tools can delegate into them.
import sys
sys.path.insert(0, str(Path(__file__).parent))
import artifacts as _artifacts  # noqa: E402
import memory as _memory  # noqa: E402

MAX_SEARCH_RESULTS = 5  # hard cap — Tavily prices per result

load_dotenv(Path(__file__).parent / ".env")

mcp = FastMCP("eagv3-s7-server")

SANDBOX = Path(__file__).parent / "sandbox"
SANDBOX.mkdir(exist_ok=True)

USAGE_PATH = Path(__file__).parent / "usage.json"
MONTHLY_CAP = 950  # leave 50/mo headroom on Tavily
_usage_lock = threading.Lock()


def _safe(path: str) -> Path:
    p = (SANDBOX / path).resolve()
    base = SANDBOX.resolve()
    if p != base and base not in p.parents:
        raise ValueError(f"Path '{path}' escapes the sandbox")
    return p


def _empty_usage(month: str) -> dict:
    return {
        "month": month,
        "tavily": {"count": 0, "errors": 0},
        "duckduckgo": {"count": 0, "errors": 0},
    }


def _load_usage() -> dict:
    month = datetime.now().strftime("%Y-%m")
    if not USAGE_PATH.exists():
        return _empty_usage(month)
    try:
        data = json.loads(USAGE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _empty_usage(month)
    if data.get("month") != month:
        return _empty_usage(month)
    for k in ("tavily", "duckduckgo"):
        data.setdefault(k, {"count": 0, "errors": 0})
    return data


def _save_usage(data: dict) -> None:
    USAGE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _bump(provider: str, field: str = "count") -> None:
    with _usage_lock:
        data = _load_usage()
        data[provider][field] = data[provider].get(field, 0) + 1
        _save_usage(data)


def _under_cap(provider: str) -> bool:
    return _load_usage()[provider]["count"] < MONTHLY_CAP


def _tavily_search(query: str, max_results: int) -> list[dict]:
    from tavily import TavilyClient

    client = TavilyClient(os.environ["TAVILY_API_KEY"])
    resp = client.search(query=query, max_results=max_results, search_depth="advanced")
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", ""),
        }
        for r in resp.get("results", [])
    ]


def _ddg_search(query: str, max_results: int) -> list[dict]:
    hits: list[dict] = []
    with DDGS() as ddgs:
        for backend in ("auto", "html", "lite"):
            try:
                hits = list(ddgs.text(query, max_results=max_results, backend=backend))
            except Exception:
                hits = []
            if hits:
                break
    return [
        {
            "title": h.get("title", ""),
            "url": h.get("href", ""),
            "snippet": h.get("body", ""),
        }
        for h in hits
    ]


async def _crawl4ai_fetch(url: str) -> dict:
    """Try crawl4ai/Playwright first; fall back to plain httpx if browser missing."""
    # ── Attempt 1: crawl4ai (headless Chromium) ──────────────────────────────
    try:
        from crawl4ai import AsyncWebCrawler

        saved_fd = os.dup(1)
        os.dup2(2, 1)
        try:
            async with AsyncWebCrawler(verbose=False) as crawler:
                r = await crawler.arun(url=url)
        finally:
            os.dup2(saved_fd, 1)
            os.close(saved_fd)

        md = r.markdown
        raw = (
            getattr(md, "raw_markdown", None)
            or getattr(md, "fit_markdown", None)
            or md
            or r.cleaned_html
            or r.html
            or ""
        )
        text = str(raw)
        return {
            "status": int(getattr(r, "status_code", None) or 200),
            "content_type": "text/markdown",
            "length_bytes": len(text.encode("utf-8")),
            "text": text,
            "fetcher": "crawl4ai",
        }

    except Exception as crawl_err:
        # Playwright binary missing, import error, or network error — fall through
        err_msg = str(crawl_err)
        if "Executable doesn't exist" not in err_msg and "playwright" not in err_msg.lower():
            # Real crawl4ai error (not a missing-browser issue) — still try httpx
            pass

    # ── Attempt 2: plain httpx (no JavaScript rendering) ─────────────────────
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
    }
    async with httpx.AsyncClient(
        timeout=30,
        follow_redirects=True,
        headers=headers,
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    # Very light HTML -> text strip (remove tags)
    import re as _re
    raw_html = resp.text
    # strip scripts/styles
    raw_html = _re.sub(r"<(script|style)[^>]*>.*?</\1>", "", raw_html, flags=_re.S | _re.I)
    # strip all remaining tags
    text = _re.sub(r"<[^>]+>", " ", raw_html)
    # collapse whitespace
    text = " ".join(text.split())

    return {
        "status": resp.status_code,
        "content_type": resp.headers.get("content-type", "text/html"),
        "length_bytes": len(text.encode("utf-8")),
        "text": text,
        "fetcher": "httpx-fallback (Playwright not installed — run: python -m playwright install chromium)",
    }


@mcp.tool()
def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web (Tavily primary, DDG fallback). Hard-capped at 5 results. Example: web_search("python asyncio tutorial", 3)."""
    max_results = max(1, min(max_results, MAX_SEARCH_RESULTS))
    if os.environ.get("TAVILY_API_KEY") and _under_cap("tavily"):
        try:
            results = _tavily_search(query, max_results)
            if results:
                _bump("tavily")
                return results
        except Exception:
            _bump("tavily", "errors")
    results = _ddg_search(query, max_results)
    _bump("duckduckgo")
    return results


@mcp.tool()
async def fetch_url(url: str, timeout: int = 20) -> dict:
    """Fetch clean markdown from a URL via crawl4ai (headless Chromium). Example: fetch_url("https://example.com")."""
    return await _crawl4ai_fetch(url)


@mcp.tool()
def get_time(timezone: str = "UTC") -> dict:
    """Current time in a named IANA timezone. Example: get_time("Asia/Kolkata")."""
    tz = ZoneInfo(timezone)
    now = datetime.now(tz)
    offset = now.utcoffset()
    offset_hours = offset.total_seconds() / 3600 if offset else 0.0
    return {
        "iso": now.isoformat(),
        "human": now.strftime("%A, %d %B %Y %H:%M:%S %Z"),
        "timezone": timezone,
        "offset_hours": offset_hours,
    }


@mcp.tool()
def currency_convert(amount: float, from_currency: str, to_currency: str) -> dict:
    """Convert money between ISO-3 currencies via frankfurter.dev. Example: currency_convert(100, "USD", "INR")."""
    f = from_currency.upper()
    t = to_currency.upper()
    url = f"https://api.frankfurter.dev/v1/latest?amount={amount}&base={f}&symbols={t}"
    with httpx.Client(timeout=20, follow_redirects=True) as client:
        r = client.get(url)
        r.raise_for_status()
        data = r.json()
    converted = data["rates"][t]
    return {
        "amount": amount,
        "from": f,
        "to": t,
        "rate": converted / amount if amount else 0.0,
        "converted": converted,
        "date": data["date"],
        "source": "frankfurter.dev",
    }


@mcp.tool()
def read_file(path: str) -> dict:
    """Read a UTF-8 text file from the sandbox. Example: read_file("notes.txt")."""
    p = _safe(path)
    text = p.read_text(encoding="utf-8")
    return {
        "path": path,
        "size_bytes": p.stat().st_size,
        "content": text,
        "encoding": "utf-8",
    }


@mcp.tool()
def list_dir(path: str = ".") -> dict:
    """List a directory inside the sandbox. Example: list_dir(".")."""
    # NOTES_RUNS §6 (1): a list[dict] return was being rendered as one MCP
    # TextContent per entry. After agent7.py's 300-char clip and decision.py's
    # downstream slicing, only the first 2-3 file dicts survived into the
    # Decision prompt, and Decision then declared the directory complete at
    # whatever it could see. Returning a single dict with `count` and a flat
    # `names` list keeps the cardinality visible even under truncation.
    p = _safe(path)
    entries = []
    names: list[str] = []
    for child in sorted(p.iterdir()):
        is_dir = child.is_dir()
        entries.append({
            "name": child.name,
            "type": "dir" if is_dir else "file",
            "size_bytes": 0 if is_dir else child.stat().st_size,
        })
        names.append(child.name)
    return {"path": path, "count": len(entries), "names": names, "entries": entries}


@mcp.tool()
def create_file(path: str, content: str) -> dict:
    """Create a new file in the sandbox; errors if it exists. Example: create_file("hello.txt", "hi")."""
    p = _safe(path)
    if p.exists():
        raise ValueError(f"File '{path}' already exists")
    if not p.parent.exists():
        raise ValueError(f"Parent directory of '{path}' does not exist")
    p.write_text(content, encoding="utf-8")
    return {"ok": True, "path": path, "size_bytes": p.stat().st_size}


@mcp.tool()
def update_file(path: str, content: str) -> dict:
    """Overwrite an existing sandbox file. Example: update_file("hello.txt", "new body")."""
    p = _safe(path)
    if not p.exists():
        raise ValueError(f"File '{path}' does not exist")
    p.write_text(content, encoding="utf-8")
    return {"ok": True, "path": path, "size_bytes": p.stat().st_size}


@mcp.tool()
def edit_file(path: str, find: str, replace: str, replace_all: bool = False) -> dict:
    """Find-and-replace inside a sandbox file. Example: edit_file("hello.txt", "foo", "bar")."""
    p = _safe(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(find)
    if count == 0:
        raise ValueError(f"'{find}' not found in '{path}'")
    if count > 1 and not replace_all:
        raise ValueError(
            f"'{find}' occurs {count} times in '{path}'; pass replace_all=True"
        )
    new_text = text.replace(find, replace) if replace_all else text.replace(find, replace, 1)
    p.write_text(new_text, encoding="utf-8")
    replacements = count if replace_all else 1
    return {
        "ok": True,
        "path": path,
        "replacements": replacements,
        "size_bytes": p.stat().st_size,
    }


# ── document indexing (Session 7) ───────────────────────────────────────────

def _read_for_index(path: str) -> tuple[str, str]:
    """Return (content, source_label) for an indexable file or artifact."""
    if path.startswith("art:"):
        return _artifacts.get_bytes(path).decode("utf-8", errors="replace"), path
    p = _safe(path)
    ext = p.suffix.lower()
    if ext == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(p)
        text_parts = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
        return "\n".join(text_parts), f"sandbox:{path}"
    else:
        return p.read_text(encoding="utf-8", errors="replace"), f"sandbox:{path}"


def _chunk_text(text: str, size: int = 400, overlap: int = 80) -> list[tuple[str, int]]:
    """Sliding-window chunking by word count, returning list of (chunk_text, char_offset) tuples."""
    import re
    word_matches = list(re.finditer(r'\S+', text))
    if not word_matches:
        return []
    chunks: list[tuple[str, int]] = []
    stride = max(1, size - overlap)
    i = 0
    while i < len(word_matches):
        end_idx = min(i + size, len(word_matches))
        chunk_words = word_matches[i:end_idx]
        
        # Compute start and end characters from original text
        start_char = chunk_words[0].start()
        end_char = chunk_words[-1].end()
        chunk_str = text[start_char:end_char]
        
        chunks.append((chunk_str, start_char))
        if i + size >= len(word_matches):
            break
        i += stride
    return chunks


@mcp.tool()
def index_document(path: str, chunk_size: int = 400, overlap: int = 80) -> dict:
    """Chunk a sandbox file or artifact and write each chunk into Memory as a searchable `fact`. Use this when the content must remain retrievable across later turns or runs (an indexing step before later vector queries). For one-shot inspection of a known file's contents in this turn, prefer `read_file` instead. Example: index_document("notes/spec.md")."""
    text, source = _read_for_index(path)
    if not text.strip():
        return {"path": path, "source": source, "chunks_indexed": 0, "warning": "empty content"}
    chunks = _chunk_text(text, size=chunk_size, overlap=overlap)
    run_id = f"index-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    indexed = 0
    for i, (chunk, offset) in enumerate(chunks):
        preview = chunk[:120].replace("\n", " ")
        descriptor = f"[{source} chunk {i+1}/{len(chunks)}] {preview}"
        _memory.add_fact(
            descriptor=descriptor,
            value={
                "chunk": chunk,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "source": source,
                "chunk_offset": offset,
            },
            source=source,
            run_id=run_id,
        )
        indexed += 1
    return {
        "path": path,
        "source": source,
        "chunks_indexed": indexed,
        "chunk_size": chunk_size,
        "overlap": overlap,
    }


@mcp.tool()
def index_directory(path: str, chunk_size: int = 400, overlap: int = 80) -> dict:
    """Recursively index all text, markdown, and PDF files inside a sandbox directory. Skip duplicates by content hash. Example: index_directory("corpus")."""
    import hashlib
    p = _safe(path)
    if not p.exists() or not p.is_dir():
        raise ValueError(f"Directory '{path}' does not exist or is not a directory")
        
    db_path = Path(__file__).parent / "state" / "indexed_files.json"
    db_path.parent.mkdir(exist_ok=True)
    if db_path.exists():
        try:
            indexed_db = json.loads(db_path.read_text(encoding="utf-8"))
        except Exception:
            indexed_db = {}
    else:
        indexed_db = {}
        
    indexed_files = 0
    total_chunks = 0
    skipped_duplicates = 0
    
    for root, _, files in os.walk(p):
        for file in files:
            file_path = Path(root) / file
            ext = file_path.suffix.lower()
            if ext not in (".md", ".txt", ".pdf"):
                continue
                
            try:
                rel_path = str(file_path.relative_to(SANDBOX))
            except ValueError:
                rel_path = str(file_path)
                
            try:
                content_bytes = file_path.read_bytes()
                file_hash = hashlib.sha256(content_bytes).hexdigest()
            except Exception:
                continue
                
            if rel_path in indexed_db and indexed_db[rel_path] == file_hash:
                skipped_duplicates += 1
                continue
                
            try:
                doc_res = index_document(rel_path, chunk_size=chunk_size, overlap=overlap)
                chunks_count = doc_res.get("chunks_indexed", 0)
                if chunks_count > 0:
                    indexed_db[rel_path] = file_hash
                    indexed_files += 1
                    total_chunks += chunks_count
            except Exception as e:
                print(f"[index_directory] Failed to index {rel_path}: {e}")
                
    db_path.write_text(json.dumps(indexed_db, indent=2), encoding="utf-8")
    
    return {
        "directory": path,
        "files_indexed": indexed_files,
        "total_chunks_indexed": total_chunks,
        "duplicates_skipped": skipped_duplicates,
    }


@mcp.tool()
def search_knowledge(query: str, k: int = 5) -> list[dict]:
    """Vector search over indexed `fact` chunks. Returns up to k ranked chunks with provenance. Call this rather than re-fetching URLs or re-reading source files whenever Memory already contains indexed chunks for the topic — that is the whole point of having indexed the corpus. Example: search_knowledge("authentication flow", 5)."""
    items = _memory.read(query, kinds=["fact"], top_k=k)
    return [
        {
            "id": item.id,
            "descriptor": item.descriptor,
            "source": item.source,
            "chunk": item.value.get("chunk") or "",
            "chunk_preview": item.value.get("chunk") or "",
            "metadata": {k_: v for k_, v in item.value.items() if k_ != "chunk"},
        }
        for item in items
    ]


@mcp.tool()
def semantic_search(query: str, k: int = 5) -> list[dict]:
    """Perform embedding similarity search over all indexed documents. Returns up to k matched chunks with full text, original source path, offsets, and metadata. Example: semantic_search("credit assignment problem", 3)."""
    items = _memory.read(query, kinds=["fact"], top_k=k)
    results = []
    for item in items:
        val = item.value or {}
        chunk_text = val.get("chunk") or ""
        source_file = val.get("source") or item.source
        chunk_offset = val.get("chunk_offset") or 0
        
        meta = {
            "source_file": source_file,
            "chunk_index": val.get("chunk_index"),
            "total_chunks": val.get("total_chunks"),
            "chunk_offset": chunk_offset,
        }
        for k_, v_ in val.items():
            if k_ not in ("chunk", "source", "chunk_index", "total_chunks", "chunk_offset"):
                meta[k_] = v_
                
        results.append({
            "item_id": item.id,
            "descriptor": item.descriptor,
            "chunk_text": chunk_text,
            "source_file": source_file,
            "chunk_offset": chunk_offset,
            "metadata": meta
        })
    return results


@mcp.tool()
def corpus_stats() -> dict:
    """Return comprehensive analytics of the indexed RAG corpus, including unique file count, chunk count, embedding count, size in bytes, and file type distributions. Example: corpus_stats()."""
    items = _memory._load()
    fact_items = [i for i in items if i.kind == "fact" and "chunk" in (i.value or {})]
    
    unique_sources = set()
    total_chunks = len(fact_items)
    embedding_count = sum(1 for i in items if i.embedding is not None)
    file_types = {}
    total_size_bytes = 0
    
    for item in fact_items:
        val = item.value or {}
        src = val.get("source") or ""
        if src:
            unique_sources.add(src)
            
    for src in unique_sources:
        if src.startswith("sandbox:"):
            path_str = src[len("sandbox:"):]
            p = SANDBOX / path_str
            if p.exists() and p.is_file():
                ext = p.suffix.lower()
                file_types[ext] = file_types.get(ext, 0) + 1
                total_size_bytes += p.stat().st_size
            else:
                ext = Path(path_str).suffix.lower()
                file_types[ext] = file_types.get(ext, 0) + 1
        else:
            ext = Path(src).suffix.lower() or ".txt"
            file_types[ext] = file_types.get(ext, 0) + 1
            
    return {
        "corpus_files_count": len(unique_sources),
        "total_chunks_count": total_chunks,
        "total_embeddings_count": embedding_count,
        "total_size_bytes": total_size_bytes,
        "file_type_distribution": file_types,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
