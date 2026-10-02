const { createApp, ref, nextTick } = Vue;

createApp({
  setup() {
    const mensajes = ref([]);
    const input = ref("");
    const cargando = ref(false);
    const scrollArea = ref(null);
    const thread_id = "default";

    function renderMarkdown(texto) {
      if (!texto) return "";
      const html = marked.parse(texto);
      return DOMPurify.sanitize(html);
    }

    async function scrollAbajo() {
      await nextTick();
      if (scrollArea.value) {
        scrollArea.value.scrollTop = scrollArea.value.scrollHeight;
      }
    }

    async function enviar() {
      if (!input.value.trim() || cargando.value) return;
      const texto = input.value;
      mensajes.value.push({ rol: "user", contenido: texto });
      input.value = "";
      cargando.value = true;
      await scrollAbajo();

      const idx = mensajes.value.length;
      mensajes.value.push({ rol: "assistant", contenido: "", streaming: true });
      await scrollAbajo();

      try {
        const res = await fetch("http://localhost:8000/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mensaje: texto, thread_id }),
        });

        if (!res.ok) throw new Error("Error en el servidor");

        cargando.value = false;
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lineas = buffer.split("\n\n");
          buffer = lineas.pop();
          for (const linea of lineas) {
            if (!linea.startsWith("data: ")) continue;
            try {
              const data = JSON.parse(linea.slice(6));
              if (data.token) {
                mensajes.value[idx].contenido += data.token;
                await scrollAbajo();
              }
              if (data.done) {
                mensajes.value[idx].streaming = false;
                if (data.fuentes && data.fuentes.length) {
                  console.log("Fuentes:", data.fuentes);
                }
              }
            } catch (e) {
              console.error("Error parseando SSE:", e);
            }
          }
        }
        mensajes.value[idx].streaming = false;
      } catch (err) {
        cargando.value = false;
        mensajes.value[idx].contenido = "Lo siento, hubo un error al procesar tu consulta. Intenta de nuevo.";
        mensajes.value[idx].streaming = false;
        console.error(err);
      }
    }

    return { mensajes, input, cargando, enviar, renderMarkdown, scrollArea };
  },
}).mount("#app");