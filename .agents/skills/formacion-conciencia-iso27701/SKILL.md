---
name: formacion-conciencia-iso27701
description: Especificación técnica y catálogo de Herramientas MCP (Model Context Protocol) del Agente #8 PIMS UNSA (Formación, Concienciación y Confidencialidad ISO/IEC 27701:2025 Controles A.3.17 y A.3.18, Ley 29733). Diseñado para integración con el Orquestador Global Multiagente.
---

# Skill: Agente #8 — Formación, Conciencia y Gestión de Acuerdos (PIMS UNSA)

Este documento formaliza la especificación técnica del **Agente #8** dentro del ecosistema multiagente del **Privacy Information Management System (PIMS)** de la **Universidad Nacional de San Agustín de Arequipa (UNSA)**.

---

## 1. Identificación y Alcance Normativo

| Metadato | Detalle Técnico |
| :--- | :--- |
| **Identificador** | `agente-formacion-conciencia-iso27701` (Agente #8) |
| **Rol en el PIMS** | Copiloto del DPO y supervisor automatizado de competencias en privacidad |
| **Control ISO 27701 A.3.17** | Formación continua, concienciación y evaluación de competencias en privacidad |
| **Control ISO 27701 A.3.18** | Gestión, suscripción, seguimiento y renovación anual de Acuerdos de Confidencialidad (NDAs) |
| **Marco Legal Nacional** | Ley N° 29733 (Art. 17 Deber de Secreto, Art. 19 Seguridad) y D.S. 003-2013-JUS (Art. 38 Capacitación) |
| **Protocolo de Integración** | **Model Context Protocol (FastMCP)** + **LangGraph StateGraph** |

---

## 2. Integración con el Orquestador Global del PIMS

El Agente #8 expone su servidor **FastMCP** (`backend/mcp_server.py`) para ser descubierto y consumido por el **Orquestador Central Multiagente** mediante dos modalidades estándar:

```text
       +-------------------------------------------------------+
       |             ORQUESTADOR GLOBAL PIMS UNSA              |
       +-------------------------------------------------------+
                                  |
              Protocolo MCP (SSE / stdio / JSON-RPC)
                                  v
+---------------------------------------------------------------------+
|              AGENTE #8: FORMACIÓN Y CONCIENCIA (FASTMCP)             |
|                                                                     |
|  [Tools de Dominio]                                                 |
|   ├── Tool: consultar_estado_formacion()                            |
|   ├── Tool: gestionar_alta_formacion()  ──────> MCP LMS Mock (Moodle)|
|   ├── Tool: gestionar_acuerdo_confidencialidad() ─> MCP Firma Mock  |
|   ├── Tool: generar_reporte_conciencia()                            |
|   ├── Tool: listar_usuarios()                                       |
|   └── Tool: enviar_correo_masivo() ───────────> MCP Correo Mock     |
|                                                                     |
|  [Motor RAG Semántico] (ChromaDB + ONNX)                             |
|   ├── buscar_normativa_iso() (1,285 chunks)                         |
|   └── buscar_politica_negocio() (319 chunks)                        |
|                                                                     |
|  [Gobernanza y Supervisión Humana]                                  |
|   └── Protocolo HITL (Human-in-the-Loop) con validación SHA-256    |
+---------------------------------------------------------------------+
```

### Protocolo de Comunicación con el Orquestador:
1. **Descubrimiento de Herramientas (`tools/list`):** El Orquestador consulta la lista de herramientas disponibles mediante FastMCP y recibe los esquemas JSON de cada Tool.
2. **Invocación de Herramientas (`tools/call`):** El Orquestador solicita la ejecución de una herramienta pasando parámetros tipados (`user_id`, `formacion_id`, `filtros`, etc.).
3. **Cliente Despachador Interno (`MCPClient`):** En `backend/mcp_client.py`, el agente gestiona tanto las herramientas propias como los conectores externos hacia otros servicios del PIMS.

---

## 3. Catálogo Exhaustivo de Herramientas MCP (FastMCP Tools)

Ubicación del código fuente: [`backend/mcp_server.py`](file:///c:/Users/dhuam/Desktop/REM/auditorioa/agente-formacion-conciencia-iso27701/backend/mcp_server.py)

### Tool 1: `consultar_estado_formacion`
- **Propósito:** Evalúa el avance del personal frente a la matriz formativa obligatoria y verifica la vigencia de su Acuerdo de Confidencialidad.
- **Firma:** `consultar_estado_formacion(user_id: str) -> dict`
- **Parámetros:**
  - `user_id` *(str, requerido)*: Identificador institucional del usuario (ej: `carlos.ruiz`, `maria.lopez`).
- **Retorno:**
  - `status`: `"success"` | `"error"`
  - `usuario`: Datos de identidad, rol y facultad.
  - `resumen`: `total_formaciones`, `completadas`, `pendientes`, `vencidas`, `porcentaje_cumplimiento`.
  - `formaciones`: Lista detallada de cursos con fechas de vencimiento y URLs de certificados.
  - `acuerdos_confidencialidad`: Historial de NDAs y estado de firma.
- **Control ISO:** A.3.17 y A.3.18.

---

### Tool 2: `gestionar_alta_formacion`
- **Propósito:** Asigna un módulo formativo en base de datos y orquesta la matrícula física en el LMS institucional.
- **Firma:** `gestionar_alta_formacion(user_id: str, formacion_id: str) -> dict`
- **Parámetros:**
  - `user_id` *(str, requerido)*: Identificador del usuario a matricular.
  - `formacion_id` *(str, requerido)*: Código de la formación (ej: `f001` Ley 29733, `f003` Gestión de Brechas, `f004` Derechos ARCO).
- **Conector Externo Invocado:**
  - **`mcp_externos.lms_mock.matricular`**: Simula la integración con Moodle UNSA, genera ID de matrícula persistente en `matriculas_lms_mock` y audita la acción.
- **Retorno:** `asignacion_id`, `curso`, `control_iso`, `fecha_vencimiento` (30 días), `lms_integracion`.
- **Control ISO:** A.3.17 (Cláusula 7.2).

---

### Tool 3: `gestionar_acuerdo_confidencialidad`
- **Propósito:** Administra el ciclo de vida de los Acuerdos de Confidencialidad y Secreto Profesional (emisión, firma y consulta).
- **Firma:** `gestionar_acuerdo_confidencialidad(user_id: str, tipo: str, accion: str) -> dict`
- **Parámetros:**
  - `user_id` *(str, requerido)*: Identificador del titular.
  - `tipo` *(str, default="NDA General UNSA")*: Tipo de acuerdo (`"NDA Docente UNSA"`, `"NDA Administrativo"`, `"NDA Externo"`).
  - `accion` *(str, default="consultar")*: `"consultar"`, `"crear"` o `"firmar"`.
- **Conector Externo Invocado:**
  - **`mcp_externos.firma_mock.solicitar_firma`**: Simula la plataforma de firma electrónica (DocuSign/Firma Digital UNSA), estampando fecha de vigencia por 365 días y registrando en `firmas_mock`.
- **Retorno:** `nda_id`, `estado`, `fecha_firma`, `fecha_vencimiento`, `firma_integracion`.
- **Control ISO:** A.3.18 (Ley 29733 Art. 17).

---

### Tool 4: `generar_reporte_conciencia`
- **Propósito:** Agrega y consolida métricas cuantitativas de cumplimiento para auditorías PIMS del DPO y decanatos.
- **Firma:** `generar_reporte_conciencia(facultad: Optional[str] = None) -> dict`
- **Parámetros:**
  - `facultad` *(str, opcional)*: Nombre de la facultad a filtrar (ej: `"Ingeniería"`, `"Medicina"`, `"Derecho"`). Si se omite, calcula la métrica global de la universidad.
- **Retorno:**
  - `total_usuarios`: Número de personas evaluadas.
  - `porcentaje_cumplimiento_cursos`: Tasa de finalización formativa.
  - `porcentaje_firmas_nda`: Tasa de acuerdos firmados y vigentes.
  - `alertas`: Lista de dependencias con cumplimiento inferior al umbral del 80%.
- **Control ISO:** A.3.17 (Cláusula 7.4).

---

### Tool 5: `listar_usuarios`
- **Propósito:** Consulta y segmenta el personal aplicando control de acceso basado en roles (RBAC).
- **Firma:** `listar_usuarios(filtros: dict, solicitante_rol: str, solicitante_facultad: str, solicitante_id: str) -> dict`
- **Parámetros:**
  - `filtros` *(dict)*: Criterios de filtrado (`"rol"`, `"facultad"`, `"antiguedad_dias"`).
  - `solicitante_rol` *(str)*: Rol del solicitante (`"admin"`, `"jefe"`, `"docente"`).
- **Regla de Privacidad (RBAC):** Jefes de departamento solo pueden visualizar personal de su propia facultad; docentes y administrativos solo acceden a sus propios datos.
- **Retorno:** `total`, `usuarios` (lista sanitizada sin hashes de contraseña).

---

### Tool 6: `enviar_correo_masivo`
- **Propósito:** Envío auditado de convocatorias, recordatorios de vencimiento y notificaciones preventivas con supervisión humana.
- **Firma:** `enviar_correo_masivo(user_ids: list, asunto: str, cuerpo: str, remitente_id: str) -> dict`
- **Parámetros:**
  - `user_ids` *(list)*: Lista de IDs de usuarios o direcciones de correo electrónico.
  - `asunto` *(str)*: Asunto formal de la comunicación.
  - `cuerpo` *(str)*: Contenido redactado del correo.
  - `remitente_id` *(str, default="admin")*: Identificador del usuario que autoriza el despacho.
- **Conector Externo Invocado:**
  - **`mcp_externos.correo_mock.enviar_correo`**: Soporta despacho físico real vía **Resend API** o **SMTP Gmail / Google Workspace**, y genera un hash criptográfico **SHA-256** registrado en `correos_enviados` para no repudio.
- **Protocolo de Seguridad:** Esta herramienta requiere aprobación previa mediante **Human-in-the-Loop (HITL)**.

---

### Herramientas Auxiliares de Integración Externa:
- **`consultar_pii(query)`**: Consulta simulada de bases de datos legadas con filtrado de datos sensibles en `mcp_externos/postgres_mock.py`.
- **`guardar_evidencia(user_id, archivo, control_iso, contenido)`**: Almacena evidencias documentales y certificados en el directorio `./evidencias/` mediante `mcp_externos/evidencias_mock.py`.

---

## 4. Herramienta de Recuperación Aumentada (Motor RAG Semántico)

Ubicación del código fuente: [`backend/rag.py`](file:///c:/Users/dhuam/Desktop/REM/auditorioa/agente-formacion-conciencia-iso27701/backend/rag.py)

- **Colección `normas_iso` (1,285 fragmentos):** Búsqueda semántica densa sobre los textos integrales de ISO/IEC 27701:2025, ISO/IEC 27001:2022, ISO/IEC 27002, ISO/IEC 29100, Ley N° 29733 y D.S. 016-2024-JUS.
- **Colección `politicas_negocio` (319 fragmentos):** Recuperación de directivas universitarias, Estatuto de la UNSA, Código de Ética, Directiva de Gestión de Brechas y MOF/ROF institucional.
- **Embeddings:** Vectorización local con modelo ONNX `all-MiniLM-L6-v2` (distancia coseno).

---

## 5. Gobernanza y Protocolo Human-in-the-Loop (HITL)

Cualquier acción de escritura masiva o modificación de estado que afecte al personal se rige por el principio de supervisión humana:
1. **Fase de Preparación (`prepare_action`):** El agente extrae entidades, redacta la propuesta y genera un registro temporal en `acciones_pendientes`.
2. **Fase de Supervisión (`human_approval`):** Se emite el evento SSE `approval_required` hacia la interfaz gráfica (`TarjetaConfirmacion.vue`) o se procesa la confirmación en lenguaje natural libre (*"sí, procede"*, *"adelante"*).
3. **Fase de Ejecución (`execute_action`):** Solo tras la confirmación explícita se invoca la herramienta MCP de escritura correspondiente y se elimina la acción pendiente.
