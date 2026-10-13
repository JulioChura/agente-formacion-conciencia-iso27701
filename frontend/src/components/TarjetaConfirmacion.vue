<template>
  <div class="confirmation-card" v-if="action">
    <div class="confirmation-header">
      <span>⚠️</span>
      <span>Aprobación Requerida para Acción del Sistema (Human-in-the-Loop)</span>
    </div>

    <div class="confirmation-preview">
      <div class="preview-field">
        <strong>Tipo de Acción:</strong> {{ formatTipo(action.tipo) }}
      </div>

      <div class="preview-field" v-if="action.preview?.total">
        <strong>Destinatarios ({{ action.preview.total }}):</strong>
        <span>{{ formatDestinatarios(action.preview.destinatarios) }}</span>
      </div>

      <div class="preview-field" v-if="action.preview?.asunto">
        <strong>Asunto:</strong> {{ action.preview.asunto }}
      </div>

      <div class="preview-field" v-if="action.preview?.cuerpo">
        <strong>Cuerpo del Mensaje:</strong>
        <p style="white-space: pre-line; margin-top: 4px; color: #4b5563;">{{ action.preview.cuerpo }}</p>
      </div>

      <div class="preview-field" v-if="action.preview?.curso">
        <strong>Curso / Formación:</strong> {{ action.preview.curso }}
      </div>

      <div class="preview-field" v-if="action.preview?.accion">
        <strong>Operación:</strong> {{ action.preview.accion }}
      </div>
    </div>

    <div class="confirmation-actions">
      <button class="btn-cancel" :disabled="loading" @click="$emit('cancel')">
        ✕ Cancelar
      </button>
      <button class="btn-confirm" :disabled="loading" @click="$emit('confirm')">
        ✓ Confirmar y Ejecutar
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  action: {
    type: Object,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  }
});

defineEmits(['confirm', 'cancel']);

function formatTipo(tipo) {
  if (tipo === 'correo_masivo') return 'Envío Masivo de Correos Institucionales';
  if (tipo === 'inscripcion_masiva') return 'Matrícula Masiva en LMS Moodle UNSA';
  if (tipo === 'firmar_nda') return 'Firma Electrónica de Acuerdo de Confidencialidad';
  return tipo || 'Acción de Escritura';
}

function formatDestinatarios(dests) {
  if (!dests) return 'Ninguno';
  if (Array.isArray(dests)) {
    return dests.slice(0, 5).join(', ') + (dests.length > 5 ? ` y ${dests.length - 5} más...` : '');
  }
  return String(dests);
}
</script>
