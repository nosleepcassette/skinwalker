from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .model import normalize_skin, sanitize_skin_name


@dataclass(frozen=True)
class LibraryEntry:
    name: str
    description: str
    source: str
    invalid: bool = False
    error: str = ""


class HermesBridge:
    def __init__(self, hermes_root: str | Path | None = None) -> None:
        root = hermes_root or os.getenv("HERMES_AGENT_ROOT") or Path.home() / ".hermes" / "hermes-agent"
        self.hermes_root = Path(root).expanduser().resolve()
        if not self.hermes_root.exists():
            raise FileNotFoundError(f"Hermes source root not found: {self.hermes_root}")

        if str(self.hermes_root) not in sys.path:
            sys.path.insert(0, str(self.hermes_root))

        from hermes_constants import get_hermes_home  # type: ignore
        from hermes_cli import skin_engine  # type: ignore

        self._get_hermes_home = get_hermes_home
        self._skin_engine = skin_engine

    @property
    def hermes_home(self) -> Path:
        return Path(self._get_hermes_home()).expanduser().resolve()

    @property
    def skins_dir(self) -> Path:
        return self.hermes_home / "skins"

    @property
    def config_path(self) -> Path:
        return self.hermes_home / "config.yaml"

    @property
    def builtin_templates(self) -> dict[str, dict[str, Any]]:
        return dict(self._skin_engine._BUILTIN_SKINS)

    @property
    def builtin_names(self) -> set[str]:
        return set(self.builtin_templates)

    def ensure_dirs(self) -> None:
        self.skins_dir.mkdir(parents=True, exist_ok=True)

    def get_active_skin_name(self) -> str:
        try:
            parsed = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
            return str(parsed.get("display", {}).get("skin", "default"))
        except Exception:
            return "default"

    def _skin_config_to_dict(self, skin_config: Any) -> dict:
        return normalize_skin(
            {
                "name": skin_config.name,
                "description": skin_config.description,
                "colors": dict(skin_config.colors),
                "spinner": dict(skin_config.spinner),
                "branding": dict(skin_config.branding),
                "tool_prefix": skin_config.tool_prefix,
                "tool_emojis": dict(skin_config.tool_emojis),
                "banner_logo": skin_config.banner_logo,
                "banner_hero": skin_config.banner_hero,
            }
        )

    def list_builtin_skins(self) -> list[LibraryEntry]:
        return [
            LibraryEntry(
                name=name,
                description=str(data.get("description", "")),
                source="builtin",
            )
            for name, data in self.builtin_templates.items()
        ]

    def list_user_skins(self) -> list[LibraryEntry]:
        self.ensure_dirs()
        result: list[LibraryEntry] = []

        for path in sorted(self.skins_dir.glob("*.yaml")):
            try:
                parsed = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                name = str(parsed.get("name", path.stem))
                if name in self.builtin_names:
                    continue
                result.append(
                    LibraryEntry(
                        name=name,
                        description=str(parsed.get("description", "")),
                        source="user",
                    )
                )
            except Exception as exc:
                result.append(
                    LibraryEntry(
                        name=path.stem,
                        description="Unreadable skin file",
                        source="user",
                        invalid=True,
                        error=str(exc),
                    )
                )

        return result

    def list_skins(self) -> list[LibraryEntry]:
        return self.list_builtin_skins() + self.list_user_skins()

    def load_skin(self, name: str, source: str | None = None) -> dict:
        normalized_name = sanitize_skin_name(name)

        if source == "builtin":
            if normalized_name not in self.builtin_templates:
                raise FileNotFoundError(f"Built-in skin not found: {normalized_name}")
            skin_config = self._skin_engine._build_skin_config(self.builtin_templates[normalized_name])
            return self._skin_config_to_dict(skin_config)

        if source == "user":
            path = self.skins_dir / f"{normalized_name}.yaml"
            if not path.exists():
                raise FileNotFoundError(f"Custom skin not found: {normalized_name}")

        skin_config = self._skin_engine.load_skin(normalized_name)
        return self._skin_config_to_dict(skin_config)

    def dump_skin_yaml(self, skin: dict, *, strict: bool = True) -> str:
        return yaml.safe_dump(
            normalize_skin(skin, strict=strict),
            sort_keys=False,
            allow_unicode=True,
            width=120,
        )

    def save_skin(self, skin: dict) -> Path:
        normalized = normalize_skin(skin)
        if normalized["name"] in self.builtin_names:
            raise ValueError("Custom skin names may not shadow built-in skins")

        self.ensure_dirs()
        path = self.skins_dir / f"{normalized['name']}.yaml"
        path.write_text(self.dump_skin_yaml(normalized), encoding="utf-8")
        return path

    def delete_skin(self, name: str) -> None:
        normalized_name = sanitize_skin_name(name)
        if normalized_name in self.builtin_names:
            raise ValueError("Built-in skins cannot be deleted")
        path = self.skins_dir / f"{normalized_name}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Custom skin not found: {normalized_name}")
        path.unlink()

    def _update_display_skin_in_config(self, content: str, skin_name: str) -> str:
        lines = content.splitlines()
        display_index = next((index for index, line in enumerate(lines) if line.strip() == "display:"), -1)

        if display_index == -1:
            suffix = "" if not content or content.endswith("\n") else "\n"
            return f"{content}{suffix}display:\n  skin: {skin_name}\n"

        block_end = len(lines)
        for index in range(display_index + 1, len(lines)):
            line = lines[index]
            if line and not line.startswith((" ", "#")) and ":" in line:
                block_end = index
                break

        for index in range(display_index + 1, block_end):
            if lines[index].startswith("  skin:"):
                lines[index] = f"  skin: {skin_name}"
                return "\n".join(lines) + "\n"

        lines.insert(display_index + 1, f"  skin: {skin_name}")
        return "\n".join(lines) + "\n"

    def activate_skin(self, name: str) -> None:
        normalized_name = sanitize_skin_name(name)
        content = ""
        if self.config_path.exists():
            content = self.config_path.read_text(encoding="utf-8")
        updated = self._update_display_skin_in_config(content, normalized_name)
        self.config_path.write_text(updated, encoding="utf-8")
