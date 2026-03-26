<script lang="ts">
  import { authHeaders } from "../lib/api";
  import type { Stats } from "../lib/types";

  let { stats, onRescan, onDonate }: { stats: Stats; onRescan: () => void; onDonate?: () => void } = $props();
  let scanning = $state(false);
  let scanPath = $state("");
  let dark = $state(typeof window !== "undefined" && document.documentElement.classList.contains("dark"));

  function toggleTheme() {
    dark = !dark;
    document.documentElement.classList.toggle("dark", dark);
    document.documentElement.style.colorScheme = dark ? "dark" : "light";
  }

  async function handleRescan() {
    scanning = true;
    scanPath = "";
    try {
      const hdrs = await authHeaders();
      const res = await fetch("/api/rescan/stream", { headers: hdrs });
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
          if (data.type === "path") scanPath = data.path;
          else if (data.type === "done") break;
        }
      }
      onRescan();
    } finally {
      scanning = false;
      scanPath = "";
    }
  }
</script>

<div class="flex items-center justify-between">
  <div class="flex items-center gap-4">
    <div class="flex items-center gap-2 rounded-lg bg-amber-900 px-3 py-1.5">
      <i class="fa-solid fa-wrench text-amber-400"></i>
      <span class="text-lg font-bold text-amber-200">DevRadar</span>
    </div>
    <button onclick={() => onDonate?.()} class="ml-1" title="Danke sagen">
      <i class="fa-solid fa-heart text-red-500" style="animation: heartbeat 1.5s ease-in-out infinite; filter: drop-shadow(0 0 3px rgba(239,68,68,0.4));"></i>
    </button>
    <span class="hidden text-lg font-semibold text-slate-700 sm:inline dark:text-slate-200">Lokale Projekte auf dem Mac organisieren</span>
  </div>
  <div class="flex items-center gap-2">
    <button
      onclick={handleRescan}
      disabled={scanning}
      class="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 transition-colors
             hover:border-amber-300 hover:text-amber-700
             disabled:opacity-50
             dark:border-slate-700 dark:text-slate-400 dark:hover:border-amber-600 dark:hover:text-amber-300"
    >
      <i class="fa-solid fa-arrows-rotate {scanning ? 'animate-spin' : ''}"></i>
      {scanning ? "Scanne..." : "Neu scannen"}
    </button>
    <button
      onclick={toggleTheme}
      class="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 transition-colors
             hover:border-amber-300 hover:text-amber-700
             dark:border-slate-700 dark:text-slate-400 dark:hover:border-amber-600 dark:hover:text-amber-300"
      title={dark ? "Light Mode" : "Dark Mode"}
    >
      <i class="fa-solid {dark ? 'fa-sun' : 'fa-moon'}"></i>
    </button>
  </div>
</div>

{#if scanning}
  <div class="mt-1 flex items-center gap-2 rounded bg-slate-100 px-3 py-1 text-[11px] text-slate-500 dark:bg-slate-800 dark:text-slate-400">
    <i class="fa-solid fa-spinner animate-spin text-amber-500"></i>
    <span class="truncate">{scanPath || "Starte Scan..."}</span>
  </div>
{/if}
