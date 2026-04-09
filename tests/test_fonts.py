from __future__ import annotations

import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from skinwalker.fonts import categorize_font, filter_fonts  # noqa: E402


class FontMetadataTests(unittest.TestCase):
    def test_categorize_font_prefers_featured(self) -> None:
        self.assertEqual(categorize_font("standard"), "featured")

    def test_filter_fonts_applies_category_and_query(self) -> None:
        fonts = ["standard", "banner3-d", "small", "bubble"]
        filtered = filter_fonts(fonts, category="shadow-3d", query="banner")
        self.assertEqual(filtered, ["banner3-d"])


if __name__ == "__main__":
    unittest.main()
