from __future__ import annotations

import argparse

from . import __version__
from .app import ImagewalkerApp
from .engine import ImageAsciiRequest, render_image_ascii


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Standalone image-to-ASCII TUI")
    parser.add_argument("image", nargs="?", help="Path to an input image")
    parser.add_argument("--print", dest="print_only", action="store_true", help="Render once to stdout and exit")
    parser.add_argument("--characters", type=int, default=80, help="Target character width")
    parser.add_argument("--gradient", default="ascii", help="Gradient / character set")
    parser.add_argument("--dither", default="none", help="Dithering mode")
    parser.add_argument("--brightness", type=float, default=100.0, help="Brightness percent")
    parser.add_argument("--contrast", type=float, default=100.0, help="Contrast percent")
    parser.add_argument("--saturation", type=float, default=100.0, help="Saturation percent")
    parser.add_argument("--hue", type=float, default=0.0, help="Hue rotation in degrees")
    parser.add_argument("--grayscale", type=float, default=100.0, help="Grayscale blend percent")
    parser.add_argument("--sepia", type=float, default=0.0, help="Sepia percent")
    parser.add_argument("--invert", type=float, default=0.0, help="Invert percent")
    parser.add_argument("--threshold", type=int, help="Enable thresholding with this offset")
    parser.add_argument("--sharpness", type=float, default=1.0, help="Sharpness amount; >1 enables sharpening")
    parser.add_argument("--edge-intensity", type=float, default=0.0, help="Edge intensity; >0 enables edge blending")
    parser.add_argument("--space-density", type=float, default=0.0, help="Space density bias 0-40")
    parser.add_argument("--transparent-frame", type=int, default=0, help="Transparent frame amount 0-10")
    parser.add_argument("--justify", default="left", help="left, center, or right")
    parser.add_argument("--fit-mode", default="flexible", help="flexible or fixed")
    parser.add_argument("--styled", action="store_true", help="Use styled markup output when printing")
    parser.add_argument("--color", default="#C8C8C8", help="Tint color for styled output")
    parser.add_argument("--version", action="version", version=f"imagewalker {__version__}")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.print_only:
        if not args.image:
            parser.error("image path is required with --print")
        result = render_image_ascii(
            ImageAsciiRequest(
                image_path=args.image,
                characters=args.characters,
                brightness=args.brightness,
                contrast=args.contrast,
                saturation=args.saturation,
                hue=args.hue,
                grayscale=args.grayscale,
                sepia=args.sepia,
                invert=args.invert,
                threshold_enabled=args.threshold is not None,
                threshold_offset=args.threshold or 128,
                sharpen_enabled=args.sharpness > 1.0,
                sharpness=args.sharpness,
                edge_enabled=args.edge_intensity > 0.0,
                edge_intensity=args.edge_intensity,
                gradient=args.gradient,
                dithering=args.dither,
                space_density=args.space_density,
                transparent_frame=args.transparent_frame,
                justify=args.justify,
                fit_mode=args.fit_mode,
                color_mode="styled" if args.styled else "plain",
                color=args.color,
            )
        )
        print(result.rich_markup if args.styled else result.plain_text)
        return

    app = ImagewalkerApp(initial_image=args.image or "")
    app.run()


if __name__ == "__main__":
    main()
