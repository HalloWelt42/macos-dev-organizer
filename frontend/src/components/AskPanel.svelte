<script lang="ts">
  import { authHeaders } from "../lib/api";
  let {
    onChunk,
    onDone,
    onStart,
  }: {
    onChunk: (data: { full: string; stats: { tokens: number; elapsed: number; tps: number } }) => void;
    onDone: (data: { full: string; project_ids: number[]; fallback: boolean; stats: { tokens: number; elapsed: number; tps: number } }) => void;
    onStart: () => void;
  } = $props();

  let question = $state("");
  let loading = $state(false);

  async function handleAsk() {
    if (!question.trim()) return;
    loading = true;
    onStart();

    try {
      const hdrs = await authHeaders({ "Content-Type": "application/json" });
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: hdrs,
        body: JSON.stringify({ question }),
      });

      if (!res.ok) throw new Error(`API-Fehler ${res.status}`);

      const contentType = res.headers.get("content-type") || "";

      if (contentType.includes("text/event-stream")) {
        const reader = res.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          while (buffer.includes("\n\n")) {
            const idx = buffer.indexOf("\n\n");
            const line = buffer.slice(0, idx).trim();
            buffer = buffer.slice(idx + 2);
            if (!line.startsWith("data: ")) continue;
            const data = JSON.parse(line.slice(6));
            if (data.type === "chunk") onChunk(data);
            else if (data.type === "done") onDone({ ...data, fallback: false });
          }
        }
      } else {
        const data = await res.json();
        onDone({ full: data.answer, project_ids: data.project_ids || [], fallback: data.fallback, stats: { tokens: 0, elapsed: 0, tps: 0 } });
      }
    } catch (e) {
      onDone({ full: `Fehler: ${e instanceof Error ? e.message : "Unbekannt"}`, project_ids: [], fallback: true, stats: { tokens: 0, elapsed: 0, tps: 0 } });
    } finally {
      loading = false;
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleAsk();
    }
  }
</script>

<div class="relative">
  <i class="fa-solid fa-robot absolute left-3 top-1/2 -translate-y-1/2 text-amber-500"></i>
  <input
    type="text"
    bind:value={question}
    onkeydown={handleKeydown}
    placeholder="KI fragen, z.B. 'Welche Projekte nutzen Svelte?'"
    class="w-full rounded-lg border border-slate-200 bg-white py-3 pl-10 pr-12 text-lg shadow-sm outline-none transition-all
           placeholder:text-slate-400
           focus:border-amber-400 focus:ring-2 focus:ring-amber-200
           dark:border-slate-700 dark:bg-slate-800 dark:placeholder:text-slate-500
           dark:focus:border-amber-500 dark:focus:ring-amber-800"
  />
  {#if question}
    <button
      onclick={() => { question = ""; }}
      class="absolute right-10 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
      aria-label="Frage leeren"
    >
      <i class="fa-solid fa-xmark"></i>
    </button>
  {/if}
  <button
    onclick={handleAsk}
    disabled={loading || !question.trim()}
    class="absolute right-3 top-1/2 -translate-y-1/2 text-amber-500 hover:text-amber-600 disabled:opacity-30"
  >
    {#if loading}
      <i class="fa-solid fa-spinner animate-spin"></i>
    {:else}
      <i class="fa-solid fa-paper-plane"></i>
    {/if}
  </button>
</div>
