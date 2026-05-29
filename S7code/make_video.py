"""
make_video.py -- Assembles slide images + gTTS voiceover into a single MP4 video.

Slides (8 total, 16:9, dark tech theme):
  1. Title
  2. What is RAG?
  3. MCP Architecture
  4. 14 MCP Tools
  5. Running a Query — Live Demo
  6. All 13 Queries Passed
  7. How to Run Locally
  8. Session 7 Complete

Each slide is shown for the duration of its voiceover narration + a 0.5s hold.
Output: rag_demo_video.mp4  (in this script's directory)
"""

import os, sys, time, textwrap
from pathlib import Path

# Fix Windows cp1252 charmap on stdout
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
from gtts import gTTS
from moviepy import (
    ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
)

# ── Paths ─────────────────────────────────────────────────────────────────────
ARTIFACTS = Path(r"C:\Users\Manish.Kapoor\.gemini\antigravity\brain\7d674821-ea4b-4da5-b5fc-6447a4b2cc4a")
OUT_DIR   = Path(__file__).parent / "video_output"
OUT_DIR.mkdir(exist_ok=True)
OUTPUT_MP4 = Path(__file__).parent / "rag_demo_video.mp4"

# ── Narration script (one entry per slide) ─────────────────────────────────
NARRATIONS = [
    # Slide 1 — Title
    """
    Welcome to the Session 7 RAG System demo.
    In this video, I'll walk you through a production-quality
    Retrieval-Augmented Generation system built on the Agent 7
    architecture from School of AI.
    """,

    # Slide 2 — What is RAG?
    """
    R A G stands for Retrieval Augmented Generation.
    Instead of relying only on the language model's training knowledge,
    the agent first searches YOUR indexed documents using a FAISS vector index,
    then uses those retrieved chunks to answer your question accurately.
    We indexed 52 AI and machine learning documents,
    and the memory persists across every restart.
    """,

    # Slide 3 — MCP Architecture
    """
    The system follows a strict four-layer architecture:
    Memory reads relevant context using vector search.
    Perception uses an LLM to plan goals — with zero MCP tool names
    leaked into the system prompt, passing our Grep Test.
    Decision picks the next action — either a tool call or a final answer.
    And Action executes the chosen tool through the MCP protocol.
    This loop repeats until all goals are satisfied.
    """,

    # Slide 4 — 14 Tools
    """
    The agent has access to 14 MCP tools.
    These include web search, URL fetching, time and currency conversion,
    and full file system operations inside a sandbox.
    The four highlighted RAG tools are index document,
    index directory, semantic search, and corpus stats.
    These allow the agent to ingest new documents on demand
    and query them with true semantic similarity.
    """,

    # Slide 5 — Demo
    """
    Running a query is simple. Just call run_query dot py
    with your question as a command line argument.
    The gateway starts automatically on port 8107.
    Watch the agent iterate: it reads memory, plans goals with Perception,
    calls semantic search to retrieve from the FAISS index,
    and returns a precise answer grounded in your indexed documents.
    """,

    # Slide 6 — Results
    """
    We ran 13 evaluation queries in total.
    Eight mandatory base queries covered web search, memory persistence,
    document indexing, and cross-paper comparison.
    Five custom RAG queries tested deep semantic retrieval —
    topics like Batch Normalization, DPO versus RLHF,
    LLM alignment without PPO, BLEU and ROUGE metrics,
    and Random Forest versus SVM.
    All 13 queries passed.
    """,

    # Slide 7 — How to Run
    """
    To run locally, change to the S7code directory.
    Then run python run_query dot py followed by your question in quotes
    for single-shot mode.
    Or run python run_query dot py with no arguments
    to enter the interactive REPL where you can ask multiple questions.
    The gateway starts automatically, and your indexed memory is loaded
    from the state directory on every run.
    """,

    # Slide 8 — Closing
    """
    That wraps up our Session 7 RAG system demo.
    The architecture strictly preserves Memory, Perception, Decision, and Action boundaries.
    The Grep Test passes — zero tool names leak into the Perception prompt.
    Semantic recall is verified with FAISS embeddings.
    And all thirteen queries completed successfully.
    Thank you for watching — Session 7, School of AI.
    """,
]

# ── Slide image filenames (in artifacts directory, find by prefix) ──────────
SLIDE_PREFIXES = [
    "slide_01_title",
    "slide_02_what_is_rag",
    "slide_03_architecture",
    "slide_04_tools",
    "slide_05_demo",
    "slide_06_results",
    "slide_07_how_to_run",
    "slide_08_closing",
]


def find_slide(prefix: str) -> Path:
    matches = sorted(ARTIFACTS.glob(f"{prefix}_*.png"))
    if not matches:
        raise FileNotFoundError(f"No image found for prefix: {prefix}")
    return matches[-1]  # latest


def clean_narration(text: str) -> str:
    return " ".join(text.split())


def make_audio(text: str, path: Path) -> float:
    """Generate TTS mp3, return duration in seconds."""
    tts = gTTS(text=text, lang="en", slow=False)
    tts.save(str(path))
    clip = AudioFileClip(str(path))
    dur = clip.duration
    clip.close()
    return dur


def main():
    print("=" * 60)
    print("RAG Demo Video Builder")
    print("=" * 60)

    clips = []

    for i, (prefix, narration) in enumerate(zip(SLIDE_PREFIXES, NARRATIONS), 1):
        print(f"\n[{i}/8] Processing slide: {prefix}")

        # Find slide image
        img_path = find_slide(prefix)
        print(f"  Image : {img_path.name}")

        # Generate TTS audio
        audio_path = OUT_DIR / f"audio_{i:02d}.mp3"
        text = clean_narration(narration)
        print(f"  TTS   : {len(text)} chars -> {audio_path.name}")
        duration = make_audio(text, audio_path)
        hold = 0.7  # extra seconds after narration ends
        total_dur = duration + hold
        print(f"  Duration: {duration:.1f}s + {hold}s hold = {total_dur:.1f}s")

        # Build clip
        img_clip = ImageClip(str(img_path), duration=total_dur)
        audio_clip = AudioFileClip(str(audio_path))
        img_clip = img_clip.with_audio(audio_clip)
        img_clip = img_clip.with_fps(24)

        clips.append(img_clip)

    print("\n" + "=" * 60)
    print("Concatenating all clips …")
    final = concatenate_videoclips(clips, method="compose")

    print(f"Writing video → {OUTPUT_MP4}")
    final.write_videofile(
        str(OUTPUT_MP4),
        fps=24,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=str(OUT_DIR / "temp_audio.m4a"),
        remove_temp=True,
        logger="bar",
    )

    print("\n" + "=" * 60)
    print(f"✅  Video saved: {OUTPUT_MP4}")
    print(f"   Duration   : {final.duration:.1f}s")
    print(f"   Resolution : {final.size}")
    print("=" * 60)


if __name__ == "__main__":
    main()
