from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .model import FIGLET_STYLE_MAP


SYSTEM_PROMPT = (
    "You are helping generate Hermes skin content. "
    "Return only valid JSON. Do not include markdown fences or commentary."
)


@dataclass(frozen=True)
class AIBackend:
    key: str
    label: str


BACKENDS = {
    "hermes": AIBackend("hermes", "Hermes CLI"),
    "openai": AIBackend("openai", "OpenAI API"),
    "openrouter": AIBackend("openrouter", "OpenRouter API"),
    "google": AIBackend("google", "Google API"),
}


def discover_backends() -> list[str]:
    available: list[str] = []
    if shutil.which("hermes"):
        available.append("hermes")
    if os.getenv("OPENAI_API_KEY"):
        available.append("openai")
    if os.getenv("OPENROUTER_API_KEY"):
        available.append("openrouter")
    if os.getenv("GOOGLE_API_KEY"):
        available.append("google")
    return available


def backend_labels(backends: list[str] | None = None) -> list[str]:
    keys = backends or discover_backends()
    return [BACKENDS[key].label for key in keys if key in BACKENDS]


def backend_options(backends: list[str] | None = None) -> list[tuple[str, str]]:
    keys = backends or discover_backends()
    return [(BACKENDS[key].label, key) for key in keys if key in BACKENDS]


def _extract_json_object(text: str) -> dict:
    raw = str(text or "").strip()
    if not raw:
        raise ValueError("AI backend returned empty output")

    start = raw.find("{")
    if start == -1:
        raise ValueError("AI backend did not return JSON")

    depth = 0
    in_string = False
    escaped = False
    end = -1

    for index, char in enumerate(raw[start:], start=start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                break

    if end == -1:
        raise ValueError("AI backend returned incomplete JSON")

    try:
        parsed = json.loads(raw[start:end])
    except json.JSONDecodeError as exc:
        raise ValueError(f"AI backend returned invalid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("AI backend returned a non-object payload")
    return parsed


def _post_json(url: str, headers: dict[str, str], payload: dict) -> dict:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ValueError(f"API request failed: {body}") from exc
    except URLError as exc:
        raise ValueError(f"API request failed: {exc}") from exc


def _run_hermes(prompt: str) -> str:
    result = subprocess.run(
        ["hermes", "chat", "-Q", "-q", prompt, "--source", "tool"],
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or result.stdout.strip() or "Hermes CLI request failed")
    return result.stdout.strip()


def _run_openai(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")
    model = os.getenv("SKINWALKER_OPENAI_MODEL", "gpt-5-mini")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }
    response = _post_json(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        payload=payload,
    )
    return str(response["choices"][0]["message"]["content"])


def _run_openrouter(prompt: str) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not set")
    model = os.getenv("SKINWALKER_OPENROUTER_MODEL", "openai/gpt-5-mini")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }
    response = _post_json(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        payload=payload,
    )
    return str(response["choices"][0]["message"]["content"])


def _run_google(prompt: str) -> str:
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is not set")
    model = os.getenv("SKINWALKER_GOOGLE_MODEL", "gemini-2.5-flash")
    response = _post_json(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
        headers={},
        payload={
            "contents": [
                {
                    "parts": [
                        {"text": SYSTEM_PROMPT},
                        {"text": prompt},
                    ]
                }
            ]
        },
    )
    parts = response.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    return "\n".join(str(part.get("text", "")) for part in parts if part.get("text"))


def generate_json(prompt: str, *, backend: str = "hermes") -> dict:
    selected = str(backend or "hermes").strip().lower()
    if selected == "hermes":
        output = _run_hermes(prompt)
    elif selected == "openai":
        output = _run_openai(prompt)
    elif selected == "openrouter":
        output = _run_openrouter(prompt)
    elif selected == "google":
        output = _run_google(prompt)
    else:
        raise ValueError(f"Unknown AI backend: {backend}")
    return _extract_json_object(output)


def _skin_context(skin: dict) -> str:
    branding = skin.get("branding", {})
    spinner = skin.get("spinner", {})
    return (
        f"Skin name: {skin.get('name', '')}\n"
        f"Description: {skin.get('description', '')}\n"
        f"Agent name: {branding.get('agent_name', '')}\n"
        f"Welcome: {branding.get('welcome', '')}\n"
        f"Prompt symbol: {branding.get('prompt_symbol', '')}\n"
        f"Waiting faces: {spinner.get('waiting_faces', [])}\n"
        f"Thinking faces: {spinner.get('thinking_faces', [])}\n"
        f"Thinking verbs: {spinner.get('thinking_verbs', [])}\n"
    )


def _direction_context(direction: str = "") -> str:
    text = str(direction or "").strip()
    return f"Creative direction: {text}\n" if text else ""


def _normalize_branding_payload(payload: dict) -> dict[str, str]:
    branding = payload.get("branding", payload)
    if not isinstance(branding, dict):
        raise ValueError("AI branding payload was not an object")
    return {
        key: str(branding.get(key, "")).strip()
        for key in ("agent_name", "welcome", "goodbye", "response_label", "prompt_symbol", "help_header")
        if str(branding.get(key, "")).strip()
    }


def _normalize_spinner_payload(payload: dict) -> dict[str, list]:
    spinner = payload.get("spinner", payload)
    if not isinstance(spinner, dict):
        raise ValueError("AI spinner payload was not an object")

    waiting = [str(item).strip() for item in spinner.get("waiting_faces", []) if str(item).strip()]
    thinking = [str(item).strip() for item in spinner.get("thinking_faces", []) if str(item).strip()]
    verbs = [str(item).strip() for item in spinner.get("thinking_verbs", []) if str(item).strip()]
    wings = []
    for pair in spinner.get("wings", []):
        if isinstance(pair, (list, tuple)) and len(pair) == 2:
            left = str(pair[0]).strip()
            right = str(pair[1]).strip()
            if left or right:
                wings.append([left, right])

    return {
        "waiting_faces": waiting,
        "thinking_faces": thinking,
        "thinking_verbs": verbs,
        "wings": wings,
    }


def _normalize_logo_payload(payload: dict) -> dict[str, str]:
    logo = payload.get("logo", payload)
    if not isinstance(logo, dict):
        raise ValueError("AI logo payload was not an object")

    title = str(logo.get("title", "")).strip()
    style_hint = str(logo.get("style_hint", "")).strip().lower()
    art = str(logo.get("art", "")).strip("\n")
    if style_hint and style_hint not in FIGLET_STYLE_MAP:
        style_hint = ""

    return {
        "title": title,
        "style_hint": style_hint,
        "art": art,
    }


def _normalize_hero_payload(payload: dict) -> dict[str, str]:
    hero = payload.get("hero", payload)
    if not isinstance(hero, dict):
        raise ValueError("AI hero payload was not an object")
    return {
        "art": str(hero.get("art", "")).strip("\n"),
    }


def generate_branding_bundle(skin: dict, *, backend: str = "hermes", direction: str = "") -> dict[str, str]:
    prompt = (
        "Generate a Hermes skin branding bundle.\n"
        "Return JSON shaped as "
        '{"branding":{"agent_name":"","welcome":"","goodbye":"","response_label":"","prompt_symbol":"","help_header":""}}.\n'
        "Keep the text concise, vivid, and terminal-friendly.\n"
        f"{_direction_context(direction)}"
        f"{_skin_context(skin)}"
    )
    return _normalize_branding_payload(generate_json(prompt, backend=backend))


def generate_spinner_bundle(skin: dict, *, backend: str = "hermes", direction: str = "") -> dict[str, list]:
    prompt = (
        "Generate a Hermes spinner bundle.\n"
        "Return JSON shaped as "
        '{"spinner":{"waiting_faces":[],"thinking_faces":[],"thinking_verbs":[],"wings":[["",""]]}}.\n'
        "Use short terminal-safe strings and keep faces visually distinct.\n"
        f"{_direction_context(direction)}"
        f"{_skin_context(skin)}"
    )
    return _normalize_spinner_payload(generate_json(prompt, backend=backend))


def generate_logo_bundle(skin: dict, *, backend: str = "hermes", direction: str = "") -> dict[str, str]:
    prompt = (
        "Generate Hermes logo concepts.\n"
        'Return JSON shaped as {"logo":{"title":"","style_hint":"","art":""}}.\n'
        f"style_hint must be one of: {', '.join(FIGLET_STYLE_MAP)}.\n"
        "title should be short and suitable for a figlet banner.\n"
        "art should be optional plain ASCII text art with no markdown fences, at most 8 lines tall, and at most 72 columns wide.\n"
        f"{_direction_context(direction)}"
        f"{_skin_context(skin)}"
    )
    return _normalize_logo_payload(generate_json(prompt, backend=backend))


def generate_hero_bundle(skin: dict, *, backend: str = "hermes", direction: str = "") -> dict[str, str]:
    prompt = (
        "Generate Hermes hero ASCII art.\n"
        'Return JSON shaped as {"hero":{"art":""}}.\n'
        "The art must be plain ASCII or terminal-safe Unicode text, no markdown fences, at most 14 lines tall, and at most 72 columns wide.\n"
        "Favor strong silhouettes and a readable terminal scene.\n"
        f"{_direction_context(direction)}"
        f"{_skin_context(skin)}"
    )
    return _normalize_hero_payload(generate_json(prompt, backend=backend))


def generate_skin_bundle(skin: dict, *, backend: str = "hermes", direction: str = "") -> dict:
    prompt = (
        "Generate a Hermes skin concept bundle.\n"
        "Return JSON shaped as "
        '{"branding":{"agent_name":"","welcome":"","goodbye":"","response_label":"","prompt_symbol":"","help_header":""},'
        '"spinner":{"waiting_faces":[],"thinking_faces":[],"thinking_verbs":[],"wings":[["",""]]},'
        '"logo":{"title":"","style_hint":"","art":""},'
        '"hero":{"art":""}}.\n'
        f"logo.style_hint must be one of: {', '.join(FIGLET_STYLE_MAP)}.\n"
        "Keep all text terminal-friendly and concise. Logo and hero art are optional.\n"
        f"{_direction_context(direction)}"
        f"{_skin_context(skin)}"
    )
    payload = generate_json(prompt, backend=backend)
    return {
        "branding": _normalize_branding_payload(payload),
        "spinner": _normalize_spinner_payload(payload),
        "logo": _normalize_logo_payload(payload),
        "hero": _normalize_hero_payload(payload),
    }
