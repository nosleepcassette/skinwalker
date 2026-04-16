from __future__ import annotations

from skinwalker.art import HERO_STYLE_MAP

GRADIENTS = dict(HERO_STYLE_MAP)


def gradient_names() -> list[str]:
    return sorted(GRADIENTS)
