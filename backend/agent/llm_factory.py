from backend.config import (
    LLM_PROVIDER, EMBEDDINGS_PROVIDER, OLLAMA_HOST, MODELO_LLM,
    MODELO_EMBEDDINGS, OPENAI_API_KEY, OPENAI_BASE_URL,
    OPENROUTER_API_KEY, OPENROUTER_BASE_URL,
)

def get_llm():
    if LLM_PROVIDER == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=MODELO_LLM, base_url=OLLAMA_HOST)
    elif LLM_PROVIDER == "openrouter":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=MODELO_LLM,
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
        )
    elif LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=MODELO_LLM,
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
        )
    raise ValueError(f"Proveedor LLM no soportado: {LLM_PROVIDER}")

def get_embeddings():
    if EMBEDDINGS_PROVIDER == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(
            model=MODELO_EMBEDDINGS, 
            base_url=OLLAMA_HOST
        )
    elif EMBEDDINGS_PROVIDER == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model=MODELO_EMBEDDINGS,
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
        )
    elif EMBEDDINGS_PROVIDER == "huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name=MODELO_EMBEDDINGS)
    
    raise ValueError(f"Proveedor embeddings no soportado: {EMBEDDINGS_PROVIDER}")