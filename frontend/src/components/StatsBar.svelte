<script lang="ts">
  import { rescan } from "../lib/api";
  import type { Stats } from "../lib/types";

  let { stats, onRescan, onDonate }: { stats: Stats; onRescan: () => void; onDonate?: () => void } = $props();
  let scanning = $state(false);

  async function handleRescan() {
    scanning = true;
    try {
      await rescan();
      onRescan();
    } finally {
      scanning = false;
    }
  }
</script>

<div class="flex items-center justify-between">
  <div class="flex items-center gap-4">
    <div class="flex items-center gap-2 rounded-lg bg-amber-100 px-3 py-1.5 dark:bg-amber-900">
      <i class="fa-solid fa-wrench text-amber-600 dark:text-amber-400"></i>
      <span class="text-lg font-bold text-amber-800 dark:text-amber-200">DevRadar</span>
    </div>
    <button onclick={() => onDonate?.()} class="ml-1" title="Danke sagen">
      <i class="fa-solid fa-heart text-red-500" style="animation: heartbeat 1.5s ease-in-out infinite; filter: drop-shadow(0 0 3px rgba(239,68,68,0.4));"></i>
    </button>
    <span class="hidden text-lg font-semibold text-slate-700 sm:inline dark:text-slate-200">Lokale Projekte auf dem Mac organisieren</span>
  </div>
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
</div>
