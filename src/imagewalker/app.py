from __future__ import annotations

from pathlib import Path

from PIL import Image
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Input, Select, Static, TextArea

from .engine import ImageAsciiRequest, ImageAsciiResult, render_image_ascii, render_source_preview
from .export import copy_to_clipboard, save_png_from_markup, save_text
from .gradients import gradient_names


def _select_options(values: list[str]) -> list[tuple[str, str]]:
    return [(value, value) for value in values]


class ImagewalkerApp(App[None]):
    CSS = """
    Screen {
        layout: vertical;
    }

    #layout {
        height: 1fr;
    }

    #controls {
        width: 44;
        min-width: 38;
        padding: 1;
        border: round $panel;
    }

    #source-pane {
        width: 30;
        min-width: 26;
        padding: 1;
        border: round $boost;
    }

    #output-pane {
        width: 1fr;
        padding: 1;
        border: round $accent;
    }

    .section-title {
        margin-top: 1;
        text-style: bold;
    }

    .field-label {
        margin-top: 1;
    }

    .button-row {
        height: auto;
        margin-top: 1;
    }

    .button-row Button {
        margin-right: 1;
    }

    #source-preview {
        height: 1fr;
        border: solid $panel;
        padding: 1;
    }

    #output {
        height: 1fr;
        border: solid $panel;
    }

    #status {
        margin-top: 1;
    }
    """

    BINDINGS = [Binding("ctrl+r", "render", "Render")]

    def __init__(self, *, initial_image: str = "") -> None:
        super().__init__()
        self.initial_image = initial_image
        self.last_result: ImageAsciiResult | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="layout"):
            with VerticalScroll(id="controls"):
                yield Static("Imagewalker", classes="section-title")
                yield Static("Standalone image-to-ASCII lab with wider output and parity-oriented controls.", classes="field-label")
                yield Static("Image path", classes="field-label")
                yield Input(self.initial_image, id="image-path", placeholder="~/Pictures/image.png")
                yield Static("Gradient", classes="field-label")
                yield Select(_select_options(gradient_names()), id="gradient", allow_blank=False, value="ascii")
                yield Static("Dither", classes="field-label")
                yield Select(
                    [
                        ("none", "none"),
                        ("floyd-steinberg", "floyd-steinberg"),
                        ("atkinson", "atkinson"),
                        ("jjn", "jjn"),
                        ("stucki", "stucki"),
                    ],
                    id="dither",
                    allow_blank=False,
                    value="none",
                )
                yield Static("Characters (20-400)", classes="field-label")
                yield Input("80", id="characters", placeholder="80")
                yield Static("Brightness % (0-200)", classes="field-label")
                yield Input("100", id="brightness", placeholder="100")
                yield Static("Contrast % (0-200)", classes="field-label")
                yield Input("100", id="contrast", placeholder="100")
                yield Static("Saturation % (0-400)", classes="field-label")
                yield Input("100", id="saturation", placeholder="100")
                yield Static("Hue (0-360)", classes="field-label")
                yield Input("0", id="hue", placeholder="0")
                yield Static("Grayscale % (0-100)", classes="field-label")
                yield Input("100", id="grayscale", placeholder="100")
                yield Static("Sepia % (0-100)", classes="field-label")
                yield Input("0", id="sepia", placeholder="0")
                yield Static("Invert % (0-100)", classes="field-label")
                yield Input("0", id="invert", placeholder="0")
                yield Static("Threshold offset (blank = off)", classes="field-label")
                yield Input("", id="threshold", placeholder="")
                yield Static("Sharpness (1.0 = off)", classes="field-label")
                yield Input("1.0", id="sharpness", placeholder="1.0")
                yield Static("Edge intensity (0-2)", classes="field-label")
                yield Input("0.0", id="edge-intensity", placeholder="0.0")
                yield Static("Space density (0-40)", classes="field-label")
                yield Input("0", id="space-density", placeholder="0")
                yield Static("Transparent frame (0-10)", classes="field-label")
                yield Input("0", id="transparent-frame", placeholder="0")
                yield Static("Justify", classes="field-label")
                yield Select(_select_options(["left", "center", "right"]), id="justify", allow_blank=False, value="left")
                yield Static("Fit mode", classes="field-label")
                yield Select(_select_options(["flexible", "fixed"]), id="fit-mode", allow_blank=False, value="flexible")
                yield Static("Color mode", classes="field-label")
                yield Select(_select_options(["plain", "styled"]), id="color-mode", allow_blank=False, value="plain")
                yield Static("Tint color", classes="field-label")
                yield Input("#C8C8C8", id="tint-color", placeholder="#C8C8C8")
                yield Static("Export TXT path", classes="field-label")
                yield Input("~/art/imagewalker.txt", id="export-text-path", placeholder="~/art/imagewalker.txt")
                yield Static("Export PNG path", classes="field-label")
                yield Input("~/art/imagewalker.png", id="export-png-path", placeholder="~/art/imagewalker.png")
                with Horizontal(classes="button-row"):
                    yield Button("Render", id="render")
                    yield Button("Copy", id="copy")
                with Horizontal(classes="button-row"):
                    yield Button("Save TXT", id="save-text")
                    yield Button("Save PNG", id="save-png")
                yield Static("", id="status")
            with Vertical(id="source-pane"):
                yield Static("Source", classes="section-title")
                yield Static("", id="source-meta")
                yield Static("", id="source-preview")
            with Vertical(id="output-pane"):
                yield Static("ASCII Output", classes="section-title")
                yield Static("", id="output-meta")
                yield TextArea("", id="output")
        yield Footer()

    def on_mount(self) -> None:
        if self.initial_image:
            self.action_render()

    def _set_status(self, text: str) -> None:
        self.query_one("#status", Static).update(text)

    def _float_input(self, widget_id: str, default: float) -> float:
        try:
            return float(self.query_one(f"#{widget_id}", Input).value.strip())
        except ValueError:
            return default

    def _int_input(self, widget_id: str, default: int) -> int:
        try:
            return int(float(self.query_one(f"#{widget_id}", Input).value.strip()))
        except ValueError:
            return default

    def _read_source_meta(self, image_path: str) -> str:
        try:
            path = Path(image_path).expanduser()
            with Image.open(path) as image:
                return f"{path.name} | {image.width}x{image.height} | {image.mode}"
        except Exception:
            return ""

    def _build_request(self) -> ImageAsciiRequest:
        threshold_text = self.query_one("#threshold", Input).value.strip()
        sharpness = self._float_input("sharpness", 1.0)
        edge_intensity = self._float_input("edge-intensity", 0.0)
        return ImageAsciiRequest(
            image_path=self.query_one("#image-path", Input).value.strip(),
            characters=self._int_input("characters", 80),
            brightness=self._float_input("brightness", 100.0),
            contrast=self._float_input("contrast", 100.0),
            saturation=self._float_input("saturation", 100.0),
            hue=self._float_input("hue", 0.0),
            grayscale=self._float_input("grayscale", 100.0),
            sepia=self._float_input("sepia", 0.0),
            invert=self._float_input("invert", 0.0),
            threshold_enabled=bool(threshold_text),
            threshold_offset=self._int_input("threshold", 128),
            sharpen_enabled=sharpness > 1.0,
            sharpness=sharpness,
            edge_enabled=edge_intensity > 0.0,
            edge_intensity=edge_intensity,
            gradient=str(self.query_one("#gradient", Select).value) or "ascii",
            dithering=str(self.query_one("#dither", Select).value) or "none",
            space_density=self._float_input("space-density", 0.0),
            transparent_frame=max(0, self._int_input("transparent-frame", 0)),
            justify=str(self.query_one("#justify", Select).value) or "left",
            fit_mode=str(self.query_one("#fit-mode", Select).value) or "flexible",
            color_mode=str(self.query_one("#color-mode", Select).value) or "plain",
            color=self.query_one("#tint-color", Input).value.strip() or "#C8C8C8",
        )

    def action_render(self) -> None:
        try:
            request = self._build_request()
            result = render_image_ascii(request)
        except Exception as exc:
            self._set_status(f"Render failed: {exc}")
            return

        self.last_result = result
        self.query_one("#output", TextArea).load_text(result.plain_text)
        meta = f"Rendered {result.width}x{result.height} | {request.gradient} | {request.dithering}"
        if request.color_mode == "styled":
            meta = f"{meta} | styled tint {request.color}"
        if result.overflow:
            meta = f"{meta} | overflow"
        if result.warnings:
            meta = f"{meta} | {' | '.join(result.warnings)}"
        self.query_one("#output-meta", Static).update(meta)
        self.query_one("#source-meta", Static).update(self._read_source_meta(request.image_path))
        try:
            self.query_one("#source-preview", Static).update(render_source_preview(request.image_path))
        except Exception:
            self.query_one("#source-preview", Static).update("")
        self._set_status("Rendered image to ASCII")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "render":
            self.action_render()
        elif button_id == "copy":
            if not self.last_result:
                self._set_status("Render something first")
                return
            try:
                copy_to_clipboard(self.last_result.plain_text)
                self._set_status("Copied ASCII output to clipboard")
            except Exception as exc:
                self._set_status(f"Copy failed: {exc}")
        elif button_id == "save-text":
            if not self.last_result:
                self._set_status("Render something first")
                return
            try:
                path = save_text(self.last_result.plain_text, self.query_one("#export-text-path", Input).value.strip())
                self._set_status(f"Saved TXT -> {path}")
            except Exception as exc:
                self._set_status(f"Save TXT failed: {exc}")
        elif button_id == "save-png":
            if not self.last_result:
                self._set_status("Render something first")
                return
            try:
                path = save_png_from_markup(self.last_result.rich_markup, self.query_one("#export-png-path", Input).value.strip())
                self._set_status(f"Saved PNG -> {path}")
            except Exception as exc:
                self._set_status(f"Save PNG failed: {exc}")
