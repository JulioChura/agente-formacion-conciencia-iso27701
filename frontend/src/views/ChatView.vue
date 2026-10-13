<template>
  <div class="chat-layout">
    <!-- Barra Lateral Izquierda -->
    <Sidebar />

    <!-- Área Principal de Chat -->
    <main class="chat-main">
      <header class="chat-header">
        <div class="header-title-box">
          <h2>Agente de Formación y Conciencia</h2>
        </div>
        <div class="header-badges">
          <span class="badge-pims">ISO 27701 (A.3.17 & A.3.18)</span>
          <span class="badge-tag">Ley 29733</span>
          <span class="badge-tag">{{ authStore.user?.facultad || 'UNSA' }}</span>
        </div>
      </header>

      <!-- Contenedor de Mensajes con Scroll -->
      <div class="chat-messages" ref="messagesContainer">
        <ChatMessage
          v-for="msg in chatStore.mensajes"
          :key="msg.id"
          :message="msg"
        />

        <!-- Tarjeta de Confirmación de Acción (Human-in-the-Loop) -->
        <TarjetaConfirmacion
          v-if="chatStore.pendingApproval"
          :action="chatStore.pendingApproval"
          :loading="chatStore.isStreaming"
          @confirm="handleConfirmApproval"
          @cancel="handleCancelApproval"
        />

        <!-- Indicador de tipeo / streaming -->
        <div v-if="chatStore.isStreaming" class="typing-indicator">
          <span>🛡️ Agente formulando respuesta</span>
          <span class="typing-dots">...</span>
        </div>
      </div>

      <!-- Barra de Sugerencias y Acciones Rápidas -->
      <div class="quick-actions-bar" v-if="!chatStore.isStreaming">
        <button
          v-for="accion in sugerenciasAcciones"
          :key="accion"
          class="quick-action-btn"
          @click="ejecutarSugerencia(accion)"
        >
          💡 {{ accion }}
        </button>
      </div>

      <!-- Barra Inferior de Entrada de Mensaje -->
      <footer class="chat-input-area">
        <form class="input-container" @submit.prevent="handleSendMessage">
          <textarea
            v-model="inputMessage"
            class="chat-textarea"
            placeholder="Pregunta sobre formaciones, NDAs, Ley 29733, o solicita una acción institucional..."
            rows="1"
            :disabled="chatStore.isStreaming"
            @keydown.enter.exact.prevent="handleSendMessage"
            @input="autoResize"
            ref="textareaRef"
          ></textarea>
          <button
            type="submit"
            class="btn-send"
            :disabled="chatStore.isStreaming || !inputMessage.trim()"
            title="Enviar mensaje"
          >
            ➤
          </button>
        </form>
      </footer>
    </main>

    <!-- Panel Lateral Derecho de Estado y Cumplimiento -->
    <PanelEstado :data="chatStore.dashboardData" />
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch, computed } from 'vue';
import { useAuthStore } from '../stores/auth';
import { useChatStore } from '../stores/chat';
import Sidebar from '../components/Sidebar.vue';
import ChatMessage from '../components/ChatMessage.vue';
import TarjetaConfirmacion from '../components/TarjetaConfirmacion.vue';
import PanelEstado from '../components/PanelEstado.vue';

const authStore = useAuthStore();
const chatStore = useChatStore();

const inputMessage = ref('');
const messagesContainer = ref(null);
const textareaRef = ref(null);

const sugerenciasAcciones = computed(() => {
  if (authStore.isAdmin) {
    return [
      '¿Quiénes son los usuarios nuevos?',
      'Envíales un correo sobre el curso del lunes a las 10',
      'Inscribe a todos los docentes de Ingeniería en el curso f001',
      '¿Qué me falta?'
    ];
  }
  return [
    '¿Qué me falta?',
    '¿Qué dice el control A.3.17 de ISO 27701?',
    '¿Cómo reportar una brecha de datos?',
    'Firmar mi acuerdo de confidencialidad'
  ];
});

onMounted(async () => {
  await chatStore.loadConversaciones();
  await chatStore.loadDashboard();
  scrollToBottom();
});

watch(
  () => chatStore.mensajes.length,
  () => {
    nextTick(scrollToBottom);
  }
);

watch(
  () => chatStore.streamingText,
  () => {
    nextTick(scrollToBottom);
  }
);

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
}

function autoResize(e) {
  const target = e.target;
  target.style.height = 'auto';
  target.style.height = `${Math.min(target.scrollHeight, 120)}px`;
}

async function handleSendMessage() {
  const text = inputMessage.value.trim();
  if (!text || chatStore.isStreaming) return;

  inputMessage.value = '';
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto';
  }

  await chatStore.sendUserMessage(text);
}

function ejecutarSugerencia(texto) {
  inputMessage.value = texto;
  handleSendMessage();
}

async function handleConfirmApproval() {
  await chatStore.respondApproval(true);
}

async function handleCancelApproval() {
  await chatStore.respondApproval(false);
}
</script>
