from __future__ import annotations

from pathlib import Path
import subprocess

from rich.markup import escape

from skinwalker.art import _export_ascii_png


def copy_to_clipboard(text: str) -> None:
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)


def save_text(text: str, output_path: str | Path) -> Path:
    path = Path(output_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def save_png_from_text(text: str, output_path: str | Path, font_size: int = 14) -> Path:
    path = Path(output_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    _export_ascii_png(escape(text), path, font_size=font_size)
    return path


def save_png_from_markup(markup: str, output_path: str | Path, font_size: int = 14) -> Path:
    path = Path(output_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    _export_ascii_png(markup, path, font_size=font_size)
    return path
