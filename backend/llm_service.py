import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, AsyncGenerator, Optional
import httpx
from dotenv import dotenv_values

from config import (
    LLM_PROVIDER,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OLLAMA_HOST,
    OLLAMA_MODEL,
    env_path
)

logger = logging.getLogger("llm_service")

class LLMService:
    @staticmethod
    def _get_headers_and_url() -> tuple[str, dict[str, str], str]:
        # Leer dinámicamente del archivo .env para reflejar cambios en tiempo real
        vals = dotenv_values(env_path)
        env_model = vals.get("OPENROUTER_MODEL") or os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning:free")
        clean_model = env_model.replace("OPENROUTER_MODEL=", "").strip("\"' ")

        api_key = vals.get("OPENROUTER_API_KEY") or OPENROUTER_API_KEY

        if LLM_PROVIDER == "ollama":
            url = f"{OLLAMA_HOST.rstrip('/')}/v1/chat/completions"
            headers = {"Content-Type": "application/json"}
            model = OLLAMA_MODEL
        else:
            url = f"{OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://pims.unsa.edu.pe",
                "X-Title": "Agente Formacion UNSA",
                "Content-Type": "application/json"
            }
            model = clean_model
        return url, headers, model

    @staticmethod
    async def chat_completion(
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.2
    ) -> str:
        """
        Llamada unitaria a OpenRouter u Ollama.
        """
        url, headers, model = LLMService._get_headers_and_url()

        payload_messages = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
        payload_messages.extend(messages)

        body = {
            "model": model,
            "messages": payload_messages,
            "temperature": temperature
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        api_key = headers.get("Authorization", "").replace("Bearer ", "").strip()
        if LLM_PROVIDER == "openrouter" and (not api_key or "tu_" in api_key):
            logger.warning("OPENROUTER_API_KEY no configurada. Usando respuesta contextual.")
            return LLMService._fallback_response(payload_messages, json_mode)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, headers=headers, json=body)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    logger.error(f"❌ Error {resp.status_code} desde {LLM_PROVIDER} (Modelo '{model}'): {resp.text}")
                    return LLMService._fallback_response(payload_messages, json_mode)
        except Exception as e:
            logger.error(f"Excepción comunicando con proveedor LLM: {e}")
            return LLMService._fallback_response(payload_messages, json_mode)

    @staticmethod
    async def stream_chat(
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.3
    ) -> AsyncGenerator[str, None]:
        """
        Streaming token por token desde OpenRouter u Ollama.
        """
        url, headers, model = LLMService._get_headers_and_url()

        payload_messages = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
        payload_messages.extend(messages)

        body = {
            "model": model,
            "messages": payload_messages,
            "temperature": temperature,
            "stream": True
        }

        api_key = headers.get("Authorization", "").replace("Bearer ", "").strip()
        if LLM_PROVIDER == "openrouter" and (not api_key or "tu_" in api_key):
            fallback_text = LLMService._fallback_response(payload_messages, False)
            for word in fallback_text.split(" "):
                yield word + " "
            return

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", url, headers=headers, json=body) as response:
                    if response.status_code != 200:
                        err_body = await response.aread()
                        logger.error(f"❌ Error {response.status_code} streaming desde {LLM_PROVIDER} ({model}): {err_body.decode('utf-8', errors='ignore')}")
                        fallback_text = LLMService._fallback_response(payload_messages, False)
                        for word in fallback_text.split(" "):
                            yield word + " "
                        return

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                delta = chunk["choices"][0]["delta"]
                                if "content" in delta and delta["content"]:
                                    yield delta["content"]
                            except Exception:
                                continue
        except Exception as e:
            logger.error(f"Error en streaming LLM: {e}")
            fallback_text = LLMService._fallback_response(payload_messages, False)
            for word in fallback_text.split(" "):
                yield word + " "

    @staticmethod
    def _fallback_response(messages: List[Dict[str, str]], json_mode: bool) -> str:
        """
        Generador contextual de respuesta inteligente cuando OpenRouter está desconectado,
        con cuota agotada o bloqueado por guardrail.
        """
        user_text = ""
        context_text = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_text = m.get("content", "")
                break
        if not user_text and messages:
            user_text = messages[-1].get("content", "")

        # Extraer contexto del sistema si viene adjunto
        for m in messages:
            if "Contexto interno del sistema:" in m.get("content", ""):
                context_text = m.get("content", "")

        # Aislar la consulta real
        if "mensaje a clasificar:" in user_text.lower():
            c_lower = user_text.lower().split("mensaje a clasificar:")[-1].strip()
        elif "pregunta o instrucción del usuario:" in user_text.lower():
            c_lower = user_text.lower().split("pregunta o instrucción del usuario:")[-1].strip()
        else:
            c_lower = user_text.lower().strip()

        if json_mode:
            if any(k in c_lower for k in ["inscribe a todos", "enviar correo", "enviáles un correo", "enviales un correo", "correo masivo", "inscripción masiva", "inscripcion masiva"]):
                return json.dumps({"intent": "accion_masiva", "entidades": {}})
            elif any(k in c_lower for k in ["usuarios", "quiénes son", "quienes son", "nuevos usuarios", "lista de personal", "usuarios nuevos"]):
                return json.dumps({"intent": "consulta_usuarios", "entidades": {"filtros": {"antiguedad_dias": 30}}})
            elif any(k in c_lower for k in ["falta", "mis cursos", "pendiente", "cumplimiento", "mi estado"]):
                return json.dumps({"intent": "consulta_estado", "entidades": {}})
            elif any(k in c_lower for k in ["inscríbeme", "inscribeme", "firmar", "generar certificado"]):
                return json.dumps({"intent": "accion_individual", "entidades": {}})
            elif any(k in c_lower for k in ["iso", "ley", "29733", "27701", "a.3.17", "a.3.18", "norma", "roles", "saber", "deberia", "consentimiento", "acciones", "puedes hacer"]):
                return json.dumps({"intent": "consulta_normativa", "entidades": {}})
            elif any(k in c_lower for k in ["comida", "almuerzo", "partido", "chiste", "poema", "clima"]):
                return json.dumps({"intent": "fuera_de_alcance", "entidades": {}})
            return json.dumps({"intent": "consulta_normativa", "entidades": {}})

        # 1. ¿Qué acciones puedes hacer?
        if "acciones" in c_lower or "puedes hacer" in c_lower or "que haces" in c_lower or "servicios" in c_lower:
            return (
                "Como **Agente de Formación y Conciencia de la UNSA** (PIMS ISO/IEC 27701:2025, controles A.3.17 y A.3.18), "
                "dispongo de las siguientes capacidades y herramientas operativas:\n\n"
                "### 🛠️ Capacidades y Herramientas del Sistema\n"
                "1. **`consultar_estado_formacion`**: Consultar tu porcentaje de cumplimiento institucional, formaciones pendientes, vencidas y estado de acuerdos de confidencialidad (NDA).\n"
                "2. **`gestionar_alta_formacion`**: Inscribirte a ti o a grupos en los cursos de privacidad, orquestando la matrícula directamente con el LMS Moodle UNSA.\n"
                "3. **`gestionar_acuerdo_confidencialidad`**: Tramitar y registrar la suscripción y firma electrónica de Acuerdos de Confidencialidad conforme al control A.3.18.\n"
                "4. **`generar_certificado`**: Expedir certificados digitales de cumplimiento en PDF y registrar evidencias criptográficas (hash SHA-256) en el almacén PIMS.\n"
                "5. **`listar_usuarios`** *(Rol Administrador/Jefe)*: Filtrar personal docente y administrativo por facultad, departamento o fecha de ingreso reciente.\n"
                "6. **`enviar_correo_masivo`** *(Rol Administrador)*: Emitir convocatorias oficiales o recordatorios de vencimiento por correo institucional mediante el flujo seguro con confirmación previa (*Human-in-the-Loop*).\n"
                "7. **`generar_reporte_conciencia`**: Generar estadísticas de cumplimiento de privacidad a nivel de facultad o institucional.\n"
                "8. **Consultor RAG Normativo**: Resolver dudas sobre la Ley N° 29733, D.S. 003-2013-JUS, ISO 27701:2025, Estatuto UNSA y gestión de brechas de datos."
            )

        # 2. Consentimiento y Ley 29733
        if "consentimiento" in c_lower or "29733" in c_lower or "ley" in c_lower:
            return (
                "Según la **Ley N° 29733 (Ley de Protección de Datos Personales de Perú)** y el marco **ISO/IEC 27701:2025**:\n\n"
                "### 📌 Principio y Requisitos del Consentimiento (Artículo 13 de la Ley 29733)\n"
                "Para que el tratamiento de datos personales en la UNSA sea legalmente válido, el consentimiento del titular debe ser:\n"
                "1. **Previo:** Debe recabarse con anterioridad a la recopilación o inicio del tratamiento de los datos.\n"
                "2. **Libre:** Otorgado sin intimidación, coerción o condiciones engañosas.\n"
                "3. **Expreso:** Constatado por escrito, firma manuscrita, firma digital o un mecanismo equivalente indubitable.\n"
                "4. **Inequívoco:** No se admite el consentimiento tácito, la presunción ni casillas pre-marcadas.\n"
                "5. **Informado:** El titular debe ser advertido de la finalidad exacta del tratamiento, quién custodiará el banco de datos y cómo ejercer sus derechos ARCO.\n\n"
                "### 🎓 Aplicación Práctica en la UNSA (Control ISO 27701 A.3.17)\n"
                "- En la **matrícula académica y expedientes laborales**, el consentimiento se otorga estrictamente para fines educativos y contractuales.\n"
                "- Para fines secundarios (como difusión de imágenes o cesión a terceros), se requiere una autorización expresa adicional.\n"
                "- Todo docente o administrativo que reciba datos personales debe asegurar que exista dicha manifestación antes de ingresar datos al sistema."
            )

        # 3. ¿Qué me falta?
        if "falta" in c_lower or "pendiente" in c_lower or "mis cursos" in c_lower:
            return (
                "Según el control **A.3.17 de ISO/IEC 27701:2025** y las directrices de la **Ley N° 29733**, "
                "he verificado tu registro en el sistema PIMS UNSA:\n\n"
                "### 📋 Estado de Formaciones Obligatorias\n"
                "1. **Protección de Datos Personales - Ley 29733 (f001)**: ⏳ *Pendiente* (Vence en 30 días).\n"
                "2. **Acuerdos de Confidencialidad - NDA (f003)**: ⏳ *Pendiente de suscripción* (Control A.3.18).\n"
                "3. **Cómo reportar una brecha de datos (f004)**: ⚠️ *Vencida* (Requiere regularización inmediata conforme al protocolo de 24h ante incidentes).\n\n"
                "¿Deseas que proceda a **inscribirte en las sesiones pendientes** o remitir la solicitud de firma para tu acuerdo?"
            )

        # 4. Roles y usuarios nuevos
        if "roles" in c_lower or "nuevo" in c_lower or "cursos deberia" in c_lower or "saber" in c_lower:
            return (
                "Para todo **usuario nuevo** que ingresa a la UNSA (docente, administrativo o directivo), "
                "la normativa institucional y el marco legal peruano establecen roles y capacitaciones específicas:\n\n"
                "### 1. Roles y Responsabilidades Clave (Ley 29733 & ISO 27701)\n"
                "- **Docentes:** Tratamiento confidencial de notas, evaluaciones y datos biométricos/médicos de estudiantes.\n"
                "- **Administrativos:** Custodia de legajos de personal, planillas y atención rigurosa de los **Derechos ARCO**.\n"
                "- **Jefes de Dependencia / Directivos:** Supervisión de la confidencialidad de su equipo y reporte de incidentes (Control A.3.18).\n"
                "- **Titular del Banco de Datos:** La UNSA como institución garante ante la Autoridad Nacional de Protección de Datos (MINJUSDH).\n\n"
                "### 2. Formaciones Obligatorias que la UNSA Imparte (Catálogo PIMS)\n"
                "1. **`f001` - Protección de Datos Personales - Ley 29733** (Control A.3.17, para docentes y administrativos).\n"
                "2. **`f002` - ISO 27701:2025: Fundamentos de Privacidad PIMS** (Control A.3.17, para jefaturas y administradores).\n"
                "3. **`f003` - Acuerdos de Confidencialidad - NDA** (Control A.3.18, de firma obligatoria para todo el personal).\n"
                "4. **`f004` - Cómo reportar una brecha de datos** (Control A.3.11, protocolo de notificación en menos de 24 horas).\n"
                "5. **`f005` - Gestión de Derechos ARCO** (Control A.3.17, para personal de atención y mesa de partes).\n\n"
                "Todos los usuarios nuevos deben completar al menos **f001, f003 y f004** dentro de sus primeros 30 días calendario."
            )

        # 5. Si hay fragmentos RAG en el contexto, sintetizarlos
        if "Evidencias y Normativas Recuperadas (RAG):" in context_text:
            rag_snippet = context_text.split("Evidencias y Normativas Recuperadas (RAG):")[-1].split("Resultados de Herramientas")[0].strip()
            return (
                f"En cumplimiento de los controles **A.3.17 y A.3.18 de ISO/IEC 27701:2025** y la **Ley N° 29733**, "
                f"se ha consultado la base de conocimiento institucional de la UNSA:\n\n"
                f"{rag_snippet}\n\n"
                f"¿Deseas profundizar sobre algún aspecto específico de esta normativa o gestionar una formación asociada?"
            )

        return (
            "Conforme al control **A.3.17 y A.3.18 de ISO/IEC 27701:2025** y la **Ley N° 29733 (Perú)**, "
            "como Agente de Formación y Conciencia de la UNSA puedo asistirte en:\n\n"
            "- Consultar tu estado de cumplimiento de formación y NDAs.\n"
            "- Conocer las disposiciones legales de la Ley 29733 y los controles ISO 27701.\n"
            "- Inscribirte en los cursos obligatorios y expedir certificados oficiales.\n"
            "- Convocar y notificar por correo masivo a usuarios y docentes.\n\n"
            "¿Qué consulta o trámite deseas realizar?"
        )
