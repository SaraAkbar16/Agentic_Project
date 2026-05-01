from typing import Any, Dict, Optional
from mcp.base_tool import BaseTool
from shared.utils.llm_factory import get_llm

class TextGeneratorTool(BaseTool):
    """
    Tool for generating text using the configured LLM provider.
    """
    
    @property
    def name(self) -> str:
        return "text_generator"

    @property
    def description(self) -> str:
        return "Generates text based on a provided prompt using Ollama or Groq."

    def execute(self, prompt: str, temperature: float = 0.7, **kwargs) -> str:
        """
        Executes text generation.
        """
        try:
            llm = get_llm(temperature=temperature)
            
            print(f"📝 [TextGeneratorTool] Generating text for prompt: {prompt[:50]}...")
            
            response = llm.invoke(prompt)
            
            # LangChain ChatModels return a message object, we want the content
            content = response.content if hasattr(response, 'content') else str(response)
            
            print(f"✅ [TextGeneratorTool] Successfully generated {len(content)} characters.")
            return content
            
        except Exception as e:
            print(f"❌ [TextGeneratorTool] Error during generation: {str(e)}")
            return f"Error: {str(e)}"

# Convenience instance
text_generator = TextGeneratorTool()
