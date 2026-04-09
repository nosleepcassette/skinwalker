from __future__ import annotations

import argparse

from . import __version__
from .app import SkinwalkerApp
from .hermes import HermesBridge


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TUI editor for Hermes CLI skins")
    parser.add_argument("--hermes-root", help="Path to Hermes source checkout")
    parser.add_argument("--dump-active", action="store_true", help="Print the current active Hermes skin and exit")
    parser.add_argument("--version", action="version", version=f"skinwalker {__version__}")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.dump_active:
        bridge = HermesBridge(hermes_root=args.hermes_root)
        print(bridge.get_active_skin_name())
        return

    app = SkinwalkerApp(hermes_root=args.hermes_root)
    app.run()


if __name__ == "__main__":
    main()
