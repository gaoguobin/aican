# AICAN

通过自然语言控制周立功（ZLG）CAN卡。在 Claude Code 中直接用中文打开设备、收发 CAN 帧、解析 DBC 信号。

[English](README.md)

## 功能特性

- **16 个 MCP 工具**：设备管理、通道配置、CAN/CANFD 收发、DBC 信号解析
- **Skill 引导工作流**：交互式初始化、最佳实践提示、常见错误预警
- **中文信号搜索**：用中文关键词搜索 DBC 信号（如"母线电压" → BusVolt）
- **支持机型**：USBCANFD-200U/100U/MINI/400U/800U、USBCAN-2E-U/4E-U/8E-U、USBCAN-I/II

## 环境要求

- **Windows**（ZLG SDK 仅支持 Windows）
- **Python 3.12+**
- **Claude Code** 1.0.33+
- **ZLG CAN 硬件**，通过 USB 连接到电脑

## 安装步骤

### 1. 克隆仓库并安装

```bash
git clone https://github.com/gaoguobin/aican.git
cd aican
pip install -e .
```

**Python 环境建议**：推荐使用 `uv` 管理虚拟环境，避免依赖冲突：

```bash
pip install uv
uv venv .venv
.venv\Scripts\activate
uv pip install -e .
```

### 2. 安装 ZLG SDK

确认 ZLG 驱动已安装，并将 SDK DLL 文件（`zlgcan.dll` 等）放在以下任一位置：

- 项目根目录下的 `zlgcan/` 文件夹（默认）
- 系统 PATH 中的任意目录
- 通过环境变量 `ZLGCAN_SDK_PATH` 指定的路径

### 3. 加载为 Claude Code 插件

```bash
claude --plugin-dir /path/to/aican
```

或通过插件市场安装（便于后续更新）：

```
/plugin marketplace add gaoguobin/aican
/plugin install aican@aican-marketplace
```

## 快速开始

安装完成后，打开 Claude Code，直接输入：

> "打开CAN卡，读取母线电压"

Skill 会自动引导 Claude 完成：设备选择 → 通道初始化 → 信号读取。

更多示例：

```
发送CAN报文 ID=0x100 数据=[0x01, 0x02]
搜索DBC里和电机转速相关的信号
用500kbps初始化通道0
读一下当前的母线电流和电压
清空接收缓冲区，然后接收10帧
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

配置保存在 `skills/can-card/user-config.json`。如需重新配置，删除该文件后重新加载 Skill 即可。

## DBC 信号搜索示例

AICAN 支持用中文关键词搜索 DBC 信号，Claude 会自动将中文语义映射到英文信号名：

| 中文输入 | 找到的信号示例 |
|----------|----------------|
| 母线电压 | BusVoltage、DCBusVolt |
| 母线电流 | BusCurrent、DCBusCurr |
| 电机转速 | MotorSpeed、ActualSpeed |
| 温度 | MotorTemp、InverterTemp |
| 故障 / 报错 | FaultCode、ErrorStatus |
| 扭矩 | TorqueCmd、ActualTorque |
| 充电状态 | ChargeStatus、SOC |

示例对话：

> 搜索DBC里和"电机转速"有关的信号

Claude 会调用 `search_signal` 工具，返回匹配的信号名、所在报文 ID、起始位、长度、factor/offset 等信息。

## 高级配置

### 自定义 SDK 路径

如果 ZLG SDK 安装在非默认位置，设置环境变量：

```bash
set ZLGCAN_SDK_PATH=C:\path\to\zlgcan
```

或在 PowerShell 中：

```powershell
$env:ZLGCAN_SDK_PATH = "C:\path\to\zlgcan"
```

## 常见问题排查

### DLL 找不到 / 无法加载

**现象**：启动时报 `FileNotFoundError` 或 `OSError: [WinError 126]`

**解决**：
1. 确认已安装 ZLG 驱动（从 ZLG 官网下载）
2. 检查 `zlgcan/` 目录下是否有 `zlgcan.dll`
3. 若 DLL 在其他位置，设置 `ZLGCAN_SDK_PATH` 环境变量

---

### 波特率不匹配 / 无法接收报文

**现象**：`init_channel` 成功，但 `receive` 一直返回空

**解决**：
1. 确认波特率与总线上其他节点一致（常用：250kbps、500kbps、1Mbps）
2. 检查 CAN 总线是否已正确终端匹配（120Ω 终端电阻）
3. 尝试用 `get_receive_count` 确认是否有帧进入缓冲区

---

### 缓冲区积压旧数据

**现象**：读到的数据时间戳很旧，不是最新帧

**解决**：在每次接收前调用 `clear_buffer` 清空缓冲区：

> "先清空缓冲区，再读取最新的母线电压"

---

### 扩展帧 ID 解析错误

**现象**：DBC 中的 ID 与实际 CAN ID 对不上

**原因**：DBC 文件中扩展帧的 ID = 实际 CAN ID | 0x80000000

**解决**：AICAN 自动处理此转换，无需手动计算。如需验证：

```python
dbc_id = 0x98FF0300          # DBC 中的原始 ID
actual_id = dbc_id & 0x1FFFFFFF  # 实际 CAN ID
print(hex(actual_id))        # 0x18ff0300
```

---

### 设备被占用 / 无法打开

**现象**：`open_device` 报设备已被占用

**解决**：
1. 关闭其他 CAN 分析软件（如 ZCANPRO）
2. 调用 `close_device` 后重新 `open_device`
3. 若仍无法解决，重新插拔 USB

## 许可证

MIT — 详见 [LICENSE](LICENSE)

ZLG CAN SDK — 详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
