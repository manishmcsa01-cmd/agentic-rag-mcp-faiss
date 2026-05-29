"""Retry Query L only, with exponential back-off on 503 gateway errors."""
import asyncio, sys, time
from io import StringIO
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import agent7, gateway

QUERY = (
    "What evaluation metrics are used to compare an automatically produced "
    "summary or machine translation against human-written references, and how "
    "do they differ from classification precision and recall?"
)
TRACE = HERE / "traces" / "query_l.md"
MAX_ATTEMPTS = 3


class Tee:
    def __init__(self, real, buf):
        self.real, self.buf = real, buf
    def write(self, d):
        for s in (self.real, self.buf):
            try: s.write(d)
            except UnicodeEncodeError:
                try:
                    enc = getattr(s, "encoding", None) or "utf-8"
                    s.write(d.encode(enc, errors="replace").decode(enc))
                except Exception: pass
            except Exception: pass
    def flush(self):
        for s in (self.real, self.buf):
            try: s.flush()
            except Exception: pass


async def run_once():
    gateway.ensure_gateway()
    buf = StringIO()
    old = sys.stdout
    sys.stdout = Tee(old, buf)
    try:
        answer = await agent7.run(QUERY)
    finally:
        sys.stdout = old
    return answer, buf.getvalue()


async def main():
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\n=== Query L — attempt {attempt}/{MAX_ATTEMPTS} ===")
        try:
            answer, log = await run_once()
            if answer and not answer.startswith("ERROR"):
                TRACE.write_text(
                    f"# Query L Trace Log\n\n"
                    f"**Query:** `{QUERY}`\n\n"
                    f"**Answer:**\n{answer}\n\n"
                    f"## Execution Log\n\n```text\n{log}\n```\n",
                    encoding="utf-8",
                )
                print(f"[L] PASSED on attempt {attempt} — trace saved to {TRACE}")
                return
            else:
                print(f"[L] Got error answer: {answer[:200]}")
        except Exception as e:
            print(f"[L] Exception: {e}")
        if attempt < MAX_ATTEMPTS:
            wait = 20 * attempt
            print(f"Waiting {wait}s before retry...")
            time.sleep(wait)

    print("[L] All attempts exhausted — writing last error state to trace")
    TRACE.write_text(
        f"# Query L Trace Log\n\n**Query:** `{QUERY}`\n\n"
        f"**Answer:**\nERROR: all {MAX_ATTEMPTS} attempts failed\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    asyncio.run(main())
