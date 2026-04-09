from __future__ import annotations

from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from .model import COLOR_KEYS, normalize_color_token


def _render_markup_block(markup: str, fallback_style: str = "") -> Text:
    if not markup.strip():
        return Text("", style=fallback_style)
    try:
        return Text.from_markup(markup)
    except Exception:
        return Text(markup, style=fallback_style)


def render_skin_preview(skin: dict):
    colors = skin.get("colors") or {}
    branding = skin.get("branding") or {}
    spinner = skin.get("spinner") or {}
    tool_emojis = skin.get("tool_emojis") or {}

    border = normalize_color_token(colors.get("banner_border", "#8EA3FF"), "#8EA3FF")
    accent = normalize_color_token(colors.get("banner_accent", "#8EA3FF"), "#8EA3FF")
    dim = normalize_color_token(colors.get("banner_dim", "#586789"), "#586789")
    text_color = normalize_color_token(colors.get("banner_text", "#DCE4FF"), "#DCE4FF")
    prompt_color = normalize_color_token(colors.get("prompt", text_color), text_color)
    response_border = normalize_color_token(colors.get("response_border", "#60A5FA"), "#60A5FA")
    ui_label = normalize_color_token(colors.get("ui_label", accent), accent)
    ui_accent = normalize_color_token(colors.get("ui_accent", accent), accent)

    logo = _render_markup_block(skin.get("banner_logo", ""), normalize_color_token(colors.get("banner_title", accent), accent))
    hero = _render_markup_block(skin.get("banner_hero", ""), accent)

    waiting_faces = spinner.get("waiting_faces") or ["◐"]
    thinking_faces = spinner.get("thinking_faces") or waiting_faces
    thinking_verbs = spinner.get("thinking_verbs") or ["thinking"]
    wings = spinner.get("wings") or [["‹", "›"]]
    wing_left, wing_right = wings[0] if wings else ("", "")
    tool_prefix = str(skin.get("tool_prefix", "┊") or "┊")

    response_label = str(branding.get("response_label", " Hermes ")).strip() or "Hermes"
    prompt_symbol = str(branding.get("prompt_symbol", "› ") or "› ")
    agent_name = str(branding.get("agent_name", "") or "Hermes Agent")
    welcome = str(branding.get("welcome", "") or "Ready when you are.")

    banner_body = Group(
        Text("Session interactive CLI", style=accent),
        Text("Model gpt-5.4", style=dim),
        Text(f"Skin {skin.get('name', 'custom-skin')}", style=text_color),
        Text(welcome, style=text_color),
        hero,
    )

    waiting_line = Text.assemble(
        (f"{tool_prefix} ", ui_label),
        (f"{wing_left} ", ui_accent),
        (f"{waiting_faces[0]} ", prompt_color),
        (f"{wing_right} ", ui_accent),
        ("warming the line", text_color),
    )

    thinking_line = Text.assemble(
        (f"{tool_prefix} ", ui_label),
        (f"{wing_left} ", ui_accent),
        (f"{thinking_faces[0]} ", prompt_color),
        (f"{wing_right} ", ui_accent),
        (thinking_verbs[0], text_color),
    )

    tool_lines = []
    for tool_name, fallback_emoji, preview in [
        ("terminal", "⚡", "ls ~/.hermes/skins"),
        ("web_search", "🔎", "look up palette ergonomics"),
        ("read_file", "📄", "~/.hermes/skins/cass-ascii.yaml"),
    ]:
        tool_lines.append(
            Text.assemble(
                (f"{tool_prefix} ", ui_label),
                (f"{tool_emojis.get(tool_name, fallback_emoji)} ", prompt_color),
                (preview, text_color),
            )
        )

    prompt_line = Text.assemble(
        (prompt_symbol, prompt_color),
        ("make the launch screen feel calmer", text_color),
    )

    return Group(
        logo,
        Panel(
            banner_body,
            title=agent_name,
            border_style=border,
        ),
        Panel(
            Group(waiting_line, thinking_line, *tool_lines),
            title="Activity",
            border_style=ui_accent,
        ),
        Panel(
            Text("Skins now save directly into your Hermes folder.", style=text_color),
            title=response_label,
            border_style=response_border,
        ),
        prompt_line,
    )


def render_color_preview(colors: dict) -> Group:
    lines = []
    for key in COLOR_KEYS:
        color = normalize_color_token(colors.get(key, ""), "#8EA3FF")
        lines.append(
            Text.assemble(
                (f"{key:<16} ", "bold"),
                (color.ljust(10), color),
                ("  ", ""),
                ("█████", color),
            )
        )
    return Group(*lines)
