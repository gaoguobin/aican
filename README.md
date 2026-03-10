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

```bash
git clone https://github.com/gaoguobin/aican.git
cd aican
pip install -e .
```

### 2. Load as Claude Code plugin

```bash
claude --plugin-dir /path/to/aican
```

Or add the marketplace for easier updates:

```
/plugin marketplace add gaoguobin/aican
/plugin install aican@aican-marketplace
```

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

To reconfigure, delete the config file and reload the Skill.

## Advanced: Environment Variable

If the ZLG SDK is installed elsewhere, set `ZLGCAN_SDK_PATH`:

```bash
set ZLGCAN_SDK_PATH=C:\path\to\zlgcan
```

## License

MIT — see [LICENSE](LICENSE)

ZLG CAN SDK — see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
