import os
from pathlib import Path
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from backend.agent.llm_factory import get_embeddings

DOCS_DIR = "./documentos"
CHROMA_DIR = "./chroma_db"

def cargar_documentos():
    docs = []
    if not os.path.exists(DOCS_DIR):
        os.makedirs(DOCS_DIR)
        print(f"[!] Carpeta {DOCS_DIR} creada. Coloca ahi tus PDFs o MD.")
        return docs
    for archivo in Path(DOCS_DIR).iterdir():
        if archivo.suffix.lower() == ".pdf":
            try:
                docs.extend(PyPDFLoader(str(archivo)).load())
            except Exception as e:
                print(f"[!] Error con {archivo}: {e}")
        elif archivo.suffix.lower() in (".md", ".txt"):
            try:
                docs.extend(TextLoader(str(archivo), encoding="utf-8").load())
            except Exception as e:
                print(f"[!] Error con {archivo}: {e}")
    return docs

def indexar():
    docs = cargar_documentos()
    if not docs:
        print("[!] No hay documentos para indexar. Base vectorial vacia.")
        return
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    vs = Chroma(
        collection_name="documentos",
        embedding_function=get_embeddings(),
        persist_directory=CHROMA_DIR,
    )
    vs.add_documents(chunks)
    print(f"[OK] {len(chunks)} fragmentos indexados.")

if __name__ == "__main__":
    indexar()
