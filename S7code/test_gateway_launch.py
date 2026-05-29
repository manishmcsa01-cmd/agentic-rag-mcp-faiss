import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from gateway import ensure_gateway, embed, LLM

if __name__ == "__main__":
    try:
        ensure_gateway()
        print("Gateway started successfully!")
        
        # Test embedding
        print("Testing embedding...")
        emb_res = embed("Claude Shannon", task_type="retrieval_document")
        print("Embedding generated successfully! Vector dimension:", len(emb_res["embedding"]))
        
        # Test LLM chat
        print("Testing LLM chat...")
        llm = LLM()
        chat_res = llm.chat("Say 'System Online' in a single line.", provider="g")
        print("LLM reply:", chat_res)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
