from pathlib import Path
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from backend.agent.llm_factory import get_embeddings

CHROMA_DIR = "./chroma_db"
COLECCION = "documentos"

def get_vectorstore():
    return Chroma(
        collection_name=COLECCION,
        embedding_function=get_embeddings(),
        persist_directory=CHROMA_DIR,
    )

def buscar(query: str, k: int = 3):
    try:
        vs = get_vectorstore()
        docs = vs.similarity_search(query, k=k)
        return [{"contenido": d.page_content, "metadata": d.metadata} for d in docs]
    except Exception:
        return []
