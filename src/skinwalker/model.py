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
SKIN_IMPORT_MODE_OPTIONS = ["replace", "merge"]

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
    "nord": {
        "banner_border": "#5E81AC",
        "banner_title": "#ECEFF4",
        "banner_accent": "#88C0D0",
        "banner_dim": "#4C566A",
        "banner_text": "#D8DEE9",
        "ui_accent": "#81A1C1",
        "ui_label": "#88C0D0",
        "ui_ok": "#A3BE8C",
        "ui_error": "#BF616A",
        "ui_warn": "#EBCB8B",
        "prompt": "#E5E9F0",
        "input_rule": "#5E81AC",
        "response_border": "#81A1C1",
        "session_label": "#88C0D0",
        "session_border": "#3B4252",
    },
    "dracula": {
        "banner_border": "#BD93F9",
        "banner_title": "#F8F8F2",
        "banner_accent": "#FF79C6",
        "banner_dim": "#6272A4",
        "banner_text": "#F8F8F2",
        "ui_accent": "#BD93F9",
        "ui_label": "#8BE9FD",
        "ui_ok": "#50FA7B",
        "ui_error": "#FF5555",
        "ui_warn": "#FFB86C",
        "prompt": "#F8F8F2",
        "input_rule": "#BD93F9",
        "response_border": "#FF79C6",
        "session_label": "#8BE9FD",
        "session_border": "#44475A",
    },
    "catppuccin": {
        "banner_border": "#89B4FA",
        "banner_title": "#CDD6F4",
        "banner_accent": "#CBA6F7",
        "banner_dim": "#585B70",
        "banner_text": "#CDD6F4",
        "ui_accent": "#89B4FA",
        "ui_label": "#89DCEB",
        "ui_ok": "#A6E3A1",
        "ui_error": "#F38BA8",
        "ui_warn": "#FAB387",
        "prompt": "#CDD6F4",
        "input_rule": "#89B4FA",
        "response_border": "#CBA6F7",
        "session_label": "#89DCEB",
        "session_border": "#313244",
    },
    "solarized-dark": {
        "banner_border": "#268BD2",
        "banner_title": "#FDF6E3",
        "banner_accent": "#2AA198",
        "banner_dim": "#586E75",
        "banner_text": "#839496",
        "ui_accent": "#268BD2",
        "ui_label": "#2AA198",
        "ui_ok": "#859900",
        "ui_error": "#DC322F",
        "ui_warn": "#B58900",
        "prompt": "#93A1A1",
        "input_rule": "#268BD2",
        "response_border": "#2AA198",
        "session_label": "#657B83",
        "session_border": "#073642",
    },
    "gruvbox": {
        "banner_border": "#458588",
        "banner_title": "#EBDBB2",
        "banner_accent": "#FABD2F",
        "banner_dim": "#665C54",
        "banner_text": "#D5C4A1",
        "ui_accent": "#83A598",
        "ui_label": "#8EC07C",
        "ui_ok": "#B8BB26",
        "ui_error": "#FB4934",
        "ui_warn": "#FE8019",
        "prompt": "#EBDBB2",
        "input_rule": "#458588",
        "response_border": "#D3869B",
        "session_label": "#A89984",
        "session_border": "#3C3836",
    },
    "tokyo-night": {
        "banner_border": "#7AA2F7",
        "banner_title": "#C0CAF5",
        "banner_accent": "#BB9AF7",
        "banner_dim": "#414868",
        "banner_text": "#A9B1D6",
        "ui_accent": "#7AA2F7",
        "ui_label": "#7DCFFF",
        "ui_ok": "#9ECE6A",
        "ui_error": "#F7768E",
        "ui_warn": "#E0AF68",
        "prompt": "#C0CAF5",
        "input_rule": "#7AA2F7",
        "response_border": "#BB9AF7",
        "session_label": "#565F89",
        "session_border": "#24283B",
    },
    "one-dark": {
        "banner_border": "#61AFEF",
        "banner_title": "#ABB2BF",
        "banner_accent": "#C678DD",
        "banner_dim": "#5C6370",
        "banner_text": "#ABB2BF",
        "ui_accent": "#61AFEF",
        "ui_label": "#56B6C2",
        "ui_ok": "#98C379",
        "ui_error": "#E06C75",
        "ui_warn": "#E5C07B",
        "prompt": "#ABB2BF",
        "input_rule": "#61AFEF",
        "response_border": "#C678DD",
        "session_label": "#828997",
        "session_border": "#3E4451",
    },
    "monokai": {
        "banner_border": "#66D9E8",
        "banner_title": "#F8F8F2",
        "banner_accent": "#AE81FF",
        "banner_dim": "#75715E",
        "banner_text": "#F8F8F2",
        "ui_accent": "#AE81FF",
        "ui_label": "#66D9E8",
        "ui_ok": "#A6E22E",
        "ui_error": "#F92672",
        "ui_warn": "#FD971F",
        "prompt": "#F8F8F2",
        "input_rule": "#AE81FF",
        "response_border": "#66D9E8",
        "session_label": "#75715E",
        "session_border": "#3E3D32",
    },
    "rose-pine": {
        "banner_border": "#31748F",
        "banner_title": "#E0DEF4",
        "banner_accent": "#C4A7E7",
        "banner_dim": "#6E6A86",
        "banner_text": "#E0DEF4",
        "ui_accent": "#9CCFD8",
        "ui_label": "#EBBCBA",
        "ui_ok": "#31748F",
        "ui_error": "#EB6F92",
        "ui_warn": "#F6C177",
        "prompt": "#E0DEF4",
        "input_rule": "#C4A7E7",
        "response_border": "#EBBCBA",
        "session_label": "#908CAA",
        "session_border": "#1F1D2E",
    },
    "kanagawa": {
        "banner_border": "#7E9CD8",
        "banner_title": "#DCD7BA",
        "banner_accent": "#957FB8",
        "banner_dim": "#54546D",
        "banner_text": "#C8C093",
        "ui_accent": "#7E9CD8",
        "ui_label": "#6A9589",
        "ui_ok": "#76946A",
        "ui_error": "#C34043",
        "ui_warn": "#FFA066",
        "prompt": "#DCD7BA",
        "input_rule": "#7E9CD8",
        "response_border": "#957FB8",
        "session_label": "#727169",
        "session_border": "#2A2A37",
    },
    "everforest": {
        "banner_border": "#7FBBB3",
        "banner_title": "#D3C6AA",
        "banner_accent": "#A7C080",
        "banner_dim": "#5C6A72",
        "banner_text": "#D3C6AA",
        "ui_accent": "#83C092",
        "ui_label": "#7FBBB3",
        "ui_ok": "#A7C080",
        "ui_error": "#E67E80",
        "ui_warn": "#DBBC7F",
        "prompt": "#D3C6AA",
        "input_rule": "#7FBBB3",
        "response_border": "#D699B6",
        "session_label": "#859289",
        "session_border": "#323D43",
    },
    "synthwave": {
        "banner_border": "#FF7EDB",
        "banner_title": "#FFFFFF",
        "banner_accent": "#72F1B8",
        "banner_dim": "#495495",
        "banner_text": "#E8D9FC",
        "ui_accent": "#FF7EDB",
        "ui_label": "#72F1B8",
        "ui_ok": "#72F1B8",
        "ui_error": "#FE4450",
        "ui_warn": "#FEDE5D",
        "prompt": "#FFFFFF",
        "input_rule": "#FF7EDB",
        "response_border": "#72F1B8",
        "session_label": "#B893CE",
        "session_border": "#2B213A",
    },
    "material": {
        "banner_border": "#82AAFF",
        "banner_title": "#A6ACCD",
        "banner_accent": "#C792EA",
        "banner_dim": "#4B5263",
        "banner_text": "#A6ACCD",
        "ui_accent": "#82AAFF",
        "ui_label": "#89DDFF",
        "ui_ok": "#C3E88D",
        "ui_error": "#F07178",
        "ui_warn": "#FFCB6B",
        "prompt": "#A6ACCD",
        "input_rule": "#82AAFF",
        "response_border": "#C792EA",
        "session_label": "#676E95",
        "session_border": "#34394F",
    },
    "ayu-dark": {
        "banner_border": "#59C2FF",
        "banner_title": "#BFBAB0",
        "banner_accent": "#FFB454",
        "banner_dim": "#3D424D",
        "banner_text": "#BFBAB0",
        "ui_accent": "#59C2FF",
        "ui_label": "#95E6CB",
        "ui_ok": "#AAD94C",
        "ui_error": "#FF3333",
        "ui_warn": "#FF8F40",
        "prompt": "#BFBAB0",
        "input_rule": "#59C2FF",
        "response_border": "#D2A6FF",
        "session_label": "#626A73",
        "session_border": "#131721",
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


def parse_skin_yaml(text: str, *, strict: bool = False) -> dict:
    raw = str(text or "").strip()
    if not raw:
        raise ValueError("Paste skin YAML first")

    try:
        parsed = yaml.safe_load(raw)
    except Exception as exc:
        raise ValueError(f"Invalid YAML: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Skin YAML must decode to a mapping")

    return normalize_skin(parsed, strict=strict)


def import_skin_yaml_file(path: str, *, strict: bool = False) -> dict:
    file_path = Path(path).expanduser()
    if not file_path.exists():
        raise FileNotFoundError(f"Skin YAML file not found: {file_path}")
    return parse_skin_yaml(file_path.read_text(encoding="utf-8"), strict=strict)


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
