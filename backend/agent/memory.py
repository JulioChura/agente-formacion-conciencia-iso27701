import sqlite3
from pathlib import Path

DB = "historial.db"

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mensajes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT,
            rol TEXT,
            contenido TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def guardar(thread_id, rol, contenido):
    conn = sqlite3.connect(DB)
    conn.execute(
        "INSERT INTO mensajes (thread_id, rol, contenido) VALUES (?, ?, ?)",
        (thread_id, rol, contenido),
    )
    conn.commit()
    conn.close()

def obtener(thread_id):
    conn = sqlite3.connect(DB)
    cur = conn.execute(
        "SELECT rol, contenido FROM mensajes WHERE thread_id = ? ORDER BY id",
        (thread_id,),
    )
    filas = [{"rol": r, "contenido": c} for r, c in cur.fetchall()]
    conn.close()
    return filas
