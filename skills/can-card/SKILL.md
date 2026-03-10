---
name: can-card
description: 操作周立功CAN卡（USBCAN/USBCANFD）。当用户提到CAN卡、CAN设备、CAN通信、CAN报文、DBC信号、波特率设置、CAN收发等话题时使用。
---

# 周立功 CAN 卡操作指南

## 首次使用：交互式配置

**每次加载此 skill 时，先读取配置文件 `${CLAUDE_SKILL_DIR}/user-config.json`。**

- **文件存在** → 直接使用其中的配置值，跳过配置流程
- **文件不存在** → 执行以下交互式配置：

1. 调用 `list_supported_devices()` 获取可用设备列表
2. 用 AskUserQuestion 询问用户：
   - 设备型号（将设备列表作为选项）
   - 波特率（常用值：125000 / 250000 / 500000 / 1000000，默认推荐 500000）
3. 再用 AskUserQuestion 询问：
   - 通道号（默认 0）
   - DBC 文件路径（可选，留空则不自动加载）
4. 将配置写入 `${CLAUDE_SKILL_DIR}/user-config.json`，格式：

```json
{
  "device_type": "USBCAN-2E-U",
  "baudrate": 500000,
  "channel": 0,
  "dbc_path": "D:/path/to/file.dbc"
}
```

> `${CLAUDE_SKILL_DIR}` 即此 skill.md 所在目录。用户后续可直接编辑此 JSON 文件修改配置。

---

## 标准操作流程

**必须按顺序执行，不可跳步：**

1. **打开设备** → `open_device("{device_type}")`
2. **初始化通道** → `init_channel("{device_type}", channel={channel}, baudrate={baudrate})`
3. **收发数据**（见下方场景）
4. **关闭设备** → `close_device("{device_type}")`（结束时）

> 上述参数均取自 user-config.json 中的值。

## 常用场景

### 接收 CAN 报文
```
clear_buffer → receive(filter_ids=[目标ID])
```
**关键：接收前务必 clear_buffer！** 缓冲区会积压旧帧，不清除会读到过期数据。

### 读取 DBC 信号值
```
load_dbc("{dbc_path}") → read_signal("信号名关键词")
```
read_signal 内部已自动处理 clear_buffer + receive + 解码。

### 发送 CAN 报文
```
send_can("{device_type}", can_id=0x100, data=[0x01, 0x02, ...])
```
扩展帧需加 `is_extended=True`。

## DBC 注意事项

- DBC 中扩展帧 ID = 实际 CAN ID | 0x80000000（最高位为扩展帧标志）
- search_signal 支持信号名和中文注释模糊搜索

## 避坑要点

1. **接收前必须 clear_buffer** — 最常见问题
2. **filter_ids 用实际 CAN ID**（不是 DBC 中带 0x80000000 的值）
3. **波特率要匹配** — 与被测设备一致，否则无法通信
4. **先检查设备状态** — 用 list_open_devices 确认设备是否已打开
