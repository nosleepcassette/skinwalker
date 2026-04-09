from __future__ import annotations

import colorsys
from copy import deepcopy
from pathlib import Path
import re

from PIL import ImageColor
from rich.style import Style
import yaml


COLOR_KEYS = [
    "banner_border",
    "banner_title",
    "banner_accent",
    "banner_dim",
    "banner_text",
    "ui_accent",
    "ui_label",
    "ui_ok",
    "ui_error",
    "ui_warn",
    "prompt",
    "input_rule",
    "response_border",
    "session_label",
    "session_border",
]

BRANDING_KEYS = [
    "agent_name",
    "welcome",
    "goodbye",
    "response_label",
    "prompt_symbol",
    "help_header",
]

TOOL_EMOJI_KEYS = [
    "terminal",
    "web_search",
    "web_extract",
    "browser_navigate",
    "browser_click",
    "read_file",
    "write_file",
    "patch",
    "todo",
    "delegate_task",
]

JUSTIFY_OPTIONS = ["left", "center", "right"]
FIT_MODE_OPTIONS = ["flexible", "fixed"]
IMPORT_MODE_OPTIONS = ["plain", "markup"]
PALETTE_IMPORT_MODE_OPTIONS = ["auto", "keyed", "list"]

FIGLET_STYLE_MAP = {
    "minimal": "standard",
    "slant": "slant",
    "small": "small",
    "heavy": "doom",
    "block": "big",
    "shadow": "banner3-d",
    "wide": "banner",
    "compact": "lean",
}

COLOR_PRESETS = {
    "default": {
        "banner_border": "#CD7F32",
        "banner_title": "#FFD700",
        "banner_accent": "#FFBF00",
        "banner_dim": "#B8860B",
        "banner_text": "#FFF8DC",
        "ui_accent": "#FFBF00",
        "ui_label": "#4DD0E1",
        "ui_ok": "#4CAF50",
        "ui_error": "#EF5350",
        "ui_warn": "#FFA726",
        "prompt": "#FFF8DC",
        "input_rule": "#CD7F32",
        "response_border": "#FFD700",
        "session_label": "#DAA520",
        "session_border": "#8B8682",
    },
    "slate": {
        "banner_border": "#4C6FFF",
        "banner_title": "#DCE6FF",
        "banner_accent": "#7DD3FC",
        "banner_dim": "#41557B",
        "banner_text": "#CBD5E1",
        "ui_accent": "#7DD3FC",
        "ui_label": "#93C5FD",
        "ui_ok": "#22C55E",
        "ui_error": "#F87171",
        "ui_warn": "#FBBF24",
        "prompt": "#E2E8F0",
        "input_rule": "#4C6FFF",
        "response_border": "#60A5FA",
        "session_label": "#93C5FD",
        "session_border": "#475569",
    },
    "mono": {
        "banner_border": "#555555",
        "banner_title": "#E6EDF3",
        "banner_accent": "#AAAAAA",
        "banner_dim": "#444444",
        "banner_text": "#C9D1D9",
        "ui_accent": "#AAAAAA",
        "ui_label": "#888888",
        "ui_ok": "#888888",
        "ui_error": "#CCCCCC",
        "ui_warn": "#BBBBBB",
        "prompt": "#C9D1D9",
        "input_rule": "#555555",
        "response_border": "#888888",
        "session_label": "#AAAAAA",
        "session_border": "#555555",
    },
    "ember": {
        "banner_border": "#A33A22",
        "banner_title": "#FFD6A5",
        "banner_accent": "#FF7A59",
        "banner_dim": "#6E2E21",
        "banner_text": "#FFEFE1",
        "ui_accent": "#FF7A59",
        "ui_label": "#FFB86B",
        "ui_ok": "#7BC96F",
        "ui_error": "#FF6B6B",
        "ui_warn": "#FFB347",
        "prompt": "#FFF1E8",
        "input_rule": "#A33A22",
        "response_border": "#FF9A62",
        "session_label": "#FFB86B",
        "session_border": "#7A4A3A",
    },
    "ocean": {
        "banner_border": "#0E7490",
        "banner_title": "#CCFBF1",
        "banner_accent": "#5EEAD4",
        "banner_dim": "#155E75",
        "banner_text": "#D5F8FF",
        "ui_accent": "#5EEAD4",
        "ui_label": "#93C5FD",
        "ui_ok": "#34D399",
        "ui_error": "#FB7185",
        "ui_warn": "#FBBF24",
        "prompt": "#E0FBFC",
        "input_rule": "#0E7490",
        "response_border": "#38BDF8",
        "session_label": "#67E8F9",
        "session_border": "#25637A",
    },
    "forest": {
        "banner_border": "#2F6B3B",
        "banner_title": "#E7F7D4",
        "banner_accent": "#A3E635",
        "banner_dim": "#466A3B",
        "banner_text": "#EFFFD7",
        "ui_accent": "#A3E635",
        "ui_label": "#86EFAC",
        "ui_ok": "#4ADE80",
        "ui_error": "#FB7185",
        "ui_warn": "#FACC15",
        "prompt": "#F7FEE7",
        "input_rule": "#2F6B3B",
        "response_border": "#84CC16",
        "session_label": "#BEF264",
        "session_border": "#56754E",
    },
    "amber-phosphor": {
        "banner_border": "#71450B",
        "banner_title": "#FFD36B",
        "banner_accent": "#FFB347",
        "banner_dim": "#4C2F09",
        "banner_text": "#FFF0C2",
        "ui_accent": "#FFB347",
        "ui_label": "#E2B35C",
        "ui_ok": "#F4D37C",
        "ui_error": "#C97442",
        "ui_warn": "#FFD36B",
        "prompt": "#FFF4D6",
        "input_rule": "#71450B",
        "response_border": "#D58B1D",
        "session_label": "#E8B95C",
        "session_border": "#55350A",
    },
    "amber-cathode": {
        "banner_border": "#5E3904",
        "banner_title": "#FFC65C",
        "banner_accent": "#FFAE1A",
        "banner_dim": "#3E2504",
        "banner_text": "#F9E4A8",
        "ui_accent": "#FFAE1A",
        "ui_label": "#D59E42",
        "ui_ok": "#F0CC79",
        "ui_error": "#B45C31",
        "ui_warn": "#FFD27A",
        "prompt": "#FFF0C2",
        "input_rule": "#5E3904",
        "response_border": "#C97A0A",
        "session_label": "#D9A54A",
        "session_border": "#462A05",
    },
    "matrix": {
        "banner_border": "#0F5F1A",
        "banner_title": "#8AFF6E",
        "banner_accent": "#39FF14",
        "banner_dim": "#0C3712",
        "banner_text": "#C7FFC0",
        "ui_accent": "#39FF14",
        "ui_label": "#72FF8A",
        "ui_ok": "#5CFF7A",
        "ui_error": "#4F9A47",
        "ui_warn": "#B5FF5C",
        "prompt": "#C7FFC0",
        "input_rule": "#0F5F1A",
        "response_border": "#33CC33",
        "session_label": "#7DFF8D",
        "session_border": "#145F20",
    },
}

SPINNER_PRESETS = {
    "default": {
        "waiting_faces": ["◐", "◓", "◑", "◒"],
        "thinking_faces": ["◐", "◓", "◑", "◒"],
        "thinking_verbs": ["thinking", "routing", "drafting"],
        "wings": [["‹", "›"]],
    },
    "ares": {
        "waiting_faces": ["(⚔)", "(⛨)", "(▲)", "(<>)", "(/)"],
        "thinking_faces": ["(⚔)", "(⛨)", "(▲)", "(⌁)", "(<>)"],
        "thinking_verbs": [
            "forging",
            "marching",
            "sizing the field",
            "holding the line",
            "hammering plans",
            "plotting impact",
        ],
        "wings": [["⟪⚔", "⚔⟫"], ["⟪▲", "▲⟫"], ["⟪⛨", "⛨⟫"]],
    },
    "cassette-amber": {
        "waiting_faces": ["(✦)", "(▲)", "(◇)", "(<>)", "(🔥)"],
        "thinking_faces": ["(✦)", "(▲)", "(◇)", "(⌁)", "(🔥)"],
        "thinking_verbs": [
            "banking into the draft",
            "measuring burn",
            "reading the updraft",
            "setting wing angle",
            "holding the flame core",
            "plotting a hot landing",
        ],
        "wings": [["⟪✦", "✦⟫"], ["⟪▲", "▲⟫"], ["⟪◇", "◇⟫"]],
    },
    "sisyphus": {
        "waiting_faces": ["(◉)", "(◌)", "(◬)", "(⬤)", "(::)"],
        "thinking_faces": ["(◉)", "(◬)", "(◌)", "(○)", "(●)"],
        "thinking_verbs": [
            "finding traction",
            "measuring the grade",
            "resetting the boulder",
            "counting the ascent",
            "testing leverage",
            "pushing uphill",
        ],
        "wings": [["⟪◉", "◉⟫"], ["⟪◬", "◬⟫"], ["⟪◌", "◌⟫"]],
    },
    "matrix": {
        "waiting_faces": ["[■]", "[▣]", "[◆]", "[▲]"],
        "thinking_faces": ["[◆]", "[▲]", "[■]", "[⌘]"],
        "thinking_verbs": [
            "tracing the packet",
            "following the wire",
            "aligning the grid",
            "reducing the noise floor",
            "resolving the signal",
        ],
        "wings": [["⟦", "⟧"], ["⟪", "⟫"]],
    },
    "mono": {
        "waiting_faces": ["(·)", "(•)", "(●)", "(○)"],
        "thinking_faces": ["(•)", "(●)", "(○)", "(◌)"],
        "thinking_verbs": [
            "indexing",
            "sorting",
            "reducing",
            "checking the shape",
            "settling the draft",
        ],
        "wings": [["‹", "›"], ["«", "»"]],
    },
}

COLOR_KEY_ALIASES = {
    "border": "banner_border",
    "title": "banner_title",
    "accent": "banner_accent",
    "dim": "banner_dim",
    "text": "banner_text",
    "label": "ui_label",
    "ok": "ui_ok",
    "error": "ui_error",
    "warn": "ui_warn",
    "warning": "ui_warn",
    "prompt_text": "prompt",
    "rule": "input_rule",
    "input": "input_rule",
    "response": "response_border",
    "session": "session_label",
    "session_dim": "session_border",
}

HEX_COLOR_RE = re.compile(r"^[0-9a-fA-F]{3}$|^[0-9a-fA-F]{6}$")


def blank_skin(name: str = "custom-skin") -> dict:
    return {
        "name": sanitize_skin_name(name),
        "description": "",
        "colors": {
            "banner_border": "#8EA3FF",
            "banner_title": "#8EA3FF",
            "banner_accent": "#8EA3FF",
            "banner_dim": "#586789",
            "banner_text": "#DCE4FF",
            "ui_accent": "#8EA3FF",
            "ui_label": "#8EA3FF",
            "ui_ok": "#4CAF50",
            "ui_error": "#EF5350",
            "ui_warn": "#FFA726",
            "prompt": "#DCE4FF",
            "input_rule": "#8EA3FF",
            "response_border": "#60A5FA",
            "session_label": "#8EA3FF",
            "session_border": "#586789",
        },
        "spinner": {
            "waiting_faces": ["◐", "◓", "◑", "◒"],
            "thinking_faces": ["◐", "◓", "◑", "◒"],
            "thinking_verbs": ["thinking", "routing", "drafting"],
            "wings": [["‹", "›"]],
        },
        "branding": {
            "agent_name": "Hermes Agent",
            "welcome": "Ready when you are.",
            "goodbye": "Goodbye.",
            "response_label": " Hermes ",
            "prompt_symbol": "› ",
            "help_header": "Commands",
        },
        "tool_prefix": "┊",
        "tool_emojis": {
            "terminal": "",
            "web_search": "",
            "web_extract": "",
            "browser_navigate": "",
            "browser_click": "",
            "read_file": "",
            "write_file": "",
            "patch": "",
            "todo": "",
            "delegate_task": "",
        },
        "banner_logo": "",
        "banner_hero": "",
    }


def _slugify_skin_name(name: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() or ch in {"-", "_"} else "-" for ch in str(name).strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-")


def sanitize_skin_name(name: str) -> str:
    cleaned = _slugify_skin_name(name)
    if not cleaned:
        raise ValueError("Skin name is required")
    return cleaned


def coerce_skin_name(name: str, fallback: str = "custom-skin") -> str:
    cleaned = _slugify_skin_name(name)
    if cleaned:
        return cleaned
    return sanitize_skin_name(fallback)


def parse_multiline_list(text: str) -> list[str]:
    return [line.strip() for line in str(text).splitlines() if line.strip()]


def format_multiline_list(items: list[str]) -> str:
    return "\n".join(str(item) for item in items or [])


def parse_wings_text(text: str) -> list[list[str]]:
    wings: list[list[str]] = []
    for line in str(text).splitlines():
        if not line.strip():
            continue
        if "|" in line:
            left, right = line.split("|", 1)
        elif "," in line:
            left, right = line.split(",", 1)
        else:
            parts = line.split()
            if len(parts) >= 2:
                left, right = parts[0], " ".join(parts[1:])
            else:
                continue
        wings.append([left.strip(), right.strip()])
    return [pair for pair in wings if pair[0] or pair[1]]


def format_wings_text(wings: list[list[str]]) -> str:
    return "\n".join(f"{left} | {right}" for left, right in wings or [])


def normalize_color_token(value: str, fallback: str = "") -> str:
    raw = str(value or "").strip()
    if not raw:
        return fallback

    if raw.startswith("#") and HEX_COLOR_RE.fullmatch(raw[1:]):
        return raw.upper()
    if HEX_COLOR_RE.fullmatch(raw):
        return f"#{raw.upper()}"

    try:
        Style.parse(raw)
    except Exception:
        return fallback
    return raw


def get_color_preset(name: str) -> dict[str, str]:
    preset_name = str(name or "").strip().lower()
    if preset_name not in COLOR_PRESETS:
        raise ValueError(f"Unknown palette: {name}")
    return dict(COLOR_PRESETS[preset_name])


def get_spinner_preset(name: str) -> dict[str, list]:
    preset_name = str(name or "").strip().lower()
    if preset_name not in SPINNER_PRESETS:
        raise ValueError(f"Unknown spinner preset: {name}")
    return deepcopy(SPINNER_PRESETS[preset_name])


def color_to_rgb(value: str) -> tuple[int, int, int]:
    token = normalize_color_token(value, "")
    if not token:
        raise ValueError("Color value is empty")
    try:
        return ImageColor.getrgb(token)
    except Exception as exc:
        raise ValueError(f"Color is not adjustable as RGB: {value}") from exc


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    red, green, blue = rgb
    return f"#{red:02X}{green:02X}{blue:02X}"


def adjust_color(
    value: str,
    *,
    hue_shift: float = 0.0,
    lightness_shift: float = 0.0,
    saturation_shift: float = 0.0,
) -> str:
    red, green, blue = color_to_rgb(value)
    hue, lightness, saturation = colorsys.rgb_to_hls(red / 255, green / 255, blue / 255)
    hue = (hue + hue_shift) % 1.0
    lightness = max(0.0, min(1.0, lightness + lightness_shift))
    saturation = max(0.0, min(1.0, saturation + saturation_shift))
    out_red, out_green, out_blue = colorsys.hls_to_rgb(hue, lightness, saturation)
    return rgb_to_hex((round(out_red * 255), round(out_green * 255), round(out_blue * 255)))


def _normalize_color_key(key: str) -> str:
    normalized = str(key or "").strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in COLOR_KEYS:
        return normalized
    return COLOR_KEY_ALIASES.get(normalized, "")


def _extract_colors_from_mapping(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {}

    colors = payload.get("colors") if isinstance(payload.get("colors"), dict) else payload
    if not isinstance(colors, dict):
        return {}

    result: dict[str, str] = {}
    for raw_key, raw_value in colors.items():
        key = _normalize_color_key(str(raw_key))
        color = normalize_color_token(str(raw_value), "")
        if key and color:
            result[key] = color
    return result


def _extract_color_tokens(payload: object) -> list[str]:
    if isinstance(payload, list):
        raw_tokens = [str(item).strip() for item in payload]
    else:
        raw_tokens = re.findall(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})", str(payload))
    return [token for token in (normalize_color_token(item, "") for item in raw_tokens) if token]


def _extract_colors_from_list(payload: object) -> dict[str, str]:
    tokens = _extract_color_tokens(payload)
    return {key: token for key, token in zip(COLOR_KEYS, tokens, strict=False)}


def _parse_keyed_colors(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in str(text or "").splitlines():
        stripped = line.strip().strip(",")
        if not stripped or stripped in {"{", "}"}:
            continue
        if stripped.endswith("{"):
            stripped = stripped[:-1].rstrip()
        if stripped.lower() == "colors:":
            continue

        match = re.match(r"^(?:--)?([A-Za-z0-9 _-]+)\s*[:=]\s*(.+)$", stripped)
        if not match:
            continue

        key = _normalize_color_key(match.group(1))
        if not key:
            continue

        value_chunk = match.group(2)
        for candidate in re.findall(r"#(?:[0-9a-fA-f]{6}|[0-9a-fA-f]{3})|[A-Za-z][A-Za-z0-9_-]*", value_chunk):
            color = normalize_color_token(candidate, "")
            if color:
                result[key] = color
                break

    return result


def parse_color_scheme(text: str, *, mode: str = "auto") -> dict[str, str]:
    raw = str(text or "").strip()
    if not raw:
        raise ValueError("Paste a colorscheme first")

    import_mode = str(mode or "auto").strip().lower()
    if import_mode not in PALETTE_IMPORT_MODE_OPTIONS:
        raise ValueError(f"Unknown palette import mode: {mode}")

    parsers = [import_mode] if import_mode != "auto" else ["keyed", "list"]
    yaml_attempted = False

    if import_mode == "auto":
        try:
            parsed = yaml.safe_load(raw)
        except Exception:
            parsed = None
        else:
            yaml_attempted = True
            mapping = _extract_colors_from_mapping(parsed)
            if mapping:
                return mapping
            mapping = _extract_colors_from_list(parsed)
            if mapping:
                return mapping

    for parser_name in parsers:
        if parser_name == "keyed":
            mapping = _parse_keyed_colors(raw)
        else:
            mapping = _extract_colors_from_list(raw)
        if mapping:
            return mapping

    if not yaml_attempted:
        try:
            parsed = yaml.safe_load(raw)
        except Exception:
            parsed = None
        else:
            mapping = _extract_colors_from_mapping(parsed)
            if mapping:
                return mapping

    raise ValueError("Could not recognize any color keys or hex values in that colorscheme")


def import_color_scheme_file(path: str, *, mode: str = "auto") -> dict[str, str]:
    file_path = Path(path).expanduser()
    if not file_path.exists():
        raise FileNotFoundError(f"Colorscheme file not found: {file_path}")
    return parse_color_scheme(file_path.read_text(encoding="utf-8"), mode=mode)


def normalize_skin(source: dict, *, strict: bool = True) -> dict:
    source = source or {}
    colors = source.get("colors") or {}
    branding = source.get("branding") or {}
    spinner = source.get("spinner") or {}
    tool_emojis = source.get("tool_emojis") or {}
    skin_name = source.get("name", "custom-skin")

    normalized = {
        "name": sanitize_skin_name(skin_name) if strict else coerce_skin_name(skin_name),
        "description": str(source.get("description", "")),
        "colors": {},
        "spinner": {},
        "branding": {},
        "tool_prefix": str(source.get("tool_prefix", "┊")),
        "tool_emojis": {},
        "banner_logo": str(source.get("banner_logo", "")),
        "banner_hero": str(source.get("banner_hero", "")),
    }

    for key in COLOR_KEYS:
        if colors.get(key):
            normalized["colors"][key] = normalize_color_token(str(colors[key]), "")

    for key in BRANDING_KEYS:
        if branding.get(key):
            normalized["branding"][key] = str(branding[key])

    for key, value in tool_emojis.items():
        normalized_key = str(key).strip()
        normalized_value = str(value).strip()
        if normalized_key and normalized_value:
            normalized["tool_emojis"][normalized_key] = normalized_value

    waiting_faces = [str(item) for item in spinner.get("waiting_faces", []) if str(item).strip()]
    thinking_faces = [str(item) for item in spinner.get("thinking_faces", []) if str(item).strip()]
    thinking_verbs = [str(item) for item in spinner.get("thinking_verbs", []) if str(item).strip()]
    wings = [
        [str(pair[0]), str(pair[1])]
        for pair in spinner.get("wings", [])
        if isinstance(pair, (list, tuple)) and len(pair) == 2
    ]

    if waiting_faces:
        normalized["spinner"]["waiting_faces"] = waiting_faces
    if thinking_faces:
        normalized["spinner"]["thinking_faces"] = thinking_faces
    if thinking_verbs:
        normalized["spinner"]["thinking_verbs"] = thinking_verbs
    if wings:
        normalized["spinner"]["wings"] = wings

    return normalized


def merge_skin(base: dict, override: dict) -> dict:
    merged = deepcopy(base)
    override = override or {}

    for key in ("name", "description", "tool_prefix", "banner_logo", "banner_hero"):
        value = override.get(key)
        if value is not None:
            merged[key] = value

    for section in ("colors", "branding", "spinner", "tool_emojis"):
        merged.setdefault(section, {})
        merged[section].update(override.get(section) or {})

    return merged


def unique_skin_name(existing_names: set[str], base_name: str) -> str:
    candidate = sanitize_skin_name(base_name)
    if candidate not in existing_names:
        return candidate

    index = 2
    while True:
        candidate_with_suffix = f"{candidate}-{index}"
        if candidate_with_suffix not in existing_names:
            return candidate_with_suffix
        index += 1
