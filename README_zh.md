# AICAN

通过自然语言控制周立功（ZLG）CAN卡。在 Claude Code 中直接用中文打开设备、收发 CAN 帧、解析 DBC 信号。

[English](README.md)

## 功能特性

- **17 个 MCP 工具**：设备管理、通道配置、CAN/CANFD 收发、DBC 信号解析
- **auto_setup 一键初始化**：一次调用完成 打开设备→初始化通道→加载DBC，幂等操作
- **Skill 引导工作流**：交互式初始化、最佳实践提示、常见错误预警
- **中文信号搜索**：用中文关键词搜索 DBC 信号（如"母线电压" → BusVolt）
- **支持机型**：USBCANFD-200U/100U/MINI/400U/800U、USBCAN-2E-U/4E-U/8E-U、USBCAN-I/II

## 环境要求

- **Windows**（ZLG SDK 仅支持 Windows）
- **Python 3.12+**
- **Claude Code** 1.0.33+
- **ZLG CAN 硬件**，通过 USB 连接到电脑

## 安装

### 通过插件市场安装（推荐）

```
/plugin marketplace add gaoguobin/aican
/plugin install aican@aican-marketplace
```

安装后执行 `/reload-plugins`（或重启 Claude Code），然后 `/mcp` 确认 MCP 服务状态。

> 依赖包（`mcp`、`cantools`）首次启动时自动安装，无需手动操作。

### 本地目录加载

```bash
git clone https://github.com/gaoguobin/aican.git
claude --plugin-dir /path/to/aican
```

## 快速开始

安装完成后，打开 Claude Code，直接输入：

> "打开CAN卡，读取母线电压"

Skill 会自动引导 Claude 完成：设备初始化 → 信号读取。

更多示例：

```
发送CAN报文 ID=0x100 数据=[0x01, 0x02]
搜索DBC里和电机转速相关的信号
用500kbps初始化通道0
读一下当前的母线电流和电压
```

## 支持的设备

| 系列 | 型号 |
|------|------|
| USBCANFD | 200U、100U、MINI、400U、800U |
| USBCAN-xE-U | E-U、2E-U、4E-U、8E-U |
| USBCAN-I/II | USBCAN-I、USBCAN-II |

## MCP 工具列表

| 类别 | 工具 |
|------|------|
| 一键初始化 | auto_setup |
| 设备管理 | list_supported_devices、list_open_devices、open_device、close_device |
| 通道配置 | init_channel、reset_channel |
| 发送 | send_can、send_canfd |
| 接收 | receive、get_receive_count、clear_buffer |
| DBC 解析 | load_dbc、search_signal、read_signal |

## 配置说明

首次使用时，Skill 会交互式询问：

1. 设备型号（如 USBCAN-2E-U）
2. 波特率（如 500kbps）
3. 通道编号（如 0）
4. DBC 文件路径（可选）

配置保存在项目根目录的 `.claude/aican.local.md`（按项目存储，不提交 git）。如需重新配置，编辑或删除该文件即可。

## DBC 信号搜索示例

AICAN 支持用中文关键词搜索 DBC 信号，Claude 会自动将中文语义映射到英文信号名：

| 中文输入 | 找到的信号示例 |
|----------|----------------|
| 母线电压 | BusVoltage、DCBusVolt |
| 母线电流 | BusCurrent、DCBusCurr |
| 电机转速 | MotorSpeed、ActualSpeed |
| 温度 | MotorTemp、InverterTemp |
| 故障 / 报错 | FaultCode、ErrorStatus |

## 常见问题排查

### 波特率不匹配 / 无法接收报文

确认波特率与总线上其他节点一致（常用：250kbps、500kbps、1Mbps）。

### 缓冲区积压旧数据

在每次接收前调用 `clear_buffer` 清空缓冲区。`read_signal` 已内置此操作。

### 扩展帧 ID 解析

DBC 文件中扩展帧 ID = 实际 CAN ID | 0x80000000。AICAN 自动处理此转换。

### 设备被占用

关闭其他 CAN 分析软件（如 ZCANPRO），或调用 `close_device` 后重试。

## 高级配置

如果 ZLG SDK 安装在非默认位置，设置环境变量：

```bash
set ZLGCAN_SDK_PATH=C:\path\to\zlgcan
```

## 赞助

如果 AICAN 帮你节省了时间，欢迎[赞助作者](https://gaoguobin.github.io/sponsor)，资助 API token 消耗。

感谢：

![赞助者列表](https://gaoguobin.github.io/sponsor/list.png)

## 许可证

MIT — 详见 [LICENSE](LICENSE)

ZLG CAN SDK — 详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
