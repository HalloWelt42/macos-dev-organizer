<script lang="ts">
  let { value = $bindable(""), onSearch }: { value: string; onSearch: (q: string) => void } = $props();

  let inputEl: HTMLInputElement | undefined = $state();
  let debounceTimer: ReturnType<typeof setTimeout> | undefined;

  function handleInput(e: Event) {
    const target = e.target as HTMLInputElement;
    value = target.value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => onSearch(value), 300);
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") {
      value = "";
      onSearch("");
      inputEl?.blur();
    }
  }

  // Globaler Tastenkuerzel /
  $effect(() => {
    function onGlobalKey(e: KeyboardEvent) {
      if (e.key === "/" && document.activeElement?.tagName !== "INPUT" && document.activeElement?.tagName !== "TEXTAREA") {
        e.preventDefault();
        inputEl?.focus();
      }
    }
    window.addEventListener("keydown", onGlobalKey);
    return () => window.removeEventListener("keydown", onGlobalKey);
  });
</script>

<div class="relative">
  <i class="fa-solid fa-magnifying-glass absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"></i>
  <input
    bind:this={inputEl}
    type="text"
    {value}
    oninput={handleInput}
    onkeydown={handleKeydown}
    placeholder="Projekte suchen... (/ zum Fokussieren)"
    class="w-full rounded-lg border border-slate-200 bg-white py-3 pl-12 pr-4 text-lg shadow-sm outline-none transition-all
           placeholder:text-slate-400
           focus:border-amber-400 focus:ring-2 focus:ring-amber-200
           dark:border-slate-700 dark:bg-slate-800 dark:placeholder:text-slate-500
           dark:focus:border-amber-500 dark:focus:ring-amber-800"
  />
  {#if value}
    <button
      onclick={() => { value = ""; onSearch(""); }}
      class="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
      aria-label="Suche leeren"
    >
      <i class="fa-solid fa-xmark"></i>
    </button>
  {/if}
</div>
