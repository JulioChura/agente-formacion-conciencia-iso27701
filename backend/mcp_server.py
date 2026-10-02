from mcp.server.fastmcp import FastMCP
from backend.agent.skill import ejecutar_skill_alta_formacion
from backend.agent.rag import buscar

mcp = FastMCP("AgenteFormacion")

@mcp.tool()
def gestionar_alta_formacion(empleado_id: str, rol: str) -> dict:
    """Ejecuta la Skill de alta de formacion y confidencialidad."""
    return ejecutar_skill_alta_formacion(empleado_id, rol)

@mcp.tool()
def consultar_estado_formacion(empleado_id: str) -> dict:
    """Consulta el estado de formacion de un empleado (simulado)."""
    return {"empleado_id": empleado_id, "estado": "pendiente"}

@mcp.tool()
def generar_reporte_concienciacion(periodo: str) -> dict:
    """Genera un reporte de concienciacion (simulado)."""
    return {"periodo": periodo, "cobertura": "85%"}

@mcp.tool()
def gestionar_acuerdo_confidencialidad(empleado_id: str) -> dict:
    """Genera y envia un acuerdo de confidencialidad (simulado)."""
    return {"empleado_id": empleado_id, "estado": "enviado_a_firma"}

if __name__ == "__main__":
    mcp.run(transport="stdio")
