import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from backend.agent.llm_factory import get_llm
from backend.agent.rag import buscar
from backend.agent.memory import init_db, guardar, obtener
from backend.agent.skill import ejecutar_skill_alta_formacion

app = FastAPI(title="Agente de Formacion y Conciencia")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

class ChatRequest(BaseModel):
    mensaje: str
    thread_id: str = "default"

@app.post("/chat")
async def chat(req: ChatRequest):
    guardar(req.thread_id, "user", req.mensaje)

    async def stream():
        # 1. Recuperar contexto del RAG
        contexto = buscar(req.mensaje)
        fuentes = [c["metadata"].get("source", "doc") for c in contexto]

        # 2. Decidir si es alta de formacion
        if "ingres" in req.mensaje.lower() or "nuevo empleado" in req.mensaje.lower():
            resultado = ejecutar_skill_alta_formacion("123", "Marketing")
            texto = resultado["plan"]
            for palabra in texto.split():
                yield f"data: {json.dumps({'token': palabra + ' '})}\n\n"
            yield f"data: {json.dumps({'done': True, 'fuentes': fuentes, 'skill': 'alta_formacion'})}\n\n"
            guardar(req.thread_id, "assistant", texto)
            return

        # 3. Respuesta normal con RAG + LLM
        llm = get_llm()
        contexto_str = "\n".join([c["contenido"] for c in contexto]) or "Sin contexto."
        prompt = f"""Eres el Agente de Formacion y Conciencia (ISO 27701 A.3.17 y A.3.18).
Contexto:
{contexto_str}

Pregunta: {req.mensaje}
Respuesta:"""
        respuesta = ""
        for chunk in llm.stream(prompt):
            token = chunk.content
            respuesta += token
            yield f"data: {json.dumps({'token': token})}\n\n"
        guardar(req.thread_id, "assistant", respuesta)
        yield f"data: {json.dumps({'done': True, 'fuentes': fuentes})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")

@app.get("/historial/{thread_id}")
def historial(thread_id: str):
    return {"mensajes": obtener(thread_id)}
