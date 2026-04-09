from __future__ import annotations

import sys
from pathlib import Path
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from skinwalker.art import generate_hero_markup, generate_logo_result  # noqa: E402


class ArtGenerationTests(unittest.TestCase):
    def test_generate_logo_result_returns_dimensions_and_font(self) -> None:
        result = generate_logo_result("Skinwalker", "standard", "#FFFFFF", width=80)
        self.assertEqual(result.font, "standard")
        self.assertGreater(result.width, 0)
        self.assertGreater(result.height, 0)
        self.assertTrue(result.markup)

    def test_generate_hero_markup_supports_adjustments(self) -> None:
        path = ROOT / ".tmp_test_hero.png"
        try:
            Image.new("RGB", (24, 24), (128, 128, 128)).save(path)
            result = generate_hero_markup(
                path,
                "ascii",
                20,
                "#FFFFFF",
                brightness=1.2,
                contrast=1.1,
                invert=True,
                threshold=140,
                sharpen=1.4,
                edge_strength=0.25,
            )
        finally:
            path.unlink(missing_ok=True)

        self.assertEqual(result.style, "ascii")
        self.assertGreater(result.width, 0)
        self.assertGreater(result.height, 0)
        self.assertTrue(result.markup)


if __name__ == "__main__":
    unittest.main()
