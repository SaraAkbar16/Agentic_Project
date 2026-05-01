import os
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from mcp.tools.llm_tools.text_generator import TextGeneratorTool
from dotenv import load_dotenv

def test_provider(provider_name: str):
    print(f"\n--- Testing Provider: {provider_name} ---")
    
    # Manually override environment for testing
    os.environ["LLM_PROVIDER"] = provider_name
    
    # Reload env (if needed, though os.environ update should suffice for getenv)
    # Note: load_dotenv doesn't override existing env vars by default, 
    # but LLMFactory uses os.getenv which picks up our manual override.
    
    tool = TextGeneratorTool()
    prompt = "Say 'Hello from the Agentic AI Project' in a creative way."
    
    result = tool.execute(prompt=prompt)
    print(f"Result:\n{result}")

if __name__ == "__main__":
    # Test Ollama (assuming it's running)
    try:
        test_provider("ollama")
    except Exception as e:
        print(f"Ollama test failed: {e}")
        
    # Test Groq (requires GROQ_API_KEY in .env)
    if os.getenv("GROQ_API_KEY"):
        try:
            test_provider("groq")
        except Exception as e:
            print(f"Groq test failed: {e}")
    else:
        print("\n⚠️ Skipping Groq test (GROQ_API_KEY not found in .env)")
