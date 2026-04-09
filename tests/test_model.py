from __future__ import annotations

import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from skinwalker.model import import_skin_yaml_file, parse_skin_yaml  # noqa: E402


class SkinYamlParsingTests(unittest.TestCase):
    def test_parse_skin_yaml_normalizes_mapping(self) -> None:
        parsed = parse_skin_yaml(
            """
name: Example Skin
description: Test skin
colors:
  banner_border: abc123
branding:
  agent_name: Test Bot
"""
        )

        self.assertEqual(parsed["name"], "example-skin")
        self.assertEqual(parsed["description"], "Test skin")
        self.assertEqual(parsed["colors"]["banner_border"], "#ABC123")
        self.assertEqual(parsed["branding"]["agent_name"], "Test Bot")

    def test_parse_skin_yaml_rejects_non_mapping(self) -> None:
        with self.assertRaises(ValueError):
            parse_skin_yaml("- nope")

    def test_import_skin_yaml_file_reads_from_disk(self) -> None:
        path = ROOT / ".tmp_test_skin.yaml"
        try:
            path.write_text("name: demo\ndescription: demo\n", encoding="utf-8")
            parsed = import_skin_yaml_file(str(path))
        finally:
            path.unlink(missing_ok=True)

        self.assertEqual(parsed["name"], "demo")


if __name__ == "__main__":
    unittest.main()
