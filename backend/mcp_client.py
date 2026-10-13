import logging
from typing import Dict, Any, Optional

import mcp_server
from mcp_externos.postgres_mock import consultar_pii
from mcp_externos.evidencias_mock import guardar_evidencia

logger = logging.getLogger("mcp_client")

class MCPClient:
    """
    Cliente MCP que despacha llamadas de herramientas tanto al servidor Local FastMCP
    como a servidores externos (PostgreSQL PII, Evidencias).
    """

    @staticmethod
    async def call_tool(tool_name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = args or {}
        logger.info(f"Invocando herramienta MCP: {tool_name} con argumentos: {args}")

        try:
            # Herramientas del Servidor MCP Propio (FastMCP)
            if tool_name == "gestionar_alta_formacion":
                return mcp_server.gestionar_alta_formacion(
                    user_id=args.get("user_id"),
                    formacion_id=args.get("formacion_id")
                )

            elif tool_name == "gestionar_acuerdo_confidencialidad":
                return mcp_server.gestionar_acuerdo_confidencialidad(
                    user_id=args.get("user_id"),
                    tipo=args.get("tipo", "NDA General UNSA"),
                    accion=args.get("accion", "consultar")
                )

            elif tool_name == "consultar_estado_formacion":
                return mcp_server.consultar_estado_formacion(
                    user_id=args.get("user_id")
                )

            elif tool_name == "generar_reporte_conciencia":
                return mcp_server.generar_reporte_conciencia(
                    facultad=args.get("facultad")
                )

            elif tool_name == "listar_usuarios":
                return mcp_server.listar_usuarios(
                    filtros=args.get("filtros"),
                    solicitante_rol=args.get("solicitante_rol", "admin"),
                    solicitante_facultad=args.get("solicitante_facultad"),
                    solicitante_id=args.get("solicitante_id")
                )

            elif tool_name == "enviar_correo_masivo":
                return mcp_server.enviar_correo_masivo(
                    user_ids=args.get("user_ids", []),
                    asunto=args.get("asunto", "Aviso de Privacidad UNSA"),
                    cuerpo=args.get("cuerpo", ""),
                    remitente_id=args.get("remitente_id", "admin")
                )

            elif tool_name == "generar_certificado":
                return mcp_server.generar_certificado(
                    user_id=args.get("user_id"),
                    formacion_id=args.get("formacion_id")
                )

            # Herramientas de MCPs Externos directas
            elif tool_name == "consultar_pii":
                return consultar_pii(query=args.get("query", ""))

            elif tool_name == "guardar_evidencia":
                return guardar_evidencia(
                    user_id=args.get("user_id"),
                    archivo=args.get("archivo", "documento.pdf"),
                    control_iso=args.get("control_iso", "A.3.17"),
                    contenido=args.get("contenido")
                )

            else:
                return {
                    "status": "error",
                    "message": f"Herramienta MCP no reconocida: {tool_name}"
                }

        except Exception as e:
            logger.error(f"Fallo en ejecución de tool MCP {tool_name}: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error ejecutando {tool_name}: {str(e)}"
            }
