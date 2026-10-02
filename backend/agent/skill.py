from backend.agent.rag import buscar
from backend.agent.llm_factory import get_llm
from backend.agent.mcp_clients import MCP_RRHH, MCP_Correo, MCP_Firma, MCP_Evidencias

def ejecutar_skill_alta_formacion(empleado_id: str, rol: str):
    contexto = buscar(f"formacion para rol {rol}")
    contexto_str = "\n".join([c["contenido"] for c in contexto]) or "Sin contexto."

    llm = get_llm()
    prompt = f"""Eres el Agente de Formacion y Conciencia (ISO 27701 A.3.17 y A.3.18).
Contexto normativo:
{contexto_str}

Genera un plan de formacion para el empleado {empleado_id} con rol {rol}.
Incluye: curso recomendado, evaluacion y acuerdo de confidencialidad.
Se breve."""

    plan = llm.invoke(prompt).content

    # MCPs simulados
    mcp_rrhh = MCP_RRHH()
    mcp_correo = MCP_Correo()
    mcp_firma = MCP_Firma()
    mcp_evid = MCP_Evidencias()

    asignacion = mcp_rrhh.assign_training(empleado_id, "curso-privacidad-101")
    correo = mcp_correo.send_email(
        f"{empleado_id}@empresa.com",
        "Formacion en privacidad asignada",
        plan,
    )
    firma = mcp_firma.create_envelope(empleado_id, "plantilla-nda")
    evidencia = mcp_evid.store_evidence(
        "A.3.17",
        "Alta de formacion",
        {"empleado_id": empleado_id, "plan": plan},
    )

    return {
        "plan": plan,
        "asignacion": asignacion,
        "correo": correo,
        "firma": firma,
        "evidencia": evidencia,
    }
