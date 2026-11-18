"""Configuration management - load/save config.json with light password obfuscation."""
import base64
import json
import os
from typing import Any, Dict, List, Optional

from .paths import legacy_config_paths, user_config_path

# Frozen builds keep this in a per-user directory; see app/paths.py for why the
# bundle itself is not writable.
CONFIG_FILE = user_config_path()


# Supported database types shown in dropdown -> (display name, type code, default port)
DB_TYPES = [
    ("MySQL", "mysql", 3306),
    ("MariaDB", "mariadb", 3306),
    ("PostgreSQL", "postgresql", 5432),
    ("OpenGauss", "opengauss", 5432),
    ("瀚高（HighGo）", "highgo", 5866),
    ("海量（Vastbase）", "vastbase", 5432),
    ("人大金仓（KingbaseES）", "kingbase", 54321),
    ("OceanBase", "oceanbase", 2881),
    ("TiDB", "tidb", 4000),
    ("达梦（DM）", "dm", 5236),
    ("南大通用（GBase 8a）", "gbase", 5258),
    ("Oracle", "oracle", 1521),
    ("SQL Server", "mssql", 1433),
    ("DB2", "db2", 50000),
    ("其他（自定义）", "custom", 0),
]

# Supported AI providers.
# Tuple: (display name, code, protocol, default base url, default model)
#   protocol: "openai" (OpenAI-compatible /chat/completions) or
#             "anthropic" (Anthropic Messages API /messages)
#
# A vendor normally speaks one wire protocol and appears once below. Vendors
# that expose BOTH protocols on different endpoints appear once here and carry
# a per-protocol URL map in DUAL_PROTOCOL_PRESETS — the vendor dropdown shows a
# single entry, and flipping the protocol dropdown rewrites the base URL.
AI_PROVIDERS = [
    # ── OpenAI-compatible vendors ─────────────────────────────────────
    ("OpenAI", "openai", "openai", "https://api.openai.com/v1", "gpt-4o-mini"),
    ("阿里百炼", "bailian", "openai", "https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-max"),
    ("千问", "qwen", "openai", "https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus"),
    ("火山引擎", "volcengine", "openai",
     "https://ark.cn-beijing.volces.com/api/coding/v3", "ark-code-latest"),
    ("豆包", "doubao", "openai", "https://ark.cn-beijing.volces.com/api/v3", "doubao-pro-32k"),
    ("DeepSeek", "deepseek", "openai", "https://api.deepseek.com/v1", "deepseek-chat"),
    ("百度千帆", "qianfan", "openai", "https://qianfan.baidubce.com/v2", "ernie-4.0-turbo-8k"),
    ("智谱 GLM", "zhipu", "openai", "https://open.bigmodel.cn/api/paas/v4", "glm-4-plus"),
    ("Kimi", "kimi", "openai", "https://api.moonshot.cn/v1", "moonshot-v1-8k"),
    ("胜算云", "shengsuanyun", "openai", "https://router.shengsuanyun.com/api/v1", "deepseek-chat"),
    ("GitHub Copilot / Models", "github_models", "openai", "https://models.inference.ai.azure.com", "gpt-4o-mini"),
    # Ollama is local and exposes an OpenAI-compatible endpoint at /v1; no API
    # key needed (leave it blank). Model name must match what you pulled with
    # `ollama pull <model>` (qwen2.5 / llama3.1 / deepseek-r1 …).
    ("Ollama（本地）", "ollama", "openai", "http://localhost:11434/v1", "qwen2.5"),
    ("兼容 OpenAI 协议（自定义）", "openai_custom", "openai", "", ""),

    # ── Anthropic-compatible vendors ──────────────────────────────────
    ("Anthropic Claude", "anthropic", "anthropic", "https://api.anthropic.com/v1", "claude-3-5-sonnet-latest"),
    ("兼容 Anthropic 协议（自定义）", "anthropic_custom", "anthropic", "", ""),
]

# Vendors reachable over BOTH protocols. code -> {protocol: (base_url, model)}.
# Switching the protocol dropdown rewrites the URL for these vendors; vendors
# not in this map leave a manually typed URL alone.
#
# Volcengine ARK Coding Plan: one subscription (model ark-code-latest) with an
# OpenAI-compatible and an Anthropic-compatible entry point.
#   - OpenAI:    base ends in /api/coding/v3, the adapter appends
#                /chat/completions (OpenAI SDK convention).
#   - Anthropic: base is the bare .../api/coding exactly as documented for
#                Claude Code (ANTHROPIC_BASE_URL); the adapter appends
#                /v1/messages, matching the official Anthropic SDK.
DUAL_PROTOCOL_PRESETS: Dict[str, Dict[str, tuple]] = {
    "volcengine": {
        "openai": ("https://ark.cn-beijing.volces.com/api/coding/v3", "ark-code-latest"),
        "anthropic": ("https://ark.cn-beijing.volces.com/api/coding", "ark-code-latest"),
    },
}

# Vendor codes removed from the list above; old config.json files are migrated
# to the new code, and this alias keeps them readable even before migration.
_PROVIDER_ALIASES = {"volcengine_anthropic": "volcengine"}

# Vendors whose endpoint normally runs without authentication: Ollama locally,
# and custom OpenAI/Anthropic-compatible gateways (LM Studio, vLLM, LiteLLM …).
# An empty API key is allowed for these; a remote gateway will simply reject it
# with a 401 instead of being blocked by client-side validation.
KEYLESS_PROVIDERS = {"ollama", "openai_custom", "anthropic_custom"}


def provider_preset(code: str, protocol: str = "") -> tuple:
    """Resolve a vendor code to ``(label, protocol, base_url, default_model)``.

    Dual-protocol vendors return the URL/model for the requested protocol when
    they support it. Unknown codes return empty strings.
    """
    code = _PROVIDER_ALIASES.get(code, code)
    for label, c, proto, url, model in AI_PROVIDERS:
        if c != code:
            continue
        alt = DUAL_PROTOCOL_PRESETS.get(code)
        if alt and protocol in alt:
            url, model = alt[protocol]
            proto = protocol
        return label, proto, url, model
    return "", "openai", "", ""


def _obfuscate(text: str) -> str:
    """Very light obfuscation (base64) so plaintext isn't sitting in config.json."""
    if not text:
        return ""
    try:
        return "b64:" + base64.b64encode(str(text).encode("utf-8")).decode("ascii")
    except Exception:
        return ""


def _deobfuscate(text: str) -> str:
    if not text:
        return ""
    # A hand-edited config may hold a number/bool where a secret used to be.
    text = text if isinstance(text, str) else str(text)
    if text.startswith("b64:"):
        try:
            return base64.b64decode(text[4:].encode("ascii")).decode("utf-8")
        except Exception:
            return ""
    # Backward compat: plaintext
    return text


def _normalize_ai_entry(ai: Dict[str, Any]) -> None:
    """In-place migration for renamed vendors and corrected endpoint URLs."""
    # Text fields feed directly into QLineEdit.setText() and URL assembly.
    for field in ("name", "provider", "protocol", "api_base", "api_key", "model"):
        if field in ai and not isinstance(ai[field], str):
            ai[field] = str(ai[field])
    # The Anthropic ARK entry used to be a separate vendor code; it is now one
    # dual-protocol vendor, so fold it back and mark the protocol explicitly.
    if ai.get("provider") == "volcengine_anthropic":
        ai["provider"] = "volcengine"
        ai["protocol"] = "anthropic"

    # Coding Plan base-URL cleanup for volcengine entries:
    #   * early builds shipped a typo (/api/plan instead of /api/coding);
    #   * a later build pre-filled /api/coding/v1 for Anthropic, while the
    #     documented base is the bare .../api/coding (the client appends
    #     /v1/messages itself, like the Anthropic SDK);
    #   * users may also paste the full .../v1/messages or .../v3/chat/
    #     completions URL.
    # Canonicalize any of these to the per-protocol preset.
    if ai.get("provider") == "volcengine":
        proto = ai.get("protocol") or "openai"
        base = (ai.get("api_base") or "").strip().rstrip("/")
        if ("/api/plan" in base) or ("/api/coding" in base):
            endpoints = DUAL_PROTOCOL_PRESETS["volcengine"]
            ai["api_base"] = endpoints.get(proto, endpoints["openai"])[0]


DEFAULT_CONFIG: Dict[str, Any] = {
    "data_sources": [],
    # New multi-config schema. Legacy `ai_config` (single dict) is auto-migrated.
    "ai_configs": [],
    "current_ai_config": "",
    "current_data_source": "",
    "ui_settings": {
        "page_size": 20,
    },
}


def _default_ai_entry(name: str = "默认") -> Dict[str, Any]:
    return {
        "name": name,
        "provider": "openai",
        "protocol": "openai",
        "api_base": "https://api.openai.com/v1",
        "api_key": "",
        "model": "gpt-4o-mini",
        "temperature": 0.2,
    }


class ConfigManager:
    """Load/save configuration from config.json."""

    def __init__(self, path: str = CONFIG_FILE):
        self.path = path
        self.data: Dict[str, Any] = json.loads(json.dumps(DEFAULT_CONFIG))
        self.load()

    # ----- I/O -----
    def _read_raw(self) -> tuple[Optional[Dict[str, Any]], bool]:
        """Read the config JSON, falling back to pre-`.app` locations.

        Returns ``(raw, migrated)`` where ``migrated`` is True when the data came
        from a legacy path and should be written back to ``self.path``.
        """
        for path, is_legacy in [(self.path, False)] + [(p, True) for p in legacy_config_paths()]:
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if not isinstance(raw, dict):
                    raise ValueError("configuration root must be a JSON object")
                return raw, is_legacy
            except Exception:
                # Preserve a corrupt primary config instead of silently
                # replacing it with defaults on the next save.
                if not is_legacy:
                    try:
                        os.replace(path, f"{path}.corrupt")
                    except OSError:
                        pass
                continue
        return None, False

    def load(self) -> None:
        raw, migrated = self._read_raw()
        if raw is None:
            return

        merged = json.loads(json.dumps(DEFAULT_CONFIG))
        merged.update(raw or {})
        # Ensure nested dicts merged (a hand-edited non-object must not crash
        # startup — fall back to the defaults).
        base = DEFAULT_CONFIG["ui_settings"].copy()
        extra = merged.get("ui_settings")
        if isinstance(extra, dict):
            base.update(extra)
        merged["ui_settings"] = base

        # A hand-edited file can turn these lists into strings/objects or
        # contain scalar entries; normalize before touching each entry so
        # startup never dies on ds["password"] / ai["api_key"].
        for key in ("data_sources", "ai_configs"):
            items = merged.get(key)
            merged[key] = [x for x in items if isinstance(x, dict)] if isinstance(items, list) else []
        if not isinstance(merged.get("current_data_source"), str):
            merged["current_data_source"] = ""
        if not isinstance(merged.get("current_ai_config"), str):
            merged["current_ai_config"] = ""

        # Migrate legacy single-config schema (ai_config: {...}) -> ai_configs: [...]
        legacy = raw.get("ai_config")
        if isinstance(legacy, dict) and legacy and not merged.get("ai_configs"):
            entry = _default_ai_entry("默认")
            entry.update({k: v for k, v in legacy.items() if k in entry})
            entry["api_key"] = legacy.get("api_key", "")
            merged["ai_configs"] = [entry]
            if not merged.get("current_ai_config"):
                merged["current_ai_config"] = entry["name"]

        # Decrypt sensitive fields
        for ds in merged["data_sources"]:
            ds["password"] = _deobfuscate(ds.get("password", ""))
            # Text fields feed QLineEdit.setText() and URL assembly; numbers
            # or objects from a hand-edited file would crash the UI thread.
            for field in ("name", "type", "host", "database", "username",
                          "instance", "lib_dir"):
                if field in ds and not isinstance(ds[field], str):
                    ds[field] = str(ds[field])
            # build_engine_url() spreads this mapping into kwargs, so a
            # hand-edited string/list would raise on every connection attempt.
            if not isinstance(ds.get("params"), dict):
                ds["params"] = {}
        for ai in merged["ai_configs"]:
            ai["api_key"] = _deobfuscate(ai.get("api_key", ""))
            _normalize_ai_entry(ai)

        self.data = merged

        # Persist into the writable location so the legacy copy is only read once.
        if migrated:
            try:
                self.save()
            except Exception:
                pass

    def save(self) -> None:
        # Deep-copy and obfuscate secrets before writing
        out = json.loads(json.dumps(self.data))
        # load() normalizes these, but save() may also be called right after
        # programmatic data edits — keep it defensive all the same.
        for key in ("data_sources", "ai_configs"):
            items = out.get(key)
            out[key] = [x for x in items if isinstance(x, dict)] if isinstance(items, list) else []
        for ds in out["data_sources"]:
            ds["password"] = _obfuscate(ds.get("password", ""))
        for ai in out["ai_configs"]:
            ai["api_key"] = _obfuscate(ai.get("api_key", ""))
        # Don't persist the legacy key
        out.pop("ai_config", None)

        tmp = f"{self.path}.tmp"
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            # Atomic on the same filesystem: a crash mid-save leaves the old
            # config.json intact instead of a truncated file.
            os.replace(tmp, self.path)
        except Exception as e:
            try:
                os.remove(tmp)
            except OSError:
                pass
            raise RuntimeError(f"保存配置失败: {e}")

    # ----- Data source helpers -----
    def get_data_sources(self) -> List[Dict[str, Any]]:
        items = self.data.get("data_sources")
        if not isinstance(items, list):
            items = []
        # Drop junk entries from hand-edited files so every caller can rely on
        # dict access (ds.get / ds["name"]) without crashing at startup.
        items = [d for d in items if isinstance(d, dict)]
        self.data["data_sources"] = items
        return items

    def find_data_source(self, name: str) -> Optional[Dict[str, Any]]:
        for ds in self.get_data_sources():
            if ds.get("name") == name:
                return ds
        return None

    def upsert_data_source(self, ds: Dict[str, Any]) -> None:
        for i, existing in enumerate(self.get_data_sources()):
            if existing.get("name") == ds.get("name"):
                self.get_data_sources()[i] = ds
                return
        self.get_data_sources().append(ds)

    def remove_data_source(self, name: str) -> None:
        self.data["data_sources"] = [d for d in self.get_data_sources() if d.get("name") != name]
        if self.data.get("current_data_source") == name:
            self.data["current_data_source"] = ""

    # ----- AI configs (multi) -----
    def get_ai_configs(self) -> List[Dict[str, Any]]:
        items = self.data.get("ai_configs")
        if not isinstance(items, list):
            items = []
        items = [a for a in items if isinstance(a, dict)]
        self.data["ai_configs"] = items
        return items

    def find_ai_config(self, name: str) -> Optional[Dict[str, Any]]:
        for ai in self.get_ai_configs():
            if ai.get("name") == name:
                return ai
        return None

    def upsert_ai_config(self, cfg: Dict[str, Any]) -> None:
        for i, existing in enumerate(self.get_ai_configs()):
            if existing.get("name") == cfg.get("name"):
                self.get_ai_configs()[i] = cfg
                return
        self.get_ai_configs().append(cfg)

    def remove_ai_config(self, name: str) -> None:
        self.data["ai_configs"] = [c for c in self.get_ai_configs() if c.get("name") != name]
        if self.data.get("current_ai_config") == name:
            self.data["current_ai_config"] = ""

    def get_current_ai_config(self) -> Optional[Dict[str, Any]]:
        """Return the AI config marked as current, or the first one if none is marked."""
        name = self.data.get("current_ai_config") or ""
        if name:
            found = self.find_ai_config(name)
            if found:
                return found
        configs = self.get_ai_configs()
        return configs[0] if configs else None

    def set_current_ai_config(self, name: str) -> None:
        self.data["current_ai_config"] = name

    # ----- current selection -----
    def get_current_data_source(self) -> str:
        return self.data.get("current_data_source", "") or ""

    def set_current_data_source(self, name: str) -> None:
        self.data["current_data_source"] = name

    # ----- UI settings -----
    def get_page_size(self) -> int:
        ui = self.data.get("ui_settings")
        try:
            n = int(ui.get("page_size", 20) or 20) if isinstance(ui, dict) else 20
        except (TypeError, ValueError):
            n = 20
        return max(5, min(1000, n))

    def set_page_size(self, n: int) -> None:
        try:
            value = int(n)
        except (TypeError, ValueError):
            return  # ignore junk instead of crashing the settings page
        if not isinstance(self.data.get("ui_settings"), dict):
            self.data["ui_settings"] = {}
        self.data["ui_settings"]["page_size"] = value
