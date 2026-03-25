<script lang="ts">
  import type { Project } from "../lib/types";
  import { getProject, openProject, enrichProject, saveDescription, translateReadme, deleteTranslation } from "../lib/api";
  import { navigate } from "../lib/router";
  import SvelteMarkdown, { Html } from "@humanspeak/svelte-markdown";
  import { marked } from "marked";
  import DOMPurify from "dompurify";

  // marked fuer GitHub Flavored Markdown mit HTML
  const markedRenderer = new marked.Renderer();

  // Headings mit GitHub-kompatiblen IDs (fuer Anker-Links)
  markedRenderer.heading = function({ tokens, depth }) {
    const text = this.parser.parseInline(tokens);
    const raw = tokens.map((t: any) => t.raw || t.text || "").join("");
    const id = raw.toLowerCase().replace(/[^\w\s-]/g, "").replace(/\s+/g, "-").replace(/-+/g, "-").trim();
    return `<h${depth} id="${id}">${text}</h${depth}>`;
  };

  // YouTube-ID aus URL extrahieren
  const YT_RE = /(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/;

  // Externe Links in neuem Tab, Anker-Links scrollen inline, YouTube-Links als Thumbnail
  markedRenderer.link = function({ href, title, tokens }) {
    const text = this.parser.parseInline(tokens);
    const titleAttr = title ? ` title="${title}"` : "";
    const isAnchor = href && href.startsWith("#");

    // YouTube-Links: Thumbnail + klickbare ID
    if (href) {
      const ytMatch = href.match(YT_RE);
      if (ytMatch) {
        const vid = ytMatch[1];
        return `<div class="yt-thumb-wrap my-3 inline-block rounded-lg overflow-hidden border border-slate-200 dark:border-slate-700 cursor-pointer shadow-sm hover:shadow-md transition-shadow" data-yt-id="${vid}" title="Klick kopiert Video-ID: ${vid}">
          <div class="relative">
            <img src="/api/yt-thumb/${vid}" alt="YouTube: ${vid}" class="block w-[280px]" />
            <div class="absolute top-2 right-2">
              <div class="flex items-center gap-1 rounded bg-red-600/90 px-2 py-0.5 text-white text-[10px] font-medium shadow">
                <i class="fa-brands fa-youtube"></i> YouTube
              </div>
            </div>
            <div class="absolute bottom-0 left-0 right-0 flex items-center gap-1 bg-black/70 px-2 py-1 text-[10px]">
              <a href="https://www.youtube.com/watch?v=${vid}" target="_blank" rel="noopener noreferrer" class="text-amber-400 hover:text-amber-300 no-underline" onclick="event.stopPropagation()">
                <i class="fa-solid fa-arrow-up-right-from-square mr-0.5"></i>Öffnen
              </a>
              <span class="text-slate-500 mx-0.5">|</span>
              <span class="yt-copy-link text-slate-300 hover:text-white cursor-pointer" data-copy="https://www.youtube.com/watch?v=${vid}">
                <i class="fa-solid fa-link mr-0.5"></i>Link
              </span>
              <span class="text-slate-500 mx-0.5">|</span>
              <span class="yt-copy-id text-slate-300 hover:text-white cursor-pointer" data-copy="${vid}">
                <i class="fa-solid fa-copy mr-0.5"></i>ID
              </span>
              <code class="font-mono text-amber-400/70 ml-auto">${vid}</code>
            </div>
          </div>
        </div>`;
      }
    }

    const isExternal = href && (href.startsWith("http://") || href.startsWith("https://"));
    if (isExternal) {
      return `<a href="${href}"${titleAttr} target="_blank" rel="noopener noreferrer">${text}</a>`;
    }
    if (isAnchor) {
      return `<a href="${href}"${titleAttr} class="readme-anchor">${text}</a>`;
    }
    return `<a href="${href}"${titleAttr}>${text}</a>`;
  };
  marked.setOptions({ gfm: true, breaks: false, renderer: markedRenderer });

  const renderers = { html: Html };
  import hljs from "highlight.js/lib/core";
  import javascript from "highlight.js/lib/languages/javascript";
  import typescript from "highlight.js/lib/languages/typescript";
  import python from "highlight.js/lib/languages/python";
  import bash from "highlight.js/lib/languages/bash";
  import json from "highlight.js/lib/languages/json";
  import xml from "highlight.js/lib/languages/xml";
  import css from "highlight.js/lib/languages/css";
  import yaml from "highlight.js/lib/languages/yaml";
  import dockerfile from "highlight.js/lib/languages/dockerfile";
  import php from "highlight.js/lib/languages/php";
  import ini from "highlight.js/lib/languages/ini";

  hljs.registerLanguage("javascript", javascript);
  hljs.registerLanguage("js", javascript);
  hljs.registerLanguage("typescript", typescript);
  hljs.registerLanguage("ts", typescript);
  hljs.registerLanguage("python", python);
  hljs.registerLanguage("bash", bash);
  hljs.registerLanguage("sh", bash);
  hljs.registerLanguage("json", json);
  hljs.registerLanguage("html", xml);
  hljs.registerLanguage("xml", xml);
  hljs.registerLanguage("css", css);
  hljs.registerLanguage("yaml", yaml);
  hljs.registerLanguage("yml", yaml);
  hljs.registerLanguage("dockerfile", dockerfile);
  hljs.registerLanguage("php", php);
  hljs.registerLanguage("toml", ini);
  hljs.registerLanguage("ini", ini);
  // Plaintext-Aliase -- kein Highlighting, keine Console-Warnungen
  hljs.registerLanguage("txt", () => ({ name: "Text", contains: [] }));
  hljs.registerLanguage("text", () => ({ name: "Text", contains: [] }));
  hljs.registerLanguage("plaintext", () => ({ name: "Text", contains: [] }));

  let { projectId, allProjectIds = [] }: { projectId: number; allProjectIds?: number[] } = $props();

  let project: Project | null = $state(null);
  let loading = $state(true);
  let error = $state("");

  // KI-Anreicherung
  let enriching = $state(false);
  let enrichedText = $state("");
  let enrichStats = $state({ tokens: 0, elapsed: 0, tps: 0 });
  let enrichError = $state("");

  // README als HTML rendern (marked statt SvelteMarkdown für volle HTML-Unterstützung)
  let readmeHtml = $derived(() => {
    const src = readmeDisplaySource();
    if (!src) return "";
    const raw = marked.parse(src) as string;
    return DOMPurify.sanitize(raw, {
      ADD_TAGS: ["details", "summary"],
      ADD_ATTR: ["align", "target", "rel"],
      FORBID_TAGS: ["iframe", "object", "embed", "script", "style", "link", "form", "input", "textarea", "button", "select"],
      FORBID_ATTR: ["onerror", "onload", "onclick", "onmouseover", "onfocus", "onblur", "style"],
    });
  });

  // README-Suche
  let readmeSearch = $state("");
  let readmeSearchCount = $state(0);

  // Textgröße (persistiert in localStorage, Prozent-Stufen)
  // Lightbox fuer Bilder
  let lightboxOpen = $state(false);
  let lightboxImages: string[] = $state([]);
  let lightboxIndex = $state(0);

  function openLightbox(src: string) {
    const imgs = Array.from(document.querySelectorAll(".readme-body img"))
      .map(img => (img as HTMLImageElement).src)
      .filter(s => s);
    if (imgs.length === 0) return;
    lightboxImages = imgs;
    lightboxIndex = Math.max(0, imgs.indexOf(src));
    lightboxOpen = true;
  }

  function lightboxPrev() {
    lightboxIndex = (lightboxIndex - 1 + lightboxImages.length) % lightboxImages.length;
  }
  function lightboxNext() {
    lightboxIndex = (lightboxIndex + 1) % lightboxImages.length;
  }
  function lightboxKeydown(e: KeyboardEvent) {
    if (!lightboxOpen) return;
    if (e.key === "Escape") lightboxOpen = false;
    else if (e.key === "ArrowLeft") lightboxPrev();
    else if (e.key === "ArrowRight") lightboxNext();
  }

  const ZOOM_STEPS = [75, 85, 100, 115, 130, 150];
  let zoomIndex = $state(
    typeof localStorage !== "undefined"
      ? parseInt(localStorage.getItem("devradar-zoom") || "2") || 2
      : 2
  );
  let zoomPercent = $derived(ZOOM_STEPS[zoomIndex] || 100);

  function zoomIn() {
    if (zoomIndex < ZOOM_STEPS.length - 1) {
      zoomIndex++;
      if (typeof localStorage !== "undefined") localStorage.setItem("devradar-zoom", String(zoomIndex));
    }
  }
  function zoomOut() {
    if (zoomIndex > 0) {
      zoomIndex--;
      if (typeof localStorage !== "undefined") localStorage.setItem("devradar-zoom", String(zoomIndex));
    }
  }

  // README mit Suchmarkierung
  let readmeDisplaySource = $derived(() => {
    let source = "";
    if (showTranslation && (translatedText || project?.readme_translated)) {
      source = translatedText || project?.readme_translated || "";
    } else {
      source = readmeWithImages();
    }
    return source;
  });

  // Syntax-Highlighting + Copy-Buttons nach Markdown-Rendering
  $effect(() => {
    const _ = readmeDisplaySource();
    setTimeout(() => {
      document.querySelectorAll(".readme-body pre code").forEach((block) => {
        if (!(block as HTMLElement).dataset.highlighted) {
          hljs.highlightElement(block as HTMLElement);
        }
      });
      // Copy-Buttons fuer Code-Bloecke -- direkt am <pre> Element
      document.querySelectorAll(".readme-body pre").forEach((pre) => {
        if (pre.querySelector(".copy-btn")) return;
        (pre as HTMLElement).style.position = "relative";

        const btn = document.createElement("button");
        btn.className = "copy-btn";
        btn.innerHTML = '<i class="fa-solid fa-copy"></i>';
        btn.title = "Kopieren";
        btn.style.cssText = "position:absolute;top:6px;right:6px;padding:4px 8px;border-radius:4px;background:rgb(51 65 85);color:rgb(148 163 184);font-size:11px;border:none;cursor:pointer;opacity:0;transition:opacity 0.2s;z-index:1;";

        pre.appendChild(btn);
        pre.addEventListener("mouseenter", () => btn.style.opacity = "1");
        pre.addEventListener("mouseleave", () => btn.style.opacity = "0");

        btn.addEventListener("click", async (e) => {
          e.stopPropagation();
          const code = pre.querySelector("code");
          const text = code?.textContent || pre.textContent || "";
          await navigator.clipboard.writeText(text);
          btn.innerHTML = '<i class="fa-solid fa-check"></i>';
          btn.style.color = "#22c55e";
          setTimeout(() => { btn.innerHTML = '<i class="fa-solid fa-copy"></i>'; btn.style.color = "rgb(148 163 184)"; }, 1500);
        });
      });

      // Copy bei Hover fuer Inline-Code
      document.querySelectorAll(".readme-body code:not(pre code)").forEach((code) => {
        if ((code as HTMLElement).dataset.copyReady) return;
        (code as HTMLElement).dataset.copyReady = "1";
        (code as HTMLElement).style.cursor = "pointer";
        code.addEventListener("click", async (e) => {
          e.stopPropagation();
          const text = code.textContent || "";
          await navigator.clipboard.writeText(text);
          const orig = (code as HTMLElement).style.borderColor;
          (code as HTMLElement).style.borderColor = "#22c55e";
          setTimeout(() => { (code as HTMLElement).style.borderColor = orig; }, 1000);
        });
      });

      // Anker-Links: Inline-Scroll im README-Container
      document.querySelectorAll(".readme-body a.readme-anchor").forEach((a) => {
        if ((a as HTMLElement).dataset.anchorReady) return;
        (a as HTMLElement).dataset.anchorReady = "1";
        a.addEventListener("click", (e) => {
          e.preventDefault();
          const href = a.getAttribute("href");
          if (!href) return;
          const target = document.querySelector(`.readme-body ${href}`);
          if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
        });
      });

      // YouTube-Buttons: Link kopieren, ID kopieren
      document.querySelectorAll(".readme-body .yt-copy-link, .readme-body .yt-copy-id").forEach((btn) => {
        if ((btn as HTMLElement).dataset.copyReady) return;
        (btn as HTMLElement).dataset.copyReady = "1";
        btn.addEventListener("click", async (e) => {
          e.preventDefault();
          e.stopPropagation();
          const text = (btn as HTMLElement).dataset.copy || "";
          if (!text) return;
          await navigator.clipboard.writeText(text);
          const orig = btn.innerHTML;
          btn.innerHTML = '<i class="fa-solid fa-check mr-0.5"></i>Kopiert';
          (btn as HTMLElement).style.color = "#22c55e";
          setTimeout(() => { btn.innerHTML = orig; (btn as HTMLElement).style.color = ""; }, 1500);
        });
      });

      // Bilder: Klickbar fuer Lightbox (nur Bilder > 80px)
      document.querySelectorAll(".readme-body img").forEach((img) => {
        const el = img as HTMLImageElement;
        if (el.dataset.lightboxReady) return;
        el.dataset.lightboxReady = "1";
        const check = () => {
          if (el.naturalWidth > 80 && el.naturalHeight > 80) {
            el.style.cursor = "zoom-in";
            el.addEventListener("click", (e) => {
              e.preventDefault();
              e.stopPropagation();
              openLightbox(el.src);
            });
          }
        };
        if (el.complete) check();
        else el.addEventListener("load", check);
      });
    }, 200);
  });

  // Treffer im gerenderten README hervorheben
  $effect(() => {
    // Explizit readmeSearch tracken
    const search = readmeSearch;
    const _ = readmeDisplaySource();

    const timer = setTimeout(() => {
      const container = document.querySelector(".readme-body");
      if (!container) return;

      // Alte Markierungen entfernen
      container.querySelectorAll("mark.readme-search-hit").forEach((m) => {
        const parent = m.parentNode;
        if (parent) {
          parent.replaceChild(document.createTextNode(m.textContent || ""), m);
          parent.normalize();
        }
      });

      if (search.length < 2) { readmeSearchCount = 0; return; }

      const queryEscaped = search.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      let count = 0;

      function walkTextNodes(node: Node) {
        if (node.nodeType === Node.TEXT_NODE) {
          const text = node.textContent || "";
          const testRe = new RegExp(queryEscaped, "i");
          if (!testRe.test(text)) return;
          const re = new RegExp(`(${queryEscaped})`, "gi");
          const frag = document.createDocumentFragment();
          let lastIdx = 0;
          let match;
          while ((match = re.exec(text)) !== null) {
            if (match.index > lastIdx) frag.appendChild(document.createTextNode(text.slice(lastIdx, match.index)));
            const mark = document.createElement("mark");
            mark.className = "readme-search-hit rounded bg-amber-300 px-0.5 dark:bg-amber-600 dark:text-white";
            mark.textContent = match[1];
            frag.appendChild(mark);
            count++;
            lastIdx = re.lastIndex;
          }
          if (lastIdx < text.length) frag.appendChild(document.createTextNode(text.slice(lastIdx)));
          node.parentNode?.replaceChild(frag, node);
        } else if (node.nodeType === Node.ELEMENT_NODE && !["SCRIPT", "STYLE", "MARK"].includes(node.nodeName)) {
          Array.from(node.childNodes).forEach(walkTextNodes);
        }
      }

      walkTextNodes(container);
      readmeSearchCount = count;

      // Zum ersten Treffer scrollen
      const first = container.querySelector("mark.readme-search-hit");
      if (first) first.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 250);

    return () => clearTimeout(timer);
  });

  // Übersetzung
  let translating = $state(false);
  let translatedText = $state("");
  let translateStats = $state({ tokens: 0, elapsed: 0, tps: 0 });
  let showTranslation = $state(false);

  let readmeWithImages = $derived(() => {
    if (!project?.readme_content) return "";
    let content = project.readme_content;
    // Relative Bild-Pfade durch API-URL ersetzen
    content = content.replace(
      /!\[([^\]]*)\]\((?!https?:\/\/)([^)]+)\)/g,
      (_, alt, path) => {
        const encoded = encodeURIComponent(project!.path);
        const filePath = encodeURIComponent(path);
        return `![${alt}](/api/file?project_path=${encoded}&file_path=${filePath})`;
      }
    );
    // HTML <img> Tags mit relativen src ebenfalls umschreiben
    content = content.replace(
      /<img([^>]*?)src=["'](?!https?:\/\/)([^"']+)["']/g,
      (match, before, src) => {
        const encoded = encodeURIComponent(project!.path);
        const filePath = encodeURIComponent(src);
        return `<img${before}src="/api/file?project_path=${encoded}&file_path=${filePath}"`;
      }
    );
    return content;
  });

  $effect(() => {
    loadProject();
  });

  // Auf projectId-Änderungen reagieren (Pfeiltasten)
  $effect(() => {
    if (projectId) {
      enrichedText = "";
      enrichError = "";
      translatedText = "";
      showTranslation = false;
      loadProject();
    }
  });

  function navigateRelative(offset: number) {
    const idx = allProjectIds.indexOf(projectId);
    if (idx < 0) return;
    const newIdx = idx + offset;
    if (newIdx >= 0 && newIdx < allProjectIds.length) {
      navigate(`/project/${allProjectIds[newIdx]}`);
    }
  }

  $effect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      // Lightbox hat Vorrang
      if (lightboxOpen) {
        if (e.key === "Escape") { e.preventDefault(); lightboxOpen = false; }
        else if (e.key === "ArrowLeft") { e.preventDefault(); lightboxPrev(); }
        else if (e.key === "ArrowRight") { e.preventDefault(); lightboxNext(); }
        return;
      }
      if (e.key === "ArrowLeft") { e.preventDefault(); navigateRelative(-1); }
      if (e.key === "ArrowRight") { e.preventDefault(); navigateRelative(1); }
      if (e.key === "Escape") { navigate("/"); }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  async function loadProject() {
    loading = true;
    error = "";
    try {
      project = await getProject(projectId);
      // Gespeicherte Übersetzung laden
      if (project?.readme_translated) {
        translatedText = project.readme_translated;
      }
    } catch (e) {
      error = e instanceof Error ? e.message : "Projekt nicht gefunden";
    } finally {
      loading = false;
    }
  }

  function handleTranslate() {
    if (!project) return;
    translating = true;
    translatedText = "";
    translateStats = { tokens: 0, elapsed: 0, tps: 0 };

    translateReadme(
      project.id,
      (data) => { translatedText = data.full; translateStats = data.stats; showTranslation = true; },
      (data) => { translatedText = data.full; translating = false; showTranslation = true; },
      (err) => { console.error("Übersetzung fehlgeschlagen:", err); translating = false; }
    );
  }

  async function handleDeleteTranslation() {
    if (!project) return;
    await deleteTranslation(project.id);
    translatedText = "";
    showTranslation = false;
    if (project) project.readme_translated = "";
  }

  async function handleOpen(app: string) {
    if (!project) return;
    try {
      await openProject(project.path, app);
    } catch (e) {
      console.error("Fehler beim Öffnen:", e);
    }
  }

  function handleEnrich() {
    if (!project) return;
    enriching = true;
    enrichedText = "";
    enrichError = "";
    enrichStats = { tokens: 0, elapsed: 0, tps: 0 };

    enrichProject(
      project.id,
      (data) => { enrichedText = data.full; enrichStats = data.stats; },
      async (data) => {
        enrichedText = data.full;
        enriching = false;
        if (project && enrichedText) {
          try {
            await saveDescription(project.id, enrichedText);
            project.description = enrichedText;
          } catch (e) { console.error("Speichern fehlgeschlagen:", e); }
        }
      },
      (err) => { enrichError = err.message; enriching = false; }
    );
  }

  const typeLabels: Record<string, string> = {
    git: "Git Repository",
    node: "Node.js Projekt",
    extension: "Browser-Extension",
    docker: "Docker-Projekt",
    python: "Python-Projekt",
  };
</script>

<div class="flex h-full flex-col overflow-hidden">
<div class="mb-2 shrink-0 flex items-center justify-between">
  <button
    onclick={() => navigate("/")}
    class="flex items-center gap-2 text-sm text-slate-500 transition-colors hover:text-amber-600"
  >
    <i class="fa-solid fa-arrow-left"></i>
    Zurück
  </button>
  <div class="flex items-center gap-2 text-xs text-slate-400">
    <button onclick={() => navigateRelative(-1)} class="rounded p-1 hover:bg-slate-200 hover:text-slate-600 dark:hover:bg-slate-700 dark:hover:text-slate-300" title="Vorheriges Projekt">
      <i class="fa-solid fa-chevron-left"></i>
    </button>
    <span class="hidden sm:inline">Pfeiltasten</span>
    <button onclick={() => navigateRelative(1)} class="rounded p-1 hover:bg-slate-200 hover:text-slate-600 dark:hover:bg-slate-700 dark:hover:text-slate-300" title="Nächstes Projekt">
      <i class="fa-solid fa-chevron-right"></i>
    </button>
  </div>
</div>

{#if loading}
  <div class="flex items-center justify-center py-20">
    <i class="fa-solid fa-spinner animate-spin text-2xl text-amber-500"></i>
  </div>
{:else if error}
  <div class="py-20 text-center text-red-500">
    <i class="fa-solid fa-triangle-exclamation mb-4 text-4xl"></i>
    <p>{error}</p>
  </div>
{:else if project}
  <!-- 2-Spalten: README links (62%), Details rechts (38%) -- goldener Schnitt -->
  <div class="flex flex-1 gap-4 lg:flex-row flex-col min-h-0">
    <!-- Linke Spalte: README -->
    <div class="lg:w-[62%] min-w-0 min-h-0 flex flex-col">
      {#if project.readme_content}
        <div class="flex min-h-0 flex-1 flex-col rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
          <!-- README Toolbar -->
          <div class="flex items-center gap-2 border-b border-slate-200 px-3 py-1.5 dark:border-slate-700">
            <h3 class="shrink-0 text-sm font-medium text-slate-500">README</h3>

            <!-- Suche -->
            <div class="relative flex-1 max-w-xs">
              <i class="fa-solid fa-magnifying-glass absolute left-2 top-1/2 -translate-y-1/2 text-[10px] text-slate-400"></i>
              <input
                type="text"
                bind:value={readmeSearch}
                placeholder="Suchen..."
                class="w-full rounded-md border border-slate-200 bg-slate-50 py-1 pl-6 pr-14 text-xs outline-none
                       focus:border-amber-400 dark:border-slate-600 dark:bg-slate-900"
              />
              {#if readmeSearch}
                <span class="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                  {#if readmeSearch.length >= 2}
                    <span class="text-[10px] text-slate-400">{readmeSearchCount}</span>
                  {/if}
                  <button onclick={() => { readmeSearch = ""; }} class="text-[10px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-300" aria-label="Suche leeren">
                    <i class="fa-solid fa-xmark"></i>
                  </button>
                </span>
              {/if}
            </div>

            <!-- Zoom -->
            <div class="flex items-center gap-0.5 rounded-md border border-slate-200 dark:border-slate-600">
              <button onclick={zoomOut} disabled={zoomIndex <= 0}
                class="rounded-l-md px-1.5 py-1 text-xs text-slate-400 hover:text-slate-600 disabled:opacity-30 dark:hover:text-slate-300"
                title="Verkleinern">
                <i class="fa-solid fa-minus text-[10px]"></i>
              </button>
              <span class="px-1 text-[10px] text-slate-500 font-mono">{zoomPercent}%</span>
              <button onclick={zoomIn} disabled={zoomIndex >= ZOOM_STEPS.length - 1}
                class="rounded-r-md px-1.5 py-1 text-xs text-slate-400 hover:text-slate-600 disabled:opacity-30 dark:hover:text-slate-300"
                title="Vergrößern">
                <i class="fa-solid fa-plus text-[10px]"></i>
              </button>
            </div>

            <!-- Sprache / Übersetzen -->
            {#if translatedText || project.readme_translated}
              <div class="flex rounded-md border border-slate-200 text-xs dark:border-slate-600">
                <button
                  onclick={() => showTranslation = false}
                  class="rounded-l-md px-2 py-1 transition-colors {!showTranslation ? 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300' : 'text-slate-500 hover:text-slate-700'}"
                >EN</button>
                <button
                  onclick={() => showTranslation = true}
                  class="rounded-r-md px-2 py-1 transition-colors {showTranslation ? 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300' : 'text-slate-500 hover:text-slate-700'}"
                >DE</button>
              </div>
              <button onclick={handleDeleteTranslation} class="text-xs text-slate-400 hover:text-red-500" title="Übersetzung löschen">
                <i class="fa-solid fa-trash-can"></i>
              </button>
            {:else}
              <button onclick={handleTranslate} disabled={translating}
                class="flex items-center gap-1 rounded-md border border-amber-300 px-2 py-1 text-xs text-amber-700 transition-colors
                       hover:bg-amber-50 disabled:opacity-50 dark:border-amber-700 dark:text-amber-400">
                {#if translating}
                  <i class="fa-solid fa-spinner animate-spin"></i>
                  <span class="font-mono">{translateStats.tps} t/s</span>
                {:else}
                  <i class="fa-solid fa-language"></i>Übersetzen
                {/if}
              </button>
            {/if}
          </div>
          <!-- README Inhalt mit Innerscroll -->
          <div class="readme-body flex-1 overflow-y-auto p-4">
            <div class="prose prose-sm max-w-prose dark:prose-invert
                        prose-headings:text-slate-800 dark:prose-headings:text-slate-200
                        prose-a:text-amber-600 dark:prose-a:text-amber-400
                        prose-code:rounded prose-code:bg-slate-200 prose-code:px-1 dark:prose-code:bg-slate-800
                        prose-pre:bg-slate-200 dark:prose-pre:bg-slate-800
                        prose-img:max-w-full prose-img:rounded-lg"
                 style="font-size: {zoomPercent}%">
              {@html readmeHtml()}
            </div>
          </div>
        </div>
      {/if}
    </div>

    <!-- Rechte Spalte: Projektinfos, volle Hoehe nutzen -->
    <div class="lg:w-[38%] flex flex-col gap-3 min-h-0 overflow-hidden">
      <!-- Header -->
      <div class="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <h1 class="text-xl font-bold text-slate-900 dark:text-slate-100">{project.name}</h1>
        <p class="mt-0.5 text-sm text-slate-500">{typeLabels[project.project_type] || project.project_type}</p>

        <div class="mt-3 flex flex-wrap gap-2">
          <button onclick={() => handleOpen("finder")} class="rounded-md bg-slate-100 px-3 py-1.5 text-xs transition-colors hover:bg-amber-100 hover:text-amber-700 dark:bg-slate-700 dark:hover:bg-amber-900">
            <i class="fa-solid fa-folder-open mr-1"></i>Finder
          </button>
          <button onclick={() => handleOpen("ide")} class="rounded-md bg-slate-100 px-3 py-1.5 text-xs transition-colors hover:bg-blue-100 hover:text-blue-700 dark:bg-slate-700 dark:hover:bg-blue-900">
            <i class="fa-solid fa-code mr-1"></i>IDE
          </button>
          <button onclick={() => handleOpen("terminal")} class="rounded-md bg-slate-100 px-3 py-1.5 text-xs transition-colors hover:bg-green-100 hover:text-green-700 dark:bg-slate-700 dark:hover:bg-green-900">
            <i class="fa-solid fa-terminal mr-1"></i>Terminal
          </button>
        </div>
      </div>

      <!-- Beschreibung -->
      <div class="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        {#if project.description && !enrichedText}
          <div class="prose prose-sm max-w-none dark:prose-invert prose-a:text-amber-600 dark:prose-a:text-amber-400">
            <SvelteMarkdown source={project.description} {renderers} />
          </div>
        {/if}
        {#if enrichedText}
          <div class="rounded-md border border-amber-200 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-950/30">
            <div class="mb-1 flex items-center gap-2 text-xs text-amber-600 dark:text-amber-400">
              <i class="fa-solid fa-robot"></i>
              <span class="font-mono">{enrichStats.tps} t/s</span>
              {#if !enriching}
                <span class="text-green-500"><i class="fa-solid fa-check"></i></span>
                <button aria-label="Beschreibung löschen" onclick={async () => { if (project) { await saveDescription(project.id, ""); project.description = ""; enrichedText = ""; } }}
                  class="ml-auto text-slate-400 hover:text-red-500"><i class="fa-solid fa-trash-can"></i></button>
              {/if}
            </div>
            <div class="prose prose-sm max-w-none dark:prose-invert">
              <SvelteMarkdown source={enrichedText} {renderers} />
            </div>
          </div>
        {/if}
        {#if enrichError}<p class="mt-1 text-xs text-red-500">{enrichError}</p>{/if}
        <button onclick={handleEnrich} disabled={enriching}
          class="mt-2 flex items-center gap-1.5 rounded-md border border-amber-300 px-2.5 py-1 text-xs text-amber-700
                 hover:bg-amber-50 disabled:opacity-50 dark:border-amber-700 dark:text-amber-400">
          {#if enriching}<i class="fa-solid fa-spinner animate-spin"></i>Generiere...
          {:else}<i class="fa-solid fa-wand-magic-sparkles"></i>KI-Beschreibung{/if}
        </button>
      </div>

      <!-- Tags -->
      <div class="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
        <div class="flex flex-wrap gap-1">
          {#each project.tags as tag}
            <span class="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-300">{tag}</span>
          {/each}
        </div>
      </div>

      <!-- Metadaten -- füllt Resthöhe, Code scrollt intern -->
      <div class="min-h-0 flex-1 flex flex-col rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800 overflow-hidden">
        <div class="shrink-0 space-y-1.5 p-4 pb-2 text-sm">
          <div class="flex gap-2">
            <span class="w-24 shrink-0 text-xs text-slate-500">Pfad</span>
            <code class="truncate rounded bg-slate-100 px-1.5 py-0.5 text-xs dark:bg-slate-900">{project.path}</code>
          </div>
          <div class="flex gap-2">
            <span class="w-24 shrink-0 text-xs text-slate-500">Erstellt</span>
            <span class="text-xs">{project.detected_at ? new Date(project.detected_at).toLocaleDateString("de-DE") : "-"}</span>
          </div>
          <div class="flex gap-2">
            <span class="w-24 shrink-0 text-xs text-slate-500">Bearbeitet</span>
            <span class="text-xs">{project.last_modified ? new Date(project.last_modified).toLocaleDateString("de-DE") : "-"}</span>
          </div>
        </div>
        {#if project.metadata && Object.keys(project.metadata).length > 0}
          <div class="min-h-0 flex-1 flex flex-col px-4 pb-4">
            <h4 class="mb-1 shrink-0 text-xs text-slate-500">Weitere Details</h4>
            <pre class="min-h-0 flex-1 overflow-y-auto rounded-md bg-slate-50 p-2 text-[10px] text-slate-500 dark:bg-slate-900">{JSON.stringify(project.metadata, null, 2)}</pre>
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}
</div>

<!-- Lightbox -->
{#if lightboxOpen}
<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div
  class="fixed inset-0 z-50 flex items-center justify-center bg-black/90"
  onclick={() => lightboxOpen = false}
  onkeydown={lightboxKeydown}
  role="dialog"
  aria-label="Bildvorschau"
>
  <!-- Zaehler -->
  <div class="absolute top-4 left-1/2 -translate-x-1/2 text-sm text-white/60">
    {lightboxIndex + 1} / {lightboxImages.length}
  </div>

  <!-- Schliessen -->
  <button onclick={() => lightboxOpen = false}
    class="absolute top-4 right-4 text-2xl text-white/70 hover:text-white" aria-label="Schliessen">
    <i class="fa-solid fa-xmark"></i>
  </button>

  <!-- Vorheriges -->
  {#if lightboxImages.length > 1}
    <button onclick={(e: MouseEvent) => { e.stopPropagation(); lightboxPrev(); }}
      class="absolute left-4 top-1/2 -translate-y-1/2 rounded-full bg-white/10 p-3 text-xl text-white/70 hover:bg-white/20 hover:text-white"
      aria-label="Vorheriges Bild">
      <i class="fa-solid fa-chevron-left"></i>
    </button>
    <button onclick={(e: MouseEvent) => { e.stopPropagation(); lightboxNext(); }}
      class="absolute right-4 top-1/2 -translate-y-1/2 rounded-full bg-white/10 p-3 text-xl text-white/70 hover:bg-white/20 hover:text-white"
      aria-label="Nächstes Bild">
      <i class="fa-solid fa-chevron-right"></i>
    </button>
  {/if}

  <!-- Bild -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
  <img
    src={lightboxImages[lightboxIndex]}
    alt="Vorschau"
    class="max-h-[90vh] max-w-[90vw] object-contain"
    onclick={(e: MouseEvent) => e.stopPropagation()}
  />
</div>
{/if}
