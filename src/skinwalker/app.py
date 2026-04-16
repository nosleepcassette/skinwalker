from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Callable

from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, OptionList, Select, Static, TabPane, TabbedContent, TextArea
from textual.widgets.option_list import Option

from .ai import (
    backend_options,
    discover_backends,
    generate_branding_bundle,
    generate_hero_bundle,
    generate_logo_bundle,
    generate_skin_bundle,
    generate_spinner_bundle,
)
from .art import (
    HERO_STYLE_MAP,
    _export_ascii_png,
    _export_markup_text,
    generate_hero_markup,
    generate_logo_result,
    import_art_file,
    import_art_text,
    list_logo_fonts,
)
from .fonts import filter_fonts, font_category_label, font_category_options, font_meta
from .hermes import HermesBridge, LibraryEntry
from .history import DraftHistory
from .model import (
    COLOR_KEY_LABELS,
    COLOR_KEYS,
    COLOR_PRESETS,
    FIT_MODE_OPTIONS,
    FIGLET_STYLE_MAP,
    IMPORT_MODE_OPTIONS,
    JUSTIFY_OPTIONS,
    PALETTE_IMPORT_MODE_OPTIONS,
    SKIN_IMPORT_MODE_OPTIONS,
    SPINNER_PRESETS,
    TOOL_EMOJI_KEYS,
    blank_skin,
    adjust_color,
    format_multiline_list,
    format_wings_text,
    get_color_preset,
    get_spinner_preset,
    import_color_scheme_file,
    import_skin_yaml_file,
    merge_skin,
    normalize_color_token,
    parse_color_scheme,
    parse_skin_yaml,
    parse_multiline_list,
    sanitize_skin_name,
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
    "profile-target": "default",
    "ai-backend": "hermes",
    "palette-name": "default",
    "palette-import-mode": "auto",
    "color-target": "banner_border",
    "spinner-preset": "default",
    "yaml-import-mode": "replace",
    "logo-import-mode": "plain",
    "logo-font-category": "all",
    "logo-justify": "left",
    "logo-fit": "flexible",
    "hero-style": "braille",
    "hero-dither": "none",
    "hero-invert": "off",
    "hero-import-mode": "plain",
    "hero-justify": "left",
    "hero-fit": "flexible",
    "hero-edge": "off",
}

INPUT_DEFAULTS = {
    "yaml-file-path": "",
    "palette-file-path": "",
    "logo-width": "120",
    "logo-file-path": "",
    "logo-export-path": "",
    "logo-export-png-path": "",
    "logo-style": "standard",
    "logo-font-filter": "",
    "hero-path": "",
    "hero-width": "40",
    "hero-brightness": "100",
    "hero-contrast": "100",
    "hero-saturation": "1.0",
    "hero-hue-shift": "0.0",
    "hero-grayscale": "100",
    "hero-sepia": "0.0",
    "hero-threshold": "",
    "hero-sharpen": "100",
    "hero-space-density": "0.0",
    "hero-padding": "0",
    "hero-file-path": "",
    "hero-export-text-path": "",
    "hero-export-path": "",
}

TEXTAREA_DEFAULTS = {
    "ai-direction": "",
    "ai-output": "",
    "yaml-import": "",
    "palette-import": "",
    "logo-import": "",
    "hero-import": "",
}

TRANSIENT_SELECT_IDS = {
    "profile-target",
    "ai-backend",
    "yaml-import-mode",
    "palette-name",
    "palette-import-mode",
    "color-target",
    "spinner-preset",
    "logo-import-mode",
    "logo-font-category",
    "logo-justify",
    "logo-fit",
    "hero-style",
    "hero-dither",
    "hero-invert",
    "hero-import-mode",
    "hero-justify",
    "hero-fit",
    "hero-edge",
}

TRANSIENT_INPUT_IDS = {
    "yaml-file-path",
    "palette-file-path",
    "color-tool-value",
    "logo-title",
    "logo-width",
    "logo-file-path",
    "logo-export-path",
    "logo-export-png-path",
    "logo-style",
    "logo-font-filter",
    "hero-path",
    "hero-width",
    "hero-brightness",
    "hero-contrast",
    "hero-saturation",
    "hero-hue-shift",
    "hero-grayscale",
    "hero-sepia",
    "hero-threshold",
    "hero-sharpen",
    "hero-space-density",
    "hero-padding",
    "hero-file-path",
    "hero-export-text-path",
    "hero-export-path",
}

TRANSIENT_TEXTAREA_IDS = {
    "ai-direction",
    "yaml-import",
    "palette-import",
    "logo-import",
    "hero-import",
}

MODIFIED_TRANSIENT_SELECT_IDS = {
    "profile-target",
    "ai-backend",
    "yaml-import-mode",
    "palette-import-mode",
    "logo-import-mode",
    "logo-font-category",
    "logo-justify",
    "logo-fit",
    "hero-style",
    "hero-dither",
    "hero-invert",
    "hero-import-mode",
    "hero-justify",
    "hero-fit",
    "hero-edge",
}

MODIFIED_TRANSIENT_INPUT_IDS = {
    "yaml-file-path",
    "palette-file-path",
    "color-tool-value",
    "logo-title",
    "logo-width",
    "logo-file-path",
    "logo-export-path",
    "logo-export-png-path",
    "logo-style",
    "logo-font-filter",
    "hero-path",
    "hero-width",
    "hero-brightness",
    "hero-contrast",
    "hero-saturation",
    "hero-hue-shift",
    "hero-grayscale",
    "hero-sepia",
    "hero-threshold",
    "hero-sharpen",
    "hero-space-density",
    "hero-padding",
    "hero-file-path",
    "hero-export-text-path",
    "hero-export-path",
}

MODIFIED_TRANSIENT_TEXTAREA_IDS = {
    "ai-direction",
    "yaml-import",
    "palette-import",
    "logo-import",
    "hero-import",
}

WING_INPUT_PREFIXES = ("spinner-wing-left-", "spinner-wing-right-")
SPINNER_PREVIEW_DOT_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
SPINNER_PREVIEW_INTERVAL = 0.12
SPINNER_PREVIEW_PHASE_SECONDS = 3.0
SPINNER_PREVIEW_PHASE_FRAMES = max(1, round(SPINNER_PREVIEW_PHASE_SECONDS / SPINNER_PREVIEW_INTERVAL))

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


def build_spinner_preview_snapshot(draft: dict) -> dict[str, object]:
    colors = draft.get("colors") or {}
    spinner = draft.get("spinner") or {}
    wings = [
        [str(pair[0]), str(pair[1])]
        for pair in spinner.get("wings", [])
        if isinstance(pair, (list, tuple)) and len(pair) == 2
    ]

    return {
        "ui_accent": normalize_color_token(colors.get("ui_accent", "#8EA3FF"), "#8EA3FF"),
        "banner_text": normalize_color_token(colors.get("banner_text", "#DCE4FF"), "#DCE4FF"),
        "waiting_faces": [str(item) for item in spinner.get("waiting_faces", []) if str(item).strip()] or list(SPINNER_PREVIEW_DOT_FRAMES),
        "thinking_faces": [str(item) for item in spinner.get("thinking_faces", []) if str(item).strip()] or list(SPINNER_PREVIEW_DOT_FRAMES),
        "thinking_verbs": [str(item) for item in spinner.get("thinking_verbs", []) if str(item).strip()] or ["thinking"],
        "wings": wings,
    }


def render_spinner_preview_frame(snapshot: dict[str, object], frame_index: int) -> Text:
    ui_accent = str(snapshot.get("ui_accent", "#8EA3FF"))
    banner_text = str(snapshot.get("banner_text", "#DCE4FF"))
    waiting_faces = list(snapshot.get("waiting_faces", [])) or list(SPINNER_PREVIEW_DOT_FRAMES)
    thinking_faces = list(snapshot.get("thinking_faces", [])) or list(SPINNER_PREVIEW_DOT_FRAMES)
    thinking_verbs = list(snapshot.get("thinking_verbs", [])) or ["thinking"]
    wings = list(snapshot.get("wings", []))

    phase_index = frame_index // SPINNER_PREVIEW_PHASE_FRAMES
    phase_frame = frame_index % SPINNER_PREVIEW_PHASE_FRAMES
    waiting_phase = phase_index % 2 == 0

    faces = waiting_faces if waiting_phase else thinking_faces
    face = str(faces[phase_frame % len(faces)]) if faces else SPINNER_PREVIEW_DOT_FRAMES[phase_frame % len(SPINNER_PREVIEW_DOT_FRAMES)]
    left, right = ("", "")
    if wings:
        pair = wings[phase_frame % len(wings)]
        if len(pair) == 2:
            left, right = str(pair[0]), str(pair[1])

    rendered = Text()
    if left:
        rendered.append(f"{left} ", style=ui_accent)
    rendered.append(face, style=f"bold {ui_accent}")
    rendered.append(" ", style=ui_accent)

    if waiting_phase:
        rendered.append("⚡ running a tool", style=banner_text)
        if right:
            rendered.append(f" {right}", style=ui_accent)
        rendered.append(f" ({phase_frame * SPINNER_PREVIEW_INTERVAL:.1f}s)", style=banner_text)
        return rendered

    verb = str(thinking_verbs[phase_frame % len(thinking_verbs)]) if thinking_verbs else "thinking"
    rendered.append(f"{verb}...", style=banner_text)
    if right:
        rendered.append(f" {right}", style=ui_accent)
    return rendered


class PreviewSpinnerModal(ModalScreen[None]):
    CSS = """
    PreviewSpinnerModal {
        align: center middle;
    }

    #spinner-preview-dialog {
        width: 84;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: round $primary;
    }

    #spinner-preview-line {
        margin: 1 0;
        padding: 1;
        border: solid $surface;
    }
    """

    BINDINGS = [Binding("escape", "dismiss(None)", "Close")]

    def __init__(self, draft: dict) -> None:
        super().__init__()
        self.snapshot = build_spinner_preview_snapshot(deepcopy(draft))
        self._frame_index = 0
        self._timer = None

    def compose(self) -> ComposeResult:
        with Vertical(id="spinner-preview-dialog"):
            yield Static("Live Spinner Preview", classes="section-title")
            yield Static("Snapshot from the current draft.", classes="field-label")
            yield Static(id="spinner-preview-line")
            with Horizontal(classes="button-row"):
                yield Button("Stop", id="spinner-preview-stop")

    def on_mount(self) -> None:
        self._render_frame()
        self._timer = self.set_interval(SPINNER_PREVIEW_INTERVAL, self._advance_frame)

    def on_unmount(self) -> None:
        if self._timer is not None:
            self._timer.stop()

    def _advance_frame(self) -> None:
        self._frame_index += 1
        self._render_frame()

    def _render_frame(self) -> None:
        self.query_one("#spinner-preview-line", Static).update(render_spinner_preview_frame(self.snapshot, self._frame_index))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "spinner-preview-stop":
            self.dismiss(None)


class WingPairEditor(Vertical):
    DEFAULT_CSS = """
    WingPairEditor {
        border: round $surface;
        padding: 1;
        margin-bottom: 1;
        height: auto;
    }

    WingPairEditor.modified {
        border: round $warning;
    }

    WingPairEditor .wing-row {
        height: auto;
        margin-bottom: 1;
    }

    WingPairEditor .wing-input {
        width: 1fr;
    }

    WingPairEditor .wing-separator {
        width: 3;
        content-align: center middle;
        color: $text-muted;
    }

    WingPairEditor #spinner-wings-rows {
        height: auto;
        max-height: 10;
    }

    WingPairEditor #spinner-wings-preview {
        color: $text-muted;
        margin-bottom: 1;
    }
    """

    class Changed(Message):
        def __init__(self, wings: list[list[str]]) -> None:
            super().__init__()
            self.wings = deepcopy(wings)

    def __init__(self, wings: list[list[str]] | None = None, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._wings = self._normalize_wings(wings or [])

    @staticmethod
    def _normalize_wings(wings: list[list[str]]) -> list[list[str]]:
        return [
            [str(pair[0]), str(pair[1])]
            for pair in wings
            if isinstance(pair, (list, tuple)) and len(pair) == 2
        ]

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="spinner-wings-rows"):
            for index, (left, right) in enumerate(self._wings):
                with Horizontal(classes="wing-row"):
                    yield Input(value=left, placeholder="left", id=f"spinner-wing-left-{index}", classes="wing-input")
                    yield Static("|", classes="wing-separator")
                    yield Input(value=right, placeholder="right", id=f"spinner-wing-right-{index}", classes="wing-input")
                    yield Button("×", id=f"spinner-wing-delete-{index}", classes="tiny-button")
        yield Static(self._preview_text(), id="spinner-wings-preview")
        yield Button("+ add pair", id="spinner-wing-add")

    def _preview_text(self) -> Text:
        if not self._wings:
            return Text("Preview: add a pair to see it here")
        left, right = self._wings[0]
        return Text.assemble(
            ("Preview: ", ""),
            (left or "⟨left⟩", "bold"),
            (" ", ""),
            ("◐", "bold"),
            (" ", ""),
            (right or "⟨right⟩", "bold"),
        )

    def get_wings(self) -> list[list[str]]:
        return deepcopy(self._wings)

    def set_wings(self, wings: list[list[str]]) -> None:
        self._wings = self._normalize_wings(wings)
        if self.is_mounted:
            self.refresh(recompose=True)

    def _update_preview(self) -> None:
        self.query_one("#spinner-wings-preview", Static).update(self._preview_text())

    def _post_changed(self) -> None:
        self.post_message(self.Changed(self.get_wings()))

    def on_input_changed(self, event: Input.Changed) -> None:
        widget_id = event.input.id or ""
        if widget_id.startswith("spinner-wing-left-"):
            index = int(widget_id.removeprefix("spinner-wing-left-"))
            self._wings[index][0] = event.value
        elif widget_id.startswith("spinner-wing-right-"):
            index = int(widget_id.removeprefix("spinner-wing-right-"))
            self._wings[index][1] = event.value
        else:
            return

        self._update_preview()
        self._post_changed()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id == "spinner-wing-add":
            self._wings.append(["", ""])
            self.refresh(recompose=True)
            self._post_changed()
            return

        if not button_id.startswith("spinner-wing-delete-"):
            return

        index = int(button_id.removeprefix("spinner-wing-delete-"))
        if 0 <= index < len(self._wings):
            del self._wings[index]
            self.refresh(recompose=True)
            self._post_changed()


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

    Input.modified, TextArea.modified, Select.modified {
        border: solid $warning;
    }

    Select {
        margin-bottom: 1;
    }

    #banner-logo, #banner-hero {
        height: 12;
    }

    #yaml-view {
        height: 10;
    }

    #yaml-import, #palette-import, #logo-import, #hero-import {
        height: 6;
    }

    #ai-direction {
        height: 6;
    }

    #ai-output {
        height: 10;
    }

    #spinner-waiting, #spinner-thinking, #spinner-verbs {
        height: 6;
    }

    #logo-font-list, #emoji-options {
        height: 10;
        margin-bottom: 1;
    }

    #logo-font-meta {
        height: auto;
        margin-bottom: 1;
    }

    #logo-font-preview {
        height: auto;
        padding: 1;
        border: solid $surface;
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
        Binding("ctrl+z", "undo", "Undo"),
        Binding("ctrl+y", "redo", "Redo"),
        Binding("ctrl+shift+a", "select_focused", "Select"),
        Binding("ctrl+l", "clear_focused", "Clear"),
        Binding("ctrl+shift+r", "reset_focused", "Reset"),
        Binding("ctrl+e", "pick_emoji", "Emoji"),
    ]

    def __init__(self, hermes_root: str | Path | None = None) -> None:
        super().__init__()
        self.bridge = HermesBridge(hermes_root=hermes_root)
        self.default_skin = (
            self.bridge.load_skin("default", source="builtin")
            if "default" in self.bridge.builtin_names
            else blank_skin("default")
        )
        self.ai_backends = discover_backends() or ["hermes"]
        self.library_entries: list[LibraryEntry] = []
        self.current_source = "user"
        self.current_name = ""
        self.draft = blank_skin()
        self.reference_draft = deepcopy(self.draft)
        self.dirty = False
        self._populating_form = False
        self._emoji_target_id = ""
        self._history = DraftHistory()
        self._restoring_history = False
        self._preview_show_logo: bool = True
        self._preview_show_hero: bool = True
        self._preview_compact: bool = False
        self._preview_native: bool = False
        self._preview_live_logo: bool = False

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
                with Horizontal(classes="button-row"):
                    yield Button("Fork Built-in", id="fork-builtin")
                    yield Button("Delete", id="delete")
            with Vertical(id="center-pane"):
                with Horizontal(classes="button-row"):
                    yield Button("Save", id="save")
                    yield Button("Save As", id="save-as")
                    yield Button("Activate in Hermes", id="activate")
                    yield Button("Undo", id="undo")
                    yield Button("Redo", id="redo")
                    yield Select(
                        _select_options(self.bridge.list_profiles()),
                        id="profile-target",
                        allow_blank=False,
                        value=self.bridge.current_profile_name(),
                    )
                    yield Button("Emoji", id="pick-emoji")
                    yield Button("Logo", id="generate-logo")
                    yield Button("Hero", id="generate-hero")
                with Horizontal(classes="button-row"):
                    yield Button("Logo: on", id="toggle-logo", classes="tiny-button")
                    yield Button("Hero: on", id="toggle-hero", classes="tiny-button")
                    yield Button("Compact: off", id="toggle-compact", classes="tiny-button")
                    yield Button("Native colors: off", id="toggle-native", classes="tiny-button")
                with TabbedContent(initial="preview-tab"):
                    with TabPane("Preview", id="preview-tab"):
                        yield Static(id="preview")
                    with TabPane("YAML", id="yaml-tab"):
                        yield TextArea("", id="yaml-view", read_only=True)
                        yield Static("YAML import mode", classes="field-label")
                        yield Select(_select_options(SKIN_IMPORT_MODE_OPTIONS), id="yaml-import-mode", allow_blank=False, value="replace")
                        yield Static("YAML file path", classes="field-label")
                        yield Input(id="yaml-file-path", placeholder="~/Downloads/skin.yaml")
                        with Horizontal(classes="button-row"):
                            yield Button("Import YAML Text", id="import-yaml-text")
                            yield Button("Import YAML File", id="import-yaml-file")
                            yield Button("Export YAML File", id="export-yaml-file")
                        yield Static("YAML import text", classes="field-label")
                        yield TextArea("", id="yaml-import")
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
                                yield Button("Select Focused", id="select-focused", classes="tiny-button")
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
                            yield Select(
                                [(COLOR_KEY_LABELS.get(k, k), k) for k in COLOR_KEYS],
                                id="color-target",
                                allow_blank=False,
                                value="banner_border",
                            )
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
                            yield Static("Preview options", classes="section-title")
                            with Horizontal(classes="button-row"):
                                yield Button("Logo: on", id="colors-toggle-logo", classes="tiny-button")
                                yield Button("Hero: on", id="colors-toggle-hero", classes="tiny-button")
                                yield Button("Compact: off", id="colors-toggle-compact", classes="tiny-button")
                                yield Button("Native colors: off", id="colors-toggle-native", classes="tiny-button")
                            for color_key in COLOR_KEYS:
                                yield Static(COLOR_KEY_LABELS.get(color_key, color_key), classes="field-label")
                                yield Input(id=f"color-{color_key}", placeholder="#RRGGBB")
                    with TabPane("Spinner", id="spinner-tab"):
                        with VerticalScroll(classes="editor-scroll"):
                            yield Static("Spinner", classes="section-title")
                            yield Static("Preset shelf", classes="field-label")
                            with Horizontal(classes="button-row"):
                                yield Select(_select_options(sorted(SPINNER_PRESETS)), id="spinner-preset", allow_blank=False, value="default")
                                yield Button("Preview Spinner", id="preview-spinner")
                                yield Button("Apply Spinner Preset", id="apply-spinner-preset")
                            yield Static("Waiting faces", classes="field-label")
                            yield TextArea("", id="spinner-waiting")
                            yield Static("Thinking faces", classes="field-label")
                            yield TextArea("", id="spinner-thinking")
                            yield Static("Thinking verbs", classes="field-label")
                            yield TextArea("", id="spinner-verbs")
                            yield Static("Wing pairs", classes="field-label")
                            yield WingPairEditor(id="spinner-wings")
                    with TabPane("Art", id="art-tab"):
                        with VerticalScroll(classes="editor-scroll"):
                            yield Static("Logo Generator", classes="section-title")
                            yield Static("Logo generator title", classes="field-label")
                            yield Input(id="logo-title", placeholder="Skinwalker")
                            yield Static("Logo generator width", classes="field-label")
                            yield Input(id="logo-width", placeholder="120")
                            yield Static("Current font", classes="field-label")
                            yield Input(id="logo-style", placeholder="standard")
                            yield Static("Font category", classes="field-label")
                            yield Select(font_category_options(), id="logo-font-category", allow_blank=False, value="all")
                            yield Static("Font browser filter", classes="field-label")
                            yield Input(id="logo-font-filter", placeholder="slanted, retro, block, script")
                            yield Static("Font browser", classes="field-label")
                            yield OptionList(id="logo-font-list")
                            yield Static("", id="logo-font-meta")
                            yield Static("Live logo preview appears in the Preview tab while logo controls are focused.", id="logo-font-preview")
                            yield Static("Logo justification", classes="field-label")
                            yield Select(_select_options(JUSTIFY_OPTIONS), id="logo-justify", allow_blank=False, value="left")
                            yield Static("Logo width mode", classes="field-label")
                            yield Select(_select_options(FIT_MODE_OPTIONS), id="logo-fit", allow_blank=False, value="flexible")
                            with Horizontal(classes="button-row"):
                                yield Button("Generate Logo", id="generate-logo")
                                yield Button("Clear Logo", id="clear-logo", classes="tiny-button")
                            yield Static("Logo export TXT path", classes="field-label")
                            yield Input(id="logo-export-path", placeholder="~/art/logo.txt")
                            yield Static("Logo export PNG path", classes="field-label")
                            yield Input(id="logo-export-png-path", placeholder="~/art/logo.png")
                            with Horizontal(classes="button-row"):
                                yield Button("Export Logo TXT", id="export-logo-text")
                                yield Button("Export Logo PNG", id="export-logo-png")
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
                            yield Static("Image Lab", classes="section-title")
                            yield Static("Hero image path", classes="field-label")
                            yield Input(id="hero-path", placeholder="~/Pictures/hero.png")
                            with Horizontal(classes="button-row"):
                                yield Button("Open Imagewalker", id="launch-imagewalker")
                            yield Static("Character set", classes="field-label")
                            yield Select(_select_options(sorted(HERO_STYLE_MAP)), id="hero-style", allow_blank=False, value="braille")
                            yield Static("Dither algorithm", classes="field-label")
                            yield Select(
                                [("None", "none"), ("Floyd-Steinberg", "floyd-steinberg"), ("Atkinson", "atkinson"), ("JJN", "jjn"), ("Stucki", "stucki")],
                                id="hero-dither",
                                allow_blank=False,
                                value="none",
                            )
                            yield Static("Hero width", classes="field-label")
                            yield Input(id="hero-width", placeholder="40")
                            yield Static("Hero brightness %", classes="field-label")
                            yield Input(id="hero-brightness", placeholder="100")
                            yield Static("Hero contrast %", classes="field-label")
                            yield Input(id="hero-contrast", placeholder="100")
                            yield Static("Saturation", classes="field-label")
                            yield Input(id="hero-saturation", placeholder="1.0")
                            yield Static("Hue shift (0-360°)", classes="field-label")
                            yield Input(id="hero-hue-shift", placeholder="0.0")
                            yield Static("Grayscale %", classes="field-label")
                            yield Input(id="hero-grayscale", placeholder="100")
                            yield Static("Sepia (0-1.0)", classes="field-label")
                            yield Input(id="hero-sepia", placeholder="0.0")
                            yield Static("Hero invert", classes="field-label")
                            yield Select(_select_options(["off", "on"]), id="hero-invert", allow_blank=False, value="off")
                            yield Static("Hero threshold (blank = off)", classes="field-label")
                            yield Input(id="hero-threshold", placeholder="")
                            yield Static("Hero sharpen %", classes="field-label")
                            yield Input(id="hero-sharpen", placeholder="100")
                            yield Static("Hero edge blend", classes="field-label")
                            yield Select(_select_options(["off", "on"]), id="hero-edge", allow_blank=False, value="off")
                            yield Static("Space density (-1.0-1.0)", classes="field-label")
                            yield Input(id="hero-space-density", placeholder="0.0")
                            yield Static("Output padding (lines)", classes="field-label")
                            yield Input(id="hero-padding", placeholder="0")
                            yield Static("Hero justification", classes="field-label")
                            yield Select(_select_options(JUSTIFY_OPTIONS), id="hero-justify", allow_blank=False, value="left")
                            yield Static("Hero width mode", classes="field-label")
                            yield Select(_select_options(FIT_MODE_OPTIONS), id="hero-fit", allow_blank=False, value="flexible")
                            with Horizontal(classes="button-row"):
                                yield Button("Generate Hero", id="generate-hero")
                                yield Button("Clear Hero", id="clear-hero", classes="tiny-button")
                            yield Static("Hero export TXT path", classes="field-label")
                            yield Input(id="hero-export-text-path", placeholder="~/art/hero.txt")
                            with Horizontal(classes="button-row"):
                                yield Button("Export Hero TXT", id="export-hero-text")
                            yield Static("Hero export PNG path", classes="field-label")
                            yield Input(id="hero-export-path", placeholder="~/art/hero.png")
                            with Horizontal(classes="button-row"):
                                yield Button("Export Hero PNG", id="export-hero-png")
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
                    with TabPane("AI", id="ai-tab"):
                        with VerticalScroll(classes="editor-scroll"):
                            yield Static("AI Studio", classes="section-title")
                            yield Static("Backend", classes="field-label")
                            yield Select(
                                backend_options(self.ai_backends),
                                id="ai-backend",
                                allow_blank=False,
                                value=self.ai_backends[0],
                            )
                            yield Static("", id="ai-backend-note")
                            yield Static("Creative direction", classes="field-label")
                            yield TextArea("", id="ai-direction")
                            with Horizontal(classes="button-row"):
                                yield Button("AI Branding", id="ai-branding")
                                yield Button("AI Spinner", id="ai-spinner")
                                yield Button("AI Logo", id="ai-logo")
                                yield Button("AI Hero", id="ai-hero")
                            with Horizontal(classes="button-row"):
                                yield Button("AI Bundle", id="ai-bundle")
                            yield Static("Last AI payload", classes="field-label")
                            yield TextArea("", id="ai-output", read_only=True)
        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self._populate_form_from_draft()
        self._refresh_preview()
        self.action_refresh_library()
        self._refresh_profile_targets()
        self._refresh_ai_backend_note()
        self._refresh_logo_font_browser()
        self.query_one("#skin-list", OptionList).focus()

    def _set_status(self, text: str) -> None:
        self.query_one("#status", Static).update(text)

    def _existing_names(self) -> set[str]:
        return {entry.name for entry in self.library_entries}

    def _selected_profile_target(self) -> str:
        return str(self.query_one("#profile-target", Select).value or SELECT_DEFAULTS["profile-target"])

    def _selected_ai_backend(self) -> str:
        return str(self.query_one("#ai-backend", Select).value or self.ai_backends[0])

    def _float_input(self, widget_id: str, default: float) -> float:
        try:
            return float(self.query_one(f"#{widget_id}", Input).value.strip())
        except (ValueError, AttributeError):
            return default

    def _int_input(self, widget_id: str, default: int) -> int:
        try:
            return int(self.query_one(f"#{widget_id}", Input).value.strip())
        except (ValueError, AttributeError):
            return default

    def _toast(self, text: str) -> None:
        try:
            self.notify(text)
        except Exception:
            pass
        self._set_status(text)

    def _ai_direction(self) -> str:
        return self.query_one("#ai-direction", TextArea).text.strip()

    def _refresh_ai_backend_note(self) -> None:
        detected = ", ".join(label for label, _ in backend_options(self.ai_backends))
        selected = self._selected_ai_backend()
        note = f"Detected: {detected or 'none'} | Selected: {selected}"
        self.query_one("#ai-backend-note", Static).update(note)

    def _refresh_profile_targets(self) -> None:
        widget = self.query_one("#profile-target", Select)
        current = self._selected_profile_target() if widget.value is not None else self.bridge.current_profile_name()
        profiles = self.bridge.list_profiles()
        widget.set_options(_select_options(profiles))
        widget.value = current if current in profiles else profiles[0]

    def _update_action_buttons(self) -> None:
        activate_button = self.query_one("#activate", Button)
        fork_button = self.query_one("#fork-builtin", Button)

        try:
            sanitize_skin_name(str(self.draft.get("name", "")).strip())
        except Exception:
            activate_button.disabled = True
        else:
            activate_button.disabled = False

        fork_button.display = self.current_source == "builtin"
        fork_button.disabled = self.current_source != "builtin"

    def _draft_modified_count(self) -> int:
        count = 0
        for widget_id in INPUT_TO_DRAFT:
            if self._draft_value_for_widget(widget_id, self.draft) != self._draft_value_for_widget(widget_id, self.reference_draft):
                count += 1
        for widget_id in TEXTAREA_TO_DRAFT:
            if self._draft_value_for_widget(widget_id, self.draft) != self._draft_value_for_widget(widget_id, self.reference_draft):
                count += 1
        return count

    def _sync_widget_modified_class(self, widget_id: str, modified: bool) -> None:
        widget = self.query_one(f"#{widget_id}")
        if modified:
            widget.add_class("modified")
        else:
            widget.remove_class("modified")

    def _sync_modified_indicators(self) -> None:
        for widget_id in INPUT_TO_DRAFT:
            modified = self._draft_value_for_widget(widget_id, self.draft) != self._draft_value_for_widget(widget_id, self.reference_draft)
            self._sync_widget_modified_class(widget_id, modified)

        for widget_id in TEXTAREA_TO_DRAFT:
            modified = self._draft_value_for_widget(widget_id, self.draft) != self._draft_value_for_widget(widget_id, self.reference_draft)
            self._sync_widget_modified_class(widget_id, modified)

        for widget_id in MODIFIED_TRANSIENT_INPUT_IDS:
            current = self.query_one(f"#{widget_id}", Input).value
            default = self._control_default_value(widget_id)
            self._sync_widget_modified_class(widget_id, current != default)

        for widget_id in MODIFIED_TRANSIENT_SELECT_IDS:
            if widget_id == "profile-target":
                modified = self._selected_profile_target() != self.bridge.current_profile_name()
            else:
                current = str(self.query_one(f"#{widget_id}", Select).value or self._control_default_value(widget_id))
                modified = current != self._control_default_value(widget_id)
            self._sync_widget_modified_class(widget_id, modified)

        for widget_id in MODIFIED_TRANSIENT_TEXTAREA_IDS:
            current = self.query_one(f"#{widget_id}", TextArea).text
            default = self._control_default_value(widget_id)
            self._sync_widget_modified_class(widget_id, current != default)

    def _capture_history_state(self) -> dict:
        transient_inputs = {
            widget_id: self.query_one(f"#{widget_id}", Input).value
            for widget_id in TRANSIENT_INPUT_IDS
        }
        transient_selects = {
            widget_id: str(self.query_one(f"#{widget_id}", Select).value or self._control_default_value(widget_id))
            for widget_id in TRANSIENT_SELECT_IDS
        }
        transient_textareas = {
            widget_id: self.query_one(f"#{widget_id}", TextArea).text
            for widget_id in TRANSIENT_TEXTAREA_IDS
        }
        return {
            "draft": deepcopy(self.draft),
            "reference_draft": deepcopy(self.reference_draft),
            "current_source": self.current_source,
            "current_name": self.current_name,
            "dirty": self.dirty,
            "profile_target": self._selected_profile_target(),
            "inputs": transient_inputs,
            "selects": transient_selects,
            "textareas": transient_textareas,
        }

    def _reset_history(self, label: str) -> None:
        self._history.reset(self._capture_history_state(), label=label)

    def _record_history(self, label: str) -> None:
        if self._populating_form or self._restoring_history:
            return
        self._history.record(self._capture_history_state(), label=label)

    def _apply_history_state(self, state: dict) -> None:
        self._restoring_history = True
        self.current_source = str(state.get("current_source", self.current_source))
        self.current_name = str(state.get("current_name", self.current_name))
        self.draft = deepcopy(state.get("draft", self.draft))
        self.reference_draft = deepcopy(state.get("reference_draft", self.reference_draft))
        self.dirty = bool(state.get("dirty", self.dirty))
        self._populate_form_from_draft()

        profile_target = str(state.get("profile_target", self.bridge.current_profile_name()))
        profile_widget = self.query_one("#profile-target", Select)
        if profile_target in self.bridge.list_profiles():
            profile_widget.value = profile_target

        for widget_id, value in state.get("inputs", {}).items():
            self.query_one(f"#{widget_id}", Input).value = str(value)
        for widget_id, value in state.get("selects", {}).items():
            if widget_id == "profile-target":
                continue
            self.query_one(f"#{widget_id}", Select).value = str(value)
        for widget_id, value in state.get("textareas", {}).items():
            self.query_one(f"#{widget_id}", TextArea).load_text(str(value))

        self._refresh_ai_backend_note()
        self._refresh_logo_font_browser()
        self._refresh_preview()
        self._restoring_history = False

    def _refresh_logo_font_preview(self) -> None:
        try:
            result = self._current_logo_result()
        except Exception as exc:
            meta_text = f"Preview unavailable: {exc}"
            preview_renderable: Text | str = Text("Focus the logo controls to preview the rendered banner in the Preview tab.")
        else:
            meta = font_meta(result.font)
            meta_text = (
                f"Font: {result.font} | Category: {font_category_label(meta.category)} | "
                f"Tags: {', '.join(font_category_label(tag) for tag in meta.tags)} | Size: {result.width}x{result.height}"
            )
            preview_renderable = Text("Live logo preview is rendered in the main Preview tab.")

        self.query_one("#logo-font-meta", Static).update(meta_text)
        self.query_one("#logo-font-preview", Static).update(preview_renderable)

    def _refresh_logo_font_browser(self) -> None:
        filter_value = self.query_one("#logo-font-filter", Input).value.strip().lower()
        category = str(self.query_one("#logo-font-category", Select).value or "all")
        current_font = self.query_one("#logo-style", Input).value.strip() or INPUT_DEFAULTS["logo-style"]
        options = [Option(font_name, id=font_name) for font_name in filter_fonts(list_logo_fonts(), category=category, query=filter_value)]

        widget = self.query_one("#logo-font-list", OptionList)
        widget.clear_options()
        if not options:
            widget.add_options([Option("No matching fonts", id="__empty__", disabled=True)])
            widget.highlighted = 0
            self.query_one("#logo-font-meta", Static).update("No matching fonts")
            self.query_one("#logo-font-preview", Static).update(Text(""))
            return

        widget.add_options(options)
        target_index = next((index for index, option in enumerate(options) if option.id == current_font), 0)
        widget.highlighted = target_index
        highlighted = widget.get_option_at_index(target_index)
        if highlighted.id and highlighted.id != "__empty__":
            self.query_one("#logo-style", Input).value = highlighted.id
        self._refresh_logo_font_preview()

    def _current_logo_result(self):
        title = (
            self.query_one("#logo-title", Input).value.strip()
            or self.query_one("#agent-name", Input).value.strip()
            or self.draft.get("name", "").strip()
            or "logo"
        )
        width_text = self.query_one("#logo-width", Input).value.strip() or INPUT_DEFAULTS["logo-width"]
        style = self.query_one("#logo-style", Input).value.strip() or INPUT_DEFAULTS["logo-style"]
        justify = str(self.query_one("#logo-justify", Select).value or SELECT_DEFAULTS["logo-justify"])
        fit = str(self.query_one("#logo-fit", Select).value or SELECT_DEFAULTS["logo-fit"])
        return generate_logo_result(title, style, self._logo_color(), width=int(width_text), justify=justify, fit=fit)

    def _logo_preview_active(self) -> bool:
        return self._preview_live_logo

    def _apply_color_mapping(self, colors: dict[str, str], *, origin: str) -> None:
        self.draft.setdefault("colors", {}).update(colors)
        for key, value in colors.items():
            if key in COLOR_KEYS:
                self.query_one(f"#color-{key}", Input).value = value
        self._sync_color_tool()
        self.dirty = True
        self._refresh_preview()
        self._record_history(origin)
        self._set_status(origin)

    def _apply_branding_mapping(self, branding: dict[str, str], *, origin: str) -> None:
        if not branding:
            self._set_status(f"{origin}: no changes returned")
            return

        self.draft.setdefault("branding", {})
        widget_map = {
            "agent_name": "agent-name",
            "welcome": "welcome",
            "goodbye": "goodbye",
            "response_label": "response-label",
            "prompt_symbol": "prompt-symbol",
            "help_header": "help-header",
        }
        for key, value in branding.items():
            if key not in widget_map:
                continue
            self.draft["branding"][key] = value
            self.query_one(f"#{widget_map[key]}", Input).value = value

        if "agent_name" in branding and not self.query_one("#logo-title", Input).value.strip():
            self.query_one("#logo-title", Input).value = branding["agent_name"]

        self.dirty = True
        self._refresh_preview()
        self._record_history(origin)
        self._set_status(origin)

    def _apply_spinner_mapping(self, spinner: dict[str, list], *, origin: str) -> None:
        if not spinner:
            self._set_status(f"{origin}: no changes returned")
            return

        self.draft.setdefault("spinner", {})
        waiting = spinner.get("waiting_faces") or []
        thinking = spinner.get("thinking_faces") or []
        verbs = spinner.get("thinking_verbs") or []
        wings = spinner.get("wings") or []

        if waiting:
            self.draft["spinner"]["waiting_faces"] = waiting
            self.query_one("#spinner-waiting", TextArea).load_text(format_multiline_list(waiting))
        if thinking:
            self.draft["spinner"]["thinking_faces"] = thinking
            self.query_one("#spinner-thinking", TextArea).load_text(format_multiline_list(thinking))
        if verbs:
            self.draft["spinner"]["thinking_verbs"] = verbs
            self.query_one("#spinner-verbs", TextArea).load_text(format_multiline_list(verbs))
        if wings:
            self.draft["spinner"]["wings"] = wings
            self.query_one("#spinner-wings", WingPairEditor).set_wings(wings)

        self.dirty = True
        self._refresh_preview()
        self._record_history(origin)
        self._set_status(origin)

    def _set_ai_output(self, title: str, payload: dict) -> None:
        body = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
        self.query_one("#ai-output", TextArea).load_text(f"{title}\n{body}")

    def _apply_ai_logo(self, payload: dict[str, str], *, origin: str) -> None:
        title = payload.get("title", "").strip()
        style_hint = payload.get("style_hint", "").strip()
        art = payload.get("art", "").strip("\n")

        if title:
            self.query_one("#logo-title", Input).value = title
        if style_hint:
            resolved_font = FIGLET_STYLE_MAP.get(style_hint, "")
            if resolved_font:
                self.query_one("#logo-style", Input).value = resolved_font

        if art:
            markup = import_art_text(art, self._logo_color(), mode="plain", bold=True)
            self._set_art_field("banner_logo", "banner-logo", markup)
            self._set_status(origin)
            return

        if title or style_hint:
            self.action_generate_logo()
            self._set_status(origin)
            return

        self._set_status(f"{origin}: no logo changes returned")

    def _apply_ai_hero(self, payload: dict[str, str], *, origin: str) -> None:
        art = payload.get("art", "").strip("\n")
        if not art:
            self._set_status(f"{origin}: no hero changes returned")
            return

        markup = import_art_text(art, self._hero_color(), mode="plain")
        self._set_art_field("banner_hero", "banner-hero", markup)
        self._set_status(origin)

    def _focused_text_widget_id(self) -> str:
        focused = self.screen.focused
        widget_id = getattr(focused, "id", "") or ""
        if not widget_id:
            return ""
        if widget_id.startswith(WING_INPUT_PREFIXES):
            return widget_id
        if widget_id.startswith("tool-"):
            return widget_id
        if widget_id in EMOJI_ENABLED_FIELDS:
            return widget_id
        return ""

    def _insert_symbol(self, widget_id: str, token: str) -> None:
        if not token:
            return
        if widget_id.startswith(WING_INPUT_PREFIXES):
            widget = self.query_one(f"#{widget_id}", Input)
            widget.insert_text_at_cursor(token)
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
        if widget_id == "ai-backend":
            return self.ai_backends[0]
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
        if widget_id.startswith("spinner-wing-left-") or widget_id.startswith("spinner-wing-right-"):
            index = int(widget_id.rsplit("-", 1)[-1])
            side = 0 if "-left-" in widget_id else 1
            reference_wings = (self.reference_draft.get("spinner") or {}).get("wings", [])
            value = ""
            if index < len(reference_wings) and len(reference_wings[index]) == 2:
                value = str(reference_wings[index][side])
            self.query_one(f"#{widget_id}", Input).value = value
            return True
        if widget_id in INPUT_TO_DRAFT:
            self.query_one(f"#{widget_id}", Input).value = self._draft_value_for_widget(widget_id, self.reference_draft)
            return True
        if widget_id in TEXTAREA_TO_DRAFT:
            if widget_id == "spinner-wings":
                reference_wings = (self.reference_draft.get("spinner") or {}).get("wings", [])
                self.query_one("#spinner-wings", WingPairEditor).set_wings(reference_wings)
            else:
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
        if widget_id.startswith("spinner-wing-left-") or widget_id.startswith("spinner-wing-right-"):
            self.query_one(f"#{widget_id}", Input).value = ""
            return True
        if widget_id in INPUT_TO_DRAFT or widget_id in INPUT_DEFAULTS or widget_id == "logo-title":
            self.query_one(f"#{widget_id}", Input).value = ""
            return True
        if widget_id in TEXTAREA_TO_DRAFT or widget_id in TEXTAREA_DEFAULTS:
            if widget_id == "spinner-wings":
                self.query_one("#spinner-wings", WingPairEditor).set_wings([])
            else:
                self.query_one(f"#{widget_id}", TextArea).load_text("")
            return True
        if widget_id in SELECT_DEFAULTS:
            self.query_one(f"#{widget_id}", Select).value = self._control_default_value(widget_id)
            return True
        return False

    def _select_widget_value(self, widget_id: str) -> bool:
        try:
            if widget_id.startswith("spinner-wing-left-") or widget_id.startswith("spinner-wing-right-"):
                self.query_one(f"#{widget_id}", Input).select_all()
                return True
            if widget_id in INPUT_TO_DRAFT or widget_id in INPUT_DEFAULTS or widget_id == "logo-title":
                self.query_one(f"#{widget_id}", Input).select_all()
                return True
            if widget_id in TEXTAREA_TO_DRAFT or widget_id in TEXTAREA_DEFAULTS:
                if widget_id != "spinner-wings":
                    self.query_one(f"#{widget_id}", TextArea).select_all()
                return True
        except Exception:
            return False
        return False

    def _update_meta(self) -> None:
        current_active = self.bridge.get_active_skin_name()
        target_profile = self._selected_profile_target()
        target_active = self.bridge.get_active_skin_name(profile=target_profile)
        source = self.current_source or "-"
        dirty_marker = "unsaved" if self.dirty else "saved"
        draft_name = str(self.draft.get("name", "")).strip() or "(unnamed)"
        changed_fields = self._draft_modified_count()
        self.query_one("#meta", Static).update(
            "\n".join(
                [
                    f"Active: {current_active}",
                    f"Target: {target_profile} -> {target_active}",
                    f"Hermes: {self.bridge.hermes_home}",
                    f"Draft: {draft_name}",
                    f"Source: {source}",
                    f"State: {dirty_marker}",
                    f"Changed fields: {changed_fields}",
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
            note_marker = " !" if entry.note or entry.invalid else ""
            prompts.append(f"{active_marker}{note_marker} {entry.name} [{source}] {entry.description}")

        widget = self.query_one("#skin-list", OptionList)
        widget.clear_options()
        widget.add_options(prompts)

        if not self.library_entries:
            return

        target_name = selected_name or self.current_name or active
        index = next((i for i, entry in enumerate(self.library_entries) if entry.name == target_name), 0)
        widget.highlighted = index

    def _try_load_active_skin(self, *, profile: str | None = None) -> bool:
        if not self.bridge.available:
            return False

        try:
            skin, source = self.bridge.load_active_skin(profile=profile)
        except Exception:
            return False

        self.current_source = source
        self.current_name = str(skin.get("name", "")).strip()
        self.draft = skin
        self._snapshot_reference_draft()
        self.dirty = False
        self._populate_form_from_draft()
        self._refresh_preview()
        self._refresh_library_widget(selected_name=self.current_name)
        self._reset_history(f"Load {self.current_name}")
        self._set_status(f"loaded active skin: {self.current_name}")
        return True

    def _load_entry(self, entry: LibraryEntry) -> None:
        self.current_source = entry.source
        self.current_name = entry.name
        self.draft = self.bridge.load_skin(entry.name, source=entry.source, path=entry.path or None)
        self._snapshot_reference_draft()
        self.dirty = False
        self._populate_form_from_draft()
        self._refresh_preview()
        self._reset_history(f"Load {entry.name}")
        note_suffix = f" ({entry.note})" if entry.note else ""
        self._set_status(f"Loaded {entry.source} skin {entry.name}{note_suffix}")

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
        set_select("ai-backend", self.ai_backends[0])
        set_textarea("ai-direction", TEXTAREA_DEFAULTS["ai-direction"])
        set_textarea("ai-output", TEXTAREA_DEFAULTS["ai-output"])

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
        set_input("yaml-file-path", INPUT_DEFAULTS["yaml-file-path"])
        set_select("yaml-import-mode", SELECT_DEFAULTS["yaml-import-mode"])
        set_textarea("yaml-import", TEXTAREA_DEFAULTS["yaml-import"])
        set_input("palette-file-path", INPUT_DEFAULTS["palette-file-path"])
        set_textarea("palette-import", TEXTAREA_DEFAULTS["palette-import"])
        for color_key in COLOR_KEYS:
            set_input(f"color-{color_key}", colors.get(color_key, ""))

        spinner = draft.get("spinner", {})
        set_select("spinner-preset", SELECT_DEFAULTS["spinner-preset"])
        set_textarea("spinner-waiting", format_multiline_list(spinner.get("waiting_faces", [])))
        set_textarea("spinner-thinking", format_multiline_list(spinner.get("thinking_faces", [])))
        set_textarea("spinner-verbs", format_multiline_list(spinner.get("thinking_verbs", [])))
        self.query_one("#spinner-wings", WingPairEditor).set_wings(spinner.get("wings", []))

        tool_emojis = draft.get("tool_emojis", {})
        for tool_key in TOOL_EMOJI_KEYS:
            set_input(f"tool-{tool_key}", tool_emojis.get(tool_key, ""))

        set_input("logo-title", branding.get("agent_name") or draft.get("name", ""))
        set_input("logo-width", INPUT_DEFAULTS["logo-width"])
        set_input("logo-export-path", INPUT_DEFAULTS["logo-export-path"])
        set_input("logo-export-png-path", INPUT_DEFAULTS["logo-export-png-path"])
        set_input("logo-style", INPUT_DEFAULTS["logo-style"])
        set_select("logo-font-category", SELECT_DEFAULTS["logo-font-category"])
        set_input("logo-font-filter", INPUT_DEFAULTS["logo-font-filter"])
        set_select("logo-justify", SELECT_DEFAULTS["logo-justify"])
        set_select("logo-fit", SELECT_DEFAULTS["logo-fit"])
        set_select("logo-import-mode", SELECT_DEFAULTS["logo-import-mode"])
        set_input("logo-file-path", "")
        set_textarea("logo-import", "")
        set_textarea("banner-logo", draft.get("banner_logo", ""))

        set_input("hero-path", "")
        set_select("hero-style", SELECT_DEFAULTS["hero-style"])
        set_select("hero-dither", SELECT_DEFAULTS["hero-dither"])
        set_input("hero-width", INPUT_DEFAULTS["hero-width"])
        set_input("hero-brightness", INPUT_DEFAULTS["hero-brightness"])
        set_input("hero-contrast", INPUT_DEFAULTS["hero-contrast"])
        set_input("hero-saturation", INPUT_DEFAULTS["hero-saturation"])
        set_input("hero-hue-shift", INPUT_DEFAULTS["hero-hue-shift"])
        set_input("hero-grayscale", INPUT_DEFAULTS["hero-grayscale"])
        set_input("hero-sepia", INPUT_DEFAULTS["hero-sepia"])
        set_select("hero-invert", SELECT_DEFAULTS["hero-invert"])
        set_input("hero-threshold", INPUT_DEFAULTS["hero-threshold"])
        set_input("hero-sharpen", INPUT_DEFAULTS["hero-sharpen"])
        set_select("hero-edge", SELECT_DEFAULTS["hero-edge"])
        set_input("hero-space-density", INPUT_DEFAULTS["hero-space-density"])
        set_input("hero-padding", INPUT_DEFAULTS["hero-padding"])
        set_select("hero-justify", SELECT_DEFAULTS["hero-justify"])
        set_select("hero-fit", SELECT_DEFAULTS["hero-fit"])
        set_select("hero-import-mode", SELECT_DEFAULTS["hero-import-mode"])
        set_input("hero-file-path", INPUT_DEFAULTS["hero-file-path"])
        set_input("hero-export-text-path", INPUT_DEFAULTS["hero-export-text-path"])
        set_input("hero-export-path", INPUT_DEFAULTS["hero-export-path"])
        set_textarea("hero-import", "")
        set_textarea("banner-hero", draft.get("banner_hero", ""))

        self._populating_form = False
        self._refresh_ai_backend_note()
        self._refresh_logo_font_browser()
        self._sync_modified_indicators()
        self._update_action_buttons()
        self._update_meta()

    def _refresh_preview(self) -> None:
        preview_skin = merge_skin(self.default_skin, self.draft)
        preview_error: str | None = None
        logo_override = None
        if self._logo_preview_active():
            try:
                logo_override = self._current_logo_result().markup
            except Exception:
                logo_override = None

        try:
            preview_renderable = render_skin_preview(
                preview_skin,
                show_logo=self._preview_show_logo,
                show_hero=self._preview_show_hero,
                compact=self._preview_compact,
                native_colors=self._preview_native,
                logo_override=logo_override,
                logo_justify=str(self.query_one("#logo-justify", Select).value or SELECT_DEFAULTS["logo-justify"]),
                hero_justify=str(self.query_one("#hero-justify", Select).value or SELECT_DEFAULTS["hero-justify"]),
            )
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
        self._refresh_logo_font_preview()
        self._sync_modified_indicators()
        self._update_action_buttons()
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
        self._record_history(f"Edit {widget_id}")

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
            return
        else:
            if self.draft.get(section, "") == value:
                return
            self.draft[section] = value

        self.dirty = True
        self._refresh_preview()
        self._record_history(f"Edit {widget_id}")

    def _set_art_field(self, field_name: str, widget_id: str, markup: str) -> None:
        self.draft[field_name] = markup
        self.query_one(f"#{widget_id}", TextArea).load_text(markup)
        self.dirty = True
        self._refresh_preview()
        self._record_history(f"Update {field_name}")

    def _logo_color(self) -> str:
        colors = self.draft.get("colors", {})
        val = colors.get("logo_color") or colors.get("banner_title", "#8EA3FF")
        return normalize_color_token(val, "#8EA3FF")

    def _hero_color(self) -> str:
        colors = self.draft.get("colors", {})
        val = colors.get("hero_color") or colors.get("banner_accent", "#8EA3FF")
        return normalize_color_token(val, "#8EA3FF")

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
        self._reset_history(f"Save {self.current_name}")
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

    def _apply_imported_skin(self, imported: dict, *, mode: str, origin: str) -> None:
        import_mode = str(mode or "replace").strip().lower() or "replace"
        if import_mode not in SKIN_IMPORT_MODE_OPTIONS:
            self._set_status(f"Unknown YAML import mode: {mode}")
            return

        if import_mode == "merge":
            self.draft = merge_skin(self.draft, imported)
        else:
            self.draft = merge_skin(self.default_skin, imported)
            self.current_source = "import"
            self.current_name = str(self.draft.get("name", "")).strip()

        self.dirty = True
        self._populate_form_from_draft()
        self._refresh_preview()
        self._record_history(origin)
        self._set_status(origin)

    def action_import_yaml_text(self) -> None:
        mode = str(self.query_one("#yaml-import-mode", Select).value or "replace")
        text = self.query_one("#yaml-import", TextArea).text
        try:
            imported = parse_skin_yaml(text, strict=False)
        except Exception as exc:
            self._set_status(f"YAML import failed: {exc}")
            return

        self._apply_imported_skin(imported, mode=mode, origin=f"Imported skin YAML from text ({mode})")

    def action_import_yaml_file(self) -> None:
        mode = str(self.query_one("#yaml-import-mode", Select).value or "replace")
        path = self.query_one("#yaml-file-path", Input).value.strip()
        try:
            imported = import_skin_yaml_file(path, strict=False)
        except Exception as exc:
            self._set_status(f"YAML file import failed: {exc}")
            return

        self._apply_imported_skin(imported, mode=mode, origin=f"Imported skin YAML file ({mode})")

    def action_export_yaml_file(self) -> None:
        path_text = self.query_one("#yaml-file-path", Input).value.strip()
        if not path_text:
            self._set_status("Enter a YAML file path first")
            return

        target_path = Path(path_text).expanduser()
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(self.query_one("#yaml-view", TextArea).text, encoding="utf-8")
        except Exception as exc:
            self._set_status(f"YAML export failed: {exc}")
            return

        self._set_status(f"Exported YAML preview to {target_path}")

    def _activate_current_skin(self) -> None:
        target_profile = self._selected_profile_target()
        try:
            active_name = sanitize_skin_name(str(self.draft.get("name", "")).strip())
            self.bridge.set_active_skin_in_config(active_name, profile=target_profile)
            self._refresh_library_widget(selected_name=active_name)
            self._update_meta()
            profile_label = f"{target_profile} profile" if target_profile != "default" else "default profile"
            self._toast(f"✓ {active_name} activated in hermes ({profile_label})")
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
        self._record_history(f"Color {target}")
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

        self.query_one("#spinner-preset", Select).value = preset_name
        self._apply_spinner_mapping(spinner, origin=f"Applied spinner preset {preset_name}")

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

    def action_generate_ai_branding(self) -> None:
        backend = self._selected_ai_backend()
        direction = self._ai_direction()
        self._set_status(f"Generating branding with {backend}...")
        try:
            branding = generate_branding_bundle(self.draft, backend=backend, direction=direction)
        except Exception as exc:
            self._set_status(f"AI branding failed: {exc}")
            return

        payload = {"backend": backend, "direction": direction, "branding": branding}
        self._set_ai_output("AI Branding", payload)
        self._apply_branding_mapping(branding, origin=f"Applied AI branding via {backend}")

    def action_generate_ai_spinner(self) -> None:
        backend = self._selected_ai_backend()
        direction = self._ai_direction()
        self._set_status(f"Generating spinner bundle with {backend}...")
        try:
            spinner = generate_spinner_bundle(self.draft, backend=backend, direction=direction)
        except Exception as exc:
            self._set_status(f"AI spinner failed: {exc}")
            return

        payload = {"backend": backend, "direction": direction, "spinner": spinner}
        self._set_ai_output("AI Spinner", payload)
        self._apply_spinner_mapping(spinner, origin=f"Applied AI spinner via {backend}")

    def action_generate_ai_logo(self) -> None:
        backend = self._selected_ai_backend()
        direction = self._ai_direction()
        self._set_status(f"Generating logo concept with {backend}...")
        try:
            logo = generate_logo_bundle(self.draft, backend=backend, direction=direction)
        except Exception as exc:
            self._set_status(f"AI logo failed: {exc}")
            return

        payload = {"backend": backend, "direction": direction, "logo": logo}
        self._set_ai_output("AI Logo", payload)
        try:
            self._apply_ai_logo(logo, origin=f"Applied AI logo via {backend}")
        except Exception as exc:
            self._set_status(f"AI logo apply failed: {exc}")

    def action_generate_ai_hero(self) -> None:
        backend = self._selected_ai_backend()
        direction = self._ai_direction()
        self._set_status(f"Generating hero art with {backend}...")
        try:
            hero = generate_hero_bundle(self.draft, backend=backend, direction=direction)
        except Exception as exc:
            self._set_status(f"AI hero failed: {exc}")
            return

        payload = {"backend": backend, "direction": direction, "hero": hero}
        self._set_ai_output("AI Hero", payload)
        try:
            self._apply_ai_hero(hero, origin=f"Applied AI hero via {backend}")
        except Exception as exc:
            self._set_status(f"AI hero apply failed: {exc}")

    def action_generate_ai_bundle(self) -> None:
        backend = self._selected_ai_backend()
        direction = self._ai_direction()
        self._set_status(f"Generating full skin bundle with {backend}...")
        try:
            payload = generate_skin_bundle(self.draft, backend=backend, direction=direction)
        except Exception as exc:
            self._set_status(f"AI bundle failed: {exc}")
            return

        self._set_ai_output("AI Bundle", {"backend": backend, "direction": direction, **payload})
        try:
            branding = payload.get("branding", {})
            spinner = payload.get("spinner", {})
            logo = payload.get("logo", {})
            hero = payload.get("hero", {})

            changed = False
            if branding:
                self.draft.setdefault("branding", {})
                widget_map = {
                    "agent_name": "agent-name",
                    "welcome": "welcome",
                    "goodbye": "goodbye",
                    "response_label": "response-label",
                    "prompt_symbol": "prompt-symbol",
                    "help_header": "help-header",
                }
                for key, value in branding.items():
                    if key in widget_map and value:
                        self.draft["branding"][key] = value
                        self.query_one(f"#{widget_map[key]}", Input).value = value
                        changed = True
                if branding.get("agent_name") and not self.query_one("#logo-title", Input).value.strip():
                    self.query_one("#logo-title", Input).value = str(branding["agent_name"])

            if spinner:
                waiting = spinner.get("waiting_faces") or []
                thinking = spinner.get("thinking_faces") or []
                verbs = spinner.get("thinking_verbs") or []
                wings = spinner.get("wings") or []
                self.draft.setdefault("spinner", {})
                if waiting:
                    self.draft["spinner"]["waiting_faces"] = waiting
                    self.query_one("#spinner-waiting", TextArea).load_text(format_multiline_list(waiting))
                    changed = True
                if thinking:
                    self.draft["spinner"]["thinking_faces"] = thinking
                    self.query_one("#spinner-thinking", TextArea).load_text(format_multiline_list(thinking))
                    changed = True
                if verbs:
                    self.draft["spinner"]["thinking_verbs"] = verbs
                    self.query_one("#spinner-verbs", TextArea).load_text(format_multiline_list(verbs))
                    changed = True
                if wings:
                    self.draft["spinner"]["wings"] = wings
                    self.query_one("#spinner-wings", WingPairEditor).set_wings(wings)
                    changed = True

            logo_title = str(logo.get("title", "")).strip()
            logo_style_hint = str(logo.get("style_hint", "")).strip()
            logo_art = str(logo.get("art", "")).strip("\n")
            if logo_title:
                self.query_one("#logo-title", Input).value = logo_title
                changed = True
            if logo_style_hint:
                resolved_font = FIGLET_STYLE_MAP.get(logo_style_hint, "")
                if resolved_font:
                    self.query_one("#logo-style", Input).value = resolved_font
                    changed = True
            if logo_art:
                markup = import_art_text(logo_art, self._logo_color(), mode="plain", bold=True)
                self.draft["banner_logo"] = markup
                self.query_one("#banner-logo", TextArea).load_text(markup)
                changed = True
            elif logo_title or logo_style_hint:
                width_text = self.query_one("#logo-width", Input).value.strip() or INPUT_DEFAULTS["logo-width"]
                style = self.query_one("#logo-style", Input).value.strip() or INPUT_DEFAULTS["logo-style"]
                justify = str(self.query_one("#logo-justify", Select).value) or SELECT_DEFAULTS["logo-justify"]
                fit = str(self.query_one("#logo-fit", Select).value) or SELECT_DEFAULTS["logo-fit"]
                result = generate_logo_result(logo_title or self.query_one("#logo-title", Input).value.strip() or "logo", style, self._logo_color(), width=int(width_text), justify=justify, fit=fit)
                self.draft["banner_logo"] = result.markup
                self.query_one("#banner-logo", TextArea).load_text(result.markup)
                changed = True

            hero_art = str(hero.get("art", "")).strip("\n")
            if hero_art:
                markup = import_art_text(hero_art, self._hero_color(), mode="plain")
                self.draft["banner_hero"] = markup
                self.query_one("#banner-hero", TextArea).load_text(markup)
                changed = True
        except Exception as exc:
            self._set_status(f"AI bundle apply failed: {exc}")
            return

        if not changed:
            self._set_status(f"AI bundle via {backend} returned no changes")
            return

        self.dirty = True
        self._refresh_preview()
        self._record_history(f"AI bundle {backend}")
        self._set_status(f"Applied AI bundle via {backend}")

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
        if self._populating_form or self._restoring_history or not event.input.id:
            return
        if event.input.id == "color-tool-value":
            self._sync_modified_indicators()
            return
        if event.input.id in TRANSIENT_INPUT_IDS:
            if event.input.id in {"logo-title", "logo-width", "logo-style", "logo-font-filter"}:
                self._refresh_logo_font_browser()
            if event.input.id.startswith("hero-") or event.input.id in {"logo-title", "logo-width", "logo-style", "logo-font-filter"}:
                self._refresh_preview()
            self._sync_modified_indicators()
            self._record_history(f"Edit {event.input.id}")
            return
        if event.input.id in {"logo-font-filter", "logo-style"}:
            self._refresh_logo_font_browser()
            return
        self._apply_input_change(event.input.id, event.value)
        if event.input.id.startswith("color-") and event.input.id[6:] == str(self.query_one("#color-target", Select).value):
            self.query_one("#color-tool-value", Input).value = event.value

    def on_select_changed(self, event: Select.Changed) -> None:
        if self._populating_form or self._restoring_history or not event.select.id:
            return
        if event.select.id == "color-target":
            self._sync_color_tool()
            self._sync_modified_indicators()
            return
        if event.select.id == "ai-backend":
            self._refresh_ai_backend_note()
            self._sync_modified_indicators()
            self._record_history(f"Select {event.select.id}")
            return
        if event.select.id in {"logo-font-category", "logo-justify", "logo-fit"}:
            self._refresh_logo_font_browser()
            self._refresh_preview()
            self._sync_modified_indicators()
            self._record_history(f"Select {event.select.id}")
            return
        if event.select.id in {"profile-target", "yaml-import-mode", "hero-style", "hero-dither", "hero-invert", "hero-justify", "hero-fit", "hero-edge", "hero-import-mode", "logo-import-mode"}:
            self._refresh_preview()
            self._sync_modified_indicators()
            self._record_history(f"Select {event.select.id}")
            return
        if event.select.id in TRANSIENT_SELECT_IDS:
            self._sync_modified_indicators()
            self._record_history(f"Select {event.select.id}")

    def on_descendant_focus(self, event: events.DescendantFocus) -> None:
        widget_id = getattr(event.widget, "id", "") or ""
        preview_logo_ids = {
            "logo-title",
            "logo-width",
            "logo-style",
            "logo-font-filter",
            "logo-font-category",
            "logo-justify",
            "logo-fit",
            "logo-font-list",
        }
        live_logo = widget_id in preview_logo_ids
        if live_logo != self._preview_live_logo:
            self._preview_live_logo = live_logo
            self._refresh_preview()

    def on_wing_pair_editor_changed(self, event: WingPairEditor.Changed) -> None:
        if self._populating_form or self._restoring_history:
            return
        if self.draft.setdefault("spinner", {}).get("wings", []) == event.wings:
            return
        self.draft.setdefault("spinner", {})
        self.draft["spinner"]["wings"] = event.wings
        self.dirty = True
        self._refresh_preview()
        self._record_history("Edit spinner-wings")

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if self._populating_form or self._restoring_history or not event.text_area.id:
            return
        if event.text_area.id in TRANSIENT_TEXTAREA_IDS:
            self._sync_modified_indicators()
            self._record_history(f"Edit {event.text_area.id}")
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
                self._refresh_logo_font_preview()
                self._refresh_preview()
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
        elif button_id == "fork-builtin":
            self.action_fork_builtin()
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
        elif button_id == "preview-spinner":
            self.action_preview_spinner()
        elif button_id == "apply-spinner-preset":
            self.action_apply_spinner_preset()
        elif button_id == "import-yaml-text":
            self.action_import_yaml_text()
        elif button_id == "import-yaml-file":
            self.action_import_yaml_file()
        elif button_id == "export-yaml-file":
            self.action_export_yaml_file()
        elif button_id == "undo":
            self.action_undo()
        elif button_id == "redo":
            self.action_redo()
        elif button_id == "select-focused":
            self.action_select_focused()
        elif button_id == "clear-focused":
            self.action_clear_focused()
        elif button_id == "reset-focused":
            self.action_reset_focused()
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
        elif button_id == "export-logo-text":
            self.action_export_logo_text()
        elif button_id == "export-logo-png":
            self.action_export_logo_png()
        elif button_id == "import-logo-text":
            self.action_import_logo_text()
        elif button_id == "import-logo-file":
            self.action_import_logo_file()
        elif button_id == "generate-hero":
            self.action_generate_hero()
        elif button_id == "clear-hero":
            self._set_art_field("banner_hero", "banner-hero", "")
            self._set_status("Cleared hero art")
        elif button_id == "export-hero-text":
            self.action_export_hero_text()
        elif button_id == "export-hero-png":
            self.action_export_hero_png()
        elif button_id == "launch-imagewalker":
            self.action_launch_imagewalker()
        elif button_id == "import-hero-text":
            self.action_import_hero_text()
        elif button_id == "import-hero-file":
            self.action_import_hero_file()
        elif button_id == "ai-branding":
            self.action_generate_ai_branding()
        elif button_id == "ai-spinner":
            self.action_generate_ai_spinner()
        elif button_id == "ai-logo":
            self.action_generate_ai_logo()
        elif button_id == "ai-hero":
            self.action_generate_ai_hero()
        elif button_id == "ai-bundle":
            self.action_generate_ai_bundle()
        elif button_id == "toggle-logo":
            self._preview_show_logo = not self._preview_show_logo
            label = "Logo: on" if self._preview_show_logo else "Logo: off"
            self.query_one("#toggle-logo", Button).label = label
            self._refresh_preview()
        elif button_id == "toggle-hero":
            self._preview_show_hero = not self._preview_show_hero
            label = "Hero: on" if self._preview_show_hero else "Hero: off"
            self.query_one("#toggle-hero", Button).label = label
            self._refresh_preview()
        elif button_id == "toggle-compact":
            self._preview_compact = not self._preview_compact
            label = "Compact: on" if self._preview_compact else "Compact: off"
            self.query_one("#toggle-compact", Button).label = label
            self._refresh_preview()
        elif button_id == "toggle-native":
            self._preview_native = not self._preview_native
            label = "Native colors: on" if self._preview_native else "Native colors: off"
            self.query_one("#toggle-native", Button).label = label
            self._refresh_preview()
        elif button_id == "colors-toggle-logo":
            self._preview_show_logo = not self._preview_show_logo
            label = "Logo: on" if self._preview_show_logo else "Logo: off"
            self.query_one("#toggle-logo", Button).label = label
            self.query_one("#colors-toggle-logo", Button).label = label
            self._refresh_preview()
        elif button_id == "colors-toggle-hero":
            self._preview_show_hero = not self._preview_show_hero
            label = "Hero: on" if self._preview_show_hero else "Hero: off"
            self.query_one("#toggle-hero", Button).label = label
            self.query_one("#colors-toggle-hero", Button).label = label
            self._refresh_preview()
        elif button_id == "colors-toggle-compact":
            self._preview_compact = not self._preview_compact
            label = "Compact: on" if self._preview_compact else "Compact: off"
            self.query_one("#toggle-compact", Button).label = label
            self.query_one("#colors-toggle-compact", Button).label = label
            self._refresh_preview()
        elif button_id == "colors-toggle-native":
            self._preview_native = not self._preview_native
            label = "Native colors: on" if self._preview_native else "Native colors: off"
            self.query_one("#toggle-native", Button).label = label
            self.query_one("#colors-toggle-native", Button).label = label
            self._refresh_preview()

    def action_undo(self) -> None:
        entry = self._history.undo()
        if entry is None:
            self._set_status("Nothing to undo")
            return
        self._apply_history_state(entry.state)
        self._set_status(f"Undid: {entry.label}")

    def action_redo(self) -> None:
        entry = self._history.redo()
        if entry is None:
            self._set_status("Nothing to redo")
            return
        self._apply_history_state(entry.state)
        self._set_status(f"Redid: {entry.label}")

    def action_select_focused(self) -> None:
        focused = self.screen.focused
        if focused is None or not getattr(focused, "id", None) or not self._select_widget_value(focused.id):
            self._set_status("Focus a supported text field to select it")
            return
        self._set_status(f"Selected {focused.id}")

    def action_clear_focused(self) -> None:
        focused = self.screen.focused
        if focused is None or not getattr(focused, "id", None) or not self._clear_widget_value(focused.id):
            self._set_status("Focus a supported field to clear it")
            return
        self._record_history(f"Clear {focused.id}")
        self._set_status(f"Cleared {focused.id}")

    def action_reset_focused(self) -> None:
        focused = self.screen.focused
        if focused is None or not getattr(focused, "id", None) or not self._reset_widget_value(focused.id):
            self._set_status("Focus a supported field to reset it")
            return
        self._record_history(f"Reset {focused.id}")
        self._set_status(f"Reset {focused.id}")

    def action_refresh_library(self) -> None:
        self._refresh_profile_targets()
        self._refresh_library_widget(selected_name=self.current_name or self.bridge.get_active_skin_name())
        if not self.current_name:
            if not self._try_load_active_skin(profile=self.bridge.current_profile_name()):
                self._update_meta()
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
            self._record_history(f"New draft {name}")
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
            self._record_history(f"Clone to {new_name}")
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

    def action_preview_spinner(self) -> None:
        self.push_screen(PreviewSpinnerModal(self.draft))

    def action_fork_builtin(self) -> None:
        if self.current_source != "builtin":
            self._set_status("Only built-in skins can be forked")
            return

        original_name = str(self.draft.get("name", "")).strip() or "custom-skin"
        forked = deepcopy(self.draft)
        forked_name = unique_skin_name(self._existing_names(), f"{original_name}-custom")
        forked["name"] = forked_name

        try:
            self.bridge.save_skin(forked)
        except Exception as exc:
            self._set_status(f"Fork failed: {exc}")
            return

        self.current_source = "user"
        self.current_name = forked_name
        self.draft = forked
        self._snapshot_reference_draft()
        self.dirty = False
        self._populate_form_from_draft()
        self._refresh_library_widget(selected_name=forked_name)
        self._refresh_preview()
        self._reset_history(f"Fork {forked_name}")
        self._toast(f"forked '{original_name}' -> '{forked_name}'")

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
        justify = str(self.query_one("#logo-justify", Select).value) or SELECT_DEFAULTS["logo-justify"]
        fit = str(self.query_one("#logo-fit", Select).value) or SELECT_DEFAULTS["logo-fit"]

        try:
            result = self._current_logo_result()
        except Exception as exc:
            self._set_status(f"Logo generation failed: {exc}")
            return

        self._set_art_field("banner_logo", "banner-logo", result.markup)
        self._set_status(f"Generated logo using {result.font} at {result.width}x{result.height} ({justify}, {fit})")

    def action_export_logo_text(self) -> None:
        logo_markup = self.draft.get("banner_logo", "")
        if not logo_markup:
            self._set_status("No logo art to export")
            return
        path_input = self.query_one("#logo-export-path", Input).value.strip()
        if not path_input:
            self._set_status("Set logo TXT export path first")
            return
        try:
            _export_markup_text(logo_markup, path_input)
            self._set_status(f"Exported logo TXT -> {path_input}")
        except Exception as exc:
            self._set_status(f"Logo TXT export failed: {exc}")

    def action_export_logo_png(self) -> None:
        logo_markup = self.draft.get("banner_logo", "")
        if not logo_markup:
            self._set_status("No logo art to export")
            return
        path_input = self.query_one("#logo-export-png-path", Input).value.strip()
        if not path_input:
            self._set_status("Set logo PNG export path first")
            return
        try:
            _export_ascii_png(logo_markup, path_input)
            self._set_status(f"Exported logo PNG -> {path_input}")
        except Exception as exc:
            self._set_status(f"Logo PNG export failed: {exc}")

    def action_generate_hero(self) -> None:
        image_path = self.query_one("#hero-path", Input).value.strip()
        style = str(self.query_one("#hero-style", Select).value) or SELECT_DEFAULTS["hero-style"]
        dither = str(self.query_one("#hero-dither", Select).value) or SELECT_DEFAULTS["hero-dither"]
        invert = str(self.query_one("#hero-invert", Select).value or "off") == "on"
        threshold_text = self.query_one("#hero-threshold", Input).value.strip()
        edge_strength = 0.35 if str(self.query_one("#hero-edge", Select).value or "off") == "on" else 0.0
        justify = str(self.query_one("#hero-justify", Select).value) or SELECT_DEFAULTS["hero-justify"]
        fit = str(self.query_one("#hero-fit", Select).value) or SELECT_DEFAULTS["hero-fit"]
        color = self._hero_color()

        try:
            result = generate_hero_markup(
                image_path,
                style,
                self._int_input("hero-width", int(INPUT_DEFAULTS["hero-width"])),
                color,
                justify=justify,
                fit=fit,
                brightness=max(0.1, self._float_input("hero-brightness", float(INPUT_DEFAULTS["hero-brightness"])) / 100.0),
                contrast=max(0.1, self._float_input("hero-contrast", float(INPUT_DEFAULTS["hero-contrast"])) / 100.0),
                invert=invert,
                threshold=self._int_input("hero-threshold", 0) if threshold_text else None,
                sharpen=max(0.1, self._float_input("hero-sharpen", float(INPUT_DEFAULTS["hero-sharpen"])) / 100.0),
                edge_strength=edge_strength,
                saturation=max(0.0, self._float_input("hero-saturation", float(INPUT_DEFAULTS["hero-saturation"]))),
                hue_shift=self._float_input("hero-hue-shift", float(INPUT_DEFAULTS["hero-hue-shift"])),
                grayscale_blend=max(0.0, self._float_input("hero-grayscale", float(INPUT_DEFAULTS["hero-grayscale"]))) / 100.0,
                sepia=self._float_input("hero-sepia", float(INPUT_DEFAULTS["hero-sepia"])),
                space_density=self._float_input("hero-space-density", float(INPUT_DEFAULTS["hero-space-density"])),
                dither=dither,
                padding=max(0, self._int_input("hero-padding", int(INPUT_DEFAULTS["hero-padding"]))),
            )
        except Exception as exc:
            self._set_status(f"Hero generation failed: {exc}")
            return

        self._set_art_field("banner_hero", "banner-hero", result.markup)
        self._set_status(f"Generated {result.style} hero art at {result.width}x{result.height} ({justify}, {fit})")

    def action_export_hero_text(self) -> None:
        hero_markup = self.draft.get("banner_hero", "")
        if not hero_markup:
            self._set_status("No hero art to export")
            return
        path_input = self.query_one("#hero-export-text-path", Input).value.strip()
        if not path_input:
            self._set_status("Set hero TXT export path first")
            return
        try:
            _export_markup_text(hero_markup, path_input)
            self._set_status(f"Exported hero TXT -> {path_input}")
        except Exception as exc:
            self._set_status(f"Hero TXT export failed: {exc}")

    def action_export_hero_png(self) -> None:
        hero_markup = self.draft.get("banner_hero", "")
        if not hero_markup:
            self._set_status("No hero art to export")
            return
        path_input = self.query_one("#hero-export-path", Input).value.strip()
        if not path_input:
            self._set_status("Set export path first")
            return
        try:
            _export_ascii_png(hero_markup, path_input)
            self._set_status(f"Exported hero PNG -> {path_input}")
        except Exception as exc:
            self._set_status(f"Export failed: {exc}")

    def action_launch_imagewalker(self) -> None:
        launcher = shutil.which("imagewalker")
        if launcher:
            command = [launcher]
        else:
            command = [sys.executable, "-m", "imagewalker"]
        image_path = self.query_one("#hero-path", Input).value.strip()
        if image_path:
            command.append(image_path)
        env = dict(os.environ)
        src_root = str(Path(__file__).resolve().parents[1])
        env["PYTHONPATH"] = f"{src_root}:{env['PYTHONPATH']}" if env.get("PYTHONPATH") else src_root
        try:
            subprocess.Popen(command, cwd=str(Path(__file__).resolve().parents[2]), env=env)
            self._set_status("Launched Imagewalker")
        except Exception as exc:
            self._set_status(f"Launch failed: {exc}")
