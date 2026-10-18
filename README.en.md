# MuAsk (沐问)

<p align="center">
  <a href="https://gitee.com/super_rgh/muask/stargazers"><img src="https://gitee.com/super_rgh/muask/badge/star.svg?theme=gvp" alt="Gitee stars"></a>
  <a href="https://gitee.com/super_rgh/muask/members"><img src="https://gitee.com/super_rgh/muask/badge/fork.svg?theme=gvp" alt="Gitee forks"></a>
  <a href="https://github.com/vfaner/muask/stargazers"><img src="https://img.shields.io/github/stars/vfaner/muask?label=GitHub%20stars&logo=github" alt="GitHub stars"></a>
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License: MIT">
  <img src="https://img.shields.io/github/v/release/vfaner/muask?label=release&color=2c7be5" alt="Latest release">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-2c7be5" alt="Platforms">
</p>

<p align="center">
  <b>An open-source desktop Text2SQL tool: ask in plain language, get executable SQL, run it in one click.</b><br>
  Reads your real schema and column comments, so anyone on the team can query data immediately.
</p>

<p align="center">
  <a href="#quickstart">Quick start</a> ·
  <a href="#features">Features</a> ·
  <a href="#databases">Databases</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#contributing">Contributing</a>
</p>

<p align="center">
  <a href="https://github.com/vfaner/muask">GitHub</a> ·
  <a href="https://gitee.com/super_rgh/muask">Gitee</a> ·
  <a href="https://muask.qqmu.com">Website</a> ·
  <a href="https://www.bilibili.com/video/BV1HvY369EVe/">Video demo</a> ·
  <a href="https://github.com/vfaner/muask/releases">Changelog</a>
</p>

English | [简体中文](./README.md)

![MuAsk cover](assets/muwen.png)

---

<a id="intro" name="intro"></a>

## 📌 Overview

Taking over a mature project often means facing hundreds or thousands of tables with no up-to-date documentation: table relationships and field meanings live in the codebase and senior engineers' memories, and even an ad-hoc data lookup means digging through code, asking around and hand-writing SQL.

**MuAsk** is built for exactly this. It is a **PySide6** desktop client that packages the whole “natural language → SQL → execute” loop:

1. After you pick a data source, it reads the **real table names, columns, primary/foreign keys and Chinese comments** from the database;
2. You describe what you need in plain language (e.g. “students in grade 3 with a math score above 60”), and the AI generates SQL over your actual schema;
3. The SQL is pre-checked locally, shown in an editable area, and runs in one click — results render as a paginated table.

| Item | Details |
|---|---|
| What it is | A desktop Text2SQL client for developers, QA, ops and data analysts |
| Latest version | **v1.4.1** (2026-10-07) |
| Platforms | Windows x64 / macOS (Apple Silicon) / Linux x86_64 — **no Python installation required** |
| Databases | 14 built-in types with bundled drivers, including Dameng, KingbaseES, HighGo, Vastbase, OceanBase, TiDB and GBase 8a |
| AI providers | OpenAI-compatible `/chat/completions` and Anthropic-compatible `/messages`, plus local Ollama |
| License | [MIT](./LICENSE) |

**When it helps**

- Taking over a legacy database with hundreds of tables and no documentation;
- Running ad-hoc queries without hunting through code or interrupting colleagues;
- Domestic (“信创”) database environments that need a lightweight client with bundled Dameng / KingbaseES / HighGo / Vastbase / GBase drivers;
- Privacy-sensitive setups, where a local Ollama model keeps every query inside the intranet.

> 💡 Unlike hosted Text2SQL services, MuAsk is a **local desktop app**: connection details and query results never leave your machine. Besides the schema used to generate SQL, nothing is uploaded.

---

<a id="features" name="features"></a>

## ✨ Features

| Feature | Details |
|---|---|
| **Text2SQL** | Plain-language input → AI-generated SQL → local pre-check (rejects prose, unbalanced parentheses, etc.) → editable → one-click execution; SELECTs are paginated |
| **Grounded in the real schema** | Reads tables, columns, primary/foreign keys and comments; ranks tables against the question when there are many (CJK bigram matching for terms like “数学” / “三年级”) and reports how many were loaded |
| **14 databases, drivers bundled** | Every built-in type ships its driver inside the package and connects out of the box — no “missing driver” prompts; only the generic “custom” type needs a driver you supply |
| **Multiple AI configs** | Manage several AI configs like data sources (new / edit / delete / test / set current); switch the active one from the toolbar |
| **Two protocols, many vendors** | OpenAI-compatible (OpenAI, DeepSeek, Qwen, Doubao, Kimi, Zhipu, Qianfan, …) and Anthropic-compatible (Claude, Volcengine ARK) |
| **Local Ollama** | Optional local models via Ollama's OpenAI-compatible endpoint — no API key, no internet access |
| **Safe workflow** | SQL is fully displayed and editable before execution; a read-only database account is recommended as a safety net |
| **Friendly errors** | Dedicated scrollable error dialog with full driver messages; stale results are cleared automatically |
| **Modern desktop UI** | Frameless custom title bar, version-status pill, automatic update check, toast notifications, SQL syntax highlighting |
| **Native builds for 3 platforms** | Windows single-file exe, macOS `.app` + DMG, Linux single-file; CI builds and publishes automatically |

---

<a id="demo" name="demo"></a>

## 🎬 Demo & screenshots

> 🎬 **Video demo (~11 min, Chinese narration)**: [No more hand-writing SQL — an open-source, configure-and-use Text2SQL tool that reads table comments automatically](https://www.bilibili.com/video/BV1HvY369EVe/) (Bilibili)

### Text2SQL workspace

![Text2SQL workspace](assets/text2sql.png)

### Data source configuration

![Data source configuration](assets/db_config.png)

### Adding a data source

![Adding a data source](assets/db_config_add.png)

### AI configuration

![AI configuration](assets/ai_config.png)

### Help page

![Help page](assets/soft_method.png)

### About us

![About us](assets/about_me.png)

---

<a id="quickstart" name="quickstart"></a>

## 🚀 Quick start

### Option 1: Download a pre-built binary (recommended, no Python)

| Platform | Download | How to run |
|---|---|---|
| **Windows x64** | `muask-windows-x86_64.exe` | Single file — download and double-click. SmartScreen blocks it once; see below. |
| **macOS (Apple Silicon)** | `muask-macos-arm64.dmg` | Mount → drag to Applications → double-click. One-time approval required; see below. |
| **Linux x64** | `muask-linux-x86_64.tar.gz` | `tar -xzvf ...tar.gz` → `chmod +x muask && ./muask` |

**Download links**

- GitHub Releases (all platforms): https://github.com/vfaner/muask/releases/latest
- Gitee Releases (faster in mainland China): https://gitee.com/super_rgh/muask/releases

> Gitee caps each attachment at 100 MB, so the Linux package is split into two volumes. Download `muask-linux-x86_64.tar.gz.part1` and `.part2`, then merge them:
>
> ```bash
> cat muask-linux-x86_64.tar.gz.part1 muask-linux-x86_64.tar.gz.part2 > muask-linux-x86_64.tar.gz
> tar -xzvf muask-linux-x86_64.tar.gz
> chmod +x muask && ./muask
> ```

### 🪟 First launch on Windows needs a one-time approval

Microsoft Defender SmartScreen blocks it the first time:

1. Double-click the exe → **"Windows protected your PC"** appears
2. That dialog only shows a "Don't run" button by default — click **More info** in the lower left
3. A **Run anyway** button appears — click it
4. The app launches. Every launch after this is a plain double-click, with no prompt.

> Alternatively: right-click the downloaded exe → Properties → tick **Unblock** at the bottom. It then carries no tag and won't be blocked at all.
>
> First launch unpacks roughly 60–120 MB (all database drivers are bundled) into a temp directory, so expect a few seconds with no window. That's normal.

### 🍎 First launch on macOS needs a one-time approval

macOS blocks it the first time. To approve it:

1. Open the DMG and drag `muask.app` into Applications
2. Double-click the app → you'll get *"Apple could not verify…"* → click **Done** (**not** "Move to Trash")
3. Open **System Settings → Privacy & Security**, scroll to the Security section, and click **Open Anyway** next to the app's name
4. A second confirmation dialog appears — click **Open** in it; macOS may ask for Touch ID or your login password
5. The app launches. **Every launch after this one is a plain double-click, with no prompt at all.**

> The dialog in step 2 only offers "Done" and "Move to Trash" — **that is expected**. Any unnotarized app behaves this way; the approval lives in System Settings (step 3), not in that dialog.

> ⚠️ The widely-cited **right-click → Open** trick was **removed by Apple in macOS 15 (Sequoia)**. The System Settings path above is currently the only way to approve an unnotarized app.

If you'd rather do it in one command, strip the quarantine flag and then double-click normally:

```bash
xattr -dr com.apple.quarantine /Applications/muask.app
```

### 🐧 Running on Linux

Linux has no signature gate, but you do need to add the executable bit after unpacking:

```bash
tar -xzvf muask-linux-x86_64.tar.gz
chmod +x muask
./muask
```

If you hit `could not load the Qt platform plugin "xcb"`, your system is missing the X11 libraries Qt needs (Debian / Ubuntu):

```bash
sudo apt-get install -y libgl1 libegl1 libxkbcommon-x11-0 libxcb-cursor0 \
  libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 \
  libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 libdbus-1-3
```

### Option 2: Run from source

For development, contributions, or architectures without a pre-built binary (e.g. Intel Macs):

```bash
git clone https://gitee.com/super_rgh/muask.git
cd muask

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python main.py
```

Requires **Python 3.9+** (developed and tested on Python 3.14).

`requirements.txt` already contains the driver for every built-in database type:

- **Cross-platform pure-Python / self-contained wheels**: `PyMySQL` (MySQL, MariaDB, OceanBase MySQL tenants, TiDB, GBase 8a), `psycopg2-binary` (PostgreSQL, OpenGauss, HighGo, Vastbase, and the PostgreSQL-protocol fallback for KingbaseES), `oracledb` (Oracle thin mode — **no Oracle Instant Client needed**), `pymssql` (FreeTDS bundled — **no ODBC driver needed**), `ibm_db` (DB2, clidriver bundled).
- **Domestic (“信创”) native drivers**: `dmpython` + `dmSQLAlchemy` (Dameng) and `ksycopg2` (KingbaseES) ship **Windows / Linux wheels only**; platform markers make `pip install` skip them on macOS automatically.

### Three steps to your first query

1. **Configure AI**: “AI 配置 (AI config)” → New → pick a vendor (protocol / base URL / model auto-fill) → paste API key → Test → Save. Ollama local models work without a key.
2. **Configure a data source**: “数据源配置 (Data sources)” → New → choose a database type → fill in connection details → Test connection → Save.
3. **Ask**: back on the “沐问 (Text2SQL)” page, pick the data source and AI config, type your question → **Generate SQL** → review/edit → **Execute SQL**.

> With no data source selected the model cannot see any schema and falls back to invented placeholder names — always pick a data source and review the SQL yourself.
> The **Execute SQL** button stays disabled until a data source is selected.

---

<a id="databases" name="databases"></a>

## 🗄️ Supported databases

Every type in the dropdown builds its connection URL automatically and connects **with a bundled driver** — no driver packages to install yourself:

| Database | Driver used | Connection | Windows / Linux build | macOS build |
|---|---|---|---|---|
| MySQL | PyMySQL | MySQL protocol (3306) | ✅ bundled | ✅ bundled |
| MariaDB | PyMySQL | MySQL-compatible protocol (3306) | ✅ bundled | ✅ bundled |
| PostgreSQL | psycopg2 | PG protocol (5432) | ✅ bundled | ✅ bundled |
| OpenGauss | psycopg2 | PG protocol (5432) | ✅ bundled | ✅ bundled |
| HighGo (瀚高) | psycopg2 | PG-compatible protocol (5866) | ✅ bundled | ✅ bundled |
| Vastbase (海量) | psycopg2 | PG-compatible protocol (5432) | ✅ bundled | ✅ bundled |
| KingbaseES (人大金仓) | ksycopg2 (official, bundles libkci), psycopg2 fallback | 54321 | ✅ bundled | ✅ falls back to the PostgreSQL protocol (accepted by most instances) |
| OceanBase | PyMySQL | MySQL-tenant compatible protocol (2881) | ✅ bundled | ✅ bundled |
| TiDB | PyMySQL | MySQL-compatible protocol (4000) | ✅ bundled | ✅ bundled |
| Oracle | oracledb thin mode (no Instant Client) | `service_name` or SID (1521) | ✅ bundled | ✅ bundled |
| SQL Server | pymssql (FreeTDS bundled, no ODBC) | TDS (1433) | ✅ bundled | ✅ bundled |
| Dameng (达梦) | dmpython + dmSQLAlchemy (official; client libs bundled) | DM protocol (5236) | ✅ bundled | ⚠️ vendor publishes no macOS driver |
| GBase 8a (南大通用) | PyMySQL | MySQL-compatible protocol (5258) | ✅ bundled | ✅ bundled |
| DB2 | ibm_db + ibm-db-sa (IBM official; clidriver bundled) | DB2 protocol (50000) | ✅ bundled | ✅ bundled |
| Custom | your own | put `{"url": "..."}` in connection params | install the driver yourself | install the driver yourself |

> **ShenTong (神通) / YashanDB (崖山) / H2** are not built-in types: ShenTong publishes only JDBC / ODBC drivers; YashanDB's Python driver is not distributed on PyPI; and H2 is a pure-Java engine that requires a JVM plus `h2.jar` on the user's machine (defeating the “connects out of the box” goal). Use the “custom” data source type and supply your own driver and URL. OceanBase **Oracle tenants** likewise need “custom” (MySQL tenants are built in).

### Sample connection URLs (for custom data sources)

| Database | SQLAlchemy URL example |
|---|---|
| MySQL / MariaDB / OceanBase(MySQL tenant) / TiDB / GBase 8a | `mysql+pymysql://user:pwd@host:3306/db?charset=utf8mb4` (OceanBase 2881, TiDB 4000, GBase 8a 5258) |
| PostgreSQL / OpenGauss / HighGo / Vastbase | `postgresql+psycopg2://user:pwd@host:5432/db` (HighGo default 5866) |
| KingbaseES (PG fallback) | `postgresql+psycopg2://user:pwd@host:54321/db` |
| Oracle | `oracle+oracledb://user:pwd@host:1521/?service_name=ORCL` (or SID: `…/XE`) |
| SQL Server | `mssql+pymssql://user:pwd@host:1433/db` |
| DB2 | `ibm_db_sa://user:pwd@host:50000/db` |
| Dameng | `dm+dmpython://user:pwd@host:5236/DAMENG` |
| Custom | Put `{"url": "your+dialect://..."}` in the data source's connection params. |

---

<a id="ai" name="ai"></a>

## 🤖 Supported AI providers

### OpenAI-compatible `/chat/completions`

| Vendor | Default base URL | Default model |
|---|---|---|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| Aliyun Bailian (Qwen) | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-max` |
| Qwen | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` |
| Volcengine ARK (Coding Plan) | `https://ark.cn-beijing.volces.com/api/coding/v3` | `ark-code-latest` |
| Doubao | `https://ark.cn-beijing.volces.com/api/v3` | `doubao-pro-32k` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| Baidu Qianfan (ERNIE) | `https://qianfan.baidubce.com/v2` | `ernie-4.0-turbo-8k` |
| Zhipu GLM | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-plus` |
| Kimi (Moonshot) | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| Shengsuanyun | `https://router.shengsuanyun.com/api/v1` | `deepseek-chat` |
| GitHub Copilot / Models | `https://models.inference.ai.azure.com` | `gpt-4o-mini` |
| **Ollama (local)** | `http://localhost:11434/v1` | any model you have pulled |
| OpenAI-compatible (custom) | (user-provided) | (user-provided) |

### Anthropic-compatible `/messages`

| Vendor | Default base URL | Default model |
|---|---|---|
| Anthropic Claude | `https://api.anthropic.com/v1` | `claude-3-5-sonnet-latest` |
| Volcengine ARK (auto-filled when switching to the Anthropic protocol) | `https://ark.cn-beijing.volces.com/api/coding` | `ark-code-latest` |
| Anthropic-compatible (custom) | (user-provided) | (user-provided) |

> Selecting a vendor auto-fills **Protocol**, **Base URL** and **Default model**. Vendors that support both protocols (e.g. Volcengine ARK) appear only once, and flipping the Protocol dropdown **rewrites the API address to the matching endpoint**. You can also switch protocol manually for third-party compatibility gateways (LiteLLM, OpenRouter, etc.) that aren't in the preset list.
>
> URL assembly follows the official SDKs: an OpenAI base URL must include the version segment (e.g. `…/api/coding/v3`, the app appends `/chat/completions`); an Anthropic base URL is filled down to the root (e.g. `…/api/coding`, exactly like Claude Code's `ANTHROPIC_BASE_URL`, and the app appends `/v1/messages`; if the base already ends in `/v1`, only `/messages` is appended).

---

<a id="config" name="config"></a>

## ⚙️ Configuration

Where `config.json` lives depends on how you run the app:

| How you run it | `config.json` location |
|---|---|
| From source | Project root (see `config.example.json` for a template) |
| macOS build | `~/Library/Application Support/muask/` |
| Windows build | `%APPDATA%\muask\` |
| Linux build | `$XDG_CONFIG_HOME/muask/` (defaults to `~/.config/…`) |

Packaged builds **cannot** keep config next to the executable: writing inside a macOS `.app` invalidates its code signature and the bundle stops launching, and a one-file build's runtime directory is a temp dir that's deleted on exit. That's exactly why older builds lost your settings on every restart — config from the old location is now migrated automatically, so there's nothing to move by hand.

Passwords and API keys are stored with a `b64:` prefix — this is obfuscation, **not** real encryption. For production-grade secrets management, swap it out for `cryptography` or your system keyring.

---

<a id="architecture" name="architecture"></a>

## 🧱 Architecture

### Tech stack

| Layer | Choice |
|---|---|
| Desktop UI | Python 3 / **PySide6** (Qt Widgets), QSS styling, frameless custom title bar |
| Data access | **SQLAlchemy** + native drivers; in-project SQLAlchemy dialect shims for Dameng / KingbaseES |
| AI access | `requests`, dual-protocol adapter for **OpenAI `/chat/completions`** and **Anthropic `/messages`** |
| Concurrency | QThread workers (AI generation, connection test, SQL execution, schema loading) — the UI never blocks |
| Config | Local `config.json` in the per-platform user directory, with automatic migration from old locations |
| Packaging | **PyInstaller** (single-file on Windows / Linux, `.app` + DMG on macOS); GitHub Actions builds and releases all three platforms in parallel |

### Data flow

```
┌────────────┐  question + real schema  ┌──────────────┐
│  Text2SQL  │ ───────────────────────▶ │  AI adapter  │
│    page    │                          │ OpenAI /     │
│            │ ◀─────────────────────── │ Anthropic /  │
└─────┬──────┘        generated SQL     │ Ollama       │
      │                                 └──────────────┘
      │ local pre-check (parens / quotes / statement shape)
      ▼
┌────────────┐   execute via SQLAlchemy  ┌──────────────┐
│ SQL editor │ ────────────────────────▶ │   Database   │
│ (editable) │ ◀──────────────────────── │ 14 drivers   │
└────────────┘   table + pagination       └──────────────┘
```

### Project layout

```
muask/
├── main.py                        # Entry point
├── requirements.txt               # Python dependencies
├── config.example.json            # Example configuration
├── muask.spec                     # PyInstaller config (.app on macOS, one-file elsewhere)
├── README.md / README.en.md       # Chinese / English documentation
├── LICENSE                        # MIT License
├── .github/workflows/release.yml  # 3-platform CI build & release
├── scripts/
│   ├── build_macos.sh             # macOS build + ad-hoc sign + DMG
│   ├── prepare_icon.py            # Cuts the rounded plate out of a photo-background JPG
│   └── make_icons.py              # Generates .icns / .ico from the master art
├── assets/                        # Icons, QR codes, screenshots
└── app/
    ├── __init__.py                # Version number (single source of truth)
    ├── paths.py                   # Resource / config path resolution (source vs frozen)
    ├── config.py                  # config.json I/O, DB / AI catalogs
    ├── db.py                      # SQLAlchemy URL builders, pagination, execution, pre-check
    ├── db_dialects.py             # Dameng / KingbaseES SQLAlchemy dialect shims
    ├── ai_providers.py            # OpenAI + Anthropic dual-protocol adapter
    ├── workers.py                 # QThread workers (AI gen, DB test, SQL exec)
    ├── highlighter.py             # SQL syntax highlighter
    ├── styles.py                  # QSS
    ├── toast.py                   # Toast notifications
    ├── error_dialog.py            # Scrollable error dialog
    ├── title_bar.py               # Custom title bar (version check / Donate / window controls)
    ├── update_dialog.py           # Update-available dialog
    ├── updater.py                 # GitHub / Gitee version checker
    ├── donate_dialog.py           # QR-code donation dialog
    ├── pages_text2sql.py          # Text2SQL page
    ├── pages_data_source.py       # Data source page
    ├── pages_ai.py                # AI config page
    ├── pages_about.py             # Help page
    ├── pages_about_us.py          # About us page
    └── main_window.py             # Main window
```

---

<a id="build" name="build"></a>

## 🛠️ Development & packaging

Packaging is driven by `muask.spec` (don't use a bare `pyinstaller -F main.py` — it drops the bundled assets and the macOS bundle structure).

**Windows / Linux** — single-file executable:

```bash
pip install pyinstaller
pyinstaller --clean --noconfirm muask.spec
# → dist/muask[.exe]
```

**macOS** — `.app` bundle wrapped in a DMG; the script also ad-hoc signs it:

```bash
pip install pyinstaller
./scripts/build_macos.sh
# → dist/muask.app
#   dist/muask-macos-arm64.dmg
```

Shipping a `.app` on macOS isn't cosmetic: Gatekeeper offers **no** approval path for an unsigned bare Unix executable — its warning dialog only has “Move to Trash”, so users simply cannot run it.

If you have an Apple Developer membership, follow the two `TODO(notarize)` comments in `scripts/build_macos.sh` to sign with a real Developer ID and add the `notarytool` / `stapler` steps. Users then get **no prompt at all**.

**Changing the icon**:

- Source is already a **square icon on a transparent background**: run `python3 scripts/make_icons.py your.png` — it normalizes the image to the 1024x1024 master `assets/app_icon.png` (also the Qt window icon) and regenerates the `.icns` / `.ico`.
- Source is a **JPG on a photo background** (like the current `assets/icon.jpg`): first run `python3 scripts/prepare_icon.py assets/icon.jpg`, then `python3 scripts/make_icons.py`.

Both scripts shell out to macOS's built-in `sips` / `iconutil` (prepare also uses the already-installed PySide6), so no extra imaging library is needed.

---

<a id="roadmap" name="roadmap"></a>

## 🗺️ Releases & maintenance

- **Current version**: v1.4.1 (2026-10-07) — fixes Ollama local models working without an API key, SQL Server pagination, connection-string escaping and SQL pre-check false positives; slims the installers.
- **Changelog**: every release ships full notes on [GitHub Releases](https://github.com/vfaner/muask/releases) / [Gitee Releases](https://gitee.com/super_rgh/muask/releases); the [website changelog](https://muask.qqmu.com/changelog.html) mirrors them.
- **Status**: actively maintained; issues and pull requests are handled continuously.
- **Roadmap** (subject to change, not a commitment): more database and domestic-database adapters, schema ranking / prompt improvements, query result export, richer diagnostics and documentation.

New versions keep shipping through the three-platform GitHub Actions pipeline, and the app checks for updates on startup.

---

<a id="faq" name="faq"></a>

## ❓ FAQ & known limitations

### FAQ

- **Do I need to pay for an API key?** No. Pick `Ollama (local)` in the AI config to run an open-source model locally — free and keyless. Cloud vendors also come at different price points; choose what fits.
- **Is my schema or query data uploaded?** When generating SQL, the schema and your question are sent to the AI vendor you selected; connection details and query results stay on your machine. For sensitive data, use local Ollama — nothing leaves the intranet.
- **Is the generated SQL safe?** SQL is fully shown and editable before execution, and database errors are displayed verbatim. A read-only database account is strongly recommended.
- **Do I need to install Python or database drivers?** No — installers bundle the runtime and all drivers. Only the “custom” type needs a driver you provide.
- **Blocked on first launch on Windows / macOS?** See the approval steps under “Quick start”; each is needed only once.

### Known limitations

- **The official Dameng (`dmpython`) and KingbaseES (`ksycopg2`) drivers publish Windows / Linux wheels only — no macOS builds** (a vendor constraint). The Windows / Linux builds bundle the native drivers; on macOS, KingbaseES automatically falls back to the PostgreSQL protocol, while Dameng requires the Windows / Linux build (or running from source there).
- **ShenTong (神通) / YashanDB (崖山) / H2 are not built-in types**: the vendors publish only JDBC / ODBC bridges (H2 additionally needs a JVM + `h2.jar`). Use the “custom” data source with your own bridge driver and SQLAlchemy URL.
- GBase 8a connects over the MySQL protocol (default port 5258); other GBase product lines (8s/8t) use different protocols — connect those via “custom”. OceanBase **Oracle tenants** likewise need “custom”.
- MariaDB's official Python connector ships Windows wheels only, so this tool connects through `PyMySQL`, which is bundled on all platforms.
- Pagination wraps user SQL in a `SELECT * FROM (...) __t` subquery, which works for the vast majority of statements but may need manual pagination for very unusual SQL.
- **No safety guardrails** — `DROP TABLE users;` will drop it. This is by design for dev/test workflows; add role-based access control at the database level for shared environments.
- Multiple statements in one execution are not supported (the underlying drivers normally send one statement per call); run them one by one.
- The macOS build needs a one-time manual approval on first launch (see above).

---

<a id="contributing" name="contributing"></a>

## 🤝 Contributing & feedback

All kinds of participation are welcome:

- 🐛 **Bug reports**: open an [Issue](https://gitee.com/super_rgh/muask/issues) with your OS, app version, database type and the full error message.
- 💡 **Feature requests**: describe your scenario and the outcome you expect in an Issue.
- 🔧 **Code contributions**: Fork → create a branch → commit → open a Pull Request. Make sure `python main.py` still starts and explain the purpose of the change.
- 📖 **Documentation**: fixes to the README and guides are just as welcome.

**Contact**

| Channel | Details |
|---|---|
| Email | [vfaner@88.com](mailto:vfaner@88.com) |
| QQ | [817094](https://wpa.qq.com/msgrd?v=3&uin=817094&site=qq&menu=yes) / [2912167928](https://wpa.qq.com/msgrd?v=3&uin=2912167928&site=qq&menu=yes) |
| QQ group | [426669837 (click to join)](https://qun.qq.com/universal-share/share?ac=1&authKey=RI%2FAwTODgEDm0uGAqGTqlwV7%2FPjE7njMa3DIb8c3X7H8keqdZ4hkJpDDpDjYkw5p&busi_data=eyJncm91cENvZGUiOiI0MjY2Njk4MzciLCJ0b2tlbiI6Imh1MWtOZHRYZ3E2WnpyK3dLK1N1WWp6cFprRjNrQlZqSXZ1U0pMdXRtcjZZcjhFTndJcXV4NUNnQXhUV0tjMFEiLCJ1aW4iOiI4MTcwOTQifQ%3D%3D&data=V88jHxiTMtasEWtL2EfVUg97X6IQwgKM6LRY46VLu2mEuaWkzBX0dSiV0iEgzGkFVaSmUCTMig_Sw8wCwznxhQ&svctype=4&tempid=h5_group_info) |
| WeChat | qqmu66 (copy to add) |
| Website | https://muask.qqmu.com |

**Project links**

| Platform | URL |
|---|---|
| Gitee (primary, China) | https://gitee.com/super_rgh/muask |
| GitHub | https://github.com/vfaner/muask |

If this project is useful to you, please give it a **Star ⭐** — it's the biggest encouragement for continued maintenance.

---

## 📄 License

Released under the [**MIT License**](./LICENSE). Copyright © 2025 vfaner. Free to use, modify and distribute for personal and commercial purposes; keep the copyright notice.
