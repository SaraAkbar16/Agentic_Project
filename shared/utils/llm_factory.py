import os
from typing import Optional, Union
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_groq import ChatGroq

# Load environment variables
load_dotenv()

class LLMFactory:
    """
    Factory class to create and return LLM instances based on environment configuration.
    """
    
    @staticmethod
    def get_llm(temperature: float = 0.7):
        """
        Returns a LangChain LLM instance (ChatOllama or ChatGroq) based on LLM_PROVIDER.
        """
        provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        
        if provider == "groq":
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY is not set in environment variables")
            
            model_name = os.getenv("GROQ_MODEL", "llama3-70b-8192")
            print(f"🤖 [LLMFactory] Initializing Groq LLM (model: {model_name})")
            return ChatGroq(
                api_key=api_key,
                model_name=model_name,
                temperature=temperature
            )
            
        elif provider == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            model_name = os.getenv("OLLAMA_MODEL", "llama3")
            print(f"🤖 [LLMFactory] Initializing Ollama LLM (base_url: {base_url}, model: {model_name})")
            return ChatOllama(
                base_url=base_url,
                model=model_name,
                temperature=temperature
            )
        
        else:
            raise ValueError(f"Unsupported LLM_PROVIDER: {provider}. Use 'ollama' or 'groq'.")

# Export a convenience function
def get_llm(temperature: float = 0.7):
    return LLMFactory.get_llm(temperature)
