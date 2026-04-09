from __future__ import annotations

import sys
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from skinwalker.ai import (  # noqa: E402
    _extract_json_object,
    generate_logo_bundle,
    generate_skin_bundle,
    generate_spinner_bundle,
)


class AIHelpersTests(unittest.TestCase):
    def test_extract_json_object_accepts_surrounding_text(self) -> None:
        payload = _extract_json_object('noise {"branding":{"agent_name":"Cass"}} trailing')
        self.assertEqual(payload["branding"]["agent_name"], "Cass")

    @patch("skinwalker.ai.generate_json")
    def test_generate_spinner_bundle_normalizes_lists(self, generate_json_mock) -> None:
        generate_json_mock.return_value = {
            "spinner": {
                "waiting_faces": [" ◐ ", ""],
                "thinking_faces": [" ◓ "],
                "thinking_verbs": [" routing ", ""],
                "wings": [[" ‹ ", " › "], ["", ""]],
            }
        }
        spinner = generate_spinner_bundle({"name": "cass"}, backend="hermes", direction="focused")
        self.assertEqual(spinner["waiting_faces"], ["◐"])
        self.assertEqual(spinner["thinking_faces"], ["◓"])
        self.assertEqual(spinner["thinking_verbs"], ["routing"])
        self.assertEqual(spinner["wings"], [["‹", "›"]])

    @patch("skinwalker.ai.generate_json")
    def test_generate_logo_bundle_rejects_unknown_style_hint(self, generate_json_mock) -> None:
        generate_json_mock.return_value = {
            "logo": {
                "title": "Cassette",
                "style_hint": "unknown-style",
                "art": "[]",
            }
        }
        logo = generate_logo_bundle({"name": "cass"}, backend="hermes")
        self.assertEqual(logo["title"], "Cassette")
        self.assertEqual(logo["style_hint"], "")
        self.assertEqual(logo["art"], "[]")

    @patch("skinwalker.ai.generate_json")
    def test_generate_skin_bundle_normalizes_nested_sections(self, generate_json_mock) -> None:
        generate_json_mock.return_value = {
            "branding": {"agent_name": "Cass", "welcome": "Ready"},
            "spinner": {"waiting_faces": ["◐"], "thinking_faces": ["◓"], "thinking_verbs": ["routing"], "wings": [["<", ">"]]},
            "logo": {"title": "Cass", "style_hint": "shadow", "art": ""},
            "hero": {"art": "/\\\n||"},
        }
        bundle = generate_skin_bundle({"name": "cass"}, backend="hermes")
        self.assertEqual(bundle["branding"]["agent_name"], "Cass")
        self.assertEqual(bundle["spinner"]["thinking_verbs"], ["routing"])
        self.assertEqual(bundle["logo"]["style_hint"], "shadow")
        self.assertEqual(bundle["hero"]["art"], "/\\\n||")


if __name__ == "__main__":
    unittest.main()
