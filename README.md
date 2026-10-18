# 沐问 MuAsk

<p align="center">
  <a href="https://gitee.com/super_rgh/muask/stargazers"><img src="https://gitee.com/super_rgh/muask/badge/star.svg?theme=gvp" alt="Gitee stars"></a>
  <a href="https://gitee.com/super_rgh/muask/members"><img src="https://gitee.com/super_rgh/muask/badge/fork.svg?theme=gvp" alt="Gitee forks"></a>
  <a href="https://github.com/vfaner/muask/stargazers"><img src="https://img.shields.io/github/stars/vfaner/muask?label=GitHub%20stars&logo=github" alt="GitHub stars"></a>
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License: MIT">
  <img src="https://img.shields.io/github/v/release/vfaner/muask?label=release&color=2c7be5" alt="Latest release">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-2c7be5" alt="Platforms">
</p>

<p align="center">
  <b>开源免费的桌面 Text2SQL 工具：中文一句话，SQL 自动生成、一键执行。</b><br>
  读取真实表结构与中文注释，让不熟悉库表的人也能立刻查数据。
</p>

<p align="center">
  <a href="#quickstart">快速开始</a> ·
  <a href="#features">功能特性</a> ·
  <a href="#databases">支持数据库</a> ·
  <a href="#architecture">技术架构</a> ·
  <a href="#contributing">贡献与反馈</a>
</p>

<p align="center">
  <a href="https://github.com/vfaner/muask">GitHub</a> ·
  <a href="https://gitee.com/super_rgh/muask">Gitee</a> ·
  <a href="https://muask.qqmu.com">官网</a> ·
  <a href="https://www.bilibili.com/video/BV1HvY369EVe/">视频演示</a> ·
  <a href="https://github.com/vfaner/muask/releases">更新日志</a>
</p>

[English](./README.en.md) | 简体中文

![沐问 MuAsk 封面](assets/muwen.png)

---

<a id="intro" name="intro"></a>

## 📌 项目简介

接手一个成熟项目时，数据库里往往有几百上千张表，却缺少完整的文档：表关系与字段含义散落在代码和老员工的记忆里，临时查一条数据就要翻代码、问同事、手写一大段 SQL。

**沐问 MuAsk** 就是为这个场景做的。它是一款基于 **PySide6** 的桌面数据库查询工具，把「自然语言 → SQL → 执行」整条链路做成开箱即用的客户端：

1. 选中数据源后，自动读取数据库中**真实的表名、字段、主外键和中文注释**；
2. 你用中文描述需求（如「查询三年级数学 60 分以上的学生」），AI 在真实表结构内生成 SQL；
3. SQL 经本地预检后展示在编辑区，可人工核对、修改，再一键执行并以表格 + 分页查看结果。

| 项目信息 | 说明 |
|---|---|
| 项目定位 | 面向开发、测试、运维、数据分析的桌面 Text2SQL 客户端 |
| 最新版本 | **v1.4.1**（2026-10-07） |
| 运行环境 | Windows x64 / macOS (Apple Silicon) / Linux x86_64，安装包**无需 Python** |
| 数据库支持 | 14 类数据库内置驱动，含达梦、人大金仓、瀚高、海量、OceanBase、TiDB、GBase 8a 等信创库 |
| AI 支持 | OpenAI 兼容 `/chat/completions` 与 Anthropic 兼容 `/messages` 双协议，支持 Ollama 本地模型 |
| 开源协议 | [MIT](./LICENSE) |

**适用场景**

- 接手老项目，数据库几百上千张表却没有文档，需要快速上手查数；
- 临时取数、核对业务口径，不想为一条 SQL 翻代码、问同事；
- 信创数据库环境，需要一个内置达梦 / 金仓 / 瀚高 / 海量 / GBase 驱动的轻量客户端；
- 数据隐私敏感，希望使用本地 Ollama 模型，查询不出内网。

> 💡 相比在线的 Text2SQL 服务，沐问是**本地桌面程序**：数据库连接信息与查询结果始终留在本机；除生成 SQL 所需的表结构外，不上传任何数据。

---

<a id="features" name="features"></a>

## ✨ 功能特性

| 特性 | 说明 |
|---|---|
| **Text2SQL** | 中文输入 → AI 生成 SQL → 本地预检（拦截散文、括号不匹配等）→ 可编辑 → 一键执行，SELECT 分页浏览 |
| **真实表结构驱动** | 自动读取表、列、主外键与中文注释；表多时按问题相关性筛选（如「数学」「三年级」二元词组匹配），并提示已载入多少张表 |
| **14 类数据库 · 驱动全内置** | 每种内置类型的驱动随安装包分发，开箱直连，不提示「缺少驱动包」；仅「其他（自定义）」需自备驱动 |
| **多 AI 配置 · 一键切换** | 像数据源一样管理多份 AI 配置（新建 / 编辑 / 删除 / 测试 / 设为当前），主界面顶部随时切换 |
| **双协议 · 多厂商** | OpenAI 兼容（OpenAI、DeepSeek、通义千问、豆包、Kimi、智谱、千帆等）与 Anthropic 兼容（Claude、火山方舟） |
| **Ollama 本地模型** | 可选本地 Ollama（OpenAI 兼容端点），免 API Key、免外网，适合隐私敏感场景 |
| **安全可控** | SQL 执行前完整展示、可手动修改；建议搭配只读账号使用，从权限层兜底 |
| **友好错误处理** | 独立错误弹窗（可滚动 / 可关闭），保留完整报错，旧结果不残留 |
| **现代化桌面 UI** | 无边框自绘标题栏、版本状态胶囊、自动更新检查、Toast 通知、SQL 语法高亮 |
| **三平台原生打包** | Windows 单文件 exe、macOS `.app` + DMG、Linux 单文件，CI 自动构建发布 |

---

<a id="demo" name="demo"></a>

## 🎬 演示与界面预览

> 🎬 **视频演示（约 11 分钟）**：[告别手写 SQL！配置即用的开源 Text2SQL 工具，无需指定表名，AI 自动读表注释生成可执行语句！](https://www.bilibili.com/video/BV1HvY369EVe/)（B 站）

### Text2SQL 主界面

![Text2SQL 主界面](assets/text2sql.png)

### 数据源配置

![数据源配置](assets/db_config.png)

### 新增数据源

![新增数据源](assets/db_config_add.png)

### AI 配置

![AI 配置](assets/ai_config.png)

### 软件说明

![软件说明](assets/soft_method.png)

### 关于我们

![关于我们](assets/about_me.png)

---

<a id="quickstart" name="quickstart"></a>

## 🚀 快速开始

### 方式一：下载安装包（推荐，无需 Python 环境）

| 平台 | 下载文件 | 使用方式 |
|---|---|---|
| **Windows x64** | `muask-windows-x86_64.exe` | 单文件，下载后直接双击运行；首次会被 SmartScreen 拦一次，见下方说明 |
| **macOS (Apple Silicon)** | `muask-macos-arm64.dmg` | 挂载 → 拖到「应用程序」→ 双击；首次需放行一次，见下方说明 |
| **Linux x64** | `muask-linux-x86_64.tar.gz` | `tar -xzvf ...tar.gz` → `chmod +x muask && ./muask` |

**下载地址（双通道）**

- GitHub Releases（全部平台）：https://github.com/vfaner/muask/releases/latest
- Gitee Releases（国内加速）：https://gitee.com/super_rgh/muask/releases

> Gitee 单个附件限制 100 MB，Linux 包被拆成两个分卷。下载 `muask-linux-x86_64.tar.gz.part1` 和 `.part2` 后合并：
>
> ```bash
> cat muask-linux-x86_64.tar.gz.part1 muask-linux-x86_64.tar.gz.part2 > muask-linux-x86_64.tar.gz
> tar -xzvf muask-linux-x86_64.tar.gz
> chmod +x muask && ./muask
> ```

### 🪟 Windows 首次运行需放行一次

首次运行时 Microsoft Defender SmartScreen 会拦一次：

1. 双击 exe，弹出「**Windows 已保护你的电脑**」
2. 这个弹窗默认只显示「不运行」按钮 —— 点左下角的「**更多信息**」
3. 展开后出现「**仍要运行**」，点它
4. 程序启动，此后双击直接打开，不再提示

> 也可以右键下载好的 exe → 属性 → 勾选底部的「**解除锁定**」，这样运行时不带标记，不会触发拦截。
>
> 首次启动需要把约 60–120 MB 的内容解包到临时目录（内置了全部数据库驱动），会有几秒钟没有窗口出现，属正常现象。

### 🍎 macOS 首次运行需放行一次

从网上下载后 macOS 会拦一次。放行步骤：

1. 双击 DMG，把 `muask.app` 拖到「应用程序」
2. 双击应用 → 弹出「Apple 无法验证…是否包含恶意软件」→ 点**完成**（不要点「移到废纸篓」）
3. 打开**系统设置 → 隐私与安全性**，向下滚动到「安全性」，点应用名旁的**仍要打开**
4. 会再弹一个确认框，点里面的**打开**；系统可能要求 Touch ID 或登录密码
5. 应用启动。**之后每次双击都直接打开，不再有任何提示。**

> 第 2 步那个弹窗只有「完成」和「移到废纸篓」两个按钮，**这是正常的** —— 未公证应用必然如此，
> 放行入口在第 3 步的系统设置里，不在这个弹窗上。

> ⚠️ 网上流传的「右键 → 打开」这个老办法**在 macOS 15 (Sequoia) 及更新版本上已被 Apple 移除**，
> 上面的「系统设置」路径是目前唯一的放行入口。

嫌麻烦也可以用一行命令直接清除隔离标记，然后正常双击：

```bash
xattr -dr com.apple.quarantine /Applications/muask.app
```

### 🐧 Linux 运行说明

Linux 没有类似的签名拦截，但 tar 解包后需要手动加执行权限：

```bash
tar -xzvf muask-linux-x86_64.tar.gz
chmod +x muask
./muask
```

若报 `could not load the Qt platform plugin "xcb"`，说明系统缺 Qt 需要的 X11 库，补上即可（Debian / Ubuntu）：

```bash
sudo apt-get install -y libgl1 libegl1 libxkbcommon-x11-0 libxcb-cursor0 \
  libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 \
  libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 libdbus-1-3
```

### 方式二：从源码运行

适合二次开发或使用 Intel Mac 等没有预编译包的架构：

```bash
git clone https://gitee.com/super_rgh/muask.git
cd muask

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python main.py
```

要求 Python 3.9+（开发环境为 Python 3.14）。

`requirements.txt` 已包含所有内置数据库驱动：

- **跨平台纯 Python / 自包含 wheel**：`PyMySQL`（MySQL、MariaDB、OceanBase MySQL 租户、TiDB、GBase 8a）、`psycopg2-binary`（PostgreSQL、OpenGauss、瀚高、海量，金仓 PG 协议兜底）、`oracledb`（Oracle 瘦模式，无需 Instant Client）、`pymssql`（自带 FreeTDS，无需 ODBC）、`ibm_db`（DB2，自带 clidriver）。
- **信创原生驱动**：`dmpython` + `dmSQLAlchemy`（达梦）、`ksycopg2`（人大金仓）仅有 Windows / Linux wheel，已用平台标记限定，macOS 上安装时自动跳过。

### 三步开始查询

1. **配置 AI**：「AI 配置」→ 新建 → 选厂商（自动填协议 / 地址 / 模型）→ 填 API Key → 测试调用 → 保存。可选 Ollama 本地模型，免 Key。
2. **配置数据源**：「数据源配置」→ 新建 → 选数据库类型 → 填连接信息 → 测试连接 → 保存。
3. **开口问**：回到「沐问」页，选择数据源与 AI 配置，输入中文需求 → **生成 SQL** → 核对/修改 → **执行 SQL**。

> 未选择数据源时 AI 看不到表结构，只能凭占位名生成，请务必先选数据源并人工核对 SQL。
> 「执行 SQL」按钮在未选择数据源时会置灰。

---

<a id="databases" name="databases"></a>

## 🗄️ 支持的数据库

下拉中的每种类型都由程序自动拼好连接串并**使用内置驱动**直连，无需自行安装任何驱动包：

| 数据库类型 | 使用的驱动 | 连接方式 | Windows / Linux 打包版 | macOS 打包版 |
|---|---|---|---|---|
| MySQL | PyMySQL | MySQL 协议（3306） | ✅ 内置 | ✅ 内置 |
| MariaDB | PyMySQL | 兼容 MySQL 协议（3306） | ✅ 内置 | ✅ 内置 |
| PostgreSQL | psycopg2 | PG 协议（5432） | ✅ 内置 | ✅ 内置 |
| OpenGauss | psycopg2 | PG 协议（5432） | ✅ 内置 | ✅ 内置 |
| 瀚高 HighGo | psycopg2 | 兼容 PG 协议（5866） | ✅ 内置 | ✅ 内置 |
| 海量 Vastbase | psycopg2 | 兼容 PG 协议（5432） | ✅ 内置 | ✅ 内置 |
| 人大金仓 KingbaseES | ksycopg2（官方，自带 libkci），psycopg2 兜底 | 54321 | ✅ 内置 | ✅ 自动走 PG 协议，多数实例可直连 |
| OceanBase | PyMySQL | MySQL 租户兼容 MySQL 协议（2881） | ✅ 内置 | ✅ 内置 |
| TiDB | PyMySQL | 兼容 MySQL 协议（4000） | ✅ 内置 | ✅ 内置 |
| Oracle | oracledb（瘦模式，无需 Instant Client） | `service_name` 或 SID（1521） | ✅ 内置 | ✅ 内置 |
| SQL Server | pymssql（自带 FreeTDS，无需 ODBC） | TDS（1433） | ✅ 内置 | ✅ 内置 |
| 达梦 DM | dmpython + dmSQLAlchemy（官方，wheel 自带客户端库） | DM 协议（5236） | ✅ 内置 | ⚠️ 厂商无 macOS 驱动 |
| 南大通用 GBase 8a | PyMySQL | 兼容 MySQL 协议（5258） | ✅ 内置 | ✅ 内置 |
| DB2 | ibm_db + ibm-db-sa（IBM 官方，wheel 自带 clidriver） | DB2 协议（50000） | ✅ 内置 | ✅ 内置 |
| 其他（自定义） | 自备 | 「连接参数」中填 `{"url": "..."}` | 自行安装驱动 | 自行安装驱动 |

> **神通（ShenTong）/ 崖山 YashanDB / H2 未列入内置类型**：神通官方仅发布 JDBC / ODBC 驱动；崖山官方 Python 驱动不通过 PyPI 分发；H2 是纯 Java 引擎，必须本机装有 JVM 和 `h2.jar` 才能经 JDBC 桥接入——都与「开箱直连」目标冲突。需要连接时请选「其他（自定义）」，自行安装桥接驱动并提供 SQLAlchemy 连接串。OceanBase 的 **Oracle 租户**同理（MySQL 租户已内置）。

### 常见连接字符串（自定义数据源参考）

- MySQL / MariaDB / OceanBase(MySQL 租户) / TiDB / GBase 8a：`mysql+pymysql://user:pwd@host:3306/db?charset=utf8mb4`（OceanBase 默认 2881，TiDB 默认 4000，GBase 8a 默认 5258）
- PostgreSQL / OpenGauss / 瀚高 HighGo / 海量 Vastbase：`postgresql+psycopg2://user:pwd@host:5432/db`（HighGo 默认 5866）
- 人大金仓（PG 协议兜底写法）：`postgresql+psycopg2://user:pwd@host:54321/db`
- Oracle：`oracle+oracledb://user:pwd@host:1521/?service_name=ORCL`（或用 SID：`…/XE`）
- SQL Server：`mssql+pymssql://user:pwd@host:1433/db`
- DB2：`ibm_db_sa://user:pwd@host:50000/db`
- 达梦：`dm+dmpython://user:pwd@host:5236/DAMENG`
- 自定义：在数据源的「连接参数」中填入 `{"url": "your+dialect://..."}`。

---

<a id="ai" name="ai"></a>

## 🤖 支持的 AI 厂商

### OpenAI 兼容 `/chat/completions`

| 厂商 | 默认 Base URL | 默认模型 |
|---|---|---|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| 阿里百炼（Qwen） | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-max` |
| 千问（Qwen） | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` |
| 火山引擎 ARK（Coding Plan） | `https://ark.cn-beijing.volces.com/api/coding/v3` | `ark-code-latest` |
| 豆包（Doubao） | `https://ark.cn-beijing.volces.com/api/v3` | `doubao-pro-32k` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| 百度千帆（ERNIE） | `https://qianfan.baidubce.com/v2` | `ernie-4.0-turbo-8k` |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-plus` |
| Kimi（Moonshot） | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| 胜算云 | `https://router.shengsuanyun.com/api/v1` | `deepseek-chat` |
| GitHub Copilot / Models | `https://models.inference.ai.azure.com` | `gpt-4o-mini` |
| **Ollama（本地）** | `http://localhost:11434/v1` | 本地已拉取的模型 |
| 兼容 OpenAI 协议（自定义） | 用户填写 | 用户填写 |

### Anthropic 兼容 `/messages`

| 厂商 | 默认 Base URL | 默认模型 |
|---|---|---|
| Anthropic Claude | `https://api.anthropic.com/v1` | `claude-3-5-sonnet-latest` |
| 火山引擎 ARK（切到 Anthropic 协议时自动填充） | `https://ark.cn-beijing.volces.com/api/coding` | `ark-code-latest` |
| 兼容 Anthropic 协议（自定义） | 用户填写 | 用户填写 |

> 选择厂商后，**协议**、**Base URL**、**默认模型** 会自动填充。火山方舟等同时支持两种协议的厂商在列表中只有一项，在「协议」下拉里切换时会**自动换成对应协议的 API 地址**；也可以手动切换协议对接不在预置列表中的第三方兼容网关（LiteLLM / OpenRouter 等）。
>
> URL 拼接规则与官方 SDK 一致：OpenAI 地址需包含版本段（如 `…/api/coding/v3`，程序补 `/chat/completions`）；Anthropic 地址填到根即可（如 `…/api/coding`，与 Claude Code 的 `ANTHROPIC_BASE_URL` 写法相同，程序自动补 `/v1/messages`；若地址已以 `/v1` 结尾则只补 `/messages`）。

---

<a id="config" name="config"></a>

## ⚙️ 配置说明

配置文件位置取决于运行方式：

| 运行方式 | `config.json` 位置 |
|---|---|
| 从源码运行 | 项目根目录（示例见 `config.example.json`） |
| macOS 打包版 | `~/Library/Application Support/muask/` |
| Windows 打包版 | `%APPDATA%\muask\` |
| Linux 打包版 | `$XDG_CONFIG_HOME/muask/`（默认 `~/.config/…`） |

打包版**不能**把配置写在程序目录里：macOS 的 `.app` 一旦被写入就会破坏代码签名导致无法启动，而单文件版的运行目录是临时目录、退出即删。旧版本正是因此每次重启都丢配置 —— 现在会自动把旧配置迁移到上表位置，无需手动搬。

密码与 API Key 以 base64 编码存储（前缀 `b64:`），实用性大于安全性 —— 如需生产强度请自行改用 `cryptography` 加密。

---

<a id="architecture" name="architecture"></a>

## 🧱 技术架构

### 技术栈

| 层次 | 选型 |
|---|---|
| 桌面 UI | Python 3 / **PySide6**（Qt Widgets），QSS 自绘样式、无边框标题栏 |
| 数据访问 | **SQLAlchemy** + 各数据库原生驱动；达梦 / 金仓使用项目内的 SQLAlchemy 方言适配 |
| AI 接入 | `requests` 直连，**OpenAI `/chat/completions`** 与 **Anthropic `/messages`** 双协议适配层 |
| 并发模型 | QThread 后台 Worker（AI 生成、连接测试、SQL 执行、表结构读取），UI 不阻塞 |
| 配置存储 | 本地 `config.json`，跨平台用户目录，旧配置自动迁移 |
| 打包发布 | **PyInstaller**（Windows / Linux 单文件，macOS `.app` + DMG）；GitHub Actions 三平台并行构建发版 |

### 工作流程

```
┌────────────┐   问题 + 真实表结构    ┌──────────────┐
│  Text2SQL  │ ─────────────────────▶ │  AI 适配层    │
│   页面     │                        │ OpenAI /     │
│            │ ◀───────────────────── │ Anthropic /  │
└─────┬──────┘       生成 SQL          │ Ollama       │
      │                                └──────────────┘
      │ SQL 预检（括号 / 引号 / 语句完整性）
      ▼
┌────────────┐   SQLAlchemy 执行   ┌──────────────┐
│ SQL 编辑区  │ ──────────────────▶ │  数据库       │
│（可人工修改）│ ◀────────────────── │ 14 类内置驱动 │
└────────────┘   表格 + 分页结果     └──────────────┘
```

### 目录结构

```
muask/
├── main.py                        # 应用入口
├── requirements.txt               # 依赖清单
├── config.example.json            # 示例配置
├── muask.spec                     # PyInstaller 配置（macOS 出 .app，Win/Linux 出单文件）
├── README.md / README.en.md       # 中文 / 英文说明
├── LICENSE                        # MIT 协议
├── .github/workflows/release.yml  # 三平台 CI 构建与发版
├── scripts/
│   ├── build_macos.sh             # macOS 构建 + ad-hoc 签名 + 打 DMG
│   ├── prepare_icon.py            # 从带背景的素材抠出透明底圆角母版
│   └── make_icons.py              # 由母图生成 .icns / .ico
├── assets/                        # 图标、二维码、界面截图
└── app/
    ├── __init__.py                # 版本号（单一来源）
    ├── paths.py                   # 资源 / 配置路径解析（源码 vs 打包）
    ├── config.py                  # config.json 读写 + DB/AI 配置管理
    ├── db.py                      # SQLAlchemy URL 构造 + 各方言分页 + 执行 + 预检
    ├── db_dialects.py             # 达梦 / 人大金仓 SQLAlchemy 方言适配
    ├── ai_providers.py            # AI 适配层（OpenAI + Anthropic 双协议）
    ├── workers.py                 # 后台 QThread（AI 生成、连接测试、SQL 执行）
    ├── highlighter.py             # SQL 语法高亮
    ├── styles.py                  # QSS 样式
    ├── toast.py                   # Toast 通知
    ├── error_dialog.py            # 错误弹窗
    ├── title_bar.py               # 自定义标题栏（版本检查 / 捐赠 / 窗口控制）
    ├── update_dialog.py           # 新版本提示弹窗
    ├── updater.py                 # GitHub / Gitee 版本检查
    ├── donate_dialog.py           # 打赏二维码弹窗
    ├── pages_text2sql.py          # Text2SQL 页面
    ├── pages_data_source.py       # 数据源配置页面
    ├── pages_ai.py                # AI 配置页面
    ├── pages_about.py             # 软件说明页面
    ├── pages_about_us.py          # 关于我们页面
    └── main_window.py             # 主窗口
```

---

<a id="build" name="build"></a>

## 🛠️ 开发与打包

打包配置集中在 `muask.spec`（不要用裸 `pyinstaller -F main.py`，会丢掉 assets 和 macOS 的 bundle 结构）。

**Windows / Linux** —— 单文件可执行：

```bash
pip install pyinstaller
pyinstaller --clean --noconfirm muask.spec
# 产物：dist/muask[.exe]
```

**macOS** —— `.app` bundle + DMG，脚本会顺带做 ad-hoc 签名：

```bash
pip install pyinstaller
./scripts/build_macos.sh
# 产物：dist/muask.app
#       dist/muask-macos-arm64.dmg
```

macOS 必须打成 `.app` 而不是裸可执行文件：Gatekeeper **不给**未签名的裸 Unix 可执行文件任何放行入口，弹窗只有「移到废纸篓」一个选项，用户根本没法运行。

若你有 Apple Developer 会员，把 `scripts/build_macos.sh` 里两处 `TODO(notarize)` 按注释改成真实 Developer ID 并加上 `notarytool` / `stapler` 两步，用户即可**零提示**直接双击运行。

**换图标**：

- 素材本身是**透明底方形图标**：跑 `python3 scripts/make_icons.py 你的图.png`，脚本会归一化生成 1024x1024 母版 `assets/app_icon.png`（Qt 窗口图标），再重新生成 `.icns` / `.ico`。
- 素材是**带照片背景的 JPG**（如现在的 `assets/icon.jpg`）：先跑 `python3 scripts/prepare_icon.py assets/icon.jpg` 抠出圆角方块本体、生成透明底母版，再跑 `python3 scripts/make_icons.py`。

两个脚本都依赖 macOS 自带的 `sips` / `iconutil`（prepare 还用到项目已装的 PySide6），无需额外图像库。

---

<a id="roadmap" name="roadmap"></a>

## 🗺️ 版本与维护

- **当前版本**：v1.4.1（2026-10-07）—— 修复 Ollama 本地模型免 Key 使用、SQL Server 分页、连接串转义与 SQL 预检误判，并精简安装包体积。
- **更新日志**：每次发版均在 [GitHub Releases](https://github.com/vfaner/muask/releases) / [Gitee Releases](https://gitee.com/super_rgh/muask/releases) 附完整说明；[官网更新日志](https://muask.qqmu.com/changelog.html) 同步维护。
- **维护状态**：项目活跃维护中，问题反馈与 Pull Request 会持续处理。
- **迭代方向**（按实际需求调整，非承诺）：更多数据库与国产数据库适配、表结构筛选与提示词优化、查询结果导出、更完善的错误诊断与使用文档。

后续版本会继续通过 GitHub Actions 三平台自动构建，并在应用内提供版本检查与更新提示。

---

<a id="faq" name="faq"></a>

## ❓ 常见问题与已知局限

### 常见问题

- **一定要买 API Key 吗？** 不一定。AI 配置可选 `Ollama（本地）`，本机运行开源模型，免费、免 Key；云端厂商也有不同价位，按需选择。
- **我的表结构和查询数据会被上传吗？** 生成 SQL 时，表结构与你的问题会发送给所选 AI 厂商；数据库连接信息与查询结果始终留在本机。敏感场景请选本地 Ollama，全程无需外网。
- **AI 生成的 SQL 安全吗？** SQL 执行前完整展示、可手动修改；数据库报错原样显示。建议使用只读账号，从权限层兜底。
- **需要安装 Python 或数据库驱动吗？** 安装包已内置运行环境与全部驱动，不需要。只有「其他（自定义）」类型需要自备驱动。
- **Windows / macOS 首次运行被拦截？** 见上文「快速开始」中的放行步骤，各只需放行一次。

### 已知局限

- **达梦 / 人大金仓的官方 Python 驱动只有 Windows / Linux wheel，没有 macOS 版**（厂商发布限制）：Windows / Linux 打包版内置官方原生驱动；macOS 版连金仓自动改用 PostgreSQL 协议，连达梦请使用 Windows / Linux 版，或从源码运行。
- **神通（ShenTong）/ 崖山 YashanDB / H2 不在内置类型中**：官方仅有 JDBC / ODBC 驱动或纯 Java 引擎，请用「其他（自定义）」接入。
- GBase 8a 通过 MySQL 协议接入（默认端口 5258）；其他 GBase 系列（如 8s / 8t）协议不同，请用「其他（自定义）」。OceanBase 的 Oracle 租户同理。
- MariaDB 官方 Python connector 只有 Windows wheel，本项目统一用 PyMySQL 直连，三平台均可内置。
- 分页对复杂 SQL（含 `ORDER BY / GROUP BY / WITH`）以子查询方式包裹，绝大多数场景可用；极少数极端 SQL 可能需要手动加分页。
- 安全性：为便于开发调试，允许所有 SQL 操作。生产环境务必单独做权限控制。
- 多语句一次执行不支持（底层驱动通常一次只发一条），需要逐条执行。

---

<a id="contributing" name="contributing"></a>

## 🤝 贡献与反馈

我们欢迎任何形式的参与：

- 🐛 **问题反馈**：在 [Issues](https://gitee.com/super_rgh/muask/issues) 提交时，请附上操作系统、软件版本、数据库类型与完整报错，便于快速定位。
- 💡 **功能建议**：欢迎在 Issues 中描述使用场景与期望效果。
- 🔧 **代码贡献**：Fork → 新建分支 → 提交改动 → 发起 Pull Request。提交前请确保 `python main.py` 可正常启动，并说明改动目的。
- 📖 **文档改进**：README、使用说明的修正同样欢迎。

**联系方式**

| 方式 | 号码 |
|---|---|
| 邮箱 | [vfaner@88.com](mailto:vfaner@88.com) |
| QQ | [817094](https://wpa.qq.com/msgrd?v=3&uin=817094&site=qq&menu=yes) / [2912167928](https://wpa.qq.com/msgrd?v=3&uin=2912167928&site=qq&menu=yes) |
| QQ 群 | [426669837（点击加群）](https://qun.qq.com/universal-share/share?ac=1&authKey=RI%2FAwTODgEDm0uGAqGTqlwV7%2FPjE7njMa3DIb8c3X7H8keqdZ4hkJpDDpDjYkw5p&busi_data=eyJncm91cENvZGUiOiI0MjY2Njk4MzciLCJ0b2tlbiI6Imh1MWtOZHRYZ3E2WnpyK3dLK1N1WWp6cFprRjNrQlZqSXZ1U0pMdXRtcjZZcjhFTndJcXV4NUNnQXhUV0tjMFEiLCJ1aW4iOiI4MTcwOTQifQ%3D%3D&data=V88jHxiTMtasEWtL2EfVUg97X6IQwgKM6LRY46VLu2mEuaWkzBX0dSiV0iEgzGkFVaSmUCTMig_Sw8wCwznxhQ&svctype=4&tempid=h5_group_info) |
| 微信 | qqmu66（复制即可添加） |
| 官网 | https://muask.qqmu.com |

**项目地址**

| 平台 | 地址 |
|---|---|
| Gitee（主仓库 / 国内） | https://gitee.com/super_rgh/muask |
| GitHub | https://github.com/vfaner/muask |

如果这个项目对你有帮助，欢迎点一个 **Star ⭐** —— 这是对我们持续维护最大的鼓励。

---

## 📄 开源协议

本项目基于 [**MIT License**](./LICENSE) 开源，版权所有 © 2025 vfaner。个人与商业场景均可自由使用、修改与分发，请保留版权声明。
