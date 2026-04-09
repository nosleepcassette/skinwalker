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
    path: str = ""
    note: str = ""


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

    @property
    def profiles_root(self) -> Path:
        return Path.home() / ".hermes" / "profiles"

    def ensure_dirs(self) -> None:
        self.skins_dir.mkdir(parents=True, exist_ok=True)

    def current_profile_name(self) -> str:
        default_home = (Path.home() / ".hermes").resolve()
        profiles_root = self.profiles_root.resolve()
        current_home = self.hermes_home

        if current_home == default_home:
            return "default"

        try:
            relative = current_home.relative_to(profiles_root)
        except ValueError:
            return "custom"

        parts = relative.parts
        if not parts:
            return "default"
        return parts[0]

    def list_profiles(self) -> list[str]:
        profiles = ["default"]
        if not self.profiles_root.exists():
            return profiles
        profiles.extend(path.name for path in sorted(self.profiles_root.iterdir()) if path.is_dir())
        return profiles

    def config_path_for_profile(self, profile: str | None = None) -> Path:
        profile_name = str(profile or "").strip() or self.current_profile_name()
        if profile_name in {"", "default", "custom"}:
            if profile_name == "custom":
                return self.config_path
            return Path.home() / ".hermes" / "config.yaml"
        return self.profiles_root / profile_name / "config.yaml"

    def get_active_skin_name(self, *, profile: str | None = None) -> str:
        try:
            path = self.config_path if profile is None else self.config_path_for_profile(profile)
            parsed = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
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
        grouped: dict[str, list[tuple[Path, str]]] = {}
        invalid_entries: list[LibraryEntry] = []

        for path in sorted(self.skins_dir.glob("*.yaml")):
            try:
                parsed = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                name = str(parsed.get("name", path.stem))
                if name in self.builtin_names:
                    continue
                grouped.setdefault(name, []).append((path, str(parsed.get("description", ""))))
            except Exception as exc:
                invalid_entries.append(
                    LibraryEntry(
                        name=path.stem,
                        description="Unreadable skin file",
                        source="user",
                        invalid=True,
                        error=str(exc),
                        path=str(path),
                    )
                )

        result: list[LibraryEntry] = []
        for name in sorted(grouped):
            options = grouped[name]
            canonical_path, canonical_description = next(
                ((path, description) for path, description in options if path.stem == name),
                options[0],
            )
            description = canonical_description or next((desc for _, desc in options if desc), "")
            note = ""
            if len(options) > 1:
                duplicates = ", ".join(path.name for path, _ in options if path != canonical_path)
                note = f"Duplicate definitions ignored: {duplicates}"
            result.append(
                LibraryEntry(
                    name=name,
                    description=description,
                    source="user",
                    path=str(canonical_path),
                    note=note,
                )
            )

        return result + invalid_entries

    def list_skins(self) -> list[LibraryEntry]:
        return self.list_builtin_skins() + self.list_user_skins()

    def load_skin(self, name: str, source: str | None = None, *, path: str | Path | None = None) -> dict:
        normalized_name = sanitize_skin_name(name)

        if source == "builtin":
            if normalized_name not in self.builtin_templates:
                raise FileNotFoundError(f"Built-in skin not found: {normalized_name}")
            skin_config = self._skin_engine._build_skin_config(self.builtin_templates[normalized_name])
            return self._skin_config_to_dict(skin_config)

        if source == "user":
            file_path = Path(path).expanduser() if path else self.skins_dir / f"{normalized_name}.yaml"
            if not file_path.exists():
                raise FileNotFoundError(f"Custom skin not found: {normalized_name}")
            try:
                parsed = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
            except Exception as exc:
                raise ValueError(f"Could not parse skin file: {file_path}") from exc
            skin_config = self._skin_engine._build_skin_config(parsed)
            return self._skin_config_to_dict(skin_config)

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

    def activate_skin(self, name: str, *, profile: str | None = None) -> None:
        normalized_name = sanitize_skin_name(name)
        content = ""
        config_path = self.config_path if profile is None else self.config_path_for_profile(profile)
        if config_path.exists():
            content = config_path.read_text(encoding="utf-8")
        updated = self._update_display_skin_in_config(content, normalized_name)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(updated, encoding="utf-8")
