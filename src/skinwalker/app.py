from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Callable

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, OptionList, Select, Static, TabPane, TabbedContent, TextArea
from textual.widgets.option_list import Option

from .art import (
    HERO_STYLE_MAP,
    generate_hero_markup,
    generate_logo_markup,
    import_art_file,
    import_art_text,
    list_logo_fonts,
)
from .hermes import HermesBridge, LibraryEntry
from .model import (
    COLOR_KEYS,
    COLOR_PRESETS,
    FIT_MODE_OPTIONS,
    IMPORT_MODE_OPTIONS,
    JUSTIFY_OPTIONS,
    PALETTE_IMPORT_MODE_OPTIONS,
    SPINNER_PRESETS,
    TOOL_EMOJI_KEYS,
    blank_skin,
    adjust_color,
    format_multiline_list,
    format_wings_text,
    get_color_preset,
    get_spinner_preset,
    import_color_scheme_file,
    merge_skin,
    normalize_color_token,
    parse_color_scheme,
    parse_multiline_list,
    parse_wings_text,
    unique_skin_name,
)
from .preview import render_color_preview, render_skin_preview


INPUT_TO_DRAFT = {
    "skin-name": ("name", None),
    "description": ("description", None),
    "tool-prefix": ("tool_prefix", None),
    "agent-name": ("branding", "agent_name"),
    "welcome": ("branding", "welcome"),
    "goodbye": ("branding", "goodbye"),
    "response-label": ("branding", "response_label"),
    "prompt-symbol": ("branding", "prompt_symbol"),
    "help-header": ("branding", "help_header"),
}

for color_key in COLOR_KEYS:
    INPUT_TO_DRAFT[f"color-{color_key}"] = ("colors", color_key)

for tool_key in TOOL_EMOJI_KEYS:
    INPUT_TO_DRAFT[f"tool-{tool_key}"] = ("tool_emojis", tool_key)


TEXTAREA_TO_DRAFT = {
    "spinner-waiting": ("spinner_list", "waiting_faces"),
    "spinner-thinking": ("spinner_list", "thinking_faces"),
    "spinner-verbs": ("spinner_list", "thinking_verbs"),
    "spinner-wings": ("spinner_wings", "wings"),
    "banner-logo": ("banner_logo", None),
    "banner-hero": ("banner_hero", None),
}

SELECT_DEFAULTS = {
    "palette-name": "default",
    "palette-import-mode": "auto",
    "color-target": "banner_border",
    "spinner-preset": "default",
    "logo-import-mode": "plain",
    "logo-justify": "left",
    "logo-fit": "flexible",
    "hero-style": "braille",
    "hero-import-mode": "plain",
    "hero-justify": "left",
    "hero-fit": "flexible",
}

INPUT_DEFAULTS = {
    "palette-file-path": "",
    "logo-width": "120",
    "logo-file-path": "",
    "logo-style": "standard",
    "logo-font-filter": "",
    "hero-path": "",
    "hero-width": "40",
    "hero-file-path": "",
}

TEXTAREA_DEFAULTS = {
    "palette-import": "",
    "logo-import": "",
    "hero-import": "",
}

EMOJI_ENABLED_FIELDS = {
    "agent-name",
    "welcome",
    "goodbye",
    "response-label",
    "prompt-symbol",
    "help-header",
    "tool-prefix",
    "spinner-waiting",
    "spinner-thinking",
    "spinner-verbs",
    "spinner-wings",
    "logo-title",
    "logo-import",
    "banner-logo",
    "hero-import",
    "banner-hero",
}

EMOJI_LIBRARY = {
    "Spinner": [
        ("spark", "✦"),
        ("triangle", "▲"),
        ("diamond", "◇"),
        ("focus", "⌁"),
        ("flame", "🔥"),
        ("orb", "◉"),
        ("ring", "◌"),
        ("shield", "⛨"),
        ("blade", "⚔"),
    ],
    "Wings": [
        ("left chevron", "⟪"),
        ("right chevron", "⟫"),
        ("double angle left", "«"),
        ("double angle right", "»"),
        ("thin left", "‹"),
        ("thin right", "›"),
        ("bracket left", "⟦"),
        ("bracket right", "⟧"),
    ],
    "Tools": [
        ("terminal", "⚡"),
        ("search", "🔎"),
        ("web", "🌐"),
        ("read file", "📄"),
        ("write file", "✎"),
        ("patch", "🩹"),
        ("todo", "📝"),
        ("delegate", "🔀"),
    ],
    "Prompt": [
        ("arrow", "❯"),
        ("thin arrow", "›"),
        ("soft grin", ":^) "),
        ("caduceus", "⚕"),
        ("moon", "🌙"),
        ("sparkles", "✨"),
        ("sleep", "💤"),
        ("warning", "⚠️"),
    ],
}


def _select_options(values: list[str]) -> list[tuple[str, str]]:
    return [(value, value) for value in values]


class SaveAsScreen(ModalScreen[str | None]):
    CSS = """
    SaveAsScreen {
        align: center middle;
    }

    #save-as-dialog {
        width: 60;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: round $primary;
    }
    """

    BINDINGS = [Binding("escape", "dismiss(None)", "Cancel")]

    def __init__(self, suggested_name: str) -> None:
        super().__init__()
        self.suggested_name = suggested_name

    def compose(self) -> ComposeResult:
        with Vertical(id="save-as-dialog"):
            yield Static("Save Draft As", classes="section-title")
            yield Static("Choose a custom skin name.", classes="field-label")
            yield Input(value=self.suggested_name, id="save-as-name")
            with Horizontal(classes="button-row"):
                yield Button("Save", id="save-as-confirm")
                yield Button("Cancel", id="save-as-cancel")

    def on_mount(self) -> None:
        self.query_one("#save-as-name", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "save-as-name":
            self.dismiss(event.value.strip() or None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-as-confirm":
            self.dismiss(self.query_one("#save-as-name", Input).value.strip() or None)
        elif event.button.id == "save-as-cancel":
            self.dismiss(None)


class DirtyConfirmScreen(ModalScreen[str | None]):
    CSS = """
    DirtyConfirmScreen {
        align: center middle;
    }

    #dirty-dialog {
        width: 72;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: round $warning;
    }
    """

    BINDINGS = [Binding("escape", "dismiss(None)", "Cancel")]

    def __init__(self, reason: str, save_label: str) -> None:
        super().__init__()
        self.reason = reason
        self.save_label = save_label

    def compose(self) -> ComposeResult:
        with Vertical(id="dirty-dialog"):
            yield Static("Unsaved Changes", classes="section-title")
            yield Static(self.reason, classes="field-label")
            with Horizontal(classes="button-row"):
                yield Button(self.save_label, id="dirty-save")
                yield Button("Discard", id="dirty-discard")
                yield Button("Cancel", id="dirty-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "dirty-save":
            self.dismiss("save")
        elif button_id == "dirty-discard":
            self.dismiss("discard")
        elif button_id == "dirty-cancel":
            self.dismiss(None)


class EmojiPickerScreen(ModalScreen[str | None]):
    CSS = """
    EmojiPickerScreen {
        align: center middle;
    }

    #emoji-dialog {
        width: 68;
        height: 28;
        padding: 1 2;
        background: $surface;
        border: round $primary;
    }

    #emoji-options {
        height: 1fr;
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss(None)", "Cancel"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._filtered_options: list[tuple[str, str]] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="emoji-dialog"):
            yield Static("Emoji + Symbol Picker", classes="section-title")
            yield Static("Filter or browse, then press Enter to insert.", classes="field-label")
            yield Input(id="emoji-filter", placeholder="spark, wing, tool, prompt")
            yield Select(_select_options(list(EMOJI_LIBRARY)), id="emoji-category", allow_blank=False, value="Spinner")
            yield OptionList(id="emoji-options")
            with Horizontal(classes="button-row"):
                yield Button("Insert", id="emoji-insert")
                yield Button("Cancel", id="emoji-cancel")

    def on_mount(self) -> None:
        self._refresh_options()
        self.query_one("#emoji-filter", Input).focus()

    def _refresh_options(self) -> None:
        category = str(self.query_one("#emoji-category", Select).value or "Spinner")
        filter_text = self.query_one("#emoji-filter", Input).value.strip().lower()
        options: list[tuple[str, str]] = []
        for label, token in EMOJI_LIBRARY.get(category, []):
            haystack = f"{label} {token}".lower()
            if filter_text and filter_text not in haystack:
                continue
            options.append((label, token))

        self._filtered_options = options
        widget = self.query_one("#emoji-options", OptionList)
        widget.clear_options()
        if not options:
            widget.add_options([Option("No matching symbols", id="__empty__", disabled=True)])
            widget.highlighted = 0
            return

        widget.add_options([Option(f"{token}  {label}", id=token) for label, token in options])
        widget.highlighted = 0

    def _selected_token(self) -> str | None:
        widget = self.query_one("#emoji-options", OptionList)
        highlighted = widget.highlighted
        if highlighted is None or highlighted < 0:
            return None
        option = widget.get_option_at_index(highlighted)
        if option.id == "__empty__":
            return None
        return option.id

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "emoji-filter":
            self._refresh_options()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "emoji-category":
            self._refresh_options()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id != "emoji-options":
            return
        self.dismiss(self._selected_token())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "emoji-insert":
            self.dismiss(self._selected_token())
        elif event.button.id == "emoji-cancel":
            self.dismiss(None)


class SkinwalkerApp(App[None]):
    CSS = """
    Screen {
        layout: vertical;
    }

    #main {
        height: 1fr;
    }

    #library-pane, #center-pane, #editor-pane {
        border: solid $surface;
        padding: 1;
    }

    #library-pane {
        width: 28;
    }

    #center-pane {
        width: 1fr;
        min-width: 50;
    }

    #editor-pane {
        width: 44;
    }

    #editor-tabs {
        height: 1fr;
    }

    .editor-scroll {
        height: 1fr;
        padding-right: 1;
    }

    .button-row {
        height: auto;
        margin-bottom: 1;
    }

    Button {
        margin-right: 1;
        margin-bottom: 1;
    }

    .tiny-button {
        min-width: 12;
    }

    .field-label {
        margin-top: 1;
        color: $text-muted;
    }

    .section-title {
        margin-top: 1;
        text-style: bold;
    }

    TextArea {
        height: 8;
        margin-bottom: 1;
    }

    Select {
        margin-bottom: 1;
    }

    #banner-logo, #banner-hero, #yaml-view {
        height: 12;
    }

    #palette-import, #logo-import, #hero-import {
        height: 6;
    }

    #spinner-waiting, #spinner-thinking, #spinner-verbs, #spinner-wings {
        height: 6;
    }

    #logo-font-list, #emoji-options {
        height: 10;
        margin-bottom: 1;
    }

    #status {
        height: auto;
        padding: 0 1;
        color: $text-muted;
    }

    #meta {
        margin-bottom: 1;
    }

    #preview {
        padding: 1;
    }

    #color-preview {
        height: auto;
        margin-bottom: 1;
    }
    """

    TITLE = "Skinwalker"
    SUB_TITLE = "Hermes Skin Studio"
    BINDINGS = [
        Binding("f2", "save_skin", "Save"),
        Binding("f3", "activate_skin", "Activate"),
        Binding("f4", "new_skin", "New"),
        Binding("f5", "generate_logo", "Logo"),
        Binding("f6", "generate_hero", "Hero"),
        Binding("f7", "refresh_library", "Refresh"),
        Binding("ctrl+e", "pick_emoji", "Emoji"),
    ]

    def __init__(self, hermes_root: str | Path | None = None) -> None:
        super().__init__()
        self.bridge = HermesBridge(hermes_root=hermes_root)
        self.default_skin = self.bridge.load_skin("default", source="builtin")
        self.library_entries: list[LibraryEntry] = []
        self.current_source = "user"
        self.current_name = ""
        self.draft = blank_skin()
        self.reference_draft = deepcopy(self.draft)
        self.dirty = False
        self._populating_form = False
        self._emoji_target_id = ""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main"):
            with Vertical(id="library-pane"):
                yield Static("", id="meta")
                yield OptionList(id="skin-list")
                with Horizontal(classes="button-row"):
                    yield Button("New", id="new")
                    yield Button("Clone", id="clone")
                    yield Button("Refresh", id="refresh")
                    yield Button("Delete", id="delete")
            with Vertical(id="center-pane"):
                with Horizontal(classes="button-row"):
                    yield Button("Save", id="save")
                    yield Button("Save As", id="save-as")
                    yield Button("Activate", id="activate")
                    yield Button("Emoji", id="pick-emoji")
                    yield Button("Logo", id="generate-logo")
                    yield Button("Hero", id="generate-hero")
                with TabbedContent(initial="preview-tab"):
                    with TabPane("Preview", id="preview-tab"):
                        yield Static(id="preview")
                    with TabPane("YAML", id="yaml-tab"):
                        yield TextArea("", id="yaml-view", read_only=True)
            with Vertical(id="editor-pane"):
                with TabbedContent(id="editor-tabs", initial="identity-tab"):
                    with TabPane("Identity", id="identity-tab"):
                        with VerticalScroll(classes="editor-scroll"):
                            yield Static("Skin", classes="section-title")
                            yield Static("Skin name", classes="field-label")
                            yield Input(id="skin-name", placeholder="custom-skin")
                            yield Static("Description", classes="field-label")
                            yield Input(id="description", placeholder="Short description")
                            with Horizontal(classes="button-row"):
                                yield Button("Clear Focused", id="clear-focused", classes="tiny-button")
                                yield Button("Reset Focused", id="reset-focused", classes="tiny-button")
                            yield Static("Branding", classes="section-title")
                            for widget_id, label, placeholder in [
                                ("agent-name", "Agent name", "Hermes Agent"),
                                ("welcome", "Welcome", "Ready when you are."),
                                ("goodbye", "Goodbye", "Goodbye."),
                                ("response-label", "Response label", " Hermes "),
                                ("prompt-symbol", "Prompt symbol", "› "),
                                ("help-header", "Help header", "Commands"),
                            ]:
                                yield Static(label, classes="field-label")
                                yield Input(id=widget_id, placeholder=placeholder)
                            yield Static("Tools", classes="section-title")
                            yield Static("Tool prefix", classes="field-label")
                            yield Input(id="tool-prefix", placeholder="┊")
                            for tool_key in TOOL_EMOJI_KEYS:
                                yield Static(f"{tool_key} emoji", classes="field-label")
                                yield Input(id=f"tool-{tool_key}", placeholder="")
                    with TabPane("Colors", id="colors-tab"):
                        with VerticalScroll(classes="editor-scroll"):
                            yield Static("Colors", classes="section-title")
                            yield Static(f"Palettes: {', '.join(sorted(COLOR_PRESETS))}", classes="field-label")
                            yield Select(_select_options(sorted(COLOR_PRESETS)), id="palette-name", allow_blank=False, value="default")
                            with Horizontal(classes="button-row"):
                                yield Button("Apply Palette", id="apply-palette")
                            yield Static("", id="color-preview")
                            yield Static("Import colorscheme mode", classes="field-label")
                            yield Select(_select_options(PALETTE_IMPORT_MODE_OPTIONS), id="palette-import-mode", allow_blank=False, value="auto")
                            yield Static("Import colorscheme file", classes="field-label")
                            yield Input(id="palette-file-path", placeholder="~/Downloads/palette.yaml")
                            with Horizontal(classes="button-row"):
                                yield Button("Import Palette Text", id="import-palette-text")
                                yield Button("Import Palette File", id="import-palette-file")
                            yield Static("Import colorscheme text", classes="field-label")
                            yield TextArea("", id="palette-import")
                            yield Static("Color tool target", classes="field-label")
                            yield Select(_select_options(COLOR_KEYS), id="color-target", allow_blank=False, value="banner_border")
                            yield Static("Color tool value", classes="field-label")
                            yield Input(id="color-tool-value", placeholder="#8EA3FF")
                            with Horizontal(classes="button-row"):
                                yield Button("Apply Color", id="apply-color-tool")
                                yield Button("Sync", id="sync-color-tool")
                            with Horizontal(classes="button-row"):
                                yield Button("Lighter", id="color-lighter")
                                yield Button("Darker", id="color-darker")
                                yield Button("Warmer", id="color-warmer")
                                yield Button("Cooler", id="color-cooler")
                            with Horizontal(classes="button-row"):
                                yield Button("Saturate+", id="color-saturate-up")
                                yield Button("Saturate-", id="color-saturate-down")
                            for color_key in COLOR_KEYS:
                                yield Static(color_key, classes="field-label")
                                yield Input(id=f"color-{color_key}", placeholder="#RRGGBB")
                    with TabPane("Spinner", id="spinner-tab"):
                        with VerticalScroll(classes="editor-scroll"):
                            yield Static("Spinner", classes="section-title")
                            yield Static("Preset shelf", classes="field-label")
                            yield Select(_select_options(sorted(SPINNER_PRESETS)), id="spinner-preset", allow_blank=False, value="default")
                            with Horizontal(classes="button-row"):
                                yield Button("Apply Spinner Preset", id="apply-spinner-preset")
                            yield Static("Waiting faces", classes="field-label")
                            yield TextArea("", id="spinner-waiting")
                            yield Static("Thinking faces", classes="field-label")
                            yield TextArea("", id="spinner-thinking")
                            yield Static("Thinking verbs", classes="field-label")
                            yield TextArea("", id="spinner-verbs")
                            yield Static("Wings (left | right)", classes="field-label")
                            yield TextArea("", id="spinner-wings")
                    with TabPane("Art", id="art-tab"):
                        with VerticalScroll(classes="editor-scroll"):
                            yield Static("Logo Generator", classes="section-title")
                            yield Static("Logo generator title", classes="field-label")
                            yield Input(id="logo-title", placeholder="Skinwalker")
                            yield Static("Logo generator width", classes="field-label")
                            yield Input(id="logo-width", placeholder="120")
                            yield Static("Current font", classes="field-label")
                            yield Input(id="logo-style", placeholder="standard")
                            yield Static("Font browser filter", classes="field-label")
                            yield Input(id="logo-font-filter", placeholder="standard, slant, doom")
                            yield Static("Font browser", classes="field-label")
                            yield OptionList(id="logo-font-list")
                            yield Static("Logo justification", classes="field-label")
                            yield Select(_select_options(JUSTIFY_OPTIONS), id="logo-justify", allow_blank=False, value="left")
                            yield Static("Logo width mode", classes="field-label")
                            yield Select(_select_options(FIT_MODE_OPTIONS), id="logo-fit", allow_blank=False, value="flexible")
                            with Horizontal(classes="button-row"):
                                yield Button("Generate Logo", id="generate-logo")
                                yield Button("Clear Logo", id="clear-logo", classes="tiny-button")
                            yield Static("Logo import mode", classes="field-label")
                            yield Select(_select_options(IMPORT_MODE_OPTIONS), id="logo-import-mode", allow_blank=False, value="plain")
                            yield Static("Logo file path", classes="field-label")
                            yield Input(id="logo-file-path", placeholder="~/art/logo.txt")
                            with Horizontal(classes="button-row"):
                                yield Button("Import Logo Text", id="import-logo-text")
                                yield Button("Import Logo File", id="import-logo-file")
                            yield Static("Logo import text", classes="field-label")
                            yield TextArea("", id="logo-import")
                            yield Static("Banner logo markup", classes="field-label")
                            yield TextArea("", id="banner-logo")
                            yield Static("Hero Generator", classes="section-title")
                            yield Static("Hero image path", classes="field-label")
                            yield Input(id="hero-path", placeholder="~/Pictures/hero.png")
                            yield Static("Hero style", classes="field-label")
                            yield Select(_select_options(sorted(HERO_STYLE_MAP)), id="hero-style", allow_blank=False, value="braille")
                            yield Static("Hero width", classes="field-label")
                            yield Input(id="hero-width", placeholder="40")
                            yield Static("Hero justification", classes="field-label")
                            yield Select(_select_options(JUSTIFY_OPTIONS), id="hero-justify", allow_blank=False, value="left")
                            yield Static("Hero width mode", classes="field-label")
                            yield Select(_select_options(FIT_MODE_OPTIONS), id="hero-fit", allow_blank=False, value="flexible")
                            with Horizontal(classes="button-row"):
                                yield Button("Generate Hero", id="generate-hero")
                                yield Button("Clear Hero", id="clear-hero", classes="tiny-button")
                            yield Static("Hero import mode", classes="field-label")
                            yield Select(_select_options(IMPORT_MODE_OPTIONS), id="hero-import-mode", allow_blank=False, value="plain")
                            yield Static("Hero art file path", classes="field-label")
                            yield Input(id="hero-file-path", placeholder="~/art/hero.txt")
                            with Horizontal(classes="button-row"):
                                yield Button("Import Hero Text", id="import-hero-text")
                                yield Button("Import Hero File", id="import-hero-file")
                            yield Static("Hero import text", classes="field-label")
                            yield TextArea("", id="hero-import")
                            yield Static("Banner hero markup", classes="field-label")
                            yield TextArea("", id="banner-hero")
        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.action_refresh_library()
        self._refresh_logo_font_browser()
        self.query_one("#skin-list", OptionList).focus()

    def _set_status(self, text: str) -> None:
        self.query_one("#status", Static).update(text)

    def _existing_names(self) -> set[str]:
        return {entry.name for entry in self.library_entries}

    def _refresh_logo_font_browser(self) -> None:
        filter_value = self.query_one("#logo-font-filter", Input).value.strip().lower()
        current_font = self.query_one("#logo-style", Input).value.strip() or INPUT_DEFAULTS["logo-style"]
        options = []
        for font_name in list_logo_fonts():
            if filter_value and filter_value not in font_name.lower():
                continue
            options.append(Option(font_name, id=font_name))

        widget = self.query_one("#logo-font-list", OptionList)
        widget.clear_options()
        if not options:
            widget.add_options([Option("No matching fonts", id="__empty__", disabled=True)])
            widget.highlighted = 0
            return

        widget.add_options(options)
        target_index = next((index for index, option in enumerate(options) if option.id == current_font), 0)
        widget.highlighted = target_index

    def _apply_color_mapping(self, colors: dict[str, str], *, origin: str) -> None:
        self.draft.setdefault("colors", {}).update(colors)
        self.dirty = True
        self._populate_form_from_draft()
        self._refresh_preview()
        self._set_status(origin)

    def _focused_text_widget_id(self) -> str:
        focused = self.screen.focused
        widget_id = getattr(focused, "id", "") or ""
        if not widget_id:
            return ""
        if widget_id.startswith("tool-"):
            return widget_id
        if widget_id in EMOJI_ENABLED_FIELDS:
            return widget_id
        return ""

    def _insert_symbol(self, widget_id: str, token: str) -> None:
        if not token:
            return
        if widget_id in INPUT_TO_DRAFT or widget_id in INPUT_DEFAULTS or widget_id == "logo-title":
            widget = self.query_one(f"#{widget_id}", Input)
            widget.insert_text_at_cursor(token)
            return
        if widget_id in TEXTAREA_TO_DRAFT or widget_id in TEXTAREA_DEFAULTS:
            widget = self.query_one(f"#{widget_id}", TextArea)
            widget.insert(token)
            return
        raise ValueError(f"Unsupported emoji target: {widget_id}")

    def _snapshot_reference_draft(self) -> None:
        self.reference_draft = deepcopy(self.draft)

    def _draft_value_for_widget(self, widget_id: str, source: dict) -> str:
        if widget_id in INPUT_TO_DRAFT:
            section, key = INPUT_TO_DRAFT[widget_id]
            if section in {"name", "description", "tool_prefix"}:
                return str(source.get(section, ""))
            return str((source.get(section) or {}).get(key, ""))

        if widget_id in TEXTAREA_TO_DRAFT:
            section, key = TEXTAREA_TO_DRAFT[widget_id]
            if section == "spinner_list":
                return format_multiline_list((source.get("spinner") or {}).get(key, []))
            if section == "spinner_wings":
                return format_wings_text((source.get("spinner") or {}).get(key, []))
            return str(source.get(section, ""))

        return ""

    def _control_default_value(self, widget_id: str) -> str:
        if widget_id == "logo-title":
            return (
                str((self.reference_draft.get("branding") or {}).get("agent_name", "")).strip()
                or str(self.reference_draft.get("name", "")).strip()
            )
        if widget_id in INPUT_DEFAULTS:
            return INPUT_DEFAULTS[widget_id]
        if widget_id in SELECT_DEFAULTS:
            return SELECT_DEFAULTS[widget_id]
        if widget_id in TEXTAREA_DEFAULTS:
            return TEXTAREA_DEFAULTS[widget_id]
        return ""

    def _reset_widget_value(self, widget_id: str) -> bool:
        if widget_id in INPUT_TO_DRAFT:
            self.query_one(f"#{widget_id}", Input).value = self._draft_value_for_widget(widget_id, self.reference_draft)
            return True
        if widget_id in TEXTAREA_TO_DRAFT:
            self.query_one(f"#{widget_id}", TextArea).load_text(self._draft_value_for_widget(widget_id, self.reference_draft))
            return True
        if widget_id in SELECT_DEFAULTS:
            self.query_one(f"#{widget_id}", Select).value = self._control_default_value(widget_id)
            return True
        if widget_id in INPUT_DEFAULTS or widget_id == "logo-title":
            self.query_one(f"#{widget_id}", Input).value = self._control_default_value(widget_id)
            return True
        if widget_id in TEXTAREA_DEFAULTS:
            self.query_one(f"#{widget_id}", TextArea).load_text(self._control_default_value(widget_id))
            return True
        return False

    def _clear_widget_value(self, widget_id: str) -> bool:
        if widget_id in INPUT_TO_DRAFT or widget_id in INPUT_DEFAULTS or widget_id == "logo-title":
            self.query_one(f"#{widget_id}", Input).value = ""
            return True
        if widget_id in TEXTAREA_TO_DRAFT or widget_id in TEXTAREA_DEFAULTS:
            self.query_one(f"#{widget_id}", TextArea).load_text("")
            return True
        if widget_id in SELECT_DEFAULTS:
            self.query_one(f"#{widget_id}", Select).value = self._control_default_value(widget_id)
            return True
        return False

    def _update_meta(self) -> None:
        active = self.bridge.get_active_skin_name()
        source = self.current_source or "-"
        dirty_marker = "unsaved" if self.dirty else "saved"
        draft_name = str(self.draft.get("name", "")).strip() or "(unnamed)"
        self.query_one("#meta", Static).update(
            "\n".join(
                [
                    f"Active: {active}",
                    f"Hermes: {self.bridge.hermes_home}",
                    f"Draft: {draft_name}",
                    f"Source: {source}",
                    f"State: {dirty_marker}",
                ]
            )
        )

    def _refresh_library_widget(self, selected_name: str | None = None) -> None:
        self.library_entries = self.bridge.list_skins()
        active = self.bridge.get_active_skin_name()
        prompts = []

        for entry in self.library_entries:
            active_marker = "*" if entry.name == active else " "
            source = "builtin" if entry.source == "builtin" else "custom"
            prompts.append(f"{active_marker} {entry.name} [{source}] {entry.description}")

        widget = self.query_one("#skin-list", OptionList)
        widget.clear_options()
        widget.add_options(prompts)

        if not self.library_entries:
            return

        target_name = selected_name or self.current_name or active
        index = next((i for i, entry in enumerate(self.library_entries) if entry.name == target_name), 0)
        widget.highlighted = index

    def _load_entry(self, entry: LibraryEntry) -> None:
        self.current_source = entry.source
        self.current_name = entry.name
        self.draft = self.bridge.load_skin(entry.name, source=entry.source)
        self._snapshot_reference_draft()
        self.dirty = False
        self._populate_form_from_draft()
        self._refresh_preview()
        self._set_status(f"Loaded {entry.source} skin {entry.name}")

    def _populate_form_from_draft(self) -> None:
        self._populating_form = True
        draft = self.draft

        def set_input(widget_id: str, value: str) -> None:
            self.query_one(f"#{widget_id}", Input).value = value

        def set_textarea(widget_id: str, value: str) -> None:
            self.query_one(f"#{widget_id}", TextArea).load_text(value)

        def set_select(widget_id: str, value: str) -> None:
            self.query_one(f"#{widget_id}", Select).value = value

        set_input("skin-name", draft.get("name", ""))
        set_input("description", draft.get("description", ""))
        set_input("tool-prefix", draft.get("tool_prefix", "┊"))

        branding = draft.get("branding", {})
        set_input("agent-name", branding.get("agent_name", ""))
        set_input("welcome", branding.get("welcome", ""))
        set_input("goodbye", branding.get("goodbye", ""))
        set_input("response-label", branding.get("response_label", ""))
        set_input("prompt-symbol", branding.get("prompt_symbol", ""))
        set_input("help-header", branding.get("help_header", ""))

        colors = draft.get("colors", {})
        set_select("palette-name", "default")
        set_select("palette-import-mode", SELECT_DEFAULTS["palette-import-mode"])
        set_select("color-target", "banner_border")
        set_input("color-tool-value", colors.get("banner_border", "#8EA3FF"))
        set_input("palette-file-path", INPUT_DEFAULTS["palette-file-path"])
        set_textarea("palette-import", TEXTAREA_DEFAULTS["palette-import"])
        for color_key in COLOR_KEYS:
            set_input(f"color-{color_key}", colors.get(color_key, ""))

        spinner = draft.get("spinner", {})
        set_select("spinner-preset", SELECT_DEFAULTS["spinner-preset"])
        set_textarea("spinner-waiting", format_multiline_list(spinner.get("waiting_faces", [])))
        set_textarea("spinner-thinking", format_multiline_list(spinner.get("thinking_faces", [])))
        set_textarea("spinner-verbs", format_multiline_list(spinner.get("thinking_verbs", [])))
        set_textarea("spinner-wings", format_wings_text(spinner.get("wings", [])))

        tool_emojis = draft.get("tool_emojis", {})
        for tool_key in TOOL_EMOJI_KEYS:
            set_input(f"tool-{tool_key}", tool_emojis.get(tool_key, ""))

        set_input("logo-title", branding.get("agent_name") or draft.get("name", ""))
        set_input("logo-width", INPUT_DEFAULTS["logo-width"])
        set_input("logo-style", INPUT_DEFAULTS["logo-style"])
        set_input("logo-font-filter", INPUT_DEFAULTS["logo-font-filter"])
        set_select("logo-justify", SELECT_DEFAULTS["logo-justify"])
        set_select("logo-fit", SELECT_DEFAULTS["logo-fit"])
        set_select("logo-import-mode", SELECT_DEFAULTS["logo-import-mode"])
        set_input("logo-file-path", "")
        set_textarea("logo-import", "")
        set_textarea("banner-logo", draft.get("banner_logo", ""))

        set_input("hero-path", "")
        set_select("hero-style", SELECT_DEFAULTS["hero-style"])
        set_input("hero-width", INPUT_DEFAULTS["hero-width"])
        set_select("hero-justify", SELECT_DEFAULTS["hero-justify"])
        set_select("hero-fit", SELECT_DEFAULTS["hero-fit"])
        set_select("hero-import-mode", SELECT_DEFAULTS["hero-import-mode"])
        set_input("hero-file-path", "")
        set_textarea("hero-import", "")
        set_textarea("banner-hero", draft.get("banner_hero", ""))

        self._populating_form = False
        self._refresh_logo_font_browser()
        self._update_meta()

    def _refresh_preview(self) -> None:
        preview_skin = merge_skin(self.default_skin, self.draft)
        preview_error: str | None = None

        try:
            preview_renderable = render_skin_preview(preview_skin)
        except Exception as exc:
            preview_renderable = render_skin_preview(self.default_skin)
            preview_error = str(exc)

        try:
            color_renderable = render_color_preview(preview_skin.get("colors", {}))
        except Exception as exc:
            color_renderable = render_color_preview(self.default_skin.get("colors", {}))
            preview_error = preview_error or str(exc)

        try:
            yaml_text = self.bridge.dump_skin_yaml(preview_skin, strict=False)
        except Exception as exc:
            yaml_text = f"# Preview unavailable\n# {exc}\n"
            preview_error = preview_error or str(exc)

        self.query_one("#preview", Static).update(preview_renderable)
        self.query_one("#color-preview", Static).update(color_renderable)
        self.query_one("#yaml-view", TextArea).load_text(yaml_text)
        self._update_meta()
        if preview_error:
            self._set_status(f"Preview recovered from invalid draft state: {preview_error}")

    def _apply_input_change(self, widget_id: str, value: str) -> None:
        if widget_id not in INPUT_TO_DRAFT:
            return
        section, key = INPUT_TO_DRAFT[widget_id]

        if section in {"name", "description", "tool_prefix"}:
            if self.draft.get(section, "") == value:
                return
            self.draft[section] = value
        else:
            self.draft.setdefault(section, {})
            if self.draft[section].get(key, "") == value:
                return
            self.draft[section][key] = value

        self.dirty = True
        self._refresh_preview()

    def _apply_textarea_change(self, widget_id: str, value: str) -> None:
        if widget_id not in TEXTAREA_TO_DRAFT:
            return

        section, key = TEXTAREA_TO_DRAFT[widget_id]
        if section == "spinner_list":
            parsed = parse_multiline_list(value)
            if self.draft.setdefault("spinner", {}).get(key, []) == parsed:
                return
            self.draft.setdefault("spinner", {})
            self.draft["spinner"][key] = parsed
        elif section == "spinner_wings":
            parsed = parse_wings_text(value)
            if self.draft.setdefault("spinner", {}).get(key, []) == parsed:
                return
            self.draft.setdefault("spinner", {})
            self.draft["spinner"][key] = parsed
        else:
            if self.draft.get(section, "") == value:
                return
            self.draft[section] = value

        self.dirty = True
        self._refresh_preview()

    def _set_art_field(self, field_name: str, widget_id: str, markup: str) -> None:
        self.draft[field_name] = markup
        self.query_one(f"#{widget_id}", TextArea).load_text(markup)
        self.dirty = True
        self._refresh_preview()

    def _logo_color(self) -> str:
        return normalize_color_token(self.draft.get("colors", {}).get("banner_title", "#8EA3FF"), "#8EA3FF")

    def _hero_color(self) -> str:
        return normalize_color_token(self.draft.get("colors", {}).get("banner_accent", "#8EA3FF"), "#8EA3FF")

    def _can_save_directly(self) -> bool:
        name = str(self.draft.get("name", "")).strip()
        return bool(name) and self.current_source == "user" and name not in self.bridge.builtin_names

    def _suggest_save_as_name(self) -> str:
        base_name = str(self.draft.get("name", "")).strip() or "custom-skin"
        if self.current_source == "builtin" or base_name in self.bridge.builtin_names:
            base_name = f"{base_name}-custom"
        return unique_skin_name(self._existing_names(), base_name)

    def _save_current_skin(self, *, name_override: str | None = None) -> bool:
        original_name = self.draft.get("name", "")
        if name_override is not None:
            self.draft["name"] = name_override

        try:
            path = self.bridge.save_skin(self.draft)
        except Exception as exc:
            if name_override is not None:
                self.draft["name"] = original_name
            self._set_status(f"Save failed: {exc}")
            return False

        self.current_source = "user"
        self.current_name = self.draft["name"]
        self._snapshot_reference_draft()
        self.dirty = False
        self._refresh_library_widget(selected_name=self.current_name)
        self._refresh_preview()
        self._set_status(f"Saved {self.current_name} to {path}")
        return True

    def _open_save_as_screen(self, after_save: Callable[[], None] | None = None) -> None:
        suggested = self._suggest_save_as_name()
        self.push_screen(
            SaveAsScreen(suggested),
            callback=lambda result: self._handle_save_as_result(result, after_save),
        )

    def _handle_save_as_result(self, result: str | None, after_save: Callable[[], None] | None) -> None:
        if not result:
            return
        if self._save_current_skin(name_override=result) and after_save is not None:
            after_save()

    def _guard_dirty_replace(self, reason: str, continue_fn: Callable[[], None]) -> None:
        if not self.dirty:
            continue_fn()
            return

        save_label = "Save" if self._can_save_directly() else "Save As"
        self.push_screen(
            DirtyConfirmScreen(reason, save_label),
            callback=lambda result: self._handle_dirty_resolution(result, continue_fn),
        )

    def _handle_dirty_resolution(self, result: str | None, continue_fn: Callable[[], None]) -> None:
        if result == "discard":
            continue_fn()
        elif result == "save":
            if self._can_save_directly():
                if self._save_current_skin():
                    continue_fn()
            else:
                self._open_save_as_screen(after_save=continue_fn)

    def _activate_current_skin(self) -> None:
        try:
            self.bridge.activate_skin(self.draft["name"])
            self._refresh_library_widget(selected_name=self.draft["name"])
            self._update_meta()
            self._set_status(f"Activated {self.draft['name']}")
        except Exception as exc:
            self._set_status(f"Activate failed: {exc}")

    def _sync_color_tool(self) -> None:
        target = str(self.query_one("#color-target", Select).value)
        if target not in COLOR_KEYS:
            self._set_status(f"Unknown color target: {target}")
            return
        current = self.draft.get("colors", {}).get(target, "#8EA3FF")
        self.query_one("#color-tool-value", Input).value = current

    def _apply_color_to_target(self, color_value: str) -> None:
        target = str(self.query_one("#color-target", Select).value)
        if target not in COLOR_KEYS:
            self._set_status(f"Unknown color target: {target}")
            return

        normalized = normalize_color_token(color_value, "")
        if not normalized:
            self._set_status(f"Invalid color value: {color_value}")
            return

        self.draft.setdefault("colors", {})[target] = normalized
        self.query_one(f"#color-{target}", Input).value = normalized
        self.query_one("#color-tool-value", Input).value = normalized
        self.dirty = True
        self._refresh_preview()
        self._set_status(f"Updated {target} to {normalized}")

    def _adjust_target_color(self, *, hue_shift: float = 0.0, lightness_shift: float = 0.0, saturation_shift: float = 0.0) -> None:
        value = self.query_one("#color-tool-value", Input).value.strip()
        try:
            adjusted = adjust_color(
                value,
                hue_shift=hue_shift,
                lightness_shift=lightness_shift,
                saturation_shift=saturation_shift,
            )
        except Exception as exc:
            self._set_status(f"Color adjust failed: {exc}")
            return
        self._apply_color_to_target(adjusted)

    def action_apply_palette(self) -> None:
        palette_name = str(self.query_one("#palette-name", Select).value) or "default"
        try:
            palette = get_color_preset(palette_name)
        except Exception as exc:
            self._set_status(f"Palette failed: {exc}")
            return

        self._apply_color_mapping(palette, origin=f"Applied palette {palette_name}")
        self.query_one("#palette-name", Select).value = palette_name

    def action_import_palette_text(self) -> None:
        mode = str(self.query_one("#palette-import-mode", Select).value) or "auto"
        text = self.query_one("#palette-import", TextArea).text
        try:
            colors = parse_color_scheme(text, mode=mode)
        except Exception as exc:
            self._set_status(f"Palette import failed: {exc}")
            return

        self._apply_color_mapping(colors, origin=f"Imported colorscheme from text ({mode})")

    def action_import_palette_file(self) -> None:
        mode = str(self.query_one("#palette-import-mode", Select).value) or "auto"
        path = self.query_one("#palette-file-path", Input).value.strip()
        try:
            colors = import_color_scheme_file(path, mode=mode)
        except Exception as exc:
            self._set_status(f"Palette file import failed: {exc}")
            return

        self._apply_color_mapping(colors, origin=f"Imported colorscheme file ({mode})")

    def action_apply_spinner_preset(self) -> None:
        preset_name = str(self.query_one("#spinner-preset", Select).value) or "default"
        try:
            spinner = get_spinner_preset(preset_name)
        except Exception as exc:
            self._set_status(f"Spinner preset failed: {exc}")
            return

        self.draft["spinner"] = spinner
        self.dirty = True
        self._populate_form_from_draft()
        self._refresh_preview()
        self.query_one("#spinner-preset", Select).value = preset_name
        self._set_status(f"Applied spinner preset {preset_name}")

    def action_import_logo_text(self) -> None:
        mode = str(self.query_one("#logo-import-mode", Select).value) or "plain"
        text = self.query_one("#logo-import", TextArea).text
        try:
            markup = import_art_text(text, self._logo_color(), mode=mode, bold=(mode.strip().lower() != "markup"))
        except Exception as exc:
            self._set_status(f"Logo import failed: {exc}")
            return

        self._set_art_field("banner_logo", "banner-logo", markup)
        self._set_status(f"Imported logo text as {mode}")

    def action_import_logo_file(self) -> None:
        mode = str(self.query_one("#logo-import-mode", Select).value) or "plain"
        path = self.query_one("#logo-file-path", Input).value.strip()
        try:
            markup = import_art_file(path, self._logo_color(), mode=mode, bold=(mode.strip().lower() != "markup"))
        except Exception as exc:
            self._set_status(f"Logo file import failed: {exc}")
            return

        self._set_art_field("banner_logo", "banner-logo", markup)
        self._set_status(f"Imported logo file as {mode}")

    def action_import_hero_text(self) -> None:
        mode = str(self.query_one("#hero-import-mode", Select).value) or "plain"
        text = self.query_one("#hero-import", TextArea).text
        try:
            markup = import_art_text(text, self._hero_color(), mode=mode)
        except Exception as exc:
            self._set_status(f"Hero import failed: {exc}")
            return

        self._set_art_field("banner_hero", "banner-hero", markup)
        self._set_status(f"Imported hero text as {mode}")

    def action_import_hero_file(self) -> None:
        mode = str(self.query_one("#hero-import-mode", Select).value) or "plain"
        path = self.query_one("#hero-file-path", Input).value.strip()
        try:
            markup = import_art_file(path, self._hero_color(), mode=mode)
        except Exception as exc:
            self._set_status(f"Hero file import failed: {exc}")
            return

        self._set_art_field("banner_hero", "banner-hero", markup)
        self._set_status(f"Imported hero file as {mode}")

    def action_pick_emoji(self) -> None:
        target_id = self._focused_text_widget_id()
        if not target_id:
            self._set_status("Focus an emoji-aware text field first")
            return

        self._emoji_target_id = target_id
        self.push_screen(EmojiPickerScreen(), callback=self._handle_emoji_pick)

    def _handle_emoji_pick(self, token: str | None) -> None:
        if not token or not self._emoji_target_id:
            self._emoji_target_id = ""
            return

        try:
            self._insert_symbol(self._emoji_target_id, token)
        except Exception as exc:
            self._set_status(f"Insert failed: {exc}")
        else:
            self._set_status(f"Inserted {token} into {self._emoji_target_id}")
        finally:
            self._emoji_target_id = ""

    def on_input_changed(self, event: Input.Changed) -> None:
        if self._populating_form or not event.input.id:
            return
        if event.input.id == "color-tool-value":
            return
        if event.input.id in {"logo-font-filter", "logo-style"}:
            self._refresh_logo_font_browser()
            return
        self._apply_input_change(event.input.id, event.value)
        if event.input.id.startswith("color-") and event.input.id[6:] == str(self.query_one("#color-target", Select).value):
            self.query_one("#color-tool-value", Input).value = event.value

    def on_select_changed(self, event: Select.Changed) -> None:
        if self._populating_form or not event.select.id:
            return
        if event.select.id == "color-target":
            self._sync_color_tool()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if self._populating_form or not event.text_area.id:
            return
        self._apply_textarea_change(event.text_area.id, event.text_area.text)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_index is None:
            return
        if event.option_list.id == "logo-font-list":
            option = event.option_list.get_option_at_index(event.option_index)
            if option.id and option.id != "__empty__":
                self.query_one("#logo-style", Input).value = option.id
                self._set_status(f"Selected logo font {option.id}")
            return
        entry = self.library_entries[event.option_index]
        if entry.name == self.current_name and entry.source == self.current_source:
            return
        self._guard_dirty_replace(
            f"Open {entry.name} and discard current unsaved changes?",
            lambda: self._load_entry(entry),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "new":
            self.action_new_skin()
        elif button_id == "clone":
            self.action_clone_skin()
        elif button_id == "refresh":
            self.action_refresh_library()
        elif button_id == "delete":
            self.action_delete_skin()
        elif button_id == "apply-palette":
            self.action_apply_palette()
        elif button_id == "import-palette-text":
            self.action_import_palette_text()
        elif button_id == "import-palette-file":
            self.action_import_palette_file()
        elif button_id == "apply-color-tool":
            self._apply_color_to_target(self.query_one("#color-tool-value", Input).value.strip())
        elif button_id == "sync-color-tool":
            self._sync_color_tool()
        elif button_id == "color-lighter":
            self._adjust_target_color(lightness_shift=0.08)
        elif button_id == "color-darker":
            self._adjust_target_color(lightness_shift=-0.08)
        elif button_id == "color-warmer":
            self._adjust_target_color(hue_shift=-0.03)
        elif button_id == "color-cooler":
            self._adjust_target_color(hue_shift=0.03)
        elif button_id == "color-saturate-up":
            self._adjust_target_color(saturation_shift=0.08)
        elif button_id == "color-saturate-down":
            self._adjust_target_color(saturation_shift=-0.08)
        elif button_id == "apply-spinner-preset":
            self.action_apply_spinner_preset()
        elif button_id == "clear-focused":
            focused = self.screen.focused
            if focused is None or not getattr(focused, "id", None) or not self._clear_widget_value(focused.id):
                self._set_status("Focus a supported field to clear it")
            else:
                self._set_status(f"Cleared {focused.id}")
        elif button_id == "reset-focused":
            focused = self.screen.focused
            if focused is None or not getattr(focused, "id", None) or not self._reset_widget_value(focused.id):
                self._set_status("Focus a supported field to reset it")
            else:
                self._set_status(f"Reset {focused.id}")
        elif button_id == "pick-emoji":
            self.action_pick_emoji()
        elif button_id == "save":
            self.action_save_skin()
        elif button_id == "save-as":
            self._open_save_as_screen()
        elif button_id == "activate":
            self.action_activate_skin()
        elif button_id == "generate-logo":
            self.action_generate_logo()
        elif button_id == "clear-logo":
            self._set_art_field("banner_logo", "banner-logo", "")
            self._set_status("Cleared logo art")
        elif button_id == "import-logo-text":
            self.action_import_logo_text()
        elif button_id == "import-logo-file":
            self.action_import_logo_file()
        elif button_id == "generate-hero":
            self.action_generate_hero()
        elif button_id == "clear-hero":
            self._set_art_field("banner_hero", "banner-hero", "")
            self._set_status("Cleared hero art")
        elif button_id == "import-hero-text":
            self.action_import_hero_text()
        elif button_id == "import-hero-file":
            self.action_import_hero_file()

    def action_refresh_library(self) -> None:
        self._refresh_library_widget(selected_name=self.current_name or self.bridge.get_active_skin_name())
        if not self.current_name and self.library_entries:
            active = self.bridge.get_active_skin_name()
            entry = next((entry for entry in self.library_entries if entry.name == active), self.library_entries[0])
            self._load_entry(entry)
        else:
            self._update_meta()

    def action_new_skin(self) -> None:
        def create_new() -> None:
            existing = self._existing_names()
            name = unique_skin_name(existing, "custom-skin")
            self.current_source = "user"
            self.current_name = name
            self.draft = blank_skin(name)
            self._snapshot_reference_draft()
            self.dirty = True
            self._populate_form_from_draft()
            self._refresh_preview()
            self._set_status(f"Created draft {name}")

        self._guard_dirty_replace("Create a new draft and discard current unsaved changes?", create_new)

    def action_clone_skin(self) -> None:
        def clone_current() -> None:
            existing = self._existing_names()
            base_name = f"{self.draft.get('name', 'custom-skin')}-copy"
            new_name = unique_skin_name(existing, base_name)
            self.current_source = "user"
            self.current_name = new_name
            self.draft = merge_skin(self.default_skin, self.draft)
            self.draft["name"] = new_name
            self.draft["description"] = (self.draft.get("description", "") or "Cloned skin").strip()
            self._snapshot_reference_draft()
            self.dirty = True
            self._populate_form_from_draft()
            self._refresh_preview()
            self._set_status(f"Cloned draft to {new_name}")

        self._guard_dirty_replace("Clone into a new draft and discard current unsaved changes?", clone_current)

    def action_save_skin(self) -> None:
        if self._can_save_directly():
            self._save_current_skin()
        else:
            self._open_save_as_screen()

    def action_activate_skin(self) -> None:
        if self.dirty:
            if self._can_save_directly():
                if self._save_current_skin():
                    self._activate_current_skin()
            else:
                self._open_save_as_screen(after_save=self._activate_current_skin)
        else:
            self._activate_current_skin()

    def action_delete_skin(self) -> None:
        if self.current_source == "builtin":
            self._set_status("Built-in skins cannot be deleted")
            return

        try:
            self.bridge.delete_skin(self.draft["name"])
        except Exception as exc:
            self._set_status(f"Delete failed: {exc}")
            return

        self._set_status(f"Deleted {self.draft['name']}")
        self.current_name = ""
        self.action_refresh_library()

    def action_generate_logo(self) -> None:
        title = (
            self.query_one("#logo-title", Input).value.strip()
            or self.query_one("#agent-name", Input).value.strip()
            or self.draft.get("name", "").strip()
            or "logo"
        )
        width_text = self.query_one("#logo-width", Input).value.strip() or INPUT_DEFAULTS["logo-width"]
        style = self.query_one("#logo-style", Input).value.strip() or INPUT_DEFAULTS["logo-style"]
        justify = str(self.query_one("#logo-justify", Select).value) or SELECT_DEFAULTS["logo-justify"]
        fit = str(self.query_one("#logo-fit", Select).value) or SELECT_DEFAULTS["logo-fit"]
        color = self._logo_color()

        try:
            markup = generate_logo_markup(title, style, color, width=int(width_text), justify=justify, fit=fit)
        except Exception as exc:
            self._set_status(f"Logo generation failed: {exc}")
            return

        self._set_art_field("banner_logo", "banner-logo", markup)
        self._set_status(f"Generated logo using {style} at width {width_text} ({justify}, {fit})")

    def action_generate_hero(self) -> None:
        image_path = self.query_one("#hero-path", Input).value.strip()
        style = str(self.query_one("#hero-style", Select).value) or SELECT_DEFAULTS["hero-style"]
        width_text = self.query_one("#hero-width", Input).value.strip() or INPUT_DEFAULTS["hero-width"]
        justify = str(self.query_one("#hero-justify", Select).value) or SELECT_DEFAULTS["hero-justify"]
        fit = str(self.query_one("#hero-fit", Select).value) or SELECT_DEFAULTS["hero-fit"]
        color = self._hero_color()

        try:
            result = generate_hero_markup(image_path, style, int(width_text), color, justify=justify, fit=fit)
        except Exception as exc:
            self._set_status(f"Hero generation failed: {exc}")
            return

        self._set_art_field("banner_hero", "banner-hero", result.markup)
        self._set_status(f"Generated {result.style} hero art at {result.width}x{result.height} ({justify}, {fit})")
