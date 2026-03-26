"""LLM-Integration über LM Studio (OpenAI-kompatible API) mit SSE-Streaming."""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import AsyncGenerator

import httpx

from devradar.config import LLMConfig

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Du bist ein Projektassistent für einen Entwickler. Du hilfst beim Finden und Verstehen lokaler Projekte.

Hier ist die Liste aller Projekte:
{projects_json}

Beantworte die Frage des Benutzers basierend auf diesen Projekten. Wenn du Projekte empfiehlst, nenne ihre IDs im Format [ID:123].
Antworte auf Deutsch. Sei konkret und hilfreich. Nutze Markdown für die Formatierung."""


async def stream_llm(
    question: str,
    projects: list[dict],
    llm_config: LLMConfig,
) -> AsyncGenerator[str, None]:
    """Streame die LLM-Antwort als SSE-Events.

    Yields SSE-formatierte Zeilen:
      data: {"type":"chunk","content":"...","stats":{"tokens":N,"elapsed":N,"tps":N}}
      data: {"type":"done","full":"...","project_ids":[...]}
    """
    projects_json = json.dumps(projects, ensure_ascii=False, indent=None)
    system = SYSTEM_PROMPT.format(projects_json=projects_json)

    full_content = ""
    tokens = 0
    start_time = time.monotonic()

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            f"{llm_config.base_url}/chat/completions",
            json={
                "model": llm_config.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": question},
                ],
                "temperature": 0.3,
                "max_tokens": -1,
                "stream": True,
            },
        ) as response:
            response.raise_for_status()
            buffer = ""

            async for raw_chunk in response.aiter_text():
                buffer += raw_chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        continue

                    try:
                        data = json.loads(data_str)
                        content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if content:
                            full_content += content
                            tokens += 1
                            elapsed = time.monotonic() - start_time
                            tps = round(tokens / elapsed, 1) if elapsed > 0 else 0

                            chunk_event = json.dumps({
                                "type": "chunk",
                                "content": content,
                                "full": full_content,
                                "stats": {
                                    "tokens": tokens,
                                    "elapsed": round(elapsed, 1),
                                    "tps": tps,
                                },
                            }, ensure_ascii=False)
                            yield f"data: {chunk_event}\n\n"
                    except (json.JSONDecodeError, IndexError, KeyError):
                        pass

    # Projekt-IDs extrahieren und aus Antwort entfernen
    ids = [int(m) for m in re.findall(r"\[ID:(\d+)\]", full_content)]
    clean_answer = re.sub(r"\s*\[ID:\d+\]", "", full_content)

    elapsed = time.monotonic() - start_time
    done_event = json.dumps({
        "type": "done",
        "full": clean_answer,
        "project_ids": ids,
        "stats": {
            "tokens": tokens,
            "elapsed": round(elapsed, 1),
            "tps": round(tokens / elapsed, 1) if elapsed > 0 else 0,
        },
    }, ensure_ascii=False)
    yield f"data: {done_event}\n\n"


async def ask_llm(
    question: str,
    projects: list[dict],
    llm_config: LLMConfig,
) -> tuple[str, list[int]]:
    """Nicht-streamende Variante (Fallback)."""
    projects_json = json.dumps(projects, ensure_ascii=False, indent=None)
    system = SYSTEM_PROMPT.format(projects_json=projects_json)

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{llm_config.base_url}/chat/completions",
            json={
                "model": llm_config.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": question},
                ],
                "temperature": 0.3,
                "max_tokens": -1,
            },
        )
        response.raise_for_status()
        data = response.json()

    answer = data["choices"][0]["message"]["content"]
    ids = [int(m) for m in re.findall(r"\[ID:(\d+)\]", answer)]
    clean_answer = re.sub(r"\s*\[ID:\d+\]", "", answer)
    return clean_answer, ids


async def is_available(llm_config: LLMConfig) -> bool:
    """Prüfe ob LM Studio erreichbar ist."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{llm_config.base_url}/models")
            return response.status_code == 200
    except Exception:
        return False
