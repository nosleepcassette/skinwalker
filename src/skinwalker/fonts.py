from __future__ import annotations

from dataclasses import dataclass


FONT_CATEGORIES = [
    "all",
    "featured",
    "clean",
    "slanted",
    "compact",
    "block",
    "shadow-3d",
    "retro",
    "decorative",
    "novelty",
]

FONT_CATEGORY_LABELS = {
    "all": "All Styles",
    "featured": "Featured Picks",
    "clean": "Standard & Clean",
    "slanted": "Slanted & Italic",
    "compact": "Compact & Small",
    "block": "Heavy & Block",
    "shadow-3d": "3D & Shadow",
    "retro": "Retro & Computer",
    "decorative": "Script & Decorative",
    "novelty": "Novelty & Themed",
}

FEATURED_FONTS = {
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
}

SHADOW_TERMS = (
    "3d",
    "3-d",
    "shadow",
    "banner3",
    "banner4",
    "cyber",
    "big_money",
    "ghost",
)
BLOCK_TERMS = (
    "doom",
    "big",
    "block",
    "banner",
    "max",
    "broadway",
    "chunk",
    "colossal",
)
COMPACT_TERMS = (
    "small",
    "mini",
    "tiny",
    "3x5",
    "4x4",
    "5x7",
    "5x8",
    "6x9",
    "6x10",
    "1row",
)
SLANTED_TERMS = (
    "slant",
    "italic",
    "oblique",
    "lean",
)
RETRO_TERMS = (
    "ansi",
    "arcade",
    "computer",
    "pixel",
    "mshebrew",
    "dos",
    "future",
    "o8",
)
DECORATIVE_TERMS = (
    "script",
    "caligraphy",
    "cursive",
    "roman",
    "greek",
    "tengwar",
    "gothic",
    "fraktur",
)
NOVELTY_TERMS = (
    "alligator",
    "avatar",
    "barbwire",
    "bear",
    "bell",
    "bubble",
    "cards",
    "crazy",
    "drpepper",
    "efti",
    "flower",
    "fun",
    "keyboard",
    "letters",
    "mike",
    "poison",
    "puffy",
    "star",
    "swamp",
    "weird",
)


@dataclass(frozen=True)
class FontMeta:
    name: str
    category: str
    tags: tuple[str, ...]


def categorize_font(name: str) -> str:
    normalized = str(name or "").strip().lower()
    if not normalized:
        return "clean"
    if normalized in FEATURED_FONTS:
        return "featured"
    if any(term in normalized for term in SLANTED_TERMS):
        return "slanted"
    if any(term in normalized for term in SHADOW_TERMS):
        return "shadow-3d"
    if any(term in normalized for term in BLOCK_TERMS):
        return "block"
    if any(term in normalized for term in COMPACT_TERMS):
        return "compact"
    if any(term in normalized for term in RETRO_TERMS):
        return "retro"
    if any(term in normalized for term in DECORATIVE_TERMS):
        return "decorative"
    if any(term in normalized for term in NOVELTY_TERMS):
        return "novelty"
    return "clean"


def font_meta(name: str) -> FontMeta:
    normalized = str(name or "").strip().lower()
    tags: list[str] = []

    if normalized in FEATURED_FONTS:
        tags.append("featured")
    if any(term in normalized for term in SLANTED_TERMS):
        tags.append("slanted")
    if any(term in normalized for term in SHADOW_TERMS):
        tags.append("shadow-3d")
    if any(term in normalized for term in BLOCK_TERMS):
        tags.append("block")
    if any(term in normalized for term in COMPACT_TERMS):
        tags.append("compact")
    if any(term in normalized for term in RETRO_TERMS):
        tags.append("retro")
    if any(term in normalized for term in DECORATIVE_TERMS):
        tags.append("decorative")
    if any(term in normalized for term in NOVELTY_TERMS):
        tags.append("novelty")

    if not tags:
        tags.append("clean")

    primary_category = tags[0]
    if primary_category != "featured" and normalized in FEATURED_FONTS:
        primary_category = "featured"

    return FontMeta(name=name, category=primary_category, tags=tuple(dict.fromkeys(tags)))


def filter_fonts(fonts: list[str], *, category: str = "all", query: str = "") -> list[str]:
    selected_category = str(category or "all").strip().lower() or "all"
    query_text = str(query or "").strip().lower()
    results: list[str] = []

    for font_name in fonts:
        meta = font_meta(font_name)
        haystack = " ".join(
            (
                meta.name.lower(),
                meta.category,
                font_category_label(meta.category).lower(),
                *(font_category_label(tag).lower() for tag in meta.tags),
                *meta.tags,
            )
        )
        if selected_category not in {"", "all"} and selected_category not in {meta.category, *meta.tags}:
            continue
        if query_text and query_text not in haystack:
            continue
        results.append(font_name)

    return results


def font_category_label(category: str) -> str:
    return FONT_CATEGORY_LABELS.get(str(category or "").strip().lower(), str(category or "").strip() or "Unknown")


def font_category_options() -> list[tuple[str, str]]:
    return [(font_category_label(category), category) for category in FONT_CATEGORIES]
