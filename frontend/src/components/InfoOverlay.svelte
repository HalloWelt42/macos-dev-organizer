<script lang="ts">
  import { getVersion } from "../lib/api";

  let { onClose }: { onClose: () => void } = $props();
  let version = $state("");

  $effect(() => {
    getVersion().then(v => version = v).catch(() => {});
  });

  const year = new Date().getFullYear();

  const pythonDeps = [
    { name: "FastAPI", version: "0.135", license: "MIT", url: "https://fastapi.tiangolo.com" },
    { name: "Uvicorn", version: "0.42", license: "BSD-3-Clause", url: "https://www.uvicorn.org" },
    { name: "httpx", version: "0.28", license: "BSD-3-Clause", url: "https://www.python-httpx.org" },
    { name: "Watchdog", version: "6.0", license: "Apache-2.0", url: "https://github.com/gorakhargosh/watchdog" },
    { name: "SQLite FTS5", version: "", license: "Public Domain", url: "https://www.sqlite.org" },
  ];

  const frontendDeps = [
    { name: "Svelte", version: "5", license: "MIT", url: "https://svelte.dev" },
    { name: "Tailwind CSS", version: "4", license: "MIT", url: "https://tailwindcss.com" },
    { name: "Vite", version: "8", license: "MIT", url: "https://vite.dev" },
    { name: "TypeScript", version: "5.9", license: "Apache-2.0", url: "https://www.typescriptlang.org" },
    { name: "FontAwesome Free", version: "7", license: "CC-BY-4.0 / OFL-1.1 / MIT", url: "https://fontawesome.com" },
    { name: "marked.js", version: "", license: "MIT", url: "https://marked.js.org" },
    { name: "DOMPurify", version: "3", license: "MPL-2.0 / Apache-2.0", url: "https://github.com/cure53/DOMPurify" },
    { name: "highlight.js", version: "11", license: "BSD-3-Clause", url: "https://highlightjs.org" },
    { name: "svelte-markdown", version: "", license: "MIT", url: "https://github.com/humanspeak/svelte-markdown" },
  ];
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div
  class="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
  onclick={onClose}
  onkeydown={(e) => e.key === "Escape" && onClose()}
  role="dialog"
  aria-label="Info"
>
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
  <div
    class="relative max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-2xl"
    onclick={(e) => e.stopPropagation()}
  >
    <!-- Schliessen -->
    <button onclick={onClose} class="absolute top-4 right-4 text-slate-400 hover:text-white" aria-label="Schliessen">
      <i class="fa-solid fa-xmark text-lg"></i>
    </button>

    <!-- Header -->
    <div class="mb-6 text-center">
      <div class="mb-2 inline-flex items-center gap-2 rounded-lg bg-amber-900/30 px-4 py-2">
        <i class="fa-solid fa-wrench text-xl text-amber-400"></i>
        <span class="text-2xl font-bold text-amber-200">DevRadar</span>
      </div>
      {#if version}
        <p class="mt-1 text-sm text-slate-400">Version {version}</p>
      {/if}
      <p class="mt-2 text-xs text-slate-500">Lokale Projekte auf dem Mac organisieren</p>
    </div>

    <!-- Danke -->
    <div class="mb-6 rounded-lg border border-slate-700 bg-slate-800/50 p-4">
      <h3 class="mb-2 text-sm font-semibold text-slate-300">
        <i class="fa-solid fa-heart text-red-400 mr-1"></i> Danke an die Open-Source-Community
      </h3>
      <p class="text-xs leading-relaxed text-slate-400">
        Dieses Projekt baut auf grossartiger Open-Source-Software auf.
        Alle verwendeten Bibliotheken sind unter freien Lizenzen verfügbar.
      </p>
    </div>

    <!-- Backend -->
    <div class="mb-4">
      <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Backend</h3>
      <div class="space-y-1">
        {#each pythonDeps as dep}
          <a href={dep.url} target="_blank" rel="noopener noreferrer"
            class="flex items-center justify-between rounded-md px-3 py-1.5 text-xs transition-colors hover:bg-slate-800 no-underline">
            <span class="font-medium text-slate-200">
              {dep.name}
              {#if dep.version}
                <span class="ml-1 text-slate-500">{dep.version}</span>
              {/if}
            </span>
            <span class="rounded bg-slate-800 px-2 py-0.5 text-[10px] text-slate-400">{dep.license}</span>
          </a>
        {/each}
      </div>
    </div>

    <!-- Frontend -->
    <div class="mb-6">
      <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Frontend</h3>
      <div class="space-y-1">
        {#each frontendDeps as dep}
          <a href={dep.url} target="_blank" rel="noopener noreferrer"
            class="flex items-center justify-between rounded-md px-3 py-1.5 text-xs transition-colors hover:bg-slate-800 no-underline">
            <span class="font-medium text-slate-200">
              {dep.name}
              {#if dep.version}
                <span class="ml-1 text-slate-500">{dep.version}</span>
              {/if}
            </span>
            <span class="rounded bg-slate-800 px-2 py-0.5 text-[10px] text-slate-400">{dep.license}</span>
          </a>
        {/each}
      </div>
    </div>

    <!-- Links -->
    <div class="mb-4 flex justify-center gap-4">
      <a href="https://github.com/HalloWelt42/macos-dev-organizer" target="_blank" rel="noopener noreferrer"
        class="flex items-center gap-1.5 rounded-lg border border-slate-700 px-4 py-2 text-xs text-slate-300 transition-colors hover:border-amber-600 hover:text-amber-400 no-underline">
        <i class="fa-brands fa-github"></i> GitHub
      </a>
      <a href="https://ko-fi.com/HalloWelt42" target="_blank" rel="noopener noreferrer"
        class="flex items-center gap-1.5 rounded-lg border border-slate-700 px-4 py-2 text-xs text-slate-300 transition-colors hover:border-amber-600 hover:text-amber-400 no-underline">
        <span>☕</span> Danke sagen
      </a>
    </div>

    <!-- Footer -->
    <p class="text-center text-[10px] text-slate-600">
      {year} HalloWelt42 -- MIT-Lizenz
    </p>
  </div>
</div>
