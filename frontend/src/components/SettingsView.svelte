<script lang="ts">
  import { authHeaders } from "../lib/api";
  let { onSave }: { onSave: () => void } = $props();

  let roots: string[] = $state([]);
  let newRoot = $state("");
  let llmEnabled = $state(false);
  let llmUrl = $state("http://localhost:1234/v1");
  let llmModel = $state("");
  let llmModels: string[] = $state([]);
  let saving = $state(false);

  // Ordner-Browser
  let browsing = $state(false);
  let browseDirs: { name: string; path: string }[] = $state([]);
  let browseCurrent = $state("");
  let browseParent: string | null = $state(null);

  $effect(() => {
    loadConfig();
  });

  async function loadConfig() {
    try {
      const [rootsRes, llmRes] = await Promise.all([
        fetch("/api/config/roots"),
        fetch("/api/config/llm"),
      ]);
      const rootsData = await rootsRes.json();
      const llmData = await llmRes.json();
      roots = rootsData.roots || [];
      llmEnabled = llmData.enabled ?? false;
      llmUrl = llmData.base_url ?? "http://localhost:1234/v1";
      llmModel = llmData.model ?? "";
    } catch {}
    if (llmEnabled && llmUrl) loadModels();
  }

  let llmStatus: "idle" | "loading" | "ok" | "error" = $state("idle");

  async function loadModels() {
    llmStatus = "loading";
    try {
      const res = await fetch("/api/llm/models");
      const data = await res.json();
      llmModels = data.models || [];
      llmStatus = llmModels.length > 0 ? "ok" : "error";
    } catch {
      llmModels = [];
      llmStatus = "error";
    }
    setTimeout(() => { if (llmStatus !== "loading") llmStatus = "idle"; }, 3000);
  }

  async function saveAll() {
    saving = true;
    try {
      const hdrs = await authHeaders({ "Content-Type": "application/json" });
      await Promise.all([
        fetch("/api/config/roots", {
          method: "POST",
          headers: hdrs,
          body: JSON.stringify({ roots }),
        }),
        fetch("/api/config/llm", {
          method: "POST",
          headers: hdrs,
          body: JSON.stringify({ enabled: llmEnabled, base_url: llmUrl, model: llmModel }),
        }),
      ]);
      onSave();
    } finally {
      saving = false;
    }
  }

  function addRoot() {
    const path = newRoot.trim();
    if (path && !roots.includes(path)) {
      roots = [...roots, path];
      newRoot = "";
    }
  }

  function removeRoot(index: number) {
    roots = roots.filter((_, i) => i !== index);
  }

  // Ordner-Browser
  async function openBrowser(startPath = "~") {
    browsing = true;
    await browse(startPath);
  }

  async function browse(path: string) {
    try {
      const res = await fetch(`/api/browse?path=${encodeURIComponent(path)}`);
      const data = await res.json();
      browseDirs = data.dirs || [];
      browseCurrent = data.current || "";
      browseParent = data.parent || null;
    } catch {}
  }

  function selectBrowsed() {
    if (browseCurrent && !roots.includes(browseCurrent)) {
      roots = [...roots, browseCurrent];
    }
    browsing = false;
  }
</script>

<div class="space-y-6">
  <h1 class="text-xl font-bold text-slate-900 dark:text-slate-100">
    <i class="fa-solid fa-gear mr-2 text-amber-500"></i>Einstellungen
  </h1>

  <!-- Scan-Verzeichnisse -->
  <section class="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
    <h2 class="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-300">
      <i class="fa-solid fa-folder-tree mr-2 text-amber-500"></i>Scan-Verzeichnisse
    </h2>
    <p class="mb-3 text-xs text-slate-500">Verzeichnisse die nach Projekten durchsucht werden.</p>

    <div class="space-y-1.5">
      {#each roots as root, i}
        <div class="flex items-center gap-2 rounded-md bg-slate-50 px-3 py-2 dark:bg-slate-900">
          <i class="fa-solid fa-folder text-amber-400 text-xs"></i>
          <code class="flex-1 truncate text-xs">{root}</code>
          <button
            onclick={() => removeRoot(i)}
            class="shrink-0 text-xs text-slate-400 hover:text-red-500"
            title="Entfernen"
            aria-label="Pfad entfernen"
          >
            <i class="fa-solid fa-trash-can"></i>
          </button>
        </div>
      {/each}
      {#if roots.length === 0}
        <p class="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:bg-amber-950/30 dark:text-amber-400">
          Noch keine Verzeichnisse konfiguriert. Füge mindestens eines hinzu.
        </p>
      {/if}
    </div>

    <div class="mt-3 flex gap-2">
      <input
        type="text"
        bind:value={newRoot}
        placeholder="/Pfad/zum/Verzeichnis"
        onkeydown={(e) => e.key === "Enter" && addRoot()}
        class="flex-1 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none
               focus:border-amber-400 dark:border-slate-600 dark:bg-slate-900"
      />
      <button
        onclick={() => openBrowser(newRoot || "~")}
        class="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:border-amber-300 hover:text-amber-700
               dark:border-slate-600 dark:text-slate-400"
        title="Ordner durchsuchen"
      >
        <i class="fa-solid fa-folder-open"></i>
      </button>
      <button
        onclick={addRoot}
        disabled={!newRoot.trim()}
        class="rounded-md bg-amber-500 px-3 py-2 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-50"
      >
        Hinzufügen
      </button>
    </div>

    <!-- Ordner-Browser -->
    {#if browsing}
      <div class="mt-3 rounded-md border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30">
        <div class="flex items-center justify-between border-b border-amber-200 px-3 py-2 dark:border-amber-800">
          <div class="flex items-center gap-2 text-xs">
            {#if browseParent}
              <button onclick={() => browse(browseParent!)} class="rounded px-1.5 py-0.5 hover:bg-amber-200 dark:hover:bg-amber-900" title="Übergeordneter Ordner">
                <i class="fa-solid fa-arrow-up"></i>
              </button>
            {/if}
            <code class="truncate text-xs text-slate-600 dark:text-slate-400">{browseCurrent}</code>
          </div>
          <div class="flex gap-2">
            <button onclick={selectBrowsed} class="rounded-md bg-amber-500 px-3 py-1 text-xs font-medium text-white hover:bg-amber-600">
              Diesen Ordner wählen
            </button>
            <button onclick={() => browsing = false} class="text-xs text-slate-500 hover:text-slate-700">Abbrechen</button>
          </div>
        </div>
        <div class="max-h-48 overflow-y-auto p-1">
          {#each browseDirs as dir}
            <button
              onclick={() => browse(dir.path)}
              class="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-xs text-slate-700 transition-colors
                     hover:bg-amber-100 dark:text-slate-300 dark:hover:bg-amber-900/50"
            >
              <i class="fa-solid fa-folder text-amber-400"></i>
              {dir.name}
            </button>
          {/each}
          {#if browseDirs.length === 0}
            <p class="py-3 text-center text-xs text-slate-400">Keine Unterverzeichnisse</p>
          {/if}
        </div>
      </div>
    {/if}
  </section>

  <!-- KI-Einstellungen -->
  <section class="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
    <h2 class="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-300">
      <i class="fa-solid fa-robot mr-2 text-amber-500"></i>KI-Integration (optional)
    </h2>
    <p class="mb-3 text-xs text-slate-500">Verbindung zu einem lokalen LLM für intelligente Suche und Beschreibungen.</p>

    <label class="flex items-center gap-3 text-sm text-slate-700 dark:text-slate-300">
      <input
        type="checkbox"
        bind:checked={llmEnabled}
        class="rounded border-slate-300 text-amber-500 focus:ring-amber-400 dark:border-slate-600"
      />
      KI-Funktionen aktivieren
    </label>

    {#if llmEnabled}
      <div class="mt-4 space-y-3">
        <div>
          <label class="mb-1 block text-xs font-medium text-slate-500" for="llm-url">Server-URL</label>
          <div class="flex gap-2">
            <input
              id="llm-url"
              type="text"
              bind:value={llmUrl}
              placeholder="http://localhost:1234/v1"
              class="flex-1 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none
                     focus:border-amber-400 dark:border-slate-600 dark:bg-slate-900"
            />
            <button
              onclick={loadModels}
              disabled={llmStatus === "loading"}
              class="rounded-md border px-3 py-2 text-xs transition-colors
                     {llmStatus === 'ok' ? 'border-green-300 text-green-600 dark:border-green-700 dark:text-green-400' :
                      llmStatus === 'error' ? 'border-red-300 text-red-600 dark:border-red-700 dark:text-red-400' :
                      'border-slate-200 text-slate-600 hover:border-amber-300 hover:text-amber-700 dark:border-slate-600 dark:text-slate-400'}"
              title="Verbindung testen und Modelle laden"
            >
              {#if llmStatus === "loading"}
                <i class="fa-solid fa-spinner animate-spin mr-1"></i>Teste...
              {:else if llmStatus === "ok"}
                <i class="fa-solid fa-check mr-1"></i>{llmModels.length} Modelle
              {:else if llmStatus === "error"}
                <i class="fa-solid fa-xmark mr-1"></i>Keine Verbindung
              {:else}
                <i class="fa-solid fa-plug mr-1"></i>Verbinden
              {/if}
            </button>
          </div>
        </div>

        <div>
          <label class="mb-1 block text-xs font-medium text-slate-500" for="llm-model">Modell</label>
          {#if llmModels.length > 0}
            <select
              id="llm-model"
              bind:value={llmModel}
              class="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none
                     focus:border-amber-400 dark:border-slate-600 dark:bg-slate-900"
            >
              <option value="">-- Modell wählen --</option>
              {#each llmModels as model}
                <option value={model}>{model}</option>
              {/each}
            </select>
          {:else}
            <input
              id="llm-model"
              type="text"
              bind:value={llmModel}
              placeholder="Modellname (oder 'Verbinden' klicken)"
              class="w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none
                     focus:border-amber-400 dark:border-slate-600 dark:bg-slate-900"
            />
            <p class="mt-1 text-[10px] text-slate-400">Klicke "Verbinden" um verfügbare Modelle zu laden.</p>
          {/if}
        </div>
      </div>

      <!-- Übersetzungs-Prompt -->
      <details class="mt-4">
        <summary class="cursor-pointer text-xs font-medium text-slate-500 hover:text-slate-700 dark:hover:text-slate-300">
          <i class="fa-solid fa-file-lines mr-1"></i>Übersetzungs-Prompt anzeigen
        </summary>
        <pre class="mt-2 max-h-48 overflow-y-auto rounded-md bg-slate-50 p-3 text-[11px] leading-relaxed text-slate-600 dark:bg-slate-900 dark:text-slate-400">Übersetze die folgende README-Datei ins Deutsche.
Gib NUR die übersetzte README aus, KEINE Einleitung.

ABSOLUTE REGELN:
1. Code-Blöcke KOMPLETT UNVERÄNDERT übernehmen.
2. Inline-Code KOMPLETT UNVERÄNDERT übernehmen.
3. Markdown-Formatierung EXAKT beibehalten.
4. Fachbegriffe bleiben Englisch.
5. Produkt-/Projektnamen, URLs, Pfade, Dateinamen unverändert.
6. Badge-Links und Shield-URLs 1:1 übernehmen.
7. Natürlich klingend, nicht maschinell.
8. VOLLSTÄNDIG übersetzen, nichts weglassen.
9. KEINE Einleitung -- direkt mit dem Inhalt beginnen.</pre>
      </details>
    {/if}
  </section>

  <!-- Speichern -->
  <div class="flex justify-end">
    <button
      onclick={saveAll}
      disabled={saving}
      class="rounded-lg bg-amber-500 px-6 py-2 text-sm font-medium text-white transition-colors hover:bg-amber-600 disabled:opacity-50"
    >
      {#if saving}
        <i class="fa-solid fa-spinner animate-spin mr-2"></i>Speichere...
      {:else}
        <i class="fa-solid fa-floppy-disk mr-2"></i>Speichern & Neu scannen
      {/if}
    </button>
  </div>
</div>
