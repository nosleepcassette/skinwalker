from __future__ import annotations

from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from .model import COLOR_KEYS, TOOL_EMOJI_KEYS, normalize_color_token


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
    help_header = str(branding.get("help_header", "Activity")).strip() or "Activity"
    agent_name = str(branding.get("agent_name", "") or "Hermes Agent")
    welcome = str(branding.get("welcome", "") or "Ready when you are.")
    goodbye = str(branding.get("goodbye", "") or "Session complete.")

    banner_body = Group(
        Text("Session interactive CLI", style=accent),
        Text("Model gpt-5.4", style=dim),
        Text(f"Skin {skin.get('name', 'custom-skin')}", style=text_color),
        Text(welcome, style=text_color),
        hero,
    )

    waiting_lines = []
    for index, face in enumerate(waiting_faces[: min(3, len(waiting_faces))]):
        sample_left, sample_right = wings[index % len(wings)] if wings else ("", "")
        waiting_lines.append(
            Text.assemble(
                (f"{tool_prefix} ", ui_label),
                (f"{sample_left} ", ui_accent),
                (f"{face} ", prompt_color),
                (f"{sample_right} ", ui_accent),
                (f"warming the line {index + 1}", text_color),
            )
        )

    thinking_lines = []
    for index, face in enumerate(thinking_faces[: min(3, len(thinking_faces))]):
        sample_left, sample_right = wings[index % len(wings)] if wings else ("", "")
        verb = thinking_verbs[index % len(thinking_verbs)] if thinking_verbs else "thinking"
        thinking_lines.append(
            Text.assemble(
                (f"{tool_prefix} ", ui_label),
                (f"{sample_left} ", ui_accent),
                (f"{face} ", prompt_color),
                (f"{sample_right} ", ui_accent),
                (verb, text_color),
            )
        )

    tool_lines = []
    tool_samples = {
        "terminal": ("⚡", "ls ~/.hermes/skins"),
        "web_search": ("🔎", "search for skin ergonomics"),
        "web_extract": ("🌐", "extract page sections"),
        "browser_navigate": ("🧭", "open preview target"),
        "browser_click": ("🖱", "click apply button"),
        "read_file": ("📄", "~/.hermes/skins/cass-ascii.yaml"),
        "write_file": ("✎", "~/.hermes/skins/new-skin.yaml"),
        "patch": ("🩹", "patch spinner presets"),
        "todo": ("📝", "review remaining polish"),
        "delegate_task": ("🔀", "hand off hero variations"),
    }
    for tool_name in TOOL_EMOJI_KEYS:
        fallback_emoji, preview = tool_samples.get(tool_name, ("•", tool_name.replace("_", " ")))
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
            Group(*waiting_lines, *thinking_lines, *tool_lines),
            title=help_header,
            border_style=ui_accent,
        ),
        Panel(
            Group(
                Text("Skins now save directly into your Hermes folder.", style=text_color),
                Text(goodbye, style=dim),
            ),
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
