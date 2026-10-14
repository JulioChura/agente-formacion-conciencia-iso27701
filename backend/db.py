import sqlite3
import json
import logging
from datetime import datetime
from contextlib import contextmanager
from typing import Generator, Any
from config import DB_PATH

logger = logging.getLogger("db")

def dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict[str, Any]:
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}

@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0, check_same_thread=False)
    conn.row_factory = dict_factory
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    try:
        yield conn
        conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.error(f"Error en transacción SQLite: {exc}")
        raise
    finally:
        conn.close()

def init_schema():
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Usuarios
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nombre TEXT NOT NULL,
            rol TEXT NOT NULL CHECK(rol IN ('docente', 'administrativo', 'jefe', 'admin', 'auditor')),
            facultad TEXT,
            departamento TEXT,
            activo INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        );
        """)

        # 2. Formaciones
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS formaciones (
            id TEXT PRIMARY KEY,
            titulo TEXT NOT NULL,
            descripcion TEXT,
            obligatoria_para TEXT,
            duracion_minutos INTEGER DEFAULT 60,
            control_iso TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)

        # 3. Formación - Usuario
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS formacion_usuario (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            formacion_id TEXT NOT NULL,
            estado TEXT NOT NULL CHECK(estado IN ('pendiente', 'completado', 'vencido', 'en_curso')),
            fecha_asignacion TEXT NOT NULL,
            fecha_completado TEXT,
            fecha_vencimiento TEXT,
            certificado_url TEXT,
            FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE,
            FOREIGN KEY (formacion_id) REFERENCES formaciones(id) ON DELETE CASCADE
        );
        """)

        # 4. Acuerdos de Confidencialidad (NDAs)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS acuerdos_confidencialidad (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            tipo TEXT NOT NULL,
            estado TEXT NOT NULL CHECK(estado IN ('pendiente', 'firmado', 'vencido', 'revocado')),
            fecha_solicitud TEXT NOT NULL,
            fecha_firma TEXT,
            fecha_vencimiento TEXT,
            documento_url TEXT,
            FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE
        );
        """)

        # 5. Evidencias
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS evidencias (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            tipo TEXT NOT NULL,
            control_iso TEXT NOT NULL,
            archivo_url TEXT NOT NULL,
            hash_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE SET NULL
        );
        """)

        # 6. Conversaciones
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversaciones (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            titulo TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE
        );
        """)

        # 7. Mensajes
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS mensajes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversacion_id TEXT NOT NULL,
            rol TEXT NOT NULL CHECK(rol IN ('user', 'assistant', 'system')),
            contenido TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (conversacion_id) REFERENCES conversaciones(id) ON DELETE CASCADE
        );
        """)

        # 8. Audit Log
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            accion TEXT NOT NULL,
            detalle TEXT,
            created_at TEXT NOT NULL
        );
        """)

        # 9. Correos Enviados (Mock persistente)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS correos_enviados (
            id TEXT PRIMARY KEY,
            lote_id TEXT,
            remitente_user_id TEXT,
            destinatario_user_id TEXT,
            destinatario_email TEXT NOT NULL,
            asunto TEXT NOT NULL,
            cuerpo TEXT NOT NULL,
            enviado_at TEXT NOT NULL,
            hash_sha256 TEXT NOT NULL
        );
        """)

        # 10. Matrículas LMS Mock (Mock persistente)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS matriculas_lms_mock (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            curso_id TEXT NOT NULL,
            matriculado_at TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'inscrito'
        );
        """)

        # 11. Firmas Mock (Mock persistente)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS firmas_mock (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            documento TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'solicitada',
            solicitado_at TEXT NOT NULL
        );
        """)

        # 12. Acciones Pendientes (Human Approval)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS acciones_pendientes (
            id TEXT PRIMARY KEY,
            conversacion_id TEXT NOT NULL,
            tipo_accion TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expira_at TEXT,
            FOREIGN KEY (conversacion_id) REFERENCES conversaciones(id) ON DELETE CASCADE
        );
        """)

        conn.commit()

def registrar_audit(user_id: str | None, accion: str, detalle: Any):
    try:
        detalle_str = json.dumps(detalle, ensure_ascii=False) if isinstance(detalle, (dict, list)) else str(detalle)
        now = datetime.now().isoformat()
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO audit_log (user_id, accion, detalle, created_at) VALUES (?, ?, ?, ?)",
                (user_id, accion, detalle_str, now)
            )
    except Exception as e:
        logger.error(f"Error registrando en audit_log: {e}")
