"""
Rerun only the queries that failed with charmap encoding errors (J-M).
Fixes applied:
  - agent7.py now passes PYTHONIOENCODING=utf-8 to MCP subprocess
  - This script has UTF-8 stdout reconfiguration at the top
"""
import asyncio
import sys
import os
import re
from io import StringIO
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

# Force UTF-8 on Windows stdout/stderr before any imports
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import agent7
import memory
import gateway


class DoubleWriter:
    def __init__(self, stream1, stream2):
        self.stream1 = stream1
        self.stream2 = stream2

    def write(self, data):
        for s in (self.stream1, self.stream2):
            try:
                s.write(data)
            except UnicodeEncodeError:
                try:
                    enc = getattr(s, "encoding", None) or "utf-8"
                    safe = data.encode(enc, errors="replace").decode(enc, errors="replace")
                    s.write(safe)
                except Exception:
                    pass
            except Exception:
                pass

    def flush(self):
        for s in (self.stream1, self.stream2):
            try:
                s.flush()
            except Exception:
                pass


async def run_and_trace(query_label: str, filename: str, query: str):
    print(f"\nRunning Query {query_label}: {query}")
    traces_dir = HERE / "traces"
    traces_dir.mkdir(exist_ok=True)

    old_stdout = sys.stdout
    captured = StringIO()
    sys.stdout = DoubleWriter(old_stdout, captured)

    try:
        answer = await agent7.run(query)
    except Exception as e:
        import traceback
        traceback.print_exc()
        answer = f"ERROR occurred: {e}"
    finally:
        sys.stdout = old_stdout

    trace_path = traces_dir / filename
    with open(trace_path, "w", encoding="utf-8") as f:
        f.write(f"# Query {query_label} Trace Log\n\n")
        f.write(f"**Query:** `{query}`\n\n")
        f.write(f"**Answer:**\n{answer}\n\n")
        f.write("## Execution Log\n\n")
        f.write("```text\n")
        f.write(captured.getvalue())
        f.write("\n```\n")

    print(f"Saved trace log to {trace_path.resolve()}")
    return answer


async def main():
    print("=" * 60)
    print("RERUNNING FAILED QUERIES (J, K, L, M)")
    print("=" * 60)

    # Ensure gateway is up before starting
    gateway.ensure_gateway()
    print("[gateway] confirmed up")

    failed_queries = [
        ("J", "query_j.md",  "How do models mitigate internal covariate shift during training?"),
        ("K", "query_k.md",  "How does machine learning handle steering large language models to align with human preferences without using complex reinforcement learning loops like PPO?"),
        ("L", "query_l.md",  "What evaluation metrics are used to compare an automatically produced summary or machine translation against human-written references, and how do they differ from classification precision and recall?"),
        ("M", "query_m.md",  "Compare how Random Forest and Support Vector Machines differ in their optimization objective and decision boundaries."),
    ]

    results = {}
    for label, filename, query in failed_queries:
        answer = await run_and_trace(label, filename, query)
        results[label] = "OK" if not answer.startswith("ERROR") else "FAIL"
        print(f"\n[{label}] => {results[label]}")

    print("\n" + "=" * 60)
    print("RERUN COMPLETE")
    for label, status in results.items():
        print(f"  Query {label}: {status}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
