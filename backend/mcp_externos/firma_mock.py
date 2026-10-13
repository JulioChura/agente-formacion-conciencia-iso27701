import uuid
import logging
from datetime import datetime
from db import get_db_connection, registrar_audit

logger = logging.getLogger("mcp_firma")

def solicitar_firma(user_id: str, documento: str) -> dict:
    """
    MCP Firma (Mock persistente):
    Inserta en `firmas_mock`, imprime payload en consola
    y registra en `audit_log` con accion='firma_solicitar_mock'.
    """
    solicitud_id = f"sig_{uuid.uuid4().hex[:10]}"
    now = datetime.now().isoformat()

    print("\n" + "-"*40)
    print(f"✍️ [MCP Firma Mock - DocuSign UNSA] Solicitud de firma electrónica:")
    print(f"Usuario ID: {user_id} | Documento: {documento} | Solicitud ID: {solicitud_id}")
    print("-"*40 + "\n")

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO firmas_mock (id, user_id, documento, estado, solicitado_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (solicitud_id, user_id, documento, "solicitada", now)
        )

    registrar_audit(
        user_id=user_id,
        accion="firma_solicitar_mock",
        detalle={"solicitud_id": solicitud_id, "documento": documento, "estado": "solicitada"}
    )

    return {
        "status": "success",
        "solicitud_id": solicitud_id,
        "user_id": user_id,
        "documento": documento,
        "estado": "solicitada",
        "timestamp": now
    }
