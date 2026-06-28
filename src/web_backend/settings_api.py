from __future__ import annotations

import json
import os

from fastapi import HTTPException

from src import workspace_settings
from src.config_loader import ConfigLoader
from src.file_transaction import atomic_write_text

from .domain_base import DomainBase
from . import runtime_paths


SETTINGS_SECTIONS = {
    "module-provider": {
        "label": "moduleProvider",
        "filename": "moduleProvider.json",
    },
    "defaults": {
        "label": "Default settings",
        "filename": "config.json",
    },
    "companion": {
        "label": "Companion",
        "filename": "config.json",
    },
}


class SettingsApiDomain(DomainBase):
    def _section_meta(self, section: str) -> dict:
        safe_section = str(section or "").strip()
        meta = SETTINGS_SECTIONS.get(safe_section)
        if meta is None:
            raise HTTPException(status_code=404, detail=f"unknown settings section: {safe_section}")
        return {"id": safe_section, **meta}

    def _settings_path(self, section: str) -> str:
        if section == "module-provider":
            explicit_path = str(os.environ.get(ConfigLoader.CONFIG_PATH_ENV) or "").strip()
            if explicit_path:
                return os.path.abspath(explicit_path)
            return os.path.join(workspace_settings.get_workspace_root(), "config", "moduleProvider.json")
        if section == "defaults":
            explicit_path = str(os.environ.get(ConfigLoader.CONFIG_PATH_ENV) or "").strip()
            if explicit_path:
                return os.path.join(os.path.dirname(os.path.abspath(explicit_path)), "config.json")
            return workspace_settings.get_workspace_config_path()
        if section == "companion":
            return os.path.join(runtime_paths._get_graphs_dir(), "companion", "config.json")
        raise HTTPException(status_code=404, detail=f"unknown settings section: {section}")

    def _read_payload(self, path: str, section: str) -> tuple[str, dict]:
        if not os.path.isfile(path):
            raise HTTPException(status_code=404, detail=f"{section} settings file not found: {path}")
        try:
            with open(path, "r", encoding="utf-8") as handle:
                content = handle.read()
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=500, detail=f"{section} settings JSON is invalid: {exc}") from exc
        except OSError as exc:
            raise HTTPException(status_code=500, detail=f"failed to read {section} settings: {exc}") from exc
        self._validate_payload(section, payload)
        return content, payload

    def _parse_content(self, section: str, content: object) -> dict:
        if not isinstance(content, str):
            raise HTTPException(status_code=400, detail="content must be a JSON string")
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"{section} settings JSON is invalid: {exc}") from exc
        self._validate_payload(section, payload)
        return payload

    def _validate_payload(self, section: str, payload: object) -> None:
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail=f"{section} settings must be a top-level object")
        if section == "module-provider":
            providers = payload.get("providers")
            if not isinstance(providers, dict):
                raise HTTPException(status_code=400, detail="moduleProvider.json field 'providers' must be an object")
            for provider_id, provider in providers.items():
                if not str(provider_id or "").strip():
                    raise HTTPException(status_code=400, detail="provider id must be non-empty")
                if not isinstance(provider, dict):
                    raise HTTPException(
                        status_code=400,
                        detail=f"provider '{provider_id}' configuration must be an object",
                    )
        elif section == "defaults":
            for key in ("server", "agentNode", "graphRunner", "consoleCommand", "nodeMemory", "mcpServers"):
                value = payload.get(key)
                if value is not None and not isinstance(value, dict):
                    raise HTTPException(status_code=400, detail=f"config.json field '{key}' must be an object")
        elif section == "companion":
            type_id = str(payload.get("type_id") or "agent_node").strip() or "agent_node"
            if type_id != "agent_node":
                raise HTTPException(status_code=400, detail="companion config field 'type_id' must be 'agent_node'")
            for key in ("tools", "mcp_servers", "skills", "plugins"):
                value = payload.get(key)
                if value is not None and not isinstance(value, list):
                    raise HTTPException(status_code=400, detail=f"companion config field '{key}' must be a list")
            ui = payload.get("ui")
            if ui is not None and not isinstance(ui, dict):
                raise HTTPException(status_code=400, detail="companion config field 'ui' must be an object")

    def list_settings_sections(self):
        sections = []
        for section_id in SETTINGS_SECTIONS:
            meta = self._section_meta(section_id)
            sections.append(
                {
                    "id": meta["id"],
                    "label": meta["label"],
                    "path": self._settings_path(section_id),
                    "filename": meta["filename"],
                }
            )
        return {"sections": sections}

    def get_settings_section(self, section: str):
        meta = self._section_meta(section)
        path = self._settings_path(meta["id"])
        content, payload = self._read_payload(path, meta["id"])
        return {
            "section": meta["id"],
            "label": meta["label"],
            "path": path,
            "content": content,
            "data": payload,
        }

    def update_settings_section(self, section: str, payload: dict):
        meta = self._section_meta(section)
        path = self._settings_path(meta["id"])
        parsed = self._parse_content(meta["id"], (payload or {}).get("content"))
        content = json.dumps(parsed, ensure_ascii=False, indent=2) + "\n"
        try:
            atomic_write_text(path, content, encoding="utf-8")
        except OSError as exc:
            raise HTTPException(status_code=500, detail=f"failed to write {meta['id']} settings: {exc}") from exc
        return {
            "ok": True,
            "section": meta["id"],
            "label": meta["label"],
            "path": path,
            "content": content,
            "data": parsed,
        }


__all__ = ["SettingsApiDomain"]
