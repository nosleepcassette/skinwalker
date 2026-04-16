from __future__ import annotations

from rich.align import Align
from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from .model import COLOR_KEY_LABELS, COLOR_KEYS, TOOL_EMOJI_KEYS, normalize_color_token


def _render_markup_block(markup: str, fallback_style: str = "") -> Text:
    if not markup.strip():
        return Text("", style=fallback_style)
    try:
        return Text.from_markup(markup)
    except Exception:
        return Text(markup, style=fallback_style)


def _recolor_markup(markup: str, color: str) -> Text:
    """Extract plain text from markup and apply skin color.

    Art is stored with its generation color baked into Rich markup tags.
    Text.from_markup() honours those tags and ignores any fallback style,
    so the preview never reflects color scheme changes. This strips the
    baked-in color and re-applies the current skin's logo_color/hero_color.
    """
    if not markup.strip():
        return Text("", style=color)
    try:
        plain = Text.from_markup(markup).plain
        return Text(plain, style=color)
    except Exception:
        return Text(markup, style=color)


def _trim_outer_padding(text: Text) -> Text:
    lines = text.plain.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return Text("", style=text.style or "")

    non_empty = [line for line in lines if line.strip()]
    common_indent = min((len(line) - len(line.lstrip(" ")) for line in non_empty), default=0)
    trimmed = "\n".join(line[common_indent:].rstrip() for line in lines)
    return Text(trimmed, style=text.style or "")


def _aligned_markup(markup: str, color: str, justify: str, native_colors: bool) -> Align:
    if native_colors:
        text = _trim_outer_padding(_render_markup_block(markup, ""))
    else:
        text = _trim_outer_padding(_recolor_markup(markup, color))
    return Align(text, align=justify)


def render_skin_preview(
    skin: dict,
    *,
    show_logo: bool = True,
    show_hero: bool = True,
    compact: bool = False,
    native_colors: bool = False,
    logo_override: str | None = None,
    hero_override: str | None = None,
    logo_justify: str = "left",
    hero_justify: str = "left",
):
    colors = skin.get("colors") or {}
    branding = skin.get("branding") or {}
    spinner = skin.get("spinner") or {}
    tool_emojis = skin.get("tool_emojis") or {}

    # In native_colors mode all ANSI styling is stripped so the terminal's
    # own color scheme shows through — useful for checking legibility on
    # themes like Nord, Dracula, Catppuccin etc.
    if native_colors:
        border = accent = dim = text_color = prompt_color = ""
        response_border = ui_label = ui_accent = ""
        logo_color = ""
    else:
        border = normalize_color_token(colors.get("banner_border", "#8EA3FF"), "#8EA3FF")
        accent = normalize_color_token(colors.get("banner_accent", "#8EA3FF"), "#8EA3FF")
        dim = normalize_color_token(colors.get("banner_dim", "#586789"), "#586789")
        text_color = normalize_color_token(colors.get("banner_text", "#DCE4FF"), "#DCE4FF")
        prompt_color = normalize_color_token(colors.get("prompt", text_color), text_color)
        response_border = normalize_color_token(colors.get("response_border", "#60A5FA"), "#60A5FA")
        ui_label = normalize_color_token(colors.get("ui_label", accent), accent)
        ui_accent = normalize_color_token(colors.get("ui_accent", accent), accent)
        logo_color = normalize_color_token(
            colors.get("logo_color") or colors.get("banner_title", accent), accent
        )
        hero_color = normalize_color_token(
            colors.get("hero_color") or colors.get("banner_accent", accent), accent
        )

    logo_markup = str(logo_override if logo_override is not None else skin.get("banner_logo", ""))
    hero_markup = str(hero_override if hero_override is not None else skin.get("banner_hero", ""))
    logo = _aligned_markup(logo_markup, logo_color if not native_colors else "", logo_justify, native_colors)
    hero = _aligned_markup(hero_markup, hero_color if not native_colors else "", hero_justify, native_colors)

    waiting_faces = spinner.get("waiting_faces") or ["◐"]
    thinking_faces = spinner.get("thinking_faces") or waiting_faces
    thinking_verbs = spinner.get("thinking_verbs") or ["thinking"]
    wings = spinner.get("wings") or [["‹", "›"]]
    tool_prefix = str(skin.get("tool_prefix", "┊") or "┊")

    response_label = str(branding.get("response_label", " Hermes ")).strip() or "Hermes"
    prompt_symbol = str(branding.get("prompt_symbol", "› ") or "› ")
    help_header = str(branding.get("help_header", "Activity")).strip() or "Activity"
    agent_name = str(branding.get("agent_name", "") or "Hermes Agent")
    welcome = str(branding.get("welcome", "") or "Ready when you are.")
    goodbye = str(branding.get("goodbye", "") or "Session complete.")

    banner_items = [
        Text("Session interactive CLI", style=accent),
        Text("Model gpt-5.4", style=dim),
        Text(f"Skin {skin.get('name', 'custom-skin')}", style=text_color),
        Text(welcome, style=text_color),
    ]
    if show_hero and hero_markup.strip():
        banner_items.append(hero)
    banner_body = Group(*banner_items)

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
    if not compact:
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
            fallback_emoji, preview_text = tool_samples.get(tool_name, ("•", tool_name.replace("_", " ")))
            tool_lines.append(
                Text.assemble(
                    (f"{tool_prefix} ", ui_label),
                    (f"{tool_emojis.get(tool_name, fallback_emoji)} ", prompt_color),
                    (preview_text, text_color),
                )
            )

    prompt_line = Text.assemble(
        (prompt_symbol, prompt_color),
        ("make the launch screen feel calmer", text_color),
    )

    top_items = []
    if show_logo and logo_markup.strip():
        top_items.append(logo)

    return Group(
        *top_items,
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
        label = COLOR_KEY_LABELS.get(key, key)
        lines.append(
            Text.assemble(
                (f"{label:<18} ", "bold"),
                (color.ljust(10), color),
                ("  ", ""),
                ("█████", color),
            )
        )
    return Group(*lines)
