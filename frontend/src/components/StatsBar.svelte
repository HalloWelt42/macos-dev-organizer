<script lang="ts">
  import { rescan, getVersion } from "../lib/api";
  import type { Stats } from "../lib/types";

  let { stats, onRescan }: { stats: Stats; onRescan: () => void } = $props();
  let scanning = $state(false);
  let version = $state("");

  $effect(() => {
    getVersion().then((v) => (version = v)).catch(() => {});
  });

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
      {#if version}
        <span class="text-xs text-amber-600/60 dark:text-amber-400/60">v{version}</span>
      {/if}
    </div>
    <span class="text-sm text-slate-500 dark:text-slate-400">|</span>
    <span class="text-sm font-medium text-slate-700 dark:text-slate-200">{stats.total} Projekte</span>
    <span class="hidden text-sm text-slate-400 sm:inline">-- Lokale Projekte auf dem Mac organisieren</span>
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
