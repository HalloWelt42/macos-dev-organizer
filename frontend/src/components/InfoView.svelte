<script lang="ts">
  import { getVersion } from "../lib/api";
  import { navigate } from "../lib/router";
  import { marked } from "marked";
  import DOMPurify from "dompurify";

  let { initialTab = "info" }: { initialTab?: string } = $props();

  let version = $state("");
  let showDonate = $state(false);
  let activeTab = $derived(initialTab);
  let prompts: { id: string; name: string; description: string; prompt: string }[] = $state([]);

  // Markdown-Inhalte
  let lizenzHtml = $state("");
  let datenschutzHtml = $state("");

  $effect(() => {
    getVersion().then(v => version = v).catch(() => {});
    loadLegal();
    fetch("/api/prompts").then(r => r.json()).then(d => prompts = d.prompts || []).catch(() => {});
  });

  async function loadLegal() {
    const year = new Date().getFullYear();
    try {
      let md = await (await fetch("/legal/de/lizenz.md")).text();
      md = md.replace("{{copyright}}", String(year));
      lizenzHtml = DOMPurify.sanitize(marked.parse(md) as string);
    } catch {}
    try {
      const md = await (await fetch("/legal/de/datenschutz.md")).text();
      datenschutzHtml = DOMPurify.sanitize(marked.parse(md) as string);
    } catch {}
  }

  const year = new Date().getFullYear();

  const tabs = [
    { id: "info", label: "Info", icon: "fa-circle-info" },
    { id: "prompts", label: "Prompts", icon: "fa-robot" },
    { id: "lizenz", label: "Lizenz", icon: "fa-scale-balanced" },
    { id: "datenschutz", label: "Datenschutz", icon: "fa-shield-halved" },
    { id: "bedanken", label: "Bedanken", icon: "fa-heart" },
  ];

  const donateConfig = {
    kofi: "https://ko-fi.com/HalloWelt42",
    crypto: [
      { name: "Bitcoin", symbol: "BTC", icon: "fa-brands fa-bitcoin", color: "#f7931a", address: "bc1qnd599khdkv3v3npmj9ufxzf6h4fzanny2acwqr", qr: "/images/btc-qr.svg" },
      { name: "Dogecoin", symbol: "DOGE", icon: "fa-solid fa-dog", color: "#c3a634", address: "DL7tuiYCqm3xQjMDXChdxeQxqUGMACn1ZV", qr: "/images/doge-qr.svg" },
      { name: "Ethereum", symbol: "ETH", icon: "fa-brands fa-ethereum", color: "#627eea", address: "0x8A28fc47bFFFA03C8f685fa0836E2dBe1CA14F27", qr: "/images/eth-qr.svg" },
    ],
  };

  let activeCrypto = $state("");

  async function copyAddress(addr: string, el: HTMLElement) {
    await navigator.clipboard.writeText(addr);
    const orig = el.textContent;
    el.textContent = "Kopiert!";
    el.style.color = "#22c55e";
    setTimeout(() => { el.textContent = orig; el.style.color = ""; }, 1500);
  }
</script>

<div class="mx-auto flex h-full max-w-2xl flex-col">
  <!-- Tabs -->
  <div class="mb-5 flex justify-center gap-1">
    {#each tabs as tab}
      <button
        onclick={() => navigate(`/info/${tab.id}`)}
        class="flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-medium transition-colors
               {activeTab === tab.id
                 ? 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200'
                 : 'text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'}"
      >
        <i class="fa-solid {tab.icon} {tab.id === 'bedanken' ? 'text-red-500' : ''}"></i>
        {tab.label}
      </button>
    {/each}
  </div>

  <!-- Tab-Inhalte (scrollbar) -->
  <div class="min-h-0 flex-1 overflow-y-auto">
  {#if activeTab === "info"}
    <div class="rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800">
      <h3 class="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">Lokale Projekte auf dem Mac organisieren</h3>
      <p class="mb-4 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
        DevRadar scannt konfigurierbare Verzeichnisse nach Softwareprojekten, indiziert sie und stellt ein
        Web-Dashboard bereit. READMEs werden mit Syntax-Highlighting gerendert, Bilder gecacht und YouTube-Links
        als Thumbnails angezeigt. Optional kann ein lokales LLM für Projektsuche und Beschreibungen angebunden werden.
      </p>

      <h4 class="mb-2 text-[10px] font-semibold uppercase tracking-wide text-slate-400">Erkannte Projekttypen</h4>
      <div class="mb-4 flex flex-wrap gap-2 text-xs">
        <span class="rounded bg-slate-100 px-2 py-1 dark:bg-slate-700">Git</span>
        <span class="rounded bg-slate-100 px-2 py-1 dark:bg-slate-700">Node.js</span>
        <span class="rounded bg-slate-100 px-2 py-1 dark:bg-slate-700">Python</span>
        <span class="rounded bg-slate-100 px-2 py-1 dark:bg-slate-700">Docker</span>
        <span class="rounded bg-slate-100 px-2 py-1 dark:bg-slate-700">Browser-Extensions</span>
      </div>

      <div class="flex justify-center gap-4">
        <a href="https://github.com/HalloWelt42/macos-dev-organizer" target="_blank" rel="noopener noreferrer"
          class="flex items-center gap-1.5 rounded-lg border border-slate-200 px-4 py-2 text-xs text-slate-600 transition-colors hover:border-amber-400 hover:text-amber-600 dark:border-slate-700 dark:text-slate-400 dark:hover:border-amber-600 dark:hover:text-amber-400 no-underline">
          <i class="fa-brands fa-github"></i> GitHub
        </a>
      </div>

      <p class="mt-4 text-center text-[10px] text-slate-400 dark:text-slate-600">
        {year} HalloWelt42
      </p>
    </div>

  {:else if activeTab === "prompts"}
    <div class="space-y-3">
      {#each prompts as p}
        <div class="rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
          <div class="flex items-center gap-2 border-b border-slate-100 px-4 py-2.5 dark:border-slate-700">
            <i class="fa-solid fa-robot text-amber-500"></i>
            <span class="text-sm font-semibold text-slate-700 dark:text-slate-200">{p.name}</span>
            <span class="text-xs text-slate-400">-- {p.description}</span>
          </div>
          <pre class="max-h-60 overflow-y-auto px-4 py-3 text-[11px] leading-relaxed text-slate-600 dark:text-slate-400 whitespace-pre-wrap">{p.prompt}</pre>
        </div>
      {/each}
      {#if prompts.length === 0}
        <p class="text-xs text-slate-400">Keine Prompts verfügbar. LLM nicht verbunden?</p>
      {/if}
    </div>

  {:else if activeTab === "lizenz"}
    <div class="rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800">
      {#if lizenzHtml}
        <div class="prose prose-sm max-w-none dark:prose-invert prose-headings:text-slate-700 dark:prose-headings:text-slate-200 prose-a:text-amber-600 dark:prose-a:text-amber-400">
          {@html lizenzHtml}
        </div>
      {:else}
        <p class="text-xs text-slate-400">Wird geladen...</p>
      {/if}
    </div>

  {:else if activeTab === "datenschutz"}
    <div class="rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800">
      {#if datenschutzHtml}
        <div class="prose prose-sm max-w-none dark:prose-invert prose-headings:text-slate-700 dark:prose-headings:text-slate-200 prose-a:text-amber-600 dark:prose-a:text-amber-400">
          {@html datenschutzHtml}
        </div>
      {:else}
        <p class="text-xs text-slate-400">Wird geladen...</p>
      {/if}
    </div>

  {:else if activeTab === "bedanken"}
    <div class="flex flex-col items-center gap-6 py-2">
      <div class="text-center">
        <h3 class="text-lg font-bold text-slate-700 dark:text-slate-100">DevRadar unterstützen</h3>
        <p class="mt-1 max-w-md text-xs leading-relaxed text-slate-500 dark:text-slate-400">
          Wenn dir das Projekt gefällt und es dir bei der täglichen Arbeit hilft,
          freue ich mich über eine kleine Unterstützung.
        </p>
      </div>

      <!-- Ko-fi -->
      <a href={donateConfig.kofi} target="_blank" rel="noopener noreferrer"
        class="flex items-center gap-2.5 rounded-full bg-amber-600 px-8 py-3 text-xs font-bold uppercase tracking-wider text-white shadow-md transition-all hover:brightness-110 hover:-translate-y-0.5 no-underline">
        <i class="fa-solid fa-mug-hot text-base"></i> Unterstütze auf Ko-fi
      </a>

      <!-- Divider -->
      <div class="flex w-full max-w-md items-center gap-3">
        <span class="h-px flex-1 bg-slate-200 dark:bg-slate-700"></span>
        <span class="text-[9px] font-bold uppercase tracking-widest text-slate-400">oder per Kryptowährung</span>
        <span class="h-px flex-1 bg-slate-200 dark:bg-slate-700"></span>
      </div>

      <!-- Crypto Cards (horizontal, RadioHub-Stil) -->
      <div class="flex gap-3">
        {#each donateConfig.crypto as coin}
          <button
            onclick={() => activeCrypto = activeCrypto === coin.symbol ? "" : coin.symbol}
            class="flex flex-col items-center gap-2 rounded-lg border px-7 py-4 transition-all hover:-translate-y-0.5
                   {activeCrypto === coin.symbol
                     ? 'border-amber-500 bg-slate-100 shadow-inner dark:border-amber-600 dark:bg-slate-800'
                     : 'border-slate-200 bg-white shadow-sm hover:border-slate-300 dark:border-slate-700 dark:bg-slate-800 dark:hover:border-slate-600'}"
          >
            <div class="flex h-12 w-12 items-center justify-center rounded-full bg-slate-50 text-2xl dark:bg-slate-900"
                 style="color: {coin.color}">
              <i class="{coin.icon}"></i>
            </div>
            <span class="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400
                         {activeCrypto === coin.symbol ? '!text-slate-700 dark:!text-slate-200' : ''}">{coin.symbol}</span>
            <span class="inline-block h-1.5 w-1.5 rounded-full transition-colors
                         {activeCrypto === coin.symbol ? 'bg-green-500 shadow-[0_0_4px_rgba(34,197,94,0.6)]' : 'bg-slate-300 dark:bg-slate-600'}"></span>
          </button>
        {/each}
      </div>

      <!-- Selected Crypto Detail -->
      {#each donateConfig.crypto as coin}
        {#if activeCrypto === coin.symbol}
          <div class="flex w-full max-w-md items-center gap-5 rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800">
            <div class="flex h-28 w-28 shrink-0 items-center justify-center rounded-md bg-white p-2">
              <img src={coin.qr} alt="{coin.symbol} QR-Code" class="h-full w-full object-contain" />
            </div>
            <div class="flex-1 min-w-0">
              <span class="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-200">{coin.name}</span>
              <code class="mt-2 block break-all rounded bg-slate-100 px-3 py-2 text-[10px] leading-relaxed text-slate-500 dark:bg-slate-900 dark:text-slate-400">{coin.address}</code>
              <button
                onclick={(e) => copyAddress(coin.address, e.currentTarget as HTMLElement)}
                class="mt-3 inline-flex items-center gap-1.5 rounded-full border border-slate-200 px-4 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-500 transition-colors hover:border-amber-500 hover:text-amber-600 dark:border-slate-600 dark:text-slate-400 dark:hover:border-amber-500 dark:hover:text-amber-400"
              >
                <i class="fa-solid fa-copy"></i> Adresse kopieren
              </button>
            </div>
          </div>
        {/if}
      {/each}

      <!-- Footer -->
      <p class="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500">
        <i class="fa-solid fa-heart text-red-400/50"></i> Vielen Dank für deine Unterstützung!
      </p>
    </div>
  {/if}
  </div>
</div>
