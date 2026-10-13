import uuid
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from db import get_db_connection, registrar_audit
from mcp_externos.lms_mock import matricular as lms_matricular
from mcp_externos.firma_mock import solicitar_firma as firma_solicitar
from mcp_externos.correo_mock import enviar_correo as correo_enviar
from mcp_externos.evidencias_mock import guardar_evidencia as evidencia_guardar

logger = logging.getLogger("mcp_server")

# Inicialización condicional de FastMCP si la librería está disponible
try:
    from fastmcp import FastMCP
    mcp = FastMCP("PIMS-UNSA-Formacion-Conciencia")
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP
        mcp = FastMCP("PIMS-UNSA-Formacion-Conciencia")
    except ImportError:
        class FastMCPStub:
            def tool(self):
                def decorator(fn):
                    return fn
                return decorator
            def run(self, **kwargs):
                print("FastMCP corriendo en modo embebido")
        mcp = FastMCPStub()

# ==============================================================================
# HERRAMIENTA 1: gestionar_alta_formacion
# ==============================================================================
@mcp.tool()
def gestionar_alta_formacion(user_id: str, formacion_id: str) -> dict:
    """
    Inscribe al usuario en una formación.
    Internamente orquesta con el MCP LMS (mock) para matricularlo en Moodle UNSA.
    """
    now = datetime.now()
    fecha_asignacion = now.strftime("%Y-%m-%d")
    fecha_vencimiento = (now + timedelta(days=30)).strftime("%Y-%m-%d")

    with get_db_connection() as conn:
        user = conn.execute("SELECT id, nombre, email FROM usuarios WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return {"status": "error", "message": f"Usuario no encontrado: {user_id}"}

        curso = conn.execute("SELECT id, titulo, control_iso FROM formaciones WHERE id = ?", (formacion_id,)).fetchone()
        if not curso:
            return {"status": "error", "message": f"Formación no encontrada: {formacion_id}"}

        # Comprobar si ya existe la asignación
        asignacion = conn.execute(
            "SELECT id, estado FROM formacion_usuario WHERE user_id = ? AND formacion_id = ?",
            (user_id, formacion_id)
        ).fetchone()

        if asignacion:
            asignacion_id = asignacion["id"]
            conn.execute(
                """
                UPDATE formacion_usuario
                SET estado = 'en_curso', fecha_asignacion = ?, fecha_vencimiento = ?
                WHERE id = ?
                """,
                (fecha_asignacion, fecha_vencimiento, asignacion_id)
            )
        else:
            asignacion_id = f"fu_{uuid.uuid4().hex[:8]}"
            conn.execute(
                """
                INSERT INTO formacion_usuario (
                    id, user_id, formacion_id, estado, fecha_asignacion, fecha_vencimiento
                ) VALUES (?, ?, ?, 'en_curso', ?, ?)
                """,
                (asignacion_id, user_id, formacion_id, fecha_asignacion, fecha_vencimiento)
            )

    # Orquestación con el MCP LMS externo
    lms_res = lms_matricular(user_id=user_id, curso_id=formacion_id)

    registrar_audit(
        user_id=user_id,
        accion="gestionar_alta_formacion",
        detalle={"formacion_id": formacion_id, "lms_status": lms_res.get("status")}
    )

    return {
        "status": "success",
        "asignacion_id": asignacion_id,
        "usuario": user["nombre"],
        "curso": curso["titulo"],
        "control_iso": curso["control_iso"],
        "estado": "en_curso",
        "fecha_vencimiento": fecha_vencimiento,
        "lms_integracion": lms_res
    }

# ==============================================================================
# HERRAMIENTA 2: gestionar_acuerdo_confidencialidad
# ==============================================================================
@mcp.tool()
def gestionar_acuerdo_confidencialidad(user_id: str, tipo: str = "NDA General UNSA", accion: str = "consultar") -> dict:
    """
    Gestiona acuerdos de confidencialidad (A.3.18).
    accion in ['crear', 'firmar', 'consultar']. Si es 'crear' o 'firmar', orquesta con MCP Firma.
    """
    now = datetime.now()
    fecha_hoy = now.strftime("%Y-%m-%d")

    with get_db_connection() as conn:
        user = conn.execute("SELECT id, nombre FROM usuarios WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return {"status": "error", "message": f"Usuario {user_id} no existe"}

        if accion == "consultar":
            ndas = conn.execute(
                "SELECT * FROM acuerdos_confidencialidad WHERE user_id = ? ORDER BY fecha_solicitud DESC",
                (user_id,)
            ).fetchall()
            return {
                "status": "success",
                "user_id": user_id,
                "usuario": user["nombre"],
                "acuerdos": ndas
            }

        elif accion == "crear":
            nda_id = f"nda_{uuid.uuid4().hex[:8]}"
            fecha_vencimiento = (now + timedelta(days=365)).strftime("%Y-%m-%d")
            doc_url = f"https://pims.unsa.edu.pe/docs/nda_{user_id}_{tipo.replace(' ', '_')}.pdf"

            conn.execute(
                """
                INSERT INTO acuerdos_confidencialidad (
                    id, user_id, tipo, estado, fecha_solicitud, fecha_vencimiento, documento_url
                ) VALUES (?, ?, ?, 'pendiente', ?, ?, ?)
                """,
                (nda_id, user_id, tipo, fecha_hoy, fecha_vencimiento, doc_url)
            )

            # Orquestación MCP Firma
            firma_res = firma_solicitar(user_id=user_id, documento=doc_url)

            registrar_audit(user_id, "gestionar_acuerdo_confidencialidad_crear", {"nda_id": nda_id, "tipo": tipo})

            return {
                "status": "success",
                "nda_id": nda_id,
                "tipo": tipo,
                "estado": "pendiente",
                "fecha_vencimiento": fecha_vencimiento,
                "firma_integracion": firma_res
            }

        elif accion == "firmar":
            # Buscar NDA pendiente
            nda = conn.execute(
                "SELECT id, tipo FROM acuerdos_confidencialidad WHERE user_id = ? AND estado = 'pendiente' ORDER BY fecha_solicitud DESC LIMIT 1",
                (user_id,)
            ).fetchone()

            if not nda:
                # Si no había pendiente, se crea y se marca firmado
                nda_id = f"nda_{uuid.uuid4().hex[:8]}"
                fecha_vencimiento = (now + timedelta(days=365)).strftime("%Y-%m-%d")
                conn.execute(
                    """
                    INSERT INTO acuerdos_confidencialidad (
                        id, user_id, tipo, estado, fecha_solicitud, fecha_firma, fecha_vencimiento
                    ) VALUES (?, ?, ?, 'firmado', ?, ?, ?)
                    """,
                    (nda_id, user_id, tipo, fecha_hoy, fecha_hoy, fecha_vencimiento)
                )
            else:
                nda_id = nda["id"]
                conn.execute(
                    "UPDATE acuerdos_confidencialidad SET estado = 'firmado', fecha_firma = ? WHERE id = ?",
                    (fecha_hoy, nda_id)
                )

            firma_res = firma_solicitar(user_id=user_id, documento=f"Acuerdo_{tipo}_FIRMADO")

            registrar_audit(user_id, "gestionar_acuerdo_confidencialidad_firmar", {"nda_id": nda_id})

            return {
                "status": "success",
                "nda_id": nda_id,
                "mensaje": f"Acuerdo '{tipo}' firmado exitosamente para {user["nombre"]}",
                "estado": "firmado",
                "fecha_firma": fecha_hoy,
                "firma_integracion": firma_res
            }

        else:
            return {"status": "error", "message": f"Acción desconocida: {accion}"}

# ==============================================================================
# HERRAMIENTA 3: consultar_estado_formacion
# ==============================================================================
@mcp.tool()
def consultar_estado_formacion(user_id: str) -> dict:
    """
    Retorna lista de formaciones asignadas y su estado, más el estado de los NDAs del usuario.
    """
    with get_db_connection() as conn:
        user = conn.execute("SELECT id, nombre, rol, facultad, email FROM usuarios WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return {"status": "error", "message": f"Usuario no encontrado: {user_id}"}

        cursos = conn.execute(
            """
            SELECT fu.id as asignacion_id, f.id as formacion_id, f.titulo, f.control_iso,
                   fu.estado, fu.fecha_asignacion, fu.fecha_vencimiento, fu.certificado_url
            FROM formacion_usuario fu
            JOIN formaciones f ON fu.formacion_id = f.id
            WHERE fu.user_id = ?
            ORDER BY fu.fecha_vencimiento ASC
            """,
            (user_id,)
        ).fetchall()

        ndas = conn.execute(
            """
            SELECT id, tipo, estado, fecha_solicitud, fecha_firma, fecha_vencimiento
            FROM acuerdos_confidencialidad
            WHERE user_id = ?
            ORDER BY fecha_solicitud DESC
            """,
            (user_id,)
        ).fetchall()

    completados = [c for c in cursos if c["estado"] == "completado"]
    pendientes = [c for c in cursos if c["estado"] in ("pendiente", "en_curso")]
    vencidos = [c for c in cursos if c["estado"] == "vencido"]

    porcentaje_cumplimiento = int((len(completados) / len(cursos) * 100)) if cursos else 100

    return {
        "status": "success",
        "usuario": {
            "id": user["id"],
            "nombre": user["nombre"],
            "rol": user["rol"],
            "facultad": user["facultad"],
            "email": user["email"]
        },
        "resumen": {
            "total_formaciones": len(cursos),
            "completadas": len(completados),
            "pendientes": len(pendientes),
            "vencidas": len(vencidos),
            "porcentaje_cumplimiento": porcentaje_cumplimiento
        },
        "formaciones": cursos,
        "acuerdos_confidencialidad": ndas
    }

# ==============================================================================
# HERRAMIENTA 4: generar_reporte_conciencia
# ==============================================================================
@mcp.tool()
def generar_reporte_conciencia(facultad: Optional[str] = None) -> dict:
    """
    Genera reporte agregado de cumplimiento de formación y acuerdos de confidencialidad
    para una facultad específica o a nivel global UNSA.
    """
    with get_db_connection() as conn:
        if facultad and facultad.lower() not in ("todas", "global", "unsa"):
            usuarios = conn.execute(
                "SELECT id, nombre, rol, facultad FROM usuarios WHERE facultad LIKE ? AND activo = 1",
                (f"%{facultad}%",)
            ).fetchall()
            alcance = f"Facultad: {facultad}"
        else:
            usuarios = conn.execute("SELECT id, nombre, rol, facultad FROM usuarios WHERE activo = 1").fetchall()
            alcance = "Toda la UNSA"

        user_ids = [u["id"] for u in usuarios]
        if not user_ids:
            return {
                "status": "success",
                "alcance": alcance,
                "total_usuarios": 0,
                "mensaje": "No se encontraron usuarios en la facultad indicada"
            }

        placeholders = ",".join(["?"] * len(user_ids))

        # Métricas formaciones
        cursos_asignados = conn.execute(
            f"SELECT estado, count(*) as count FROM formacion_usuario WHERE user_id IN ({placeholders}) GROUP BY estado",
            user_ids
        ).fetchall()

        # Métricas NDAs
        ndas = conn.execute(
            f"SELECT estado, count(*) as count FROM acuerdos_confidencialidad WHERE user_id IN ({placeholders}) GROUP BY estado",
            user_ids
        ).fetchall()

    resumen_formacion = {r["estado"]: r["count"] for r in cursos_asignados}
    resumen_ndas = {r["estado"]: r["count"] for r in ndas}

    total_f = sum(resumen_formacion.values())
    completadas = resumen_formacion.get("completado", 0)
    tasa_formacion = round((completadas / total_f * 100), 1) if total_f > 0 else 0.0

    return {
        "status": "success",
        "alcance": alcance,
        "total_usuarios": len(usuarios),
        "tasa_cumplimiento_formacion_pct": tasa_formacion,
        "formaciones": {
            "total": total_f,
            "completadas": completadas,
            "pendientes": resumen_formacion.get("pendiente", 0) + resumen_formacion.get("en_curso", 0),
            "vencidas": resumen_formacion.get("vencido", 0)
        },
        "acuerdos_confidencialidad": {
            "firmados": resumen_ndas.get("firmado", 0),
            "pendientes": resumen_ndas.get("pendiente", 0),
            "vencidos": resumen_ndas.get("vencido", 0)
        },
        "timestamp": datetime.now().isoformat()
    }

# ==============================================================================
# HERRAMIENTA 5: listar_usuarios
# ==============================================================================
@mcp.tool()
def listar_usuarios(
    filtros: Optional[Dict[str, Any]] = None,
    solicitante_rol: str = "admin",
    solicitante_facultad: Optional[str] = None,
    solicitante_id: Optional[str] = None
) -> dict:
    """
    Devuelve lista de usuarios según filtros:
    filtros: {'rol': str, 'facultad': str, 'departamento': str, 'antiguedad_dias': int, 'estado_formacion': str}
    Respeta el alcance del rol:
      - docente/administrativo/estudiante: solo a sí mismo
      - jefe: solo su equipo o facultad
      - admin: toda la UNSA
      - auditor: toda la UNSA (solo lectura)
    """
    filtros = filtros or {}
    query = "SELECT id, email, nombre, rol, facultad, departamento, created_at FROM usuarios WHERE activo = 1"
    params = []

    # Control de acceso basado en rol (RBAC / Context Guardrail)
    if solicitante_rol in ("docente", "administrativo", "estudiante"):
        query += " AND id = ?"
        params.append(solicitante_id)
    elif solicitante_rol == "jefe":
        if solicitante_facultad:
            query += " AND facultad = ?"
            params.append(solicitante_facultad)

    # Filtros opcionales
    if "rol" in filtros and filtros["rol"]:
        query += " AND rol = ?"
        params.append(filtros["rol"])

    if "facultad" in filtros and filtros["facultad"]:
        query += " AND facultad LIKE ?"
        params.append(f"%{filtros['facultad']}%")

    if "departamento" in filtros and filtros["departamento"]:
        query += " AND departamento LIKE ?"
        params.append(f"%{filtros['departamento']}%")

    if "antiguedad_dias" in filtros and filtros["antiguedad_dias"] is not None:
        limite_dias = int(filtros["antiguedad_dias"])
        fecha_corte = (datetime.now() - timedelta(days=limite_dias)).strftime("%Y-%m-%d")
        query += " AND created_at >= ?"
        params.append(fecha_corte)

    with get_db_connection() as conn:
        usuarios = conn.execute(query, params).fetchall()

        # Filtro adicional si se pide por estado de formación
        if "estado_formacion" in filtros and filtros["estado_formacion"]:
            estado_req = filtros["estado_formacion"]
            filtrados = []
            for u in usuarios:
                check = conn.execute(
                    "SELECT 1 FROM formacion_usuario WHERE user_id = ? AND estado = ? LIMIT 1",
                    (u["id"], estado_req)
                ).fetchone()
                if check:
                    filtrados.append(u)
            usuarios = filtrados

    return {
        "status": "success",
        "total": len(usuarios),
        "usuarios": usuarios
    }

# ==============================================================================
# HERRAMIENTA 6: enviar_correo_masivo
# ==============================================================================
@mcp.tool()
def enviar_correo_masivo(user_ids: List[str], asunto: str, cuerpo: str, remitente_id: str = "admin") -> dict:
    """
    Envía correo a una lista de usuarios. Por cada usuario, invoca al MCP Correo (mock persistente).
    Devuelve {total, enviados, fallidos, lote_id}.
    """
    if not user_ids:
        return {"status": "error", "message": "Lista de destinatarios vacía"}

    with get_db_connection() as conn:
        placeholders = ",".join(["?"] * len(user_ids))
        encontrados = conn.execute(
            f"SELECT id, email, nombre FROM usuarios WHERE id IN ({placeholders}) OR email IN ({placeholders})",
            user_ids + user_ids
        ).fetchall()

    usuarios = list(encontrados)
    ids_o_emails_encontrados = {u["id"] for u in usuarios} | {u["email"] for u in usuarios if u["email"]}

    # Aceptar destinatarios con formato de correo directo (@) aunque no existan en la tabla usuarios
    for item in user_ids:
        if item not in ids_o_emails_encontrados and "@" in str(item):
            usuarios.append({
                "id": str(item),
                "email": str(item),
                "nombre": str(item).split("@")[0]
            })

    if not usuarios:
        return {"status": "error", "message": "Ninguno de los usuarios o correos especificados fue encontrado"}

    lote_id = f"lote_{uuid.uuid4().hex[:8]}"

    # Orquestación con el MCP Correo
    resultado_correo = correo_enviar(
        destinatarios=usuarios,
        asunto=asunto,
        cuerpo=cuerpo,
        remitente_id=remitente_id,
        lote_id=lote_id
    )

    return {
        "status": "success",
        "lote_id": lote_id,
        "total": len(usuarios),
        "enviados": resultado_correo.get("enviados", 0),
        "fallidos": resultado_correo.get("fallidos", 0),
        "asunto": asunto,
        "destinatarios_nombres": [u["nombre"] for u in usuarios]
    }

# ==============================================================================
# HERRAMIENTA AUXILIAR: generar_certificado
# ==============================================================================
@mcp.tool()
def generar_certificado(user_id: str, formacion_id: str) -> dict:
    """
    Genera PDF del certificado y guarda evidencia en MCP Evidencias (mock persistente con SHA256).
    """
    with get_db_connection() as conn:
        user = conn.execute("SELECT id, nombre, email FROM usuarios WHERE id = ?", (user_id,)).fetchone()
        curso = conn.execute("SELECT id, titulo, control_iso FROM formaciones WHERE id = ?", (formacion_id,)).fetchone()

        if not user or not curso:
            return {"status": "error", "message": "Usuario o formación no válidos"}

        now = datetime.now().strftime("%Y-%m-%d")
        cert_name = f"Certificado_{curso['id']}_{user_id}.pdf"
        cert_url = f"https://pims.unsa.edu.pe/certificados/{cert_name}"

        # Actualizar en formación usuario
        conn.execute(
            """
            UPDATE formacion_usuario
            SET estado = 'completado', fecha_completado = ?, certificado_url = ?
            WHERE user_id = ? AND formacion_id = ?
            """,
            (now, cert_url, user_id, formacion_id)
        )

    # Orquestación con MCP Evidencias
    evidencia_res = evidencia_guardar(
        user_id=user_id,
        archivo=cert_name,
        control_iso=curso["control_iso"],
        contenido=f"CERTIFICADO UNSA PIMS\nOtorgado a: {user['nombre']}\nPor completar: {curso['titulo']}\nFecha: {now}"
    )

    return {
        "status": "success",
        "certificado_url": cert_url,
        "usuario": user["nombre"],
        "curso": curso["titulo"],
        "control_iso": curso["control_iso"],
        "evidencia": evidencia_res
    }

if __name__ == "__main__":
    print("Iniciando servidor FastMCP PIMS-UNSA...")
    if hasattr(mcp, "run"):
        mcp.run()
