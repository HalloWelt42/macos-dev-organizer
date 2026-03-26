<script lang="ts">
  import { navigate } from "../lib/router";
  import { authHeaders } from "../lib/api";
  import SvelteMarkdown, { Html } from "@humanspeak/svelte-markdown";
  const mdRenderers = { html: Html };

  type Entry = {
    id: number;
    question: string;
    answer: string;
    project_ids: number[];
    tokens: number;
    elapsed: number;
    created_at: string;
  };

  let entries: Entry[] = $state([]);
  let selectedId: number | null = $state(null);
  let loading = $state(true);

  $effect(() => {
    loadHistory();
  });

  async function loadHistory() {
    loading = true;
    try {
      const res = await fetch("/api/ask/history");
      entries = await res.json();
    } catch {}
    loading = false;
  }

  async function deleteEntry(id: number) {
    const hdrs = await authHeaders();
    await fetch(`/api/ask/history/${id}`, { method: "DELETE", headers: hdrs });
    entries = entries.filter(e => e.id !== id);
    if (selectedId === id) selectedId = null;
  }

  let selected = $derived(entries.find(e => e.id === selectedId));

  function formatDate(iso: string): string {
    return new Date(iso).toLocaleString("de", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
  }
</script>

<div class="flex h-full min-h-0 gap-4">
  <!-- Liste (40%) -->
  <div class="w-[40%] flex flex-col min-h-0">
    <div class="shrink-0 flex items-center justify-between mb-2">
      <h2 class="text-sm font-semibold text-slate-700 dark:text-slate-200">
        <i class="fa-solid fa-clock-rotate-left mr-1 text-amber-500"></i>KI-Verlauf
      </h2>
      <span class="text-[10px] text-slate-400">{entries.length} Einträge</span>
    </div>
    <div class="min-h-0 flex-1 overflow-y-auto space-y-1">
      {#if loading}
        <div class="flex justify-center py-8">
          <i class="fa-solid fa-spinner animate-spin text-amber-500"></i>
        </div>
      {:else if entries.length === 0}
        <p class="py-8 text-center text-xs text-slate-400">Noch keine KI-Anfragen gestellt.</p>
      {:else}
        {#each entries as entry (entry.id)}
          <button
            onclick={() => selectedId = entry.id}
            class="flex w-full items-start gap-2 rounded-lg border p-3 text-left text-xs transition-colors
                   {selectedId === entry.id
                     ? 'border-amber-400 bg-amber-50 dark:border-amber-600 dark:bg-amber-950/30'
                     : 'border-slate-200 bg-white hover:border-slate-300 dark:border-slate-700 dark:bg-slate-800 dark:hover:border-slate-600'}"
          >
            <i class="fa-solid fa-robot mt-0.5 text-amber-500"></i>
            <div class="min-w-0 flex-1">
              <p class="truncate font-medium text-slate-700 dark:text-slate-200">{entry.question}</p>
              <div class="mt-1 flex items-center gap-2 text-[10px] text-slate-400">
                <span>{formatDate(entry.created_at)}</span>
                <span>{entry.tokens} Tokens</span>
                {#if entry.project_ids.length > 0}
                  <span>{entry.project_ids.length} Projekte</span>
                {/if}
              </div>
            </div>
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <span
              onclick={(e) => { e.stopPropagation(); deleteEntry(entry.id); }}
              class="shrink-0 cursor-pointer rounded p-1 text-slate-400 hover:text-red-500"
              title="Löschen"
              role="button"
              tabindex="-1"
            >
              <i class="fa-solid fa-trash-can text-[10px]"></i>
            </span>
          </button>
        {/each}
      {/if}
    </div>
  </div>

  <!-- Detail (60%) -->
  <div class="w-[60%] flex flex-col min-h-0">
    {#if selected}
      <div class="flex flex-col min-h-0 rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
        <div class="shrink-0 border-b border-slate-200 px-4 py-2 dark:border-slate-700">
          <p class="text-sm font-medium text-slate-700 dark:text-slate-200">{selected.question}</p>
          <div class="mt-1 flex items-center gap-3 text-[10px] text-slate-400">
            <span>{formatDate(selected.created_at)}</span>
            <span class="font-mono">{selected.tokens} Tokens -- {selected.elapsed.toFixed(1)}s</span>
          </div>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto p-4">
          <div class="prose prose-sm max-w-none dark:prose-invert
                      prose-headings:text-slate-800 dark:prose-headings:text-slate-200
                      prose-a:text-amber-600 dark:prose-a:text-amber-400">
            <SvelteMarkdown source={selected.answer} renderers={mdRenderers} />
          </div>
        </div>
      </div>
    {:else}
      <div class="flex flex-1 items-center justify-center text-sm text-slate-400">
        <p>Eintrag auswählen um die Antwort zu sehen</p>
      </div>
    {/if}
  </div>
</div>
