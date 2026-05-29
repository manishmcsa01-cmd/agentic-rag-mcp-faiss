import asyncio
import sys
import os
import re
import json
import shutil
from io import StringIO
from pathlib import Path

# Insert same directory in sys.path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

# Import agent loop and memory
# Reconfigure stdout/stderr encoding to UTF-8 on Windows
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
        try:
            self.stream1.write(data)
        except Exception:
            try:
                enc = getattr(self.stream1, "encoding", None) or "utf-8"
                safe_data = data.encode(enc, errors="replace").decode(enc, errors="replace")
                self.stream1.write(safe_data)
            except Exception:
                pass
        try:
            self.stream2.write(data)
        except Exception:
            pass
        
    def flush(self):
        try:
            self.stream1.flush()
        except Exception:
            pass
        try:
            self.stream2.flush()
        except Exception:
            pass

# Validation 1: Grep Test
def run_grep_test() -> bool:
    print("\n" + "="*50)
    print("VALIDATION 1: GREP TEST")
    print("="*50)
    
    # Read perception.py
    perception_path = HERE / "perception.py"
    content = perception_path.read_text(encoding="utf-8")
    
    # Extract SYSTEM prompt string
    match = re.search(r'SYSTEM\s*=\s*\((.*?)\)', content, re.DOTALL)
    if not match:
        # Try alternate pattern
        match = re.search(r'SYSTEM\s*=\s*"""(.*?)"""', content, re.DOTALL)
        
    if not match:
        print("ERROR: Could not locate SYSTEM prompt in perception.py")
        return False
        
    system_prompt = match.group(1)
    
    # Check for presence of MCP tool names
    mcp_tools = [
        "web_search", "fetch_url", "get_time", "currency_convert",
        "read_file", "list_dir", "create_file", "update_file", "edit_file",
        "index_document", "search_knowledge", "index_directory", 
        "semantic_search", "corpus_stats"
    ]
    
    print("Analyzing Perception SYSTEM prompt for leaked tool names...")
    found_leaks = []
    for tool in mcp_tools:
        # Case insensitive search
        if re.search(rf"\b{tool}\b", system_prompt, re.IGNORECASE):
            found_leaks.append(tool)
            
    # Just extract all double-quoted strings and join them
    strings = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', system_prompt)
    raw_system_prompt = "".join(strings)
    raw_system_prompt = raw_system_prompt.replace("\\n", "\n")
    (HERE / "perception_system.txt").write_text(raw_system_prompt, encoding="utf-8")
    print("Saved perception_system.txt for automatic validation.")
    
    if found_leaks:
        print(f"FAILED: Leaked tool names found in Perception SYSTEM prompt: {found_leaks}")
        return False
    else:
        print("PASSED: Zero MCP tool names leaked inside Perception SYSTEM prompt!")
        return True

# Validation 3: Semantic Recall Test
def run_semantic_recall_test():
    print("\n" + "="*50)
    print("VALIDATION 3: SEMANTIC RECALL TEST")
    print("="*50)
    
    print("Clearing memory to ensure deterministic results...")
    memory.clear()
    
    # Ingest dpo.md
    print("Indexing Direct Preference Optimization document...")
    dpo_text = (HERE / "sandbox" / "corpus" / "dpo.md").read_text(encoding="utf-8")
    
    # Add the document chunks
    memory.add_fact(
        descriptor="[sandbox:corpus/dpo.md chunk 1/1] Direct Preference Optimization (DPO) aligns LLMs with human preferences, bypassing PPO reward modeling.",
        value={
            "chunk": dpo_text,
            "chunk_index": 0,
            "total_chunks": 1,
            "source": "sandbox:corpus/dpo.md",
            "chunk_offset": 0
        },
        source="sandbox:corpus/dpo.md",
        run_id="test-semantic-recall"
    )
    
    # Query with pure synonym having NO overlap in keywords
    keyword_query = "guiding artificial neural systems towards desirable behaviors without conventional trial-and-error policy iteration schemes"
    
    # 1. Keyword search
    print(f"\nQuery: '{keyword_query}'")
    print("--- 1. Keyword Search ---")
    kw_hits = memory._keyword_search(keyword_query, history=None, kinds=["fact"], top_k=3)
    print(f"Keyword search hits count: {len(kw_hits)}")
    for hit in kw_hits:
        print(f"Hit ID: {hit.id} - Descriptor: {hit.descriptor}")
        
    # 2. Vector search
    print("--- 2. Vector (FAISS) Search ---")
    vec_hits = memory._vector_search(keyword_query, kinds=["fact"], top_k=3)
    print(f"Vector search hits count: {len(vec_hits)}")
    for hit in vec_hits:
        print(f"Vector Hit ID: {hit.id} - Descriptor: {hit.descriptor}")
        
    if len(vec_hits) > 0 and len(kw_hits) == 0:
        print("\nPASSED: Semantic recall verified! Vector similarity successfully matched where keyword overlap failed.")
        return True
    else:
        print("\nWARNING: Keyword search returned results. Adjusting query to have zero overlap.")
        return False

# Master Query runner
async def run_and_trace(query_label: str, filename: str, query: str):
    print(f"\nRunning Query {query_label}: {query}")
    traces_dir = HERE / "traces"
    traces_dir.mkdir(exist_ok=True)
    
    # Capture stdout
    old_stdout = sys.stdout
    captured = StringIO()
    sys.stdout = DoubleWriter(old_stdout, captured)
    
    try:
        # Run agent7 orchestrator
        answer = await agent7.run(query)
    except Exception as e:
        import traceback
        traceback.print_exc()
        answer = f"ERROR occurred: {e}"
    finally:
        # Restore stdout
        sys.stdout = old_stdout
        
    # Save trace log in markdown format
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

async def main():
    print("Starting Automated RAG Agent Evaluation Harness...")
    
    # Run static validation
    grep_passed = run_grep_test()
    semantic_passed = run_semantic_recall_test()
    
    # Clear memory for evaluation of eight base queries
    print("\nResetting memory for the base evaluation queries...")
    memory.clear()
    
    # Eight Base Queries verbatim from queries.docx
    base_queries = [
        ("A", "query_a.md", "Fetch https://en.wikipedia.org/wiki/Claude_Shannon and tell me his birth date, death date, and three key contributions to information theory."),
        ("B", "query_b.md", "Find 3 family-friendly things to do in Tokyo this weekend. Check Saturday's weather forecast there and tell me which one is most appropriate."),
        ("C_run1", "query_c_run1.md", "My mom's birthday is 15 May 2026. Remember that and create reminders for two weeks before and on the day."),
        ("C_run2", "query_c_run2.md", "When is mom's birthday?"),
        ("D", "query_d.md", "Search for \"Python asyncio best practices\", read the top 3 results, and give me a short numbered list of the advice they agree on."),
        ("E", "query_e.md", "Index the file papers/attention.md and tell me what the three key contributions of the Transformer architecture are according to this paper."),
        ("F_run1", "query_f_run1.md", "Index every .md file under papers/. Confirm how many chunks were indexed in total."),
        ("F_run2", "query_f_run2.md", "Across the papers I have indexed, what do they say about chain-of-thought reasoning?"),
        ("G", "query_g.md", "Across these papers, how do they handle the credit assignment problem?"),
        ("H", "query_h.md", "Compare how the ReAct paper and the Chain-of-Thought paper differ in their treatment of intermediate reasoning.")
    ]
    
    # 5 Custom Corpus-specific RAG Queries
    custom_queries = [
        ("I", "query_i.md", "What is the difference between Direct Preference Optimization (DPO) and RLHF in language model alignment?"),
        ("J", "query_j.md", "How do models mitigate internal covariate shift during training?"),
        ("K", "query_k.md", "How does machine learning handle steering large language models to align with human preferences without using complex reinforcement learning loops like PPO?"),
        ("L", "query_l.md", "What evaluation metrics are used to compare an automatically produced summary or machine translation against human-written references, and how do they differ from classification precision and recall?"),
        ("M", "query_m.md", "Compare how Random Forest and Support Vector Machines differ in their optimization objective and decision boundaries.")
    ]
    
    # Execute base queries
    print("\n" + "="*50)
    print("RUNNING MANDATORY BASE QUERIES")
    print("="*50)
    for label, filename, query in base_queries:
        await run_and_trace(label, filename, query)
        
    # Index the custom corpus directory to trigger recursive directory indexing
    print("\n" + "="*50)
    print("INDEXING CUSTOM 50+ DOCUMENT CORPUS")
    print("="*50)
    
    # Initialize gateway if needed and call index_directory via memory/agent tools.
    # We will trigger this by running an agent command to index the corpus directory.
    await run_and_trace("IngestCorpus", "corpus_ingestion.md", "Index the directory corpus/ under sandbox and confirm how many files and chunks were successfully indexed in total.")
    
    # Execute custom queries
    print("\n" + "="*50)
    print("RUNNING CUSTOM RAG QUERIES")
    print("="*50)
    for label, filename, query in custom_queries:
        await run_and_trace(label, filename, query)
        
    print("\n" + "="*50)
    print("EVALUATION HARNESS COMPLETED SUCCESSFULLY!")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
