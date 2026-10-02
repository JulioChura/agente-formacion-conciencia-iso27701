# MCPs simulados. En produccion se reemplazan por clientes MCP reales.
class MCP_RRHH:
    def assign_training(self, empleado_id, curso_id):
        return {"estado": "asignado", "empleado_id": empleado_id, "curso_id": curso_id, "id": "asg-001"}

    def list_employees(self):
        return [{"id": "123", "nombre": "Juan Perez", "rol": "Marketing"}]

class MCP_Correo:
    def send_email(self, destinatario, asunto, cuerpo):
        return {"estado": "enviado", "destinatario": destinatario, "id": "mail-001"}

class MCP_Firma:
    def create_envelope(self, empleado_id, plantilla):
        return {"estado": "enviado_a_firma", "empleado_id": empleado_id, "envelope_id": "env-001"}

class MCP_Evidencias:
    def store_evidence(self, control, descripcion, datos):
        return {"estado": "guardado", "control": control, "id": "ev-001"}

class MCP_PostgreSQL:
    def execute_query(self, query):
        return [{"empleado_id": "123", "formacion_completada": False}]
