# AICAN Product Release Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Release AICAN as a Claude Code Plugin on GitHub with self-hosted marketplace.

**Architecture:** Restructure existing MCP Server + Skill into standard Claude Code Plugin format. Rename SDK dir, auto-detect DLL paths, add plugin manifests, migrate skill, write docs.

**Tech Stack:** Python 3.12, FastMCP, cantools, ZLG CAN SDK (ctypes)

**Spec:** `docs/superpowers/specs/2026-03-10-product-release-design.md`

---

## Chunk 1: Restructure + Code Changes

### Task 1: Rename ZLG SDK directory

**Files:**
- Rename: `zlgcan_python_251211/` → `zlgcan/`

- [ ] **Step 1: Rename directory**

Run:
```bash
cd D:/OneDrive/ClaudeCode/AICAN && mv zlgcan_python_251211 zlgcan
```

- [ ] **Step 2: Verify contents intact**

Run:
```bash
ls D:/OneDrive/ClaudeCode/AICAN/zlgcan/
```
Expected: zlgcan.py, zlgcan.dll, kerneldlls/, etc.

---

### Task 2: Update can_manager.py — SDK path auto-detection

**Files:**
- Modify: `src/aican/can_manager.py:19-31`

- [ ] **Step 1: Replace hardcoded path with auto-detection**

Replace lines 19-31 (from `# 将 zlgcan_python_251211` to `import zlgcan`) with:

```python
def _find_zlgcan_dir() -> Path:
    """Locate ZLG CAN SDK directory by priority."""
    candidates = []

    # 1. Environment variable
    env_path = os.environ.get("ZLGCAN_SDK_PATH")
    if env_path:
        candidates.append(Path(env_path))

    # 2. Package root / zlgcan/ (pip install -e . scenario)
    _pkg_root = Path(__file__).resolve().parent.parent.parent
    candidates.append(_pkg_root / "zlgcan")

    # 3. CWD / zlgcan/
    candidates.append(Path.cwd() / "zlgcan")

    for p in candidates:
        if p.exists() and (p / "zlgcan.py").exists():
            return p

    raise RuntimeError(
        "ZLG CAN SDK not found. Either:\n"
        "  1. Set ZLGCAN_SDK_PATH environment variable\n"
        "  2. Ensure 'zlgcan/' directory exists in the project root\n"
        "See: https://github.com/<owner>/aican#installation"
    )


_zlgcan_dir = _find_zlgcan_dir()
sys.path.insert(0, str(_zlgcan_dir))

# DLL search paths
_dll_dir = _zlgcan_dir / "kerneldlls"
for p in [_zlgcan_dir, _dll_dir]:
    if p.exists():
        os.add_dll_directory(str(p))
os.environ["PATH"] = (
    str(_zlgcan_dir) + os.pathsep + str(_dll_dir) + os.pathsep
    + os.environ.get("PATH", "")
)

import zlgcan
```

- [ ] **Step 2: Verify module still imports**

Run:
```bash
cd D:/OneDrive/ClaudeCode/AICAN && python -c "from aican.can_manager import get_manager; print('OK')"
```
Expected: `OK`

---

### Task 3: Update pyproject.toml

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Rewrite pyproject.toml**

Full content:

```toml
[project]
name = "aican"
version = "0.1.0"
description = "AICAN - Control ZLG CAN devices with natural language"
requires-python = ">=3.12"
license = "MIT"
readme = "README.md"
authors = [{ name = "Cedric Gao" }]
keywords = ["can-bus", "zlg", "automotive", "mcp"]
classifiers = [
    "Operating System :: Microsoft :: Windows",
    "Programming Language :: Python :: 3.12",
]
dependencies = [
    "mcp[cli]>=1.0.0,<2",
    "cantools>=39.0.0,<40",
]

[project.urls]
Homepage = "https://github.com/<owner>/aican"
Repository = "https://github.com/<owner>/aican"

[project.scripts]
aican = "aican.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/aican"]
```

- [ ] **Step 2: Verify pip install**

Run:
```bash
cd D:/OneDrive/ClaudeCode/AICAN && pip install -e .
```
Expected: Successfully installed aican-0.1.0

- [ ] **Step 3: Verify MCP server starts**

Run:
```bash
python -c "from aican.server import mcp; print(f'Tools: {len(mcp._tool_manager._tools)}')"
```
Expected: `Tools: 16` (or current tool count)

---

### Task 4: Clean up residual files

- [ ] **Step 1: Delete pip install artifact**

Run:
```bash
rm "D:/OneDrive/ClaudeCode/AICAN/=39.0.0"
```

---

## Chunk 2: Plugin Configuration + Skill Migration

### Task 5: Create plugin manifest

**Files:**
- Create: `.claude-plugin/plugin.json`

- [ ] **Step 1: Create directory and file**

```json
{
  "name": "aican",
  "description": "Control ZLG CAN devices with natural language via MCP + Skill",
  "version": "0.1.0",
  "author": { "name": "Cedric Gao" },
  "homepage": "https://github.com/<owner>/aican",
  "repository": "https://github.com/<owner>/aican",
  "license": "MIT",
  "keywords": ["can-bus", "zlg", "automotive", "mcp", "skill"]
}
```

---

### Task 6: Create marketplace manifest

**Files:**
- Create: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Create file**

```json
{
  "name": "aican-marketplace",
  "owner": { "name": "Cedric Gao" },
  "plugins": [
    {
      "name": "aican",
      "source": ".",
      "description": "Control ZLG CAN devices with natural language via MCP + Skill"
    }
  ]
}
```

---

### Task 7: Create root .mcp.json

**Files:**
- Modify: `.mcp.json` (replace existing)

- [ ] **Step 1: Rewrite .mcp.json**

```json
{
  "mcpServers": {
    "aican": {
      "command": "python",
      "args": ["-m", "aican"]
    }
  }
}
```

No `cwd` field — relies on `pip install -e .` making the package globally available.

---

### Task 8: Migrate Skill to plugin layout

**Files:**
- Create: `skills/can-card/SKILL.md` (from `.claude/skills/can-card/skill.md`)
- Source: `.claude/skills/can-card/skill.md`

- [ ] **Step 1: Create skills directory and SKILL.md**

Read `.claude/skills/can-card/skill.md` and create `skills/can-card/SKILL.md` with these changes:
1. Add `name: can-card` to frontmatter (existing file only has `description:`)
2. Replace ALL occurrences of `{SKILL_DIR}` with `${CLAUDE_SKILL_DIR}` in the body
3. Keep all other content (操作流程、场景、避坑要点) unchanged

Final frontmatter:

```yaml
---
name: can-card
description: 操作周立功CAN卡（USBCAN/USBCANFD）。当用户提到CAN卡、CAN设备、CAN通信、CAN报文、DBC信号、波特率设置、CAN收发等话题时使用。
---
```

Body content stays the same, except all occurrences of `{SKILL_DIR}` → `${CLAUDE_SKILL_DIR}`.

- [ ] **Step 2: Verify plugin structure**

Run:
```bash
ls D:/OneDrive/ClaudeCode/AICAN/.claude-plugin/ && ls D:/OneDrive/ClaudeCode/AICAN/skills/can-card/
```
Expected: plugin.json + marketplace.json; SKILL.md

---

## Chunk 3: Documentation + Git Setup

### Task 9: Create LICENSE

**Files:**
- Create: `LICENSE`

- [ ] **Step 1: Write MIT license**

Standard MIT license text with `Copyright (c) 2026 Cedric Gao`.

---

### Task 10: Create THIRD_PARTY_NOTICES.md

**Files:**
- Create: `THIRD_PARTY_NOTICES.md`

- [ ] **Step 1: Write third-party notice**

```markdown
# Third-Party Notices

## ZLG CAN SDK (zlgcan/)

The `zlgcan/` directory contains the ZLG (ZHIYUAN Electronics) CAN SDK,
including `zlgcan.py`, `zlgcan.dll`, and supporting DLLs in `kerneldlls/`.

- **Provider:** Guangzhou ZHIYUAN Electronics Co., Ltd. (周立功)
- **Source:** Publicly available from ZLG official resources
- **Usage:** Required for communicating with ZLG CAN hardware devices

This SDK is redistributed for convenience. All rights belong to the
original author. Please refer to ZLG's official documentation for
licensing terms.
```

---

### Task 11: Create .gitignore and .gitattributes

**Files:**
- Create: `.gitignore`
- Create: `.gitattributes`

- [ ] **Step 1: Write .gitignore**

```gitignore
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
*.egg
.venv/
venv/

# User-specific
DBC/
skills/can-card/user-config.json
.claude/

# IDE
.vscode/
.idea/

# OS
Thumbs.db
.DS_Store
```

- [ ] **Step 2: Write .gitattributes**

```gitattributes
*.dll binary
*.pdf binary
```

---

### Task 12: Write README.md

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README**

Structure:

```markdown
# AICAN

AI-powered control for ZLG CAN devices. Use natural language to open devices,
send/receive CAN frames, and decode DBC signals — all through Claude Code.

[中文文档](README_zh.md)

## Features

- 16 MCP tools: device management, channel config, CAN/CANFD send/receive, DBC signal decoding
- Skill-guided workflow: interactive setup, best-practice prompts, common pitfall warnings
- Chinese signal search: search DBC signals by Chinese terms (e.g. "母线电压" → BusVolt)
- Supports: USBCANFD-200U/100U/MINI/400U/800U, USBCAN-2E-U/4E-U/8E-U, USBCAN-I/II

## Requirements

- **Windows** (ZLG SDK is Windows-only)
- **Python 3.12+**
- **Claude Code** 1.0.33+
- **ZLG CAN hardware** connected via USB

## Installation

### 1. Clone and install

​```bash
git clone https://github.com/<owner>/aican.git
cd aican
pip install -e .
​```

### 2. Load as Claude Code plugin

​```bash
claude --plugin-dir /path/to/aican
​```

Or add the marketplace for easier updates:

​```
/plugin marketplace add <owner>/aican
/plugin install aican@aican-marketplace
​```

## Quick Start

After installation, open Claude Code and try:

> "打开CAN卡，读取母线电压"

The Skill automatically guides Claude through: device selection → channel init → signal reading.

More examples:
- "发送CAN报文 ID=0x100 数据=[0x01, 0x02]"
- "搜索DBC里和电机转速相关的信号"
- "用500kbps初始化通道0"

## Supported Devices

| Series | Models |
|--------|--------|
| USBCANFD | 200U, 100U, MINI, 400U, 800U |
| USBCAN-xE-U | E-U, 2E-U, 4E-U, 8E-U |
| USBCAN-I/II | USBCAN-I, USBCAN-II |

## MCP Tools

| Category | Tools |
|----------|-------|
| Device | list_supported_devices, list_open_devices, open_device, close_device |
| Channel | init_channel, reset_channel |
| Send | send_can, send_canfd |
| Receive | receive, get_receive_count, clear_buffer |
| DBC | load_dbc, search_signal, read_signal |

## Configuration

On first use, the Skill asks for your device type, baudrate, channel, and
optional DBC file path. Settings are saved to `skills/can-card/user-config.json`.

## License

MIT — see [LICENSE](LICENSE)

ZLG CAN SDK — see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
```

---

### Task 13: Write README_zh.md

**Files:**
- Create: `README_zh.md`

- [ ] **Step 1: Write Chinese README**

Same structure as README.md but in Chinese, with more detailed:
- Installation troubleshooting (DLL path issues, Python version)
- DBC signal search examples with Chinese terms
- Common pitfalls section (clear_buffer before receive, baudrate matching)
- Link back to README.md for English

---

### Task 14: Initialize Git repo and first commit

- [ ] **Step 1: git init**

Run:
```bash
cd D:/OneDrive/ClaudeCode/AICAN && git init
```

- [ ] **Step 2: Stage all files**

Run:
```bash
git add .claude-plugin/ skills/ src/ zlgcan/ tests/ .mcp.json .gitignore .gitattributes pyproject.toml LICENSE THIRD_PARTY_NOTICES.md README.md README_zh.md
```

Note: Do NOT add `DBC/`, `.claude/`, `=39.0.0` (should already be deleted).

- [ ] **Step 3: Verify staged files look correct**

Run:
```bash
git status
```
Expected: All intended files staged, no secrets or DBC data.

- [ ] **Step 4: Create initial commit**

```bash
git commit -m "feat: initial release as Claude Code Plugin v0.1.0

AICAN — AI-powered control for ZLG CAN devices via MCP + Skill.
Supports USBCANFD, USBCAN-xE-U, and USBCAN-I/II series."
```

---

## Post-Release (Manual)

After Tasks 1-14 are complete:

1. Create GitHub repo and push
2. Submit to Anthropic Marketplace: claude.ai/settings/plugins/submit
3. Replace all `<owner>` placeholders with actual GitHub username
