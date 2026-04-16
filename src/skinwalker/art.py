from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from pyfiglet import Figlet, FigletFont
from rich.markup import escape

from .model import FIGLET_STYLE_MAP


@dataclass(frozen=True)
class LogoResult:
    plain: str
    markup: str
    font: str
    width: int
    height: int


@dataclass(frozen=True)
class HeroResult:
    markup: str
    style: str
    width: int
    height: int


HERO_STYLE_MAP = {
    "braille": {"renderer": "braille"},
    "ascii": {"renderer": "ramp", "chars": " .'`^\",:;Il!i~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"},
    "minimal": {"renderer": "ramp", "chars": " .:-=+*#%@"},
    "minimalist": {"renderer": "ramp", "chars": " .:-=+*#%@"},
    "blocks": {"renderer": "ramp", "chars": " ░▒▓█"},
    "blockelement": {"renderer": "ramp", "chars": " ░▒▓█"},
    "dots": {"renderer": "ramp", "chars": " .·•●"},
    "alphabetic": {"renderer": "ramp", "chars": " abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"},
    "alphanumeric": {"renderer": "ramp", "chars": " 0123456789abcdefghijklmnopqrstuvwxyz"},
    "numerical": {"renderer": "ramp", "chars": " 0123456789"},
    "math": {"renderer": "ramp", "chars": " +-*/=<>^~%#@"},
    "normal": {"renderer": "ramp", "chars": " .'`^\",:;Il!i~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"},
    "normal2": {"renderer": "ramp", "chars": " .,:;irsXA253hMHGS#9B&@"},
    "grayscale": {"renderer": "ramp", "chars": " .,:;ox%#@"},
    "extended": {"renderer": "ramp", "chars": " .·•*-+=rcxzvujfJCLQ0OZmwqpdbkhao#MW&8%B@$"},
    "codepage437": {"renderer": "ramp", "chars": " .░▒▓█"},
    "max": {"renderer": "ramp", "chars": " .'`^\",:;Il!i~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"},
    "arrow": {"renderer": "ramp", "chars": " ·←↑→↓↖↗↘↙◀▶▲▼"},
    "arrows": {"renderer": "ramp", "chars": " ·←↑→↓↖↗↘↙◀▶▲▼"},
    "dense": {"renderer": "ramp", "chars": " .'`^\",:;Il!i~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"},
}

BRAILLE_BIT_GRID = [
    [0x01, 0x08],
    [0x02, 0x10],
    [0x04, 0x20],
    [0x40, 0x80],
]

JUSTIFY_MAP = {"left": "left", "center": "center", "right": "right"}
FIT_MODE_MAP = {"flex": "flexible", "flexible": "flexible", "fixed": "fixed"}


def build_rich_block(text: str, color: str, *, bold: bool = False, dim: bool = False) -> str:
    cleaned = text.rstrip()
    if not cleaned:
        return ""

    styles = [part for part in ("bold" if bold else "", "dim" if dim else "", color) if part]
    style = " ".join(styles).strip()
    return f"[{style}]{escape(cleaned)}[/]" if style else escape(cleaned)


@lru_cache(maxsize=1)
def list_logo_fonts() -> list[str]:
    preferred = [
        "standard",
        "slant",
        "small",
        "doom",
        "big",
        "banner",
        "banner3-d",
        "lean",
        "univers",
        "roman",
        "cyberlarge",
        "shadow",
        "ghost",
    ]
    fonts = sorted(FigletFont.getFonts(), key=str.lower)
    preferred_available = [font for font in preferred if font in fonts]
    return preferred_available + [font for font in fonts if font not in preferred_available]


def _normalize_justify(value: str) -> str:
    justify = str(value or "").strip().lower() or "left"
    if justify not in JUSTIFY_MAP:
        raise ValueError(f"Unknown justification: {value}")
    return JUSTIFY_MAP[justify]


def _normalize_fit_mode(value: str) -> str:
    fit_mode = str(value or "").strip().lower() or "flexible"
    if fit_mode not in FIT_MODE_MAP:
        raise ValueError(f"Unknown fit mode: {value}")
    return FIT_MODE_MAP[fit_mode]


def _clamp_output_width(width: int, *, minimum: int = 16, maximum: int = 200) -> int:
    return max(minimum, min(maximum, int(width)))


def _format_generated_block(text: str, *, justify: str = "left", fit: str = "flexible", width: int | None = None) -> str:
    lines = [line.rstrip() for line in str(text or "").splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""

    justify_mode = _normalize_justify(justify)
    fit_mode = _normalize_fit_mode(fit)
    content_width = max(len(line) for line in lines)
    target_width = content_width
    if width is not None and fit_mode == "fixed":
        target_width = max(content_width, _clamp_output_width(width))

    formatted: list[str] = []
    for line in lines:
        if justify_mode == "left":
            formatted_line = line if fit_mode == "flexible" else line.ljust(target_width)
        elif justify_mode == "center":
            if fit_mode == "fixed":
                formatted_line = line.center(target_width)
            else:
                padding = max(0, (content_width - len(line)) // 2)
                formatted_line = (" " * padding) + line
        else:
            formatted_line = line.rjust(target_width)
        formatted.append(formatted_line)

    return "\n".join(formatted)


def resolve_logo_font(style: str) -> str:
    raw_style = str(style or "").strip()
    if not raw_style:
        return FIGLET_STYLE_MAP["minimal"]

    alias = FIGLET_STYLE_MAP.get(raw_style.lower())
    if alias:
        return alias

    available = set(list_logo_fonts())
    candidates = [
        raw_style,
        raw_style.lower(),
        raw_style.lower().replace(" ", "_"),
        raw_style.lower().replace(" ", "-"),
        raw_style.lower().replace("-", "_"),
        raw_style.lower().replace("_", "-"),
    ]
    for candidate in candidates:
        if candidate in available:
            return candidate

    raise ValueError(f"Unknown figlet style: {style}")


def generate_logo_result(
    title: str,
    style: str,
    color: str,
    *,
    width: int = 120,
    justify: str = "left",
    fit: str = "flexible",
) -> LogoResult:
    title = title.strip()
    if not title:
        raise ValueError("Enter a title before generating logo art")

    font_name = resolve_logo_font(style)
    width = _clamp_output_width(width, minimum=24, maximum=240)
    try:
        figlet = Figlet(font=font_name, width=width)
    except Exception as exc:
        raise ValueError(f"Unknown figlet style: {style}") from exc

    plain = _format_generated_block(figlet.renderText(title), justify=justify, fit=fit, width=width)
    height = len(plain.splitlines()) if plain else 0
    return LogoResult(
        plain=plain,
        markup=build_rich_block(plain, color, bold=True),
        font=font_name,
        width=max((len(line) for line in plain.splitlines()), default=0),
        height=height,
    )


def generate_logo_markup(
    title: str,
    style: str,
    color: str,
    *,
    width: int = 120,
    justify: str = "left",
    fit: str = "flexible",
) -> str:
    return generate_logo_result(title, style, color, width=width, justify=justify, fit=fit).markup


def import_art_text(text: str, color: str, *, mode: str = "plain", bold: bool = False, dim: bool = False) -> str:
    content = str(text or "")
    if not content.strip():
        raise ValueError("Nothing to import")

    import_mode = mode.strip().lower() or "plain"
    if import_mode == "markup":
        return content.rstrip()
    if import_mode != "plain":
        raise ValueError("Import mode must be 'plain' or 'markup'")
    return build_rich_block(content, color, bold=bold, dim=dim)


def import_art_file(path: str | Path, color: str, *, mode: str = "plain", bold: bool = False, dim: bool = False) -> str:
    file_path = Path(path).expanduser()
    if not file_path.exists():
        raise FileNotFoundError(f"Art file not found: {file_path}")
    return import_art_text(file_path.read_text(encoding="utf-8"), color, mode=mode, bold=bold, dim=dim)


def _load_image(image_path: str | Path) -> Image.Image:
    path = Path(image_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    image = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    return image


def _clamp_width(width: int) -> int:
    return max(16, min(120, int(width)))


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _prepare_image(
    image: Image.Image,
    *,
    brightness: float = 1.0,
    contrast: float = 1.0,
    invert: bool | float = False,
    threshold: int | None = None,
    sharpen: float = 1.0,
    edge_strength: float = 0.0,
    saturation: float = 1.0,
    hue_shift: float = 0.0,
    sepia: float = 0.0,
    grayscale_blend: float = 1.0,
) -> Image.Image:
    prepared = image.copy()
    if saturation != 1.0:
        prepared = ImageEnhance.Color(prepared).enhance(max(0.0, saturation))
    if hue_shift != 0.0:
        import colorsys

        rgb = prepared.convert("RGB")
        pixels = rgb.load()
        w, h = rgb.size
        for y in range(h):
            for x in range(w):
                r, g, b = pixels[x, y]
                hh, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                hh = (hh + hue_shift / 360.0) % 1.0
                r2, g2, b2 = colorsys.hsv_to_rgb(hh, s, v)
                pixels[x, y] = (int(r2 * 255), int(g2 * 255), int(b2 * 255))
        prepared = rgb
    if sepia > 0.0:
        sepia_amount = _clamp_unit(sepia)
        rgb = prepared.convert("RGB")
        pixels = list(rgb.getdata())
        sepia_pixels = []
        for r, g, b in pixels:
            tr = int(min(255, r * 0.393 + g * 0.769 + b * 0.189))
            tg = int(min(255, r * 0.349 + g * 0.686 + b * 0.168))
            tb = int(min(255, r * 0.272 + g * 0.534 + b * 0.131))
            sr = int(r * (1 - sepia_amount) + tr * sepia_amount)
            sg = int(g * (1 - sepia_amount) + tg * sepia_amount)
            sb = int(b * (1 - sepia_amount) + tb * sepia_amount)
            sepia_pixels.append((sr, sg, sb))
        out = Image.new("RGB", rgb.size)
        out.putdata(sepia_pixels)
        prepared = out
    if brightness != 1.0:
        prepared = ImageEnhance.Brightness(prepared).enhance(max(0.1, brightness))
    if contrast != 1.0:
        prepared = ImageEnhance.Contrast(prepared).enhance(max(0.1, contrast))
    invert_amount = 1.0 if invert is True else 0.0 if not invert else _clamp_unit(invert)
    if invert_amount > 0.0:
        prepared = Image.blend(prepared, ImageOps.invert(prepared), invert_amount)

    grayscale_amount = _clamp_unit(grayscale_blend)
    if grayscale_amount > 0.0:
        monochrome_rgb = prepared.convert("L").convert("RGB")
        prepared = Image.blend(prepared.convert("RGB"), monochrome_rgb, grayscale_amount)

    grayscale = prepared.convert("L")
    grayscale = ImageOps.autocontrast(grayscale)

    if sharpen != 1.0:
        grayscale = ImageEnhance.Sharpness(grayscale).enhance(max(0.0, sharpen))

    if edge_strength > 0.0:
        edges = grayscale.filter(ImageFilter.FIND_EDGES)
        grayscale = Image.blend(grayscale, edges, _clamp_unit(edge_strength))

    if threshold is not None:
        normalized_threshold = max(0, min(255, int(threshold)))
        grayscale = grayscale.point(lambda px: 255 if px >= normalized_threshold else 0)

    return grayscale


def _char_height(image: Image.Image, width: int, aspect_factor: float) -> int:
    if image.width <= 0 or image.height <= 0:
        return width
    return max(1, round((image.height / image.width) * width * aspect_factor))


def _render_ramp(image: Image.Image, chars: str, width: int, space_density: float = 0.0) -> tuple[str, int]:
    height = _char_height(image, width, 0.5)
    resized = image.resize((width, height))
    palette = chars
    steps = len(palette) - 1
    rows: list[str] = []

    for y in range(resized.height):
        chars_row: list[str] = []
        for x in range(resized.width):
            darkness = 1 - (resized.getpixel((x, y)) / 255)
            raw_index = darkness * steps
            adjusted = raw_index - (space_density * steps * 0.3)
            index = max(0, min(steps, round(adjusted)))
            chars_row.append(palette[index])
        rows.append("".join(chars_row).rstrip())

    return "\n".join(rows).strip("\n"), height


def _diffuse(
    pixels: list[list[float]],
    x: int,
    y: int,
    width: int,
    height: int,
    err: float,
    kernel: list[tuple[int, int, float]],
) -> None:
    for dy, dx, weight in kernel:
        ny, nx = y + dy, x + dx
        if 0 <= ny < height and 0 <= nx < width:
            pixels[ny][nx] = max(0.0, min(1.0, pixels[ny][nx] + err * weight))


def _render_ramp_dithered(
    image: Image.Image, chars: str, width: int, algorithm: str
) -> tuple[str, int]:
    """Ramp renderer with error-diffusion dithering."""
    height = _char_height(image, width, 0.5)
    resized = image.resize((width, height))
    steps = len(chars) - 1

    pixels = [[resized.getpixel((x, y)) / 255.0 for x in range(width)] for y in range(height)]

    rows: list[str] = []
    for y in range(height):
        row_chars: list[str] = []
        for x in range(width):
            old_val = pixels[y][x]
            darkness = 1.0 - old_val
            index = max(0, min(steps, round(darkness * steps)))
            row_chars.append(chars[index])
            quant_val = 1.0 - (index / steps)
            err = old_val - quant_val

            if algorithm == "floyd-steinberg":
                _diffuse(
                    pixels,
                    x,
                    y,
                    width,
                    height,
                    err,
                    [
                        (0, 1, 7 / 16),
                        (1, -1, 3 / 16),
                        (1, 0, 5 / 16),
                        (1, 1, 1 / 16),
                    ],
                )
            elif algorithm == "atkinson":
                _diffuse(
                    pixels,
                    x,
                    y,
                    width,
                    height,
                    err,
                    [
                        (0, 1, 1 / 8),
                        (0, 2, 1 / 8),
                        (1, -1, 1 / 8),
                        (1, 0, 1 / 8),
                        (1, 1, 1 / 8),
                        (2, 0, 1 / 8),
                    ],
                )
            elif algorithm == "jjn":
                _diffuse(
                    pixels,
                    x,
                    y,
                    width,
                    height,
                    err,
                    [
                        (0, 1, 7 / 48),
                        (0, 2, 5 / 48),
                        (1, -2, 3 / 48),
                        (1, -1, 5 / 48),
                        (1, 0, 7 / 48),
                        (1, 1, 5 / 48),
                        (1, 2, 3 / 48),
                        (2, -2, 1 / 48),
                        (2, -1, 3 / 48),
                        (2, 0, 5 / 48),
                        (2, 1, 3 / 48),
                        (2, 2, 1 / 48),
                    ],
                )
            elif algorithm == "stucki":
                _diffuse(
                    pixels,
                    x,
                    y,
                    width,
                    height,
                    err,
                    [
                        (0, 1, 8 / 42),
                        (0, 2, 4 / 42),
                        (1, -2, 2 / 42),
                        (1, -1, 4 / 42),
                        (1, 0, 8 / 42),
                        (1, 1, 4 / 42),
                        (1, 2, 2 / 42),
                        (2, -2, 1 / 42),
                        (2, -1, 2 / 42),
                        (2, 0, 4 / 42),
                        (2, 1, 2 / 42),
                        (2, 2, 1 / 42),
                    ],
                )

        rows.append("".join(row_chars).rstrip())

    return "\n".join(rows).strip("\n"), height


def _render_braille(image: Image.Image, width: int) -> tuple[str, int]:
    char_height = _char_height(image, width, 0.5)
    resized = image.resize((width * 2, char_height * 4))
    rows: list[str] = []

    for y in range(0, resized.height, 4):
        line = []
        for x in range(0, resized.width, 2):
            bits = 0
            total_darkness = 0.0
            samples = 0

            for dy in range(4):
                for dx in range(2):
                    px = x + dx
                    py = y + dy
                    if px >= resized.width or py >= resized.height:
                        continue
                    darkness = 1 - (resized.getpixel((px, py)) / 255)
                    total_darkness += darkness
                    samples += 1

            average = total_darkness / max(samples, 1)
            threshold = 0.34 if average >= 0.72 else 0.42 if average >= 0.48 else 0.50

            for dy in range(4):
                for dx in range(2):
                    px = x + dx
                    py = y + dy
                    if px >= resized.width or py >= resized.height:
                        continue
                    darkness = 1 - (resized.getpixel((px, py)) / 255)
                    if darkness >= threshold:
                        bits |= BRAILLE_BIT_GRID[dy][dx]

            line.append(chr(0x2800 + bits) if bits else " ")

        rows.append("".join(line).rstrip())

    return "\n".join(rows).strip("\n"), char_height


def generate_hero_markup(
    image_path: str | Path,
    style: str,
    width: int,
    color: str,
    *,
    justify: str = "left",
    fit: str = "flexible",
    brightness: float = 1.0,
    contrast: float = 1.0,
    invert: bool = False,
    threshold: int | None = None,
    sharpen: float = 1.0,
    edge_strength: float = 0.0,
    saturation: float = 1.0,
    hue_shift: float = 0.0,
    grayscale_blend: float = 1.0,
    sepia: float = 0.0,
    space_density: float = 0.0,
    dither: str = "none",
    padding: int = 0,
) -> HeroResult:
    style_key = style.strip().lower() or "braille"
    if style_key not in HERO_STYLE_MAP:
        raise ValueError(f"Unknown hero style: {style_key}")
    dither_mode = str(dither or "none").strip().lower() or "none"
    valid_dither_modes = {"none", "floyd-steinberg", "atkinson", "jjn", "stucki"}
    if dither_mode not in valid_dither_modes:
        raise ValueError(f"Unknown dither algorithm: {dither}")

    image = _load_image(image_path)
    image = _prepare_image(
        image,
        brightness=brightness,
        contrast=contrast,
        invert=invert,
        threshold=threshold,
        sharpen=sharpen,
        edge_strength=edge_strength,
        saturation=saturation,
        hue_shift=hue_shift,
        grayscale_blend=grayscale_blend,
        sepia=sepia,
    )
    width = _clamp_width(width)

    if HERO_STYLE_MAP[style_key]["renderer"] == "braille":
        plain, height = _render_braille(image, width)
    elif dither_mode != "none":
        plain, height = _render_ramp_dithered(image, HERO_STYLE_MAP[style_key]["chars"], width, dither_mode)
    else:
        plain, height = _render_ramp(image, HERO_STYLE_MAP[style_key]["chars"], width, space_density)

    plain = _format_generated_block(plain, justify=justify, fit=fit, width=width)
    markup = build_rich_block(plain, color)
    padding = max(0, int(padding))
    if padding > 0:
        blank = "\n" * padding
        plain = blank + plain + blank
        markup = blank + markup + blank

    return HeroResult(
        markup=markup,
        style=style_key,
        width=width,
        height=plain.count("\n") + 1 if plain else height,
    )


def _export_ascii_png(markup: str, output_path: str | Path, font_size: int = 14) -> None:
    from PIL import ImageDraw, ImageFont
    from rich.text import Text as RichText

    plain = RichText.from_markup(markup).plain
    lines = plain.splitlines()
    if not lines:
        raise ValueError("No content to export")

    try:
        font = ImageFont.truetype("Courier New.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    dummy = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(dummy)
    char_w = max(draw.textlength(line or " ", font=font) for line in lines) if lines else font_size
    char_h = font_size + 2

    img_w = int(char_w) + 8
    img_h = char_h * len(lines) + 8
    img = Image.new("RGB", (img_w, img_h), color=(10, 10, 10))
    draw = ImageDraw.Draw(img)

    for i, line in enumerate(lines):
        draw.text((4, 4 + i * char_h), line, fill=(200, 200, 200), font=font)

    img.save(str(Path(output_path).expanduser()))


def _export_markup_text(markup: str, output_path: str | Path) -> None:
    from rich.text import Text as RichText

    plain = RichText.from_markup(markup).plain
    path = Path(output_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plain, encoding="utf-8")
