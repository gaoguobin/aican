---
name: can-card
description: 操作周立功(ZLG)CAN卡（USBCAN/USBCANFD系列）。当用户提到CAN卡、CAN设备、CAN通信、CAN报文、DBC信号、波特率设置、CAN收发等话题时使用。触发示例："打开CAN设备"、"读取母线电压"、"发送CAN报文"、"初始化CAN通道"、"搜索DBC信号"、"配置波特率"。
---

# 周立功 CAN 卡操作指南

## 配置

加载此 skill 时，先读项目根目录下的 `.claude/aican.local.md`。

- **存在** → 解析 YAML frontmatter 中的 device_type / baudrate / channel / dbc_path
- **不存在** → 用 AskUserQuestion 询问上述 4 项，写入 `.claude/aican.local.md`，格式：

```markdown
---
device_type: USBCAN-2E-U
baudrate: 500000
channel: 0
dbc_path: D:/path/to/file.dbc
---
```

## 操作流程

**任何操作前先调 `auto_setup`**（幂等，已完成步骤自动跳过）：

```
auto_setup("{device_type}", channel={channel}, baudrate={baudrate}, dbc_path="{dbc_path}")
```

然后直接执行目标操作：

| 场景 | 调用 |
|------|------|
| 读DBC信号值 | `read_signal("信号名关键词", "{device_type}", channel={channel})` |
| 接收CAN报文 | `clear_buffer(...)` → `receive(...)` |
| 发送CAN报文 | `send_can(..., can_id=0x100, data=[0x01, 0x02])` |
| 搜索信号 | `search_signal("关键词")` |
| 关闭设备 | `close_device("{device_type}")` |

## 避坑要点

1. **接收前必须 clear_buffer** — 缓冲区积压旧帧
2. **filter_ids 用实际 CAN ID** — 不是 DBC 中带 0x80000000 的值
3. **波特率要匹配** — 与被测设备一致
4. **所有工具都需要 device_type 参数** — 从 `.claude/aican.local.md` 取值
