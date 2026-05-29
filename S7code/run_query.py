"""
run_query.py — Simple CLI to ask the Session 7 RAG agent a question.

Usage:
    python run_query.py "Your question here"
    python run_query.py                         # enters interactive mode

The gateway starts automatically if it is not already running.
"""

import asyncio
import sys
import os
from pathlib import Path

# ── Encoding fix for Windows ────────────────────────────────────────────────
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ── Make sure the S7code packages are importable ────────────────────────────
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import agent7
from gateway import ensure_gateway


# ── helpers ──────────────────────────────────────────────────────────────────

BANNER = """
╔══════════════════════════════════════════════════════════╗
║          Session 7 RAG Agent  —  Local Runner            ║
║  Memory: FAISS + JSON   |   Gateway: localhost:8107      ║
╚══════════════════════════════════════════════════════════╝
Type  exit / quit / q  to stop the interactive session.
"""


async def ask(query: str) -> str:
    """Run a single query through agent7 and return the final answer."""
    return await agent7.run(query)


async def interactive_loop():
    """REPL: keep asking until the user quits."""
    print(BANNER)
    while True:
        try:
            query = input("\n❓ Query: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[bye]")
            break

        if not query:
            continue
        if query.lower() in {"exit", "quit", "q"}:
            print("[bye]")
            break

        print()
        answer = await ask(query)
        print(f"\n{'─' * 78}")
        print("✅ ANSWER:")
        print(answer)
        print(f"{'─' * 78}")


async def main():
    # Refresh memory on starting a new session or running the solution again
    print("[memory] refreshing state …", end=" ", flush=True)
    import memory
    memory.clear()
    print("refreshed ✓")

    # Auto-start gateway if not running
    print("[gateway] checking …", end=" ", flush=True)
    ensure_gateway()
    print("ready ✓")

    if len(sys.argv) > 1:
        # Single-shot mode: query passed on the command line
        query = " ".join(sys.argv[1:])
        print(f"\n❓ Query: {query}\n")
        answer = await ask(query)
        print(f"\n{'─' * 78}")
        print("✅ ANSWER:")
        print(answer)
        print(f"{'─' * 78}")
    else:
        # Interactive REPL mode
        await interactive_loop()


if __name__ == "__main__":
    asyncio.run(main())
