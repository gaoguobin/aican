# AICAN 产品发布设计

## 目标

将 AICAN（MCP Server + Skill）作为 Claude Code Plugin 开源发布到 GitHub，同时提交 Anthropic 官方 Marketplace。

## 仓库结构

```
AICAN/
├── .claude-plugin/
│   ├── plugin.json            # 插件清单
│   └── marketplace.json       # 自建 Marketplace 清单
├── skills/
│   └── can-card/
│       ├── SKILL.md           # Skill 主文件
│       └── user-config.json   # 运行时生成，gitignore
├── .mcp.json                  # MCP Server 配置（插件启用时自动注册）
├── src/aican/
│   ├── __init__.py
│   ├── __main__.py
│   ├── server.py              # MCP 入口
│   └── can_manager.py         # 设备管理与收发逻辑
├── zlgcan/                    # ZLG官方SDK（重命名自 zlgcan_python_251211）
│   ├── zlgcan.py
│   ├── kerneldlls/
│   └── ...
├── pyproject.toml             # 补充元数据
├── LICENSE                    # MIT
├── THIRD_PARTY_NOTICES.md     # ZLG SDK 许可证声明
├── README.md                  # 英文为主，含中文链接
├── README_zh.md               # 中文详细版
├── .gitignore
└── .gitattributes
```

### 删除/不入仓库

- `=39.0.0`（pip 残留文件）
- `DBC/`（用户私有数据）
- `tests/`（保留，但非发布重点）
- `.claude/skills/`（迁移到顶层 `skills/`）
- `skills/can-card/user-config.json`（运行时生成，gitignore）

## Plugin 清单

### .claude-plugin/plugin.json

```json
{
  "name": "aican",
  "description": "Control ZLG CAN devices with natural language via MCP + Skill",
  "version": "0.1.0",
  "author": { "name": "Cedric Gao" },
  "homepage": "https://github.com/gaoguobin/aican",
  "repository": "https://github.com/gaoguobin/aican",
  "license": "MIT",
  "keywords": ["can-bus", "zlg", "automotive", "mcp", "skill"]
}
```

### .claude-plugin/marketplace.json

```json
{
  "name": "aican-marketplace",
  "owner": { "name": "Cedric Gao" },
  "plugins": [{
    "name": "aican",
    "source": ".",
    "description": "Control ZLG CAN devices with natural language"
  }]
}
```

### .mcp.json

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

注意：不再硬编码 cwd，依赖 pip install -e 后全局可用。

## 代码改动

### can_manager.py — DLL 路径自动探测

```
当前：硬编码 Path(__file__).parent.parent.parent / "zlgcan_python_251211"
改为按优先级搜索：
  1. 环境变量 ZLGCAN_SDK_PATH
  2. 包安装目录同级 zlgcan/（pip install -e . 场景）
  3. 当前工作目录下 zlgcan/
  4. 找不到 → 抛出明确错误，提示设置环境变量
```

### pyproject.toml — 补充元数据

```toml
[project]
name = "aican"
version = "0.1.0"
description = "AICAN - Control ZLG CAN devices with natural language"
requires-python = ">=3.12"
license = "MIT"
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
Homepage = "https://github.com/gaoguobin/aican"
Repository = "https://github.com/gaoguobin/aican"

[project.scripts]
aican = "aican.server:main"
```

### Skill 迁移

- `.claude/skills/can-card/skill.md` → `skills/can-card/SKILL.md`（大写，符合标准）
- 内容中 `{SKILL_DIR}` 替换为 `${CLAUDE_SKILL_DIR}`（标准变量）
- frontmatter 改为标准格式：

```yaml
---
name: can-card
description: 操作周立功CAN卡（USBCAN/USBCANFD）。当用户提到CAN卡、CAN设备、CAN通信、CAN报文、DBC信号、波特率设置、CAN收发等话题时使用。
---
```

### zlgcan 目录重命名

- `zlgcan_python_251211/` → `zlgcan/`
- can_manager.py 中路径引用同步更新

## README.md 要点

- 项目简介：一句话说明（AI-powered CAN card control）
- 功能亮点：支持设备列表、DBC信号解析、中文信号搜索
- 安装步骤：3步（clone → pip install → plugin 加载）
- 快速开始：截图/示例对话展示效果
- 支持设备列表
- 前置条件：Python 3.12+、周立功CAN卡硬件、Windows
- 第三方许可证声明（ZLG SDK）
- LICENSE

## 发布路径

1. **GitHub 自建 Marketplace**（首发）
   - 用户：`/plugin marketplace add gaoguobin/aican`
   - 用户：`/plugin install aican@aican-marketplace`

2. **Anthropic 官方 Marketplace**（同步提交）
   - 入口：claude.ai/settings/plugins/submit
   - 审核通过后用户可在 Discover 标签页发现

## 不做的事

- 不上 PyPI（Plugin 机制已足够）
- 不做 Docker（CAN 硬件需 USB passthrough，意义不大）
- 不做 CI/CD（首版，待反馈后加）
- 不做跨平台（ZLG SDK 仅 Windows）
