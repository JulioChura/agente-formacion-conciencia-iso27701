import { defineStore } from 'pinia';
import { api } from '../api';

export const useChatStore = defineStore('chat', {
  state: () => ({
    conversaciones: [],
    currentConversacionId: null,
    mensajes: [],
    isStreaming: false,
    streamingText: '',
    pendingApproval: null, // { action_id, tipo, preview: {destinatarios, asunto, cuerpo} }
    dashboardData: null
  }),
  actions: {
    async loadConversaciones() {
      try {
        const convs = await api.getConversaciones();
        this.conversaciones = convs;
        if (!this.currentConversacionId && convs.length > 0) {
          await this.selectConversacion(convs[0].id);
        }
      } catch (err) {
        console.error('Error cargando conversaciones:', err);
      }
    },

    async selectConversacion(id) {
      this.currentConversacionId = id;
      this.pendingApproval = null;
      try {
        const data = await api.getConversacion(id);
        this.mensajes = data.mensajes || [];
      } catch (err) {
        console.error('Error seleccionando conversación:', err);
      }
    },

    async createNewConversacion() {
      try {
        const newConv = await api.crearConversacion('Nueva consulta PIMS');
        this.conversaciones.unshift(newConv);
        await this.selectConversacion(newConv.id);
      } catch (err) {
        console.error('Error creando nueva conversación:', err);
      }
    },

    async sendUserMessage(texto) {
      if (!texto.trim() || this.isStreaming) return;
      if (!this.currentConversacionId) {
        await this.createNewConversacion();
      }

      const convId = this.currentConversacionId;

      // Insertar temporalmente mensaje del usuario
      this.mensajes.push({
        id: Date.now(),
        conversacion_id: convId,
        rol: 'user',
        contenido: texto,
        created_at: new Date().toISOString()
      });

      this.isStreaming = true;
      this.streamingText = '';
      this.pendingApproval = null;

      // Mensaje placeholder para el asistente
      const assistantMsgIndex = this.mensajes.length;
      this.mensajes.push({
        id: Date.now() + 1,
        conversacion_id: convId,
        rol: 'assistant',
        contenido: '',
        created_at: new Date().toISOString()
      });

      await api.sendMessage(convId, texto, {
        onToken: (token) => {
          this.streamingText += token;
          this.mensajes[assistantMsgIndex].contenido = this.streamingText;
        },
        onApprovalRequired: (payload) => {
          this.pendingApproval = payload;
        },
        onDone: async () => {
          this.isStreaming = false;
          this.streamingText = '';
          await this.loadDashboard();
        },
        onError: (err) => {
          this.isStreaming = false;
          this.mensajes[assistantMsgIndex].contenido += `\n\n*(Error: ${err})*`;
        }
      });
    },

    async respondApproval(approved) {
      if (!this.pendingApproval || !this.currentConversacionId) return;
      const actionId = this.pendingApproval.action_id;
      const convId = this.currentConversacionId;

      this.isStreaming = true;
      try {
        const res = await api.approveAction(convId, actionId, approved);
        this.pendingApproval = null;
        // Recargar mensajes para sincronizar estado
        const data = await api.getConversacion(convId);
        this.mensajes = data.mensajes || [];
        await this.loadDashboard();
      } catch (err) {
        console.error('Error respondiendo aprobación:', err);
      } finally {
        this.isStreaming = false;
      }
    },

    async loadDashboard() {
      try {
        const d = await api.getDashboardEstado();
        this.dashboardData = d;
      } catch (err) {
        console.error('Error cargando estado de dashboard:', err);
      }
    }
  }
});
