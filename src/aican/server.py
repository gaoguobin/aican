"""AICAN MCP Server - 自然语言操作周立功CAN卡"""

import json
from mcp.server.fastmcp import FastMCP

from aican.can_manager import get_manager, CANError

mcp = FastMCP(
    "AICAN",
    instructions="周立功CAN卡MCP Server — 通过自然语言操控CAN设备",
)


# ════════════════════════════════════════
#  设备工具
# ════════════════════════════════════════

@mcp.tool()
def list_supported_devices() -> str:
    """列出所有支持的CAN卡型号及其设备系列。
    用于查看可用设备类型、设备类型ID和所属系列。"""
    mgr = get_manager()
    return json.dumps(mgr.get_supported_devices(), ensure_ascii=False, indent=2)


@mcp.tool()
def list_open_devices() -> str:
    """列出当前已打开的设备及其通道状态。
    显示设备类型、通道配置（波特率、CAN/CANFD模式、是否已启动）等信息。"""
    mgr = get_manager()
    devices = mgr.list_devices()
    if not devices:
        return "当前没有已打开的设备。"
    return json.dumps(devices, ensure_ascii=False, indent=2)


@mcp.tool()
def open_device(device_type: str, device_index: int = 0) -> str:
    """打开一个CAN设备。

    Args:
        device_type: 设备类型名称或ID。例如 "USBCANFD-200U"、"USBCAN-2E-U"、"USBCAN-II"、"41"
        device_index: 设备索引号，连接多个同型号设备时用于区分，默认0
    """
    mgr = get_manager()
    try:
        result = mgr.open_device(device_type, device_index)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except CANError as e:
        return f"错误: {e}"


@mcp.tool()
def close_device(device_type: str, device_index: int = 0) -> str:
    """关闭一个CAN设备，释放资源。会自动停止该设备上所有通道。

    Args:
        device_type: 设备类型名称或ID
        device_index: 设备索引号，默认0
    """
    mgr = get_manager()
    try:
        result = mgr.close_device(device_type, device_index)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except CANError as e:
        return f"错误: {e}"


# ════════════════════════════════════════
#  复合工具
# ════════════════════════════════════════

@mcp.tool()
def auto_setup(
    device_type: str,
    channel: int = 0,
    baudrate: int = 500000,
    dbc_path: str = "",
    device_index: int = 0,
) -> str:
    """一键初始化CAN设备：自动完成 打开设备→初始化通道→加载DBC。
    幂等操作，已完成的步骤自动跳过。推荐作为所有操作的第一步调用。

    Args:
        device_type: 设备类型名称或ID。例如 "USBCAN-2E-U"
        channel: 通道号，默认0
        baudrate: 波特率，默认500000
        dbc_path: DBC文件路径（可选，为空则跳过DBC加载）
        device_index: 设备索引号，默认0
    """
    mgr = get_manager()
    try:
        result = mgr.auto_setup(
            device_type=device_type,
            device_index=device_index,
            channel=channel,
            baudrate=baudrate,
            dbc_path=dbc_path or None,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    except CANError as e:
        return f"错误: {e}"


# ════════════════════════════════════════
#  通道工具
# ════════════════════════════════════════

@mcp.tool()
def init_channel(
    device_type: str,
    channel: int = 0,
    baudrate: int = 500000,
    data_baudrate: int = 2000000,
    device_index: int = 0,
    is_canfd: bool = False,
    mode: int = 0,
    resistance: bool = True,
) -> str:
    """初始化并启动CAN通道。

    系统会根据设备系列自动选择正确的初始化流程：
    - USBCANFD系列：自动使用CANFD模式，需设置仲裁域和数据域波特率
    - USBCAN-xE-U系列：使用CAN模式，仅需仲裁域波特率
    - USBCAN-I/II系列：使用老式timing寄存器初始化

    Args:
        device_type: 设备类型名称或ID
        channel: 通道号，默认0
        baudrate: 仲裁域波特率，默认500000。常用值: 125000/250000/500000/1000000
        data_baudrate: 数据域波特率(仅CANFD)，默认2000000。常用值: 2000000/4000000/5000000
        device_index: 设备索引号，默认0
        is_canfd: 是否使用CANFD模式(仅当设备系列为OTHER时参考此参数)
        mode: 工作模式。0=正常模式，1=只听模式
        resistance: 是否启用终端电阻，默认启用
    """
    mgr = get_manager()
    try:
        result = mgr.init_channel(
            device_type=device_type,
            device_index=device_index,
            channel=channel,
            baudrate=baudrate,
            data_baudrate=data_baudrate,
            is_canfd=is_canfd,
            mode=mode,
            resistance=resistance,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    except CANError as e:
        return f"错误: {e}"


@mcp.tool()
def reset_channel(device_type: str, channel: int = 0, device_index: int = 0) -> str:
    """复位CAN通道，停止收发。

    Args:
        device_type: 设备类型名称或ID
        channel: 通道号，默认0
        device_index: 设备索引号，默认0
    """
    mgr = get_manager()
    try:
        result = mgr.reset_channel(device_type, device_index, channel)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except CANError as e:
        return f"错误: {e}"


# ════════════════════════════════════════
#  发送工具
# ════════════════════════════════════════

@mcp.tool()
def send_can(
    device_type: str,
    can_id: int,
    data: list[int],
    channel: int = 0,
    device_index: int = 0,
    is_extended: bool = False,
    is_remote: bool = False,
    count: int = 1,
) -> str:
    """发送CAN帧。

    Args:
        device_type: 设备类型名称或ID
        can_id: CAN帧ID。标准帧: 0x000~0x7FF，扩展帧: 0x00000000~0x1FFFFFFF
        data: 数据字节列表，最多8字节。例如 [0x01, 0x02, 0x03]
        channel: 通道号，默认0
        device_index: 设备索引号，默认0
        is_extended: 是否为扩展帧(29位ID)，默认标准帧(11位ID)
        is_remote: 是否为远程帧，默认数据帧
        count: 发送次数，默认1
    """
    mgr = get_manager()
    try:
        result = mgr.send_can(
            device_type=device_type,
            device_index=device_index,
            channel=channel,
            can_id=can_id,
            data=data,
            is_extended=is_extended,
            is_remote=is_remote,
            count=count,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    except CANError as e:
        return f"错误: {e}"


@mcp.tool()
def send_canfd(
    device_type: str,
    can_id: int,
    data: list[int],
    channel: int = 0,
    device_index: int = 0,
    is_extended: bool = False,
    brs: bool = True,
    count: int = 1,
) -> str:
    """发送CANFD帧。通道必须以CANFD模式初始化。

    Args:
        device_type: 设备类型名称或ID
        can_id: CAN帧ID
        data: 数据字节列表，最多64字节
        channel: 通道号，默认0
        device_index: 设备索引号，默认0
        is_extended: 是否为扩展帧(29位ID)
        brs: 是否启用波特率切换(BRS加速)，默认启用
        count: 发送次数，默认1
    """
    mgr = get_manager()
    try:
        result = mgr.send_canfd(
            device_type=device_type,
            device_index=device_index,
            channel=channel,
            can_id=can_id,
            data=data,
            is_extended=is_extended,
            brs=brs,
            count=count,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    except CANError as e:
        return f"错误: {e}"


# ════════════════════════════════════════
#  接收工具
# ════════════════════════════════════════

@mcp.tool()
def receive(
    device_type: str,
    channel: int = 0,
    device_index: int = 0,
    max_count: int = 100,
    wait_ms: int = 100,
    filter_ids: list[int] | None = None,
) -> str:
    """接收CAN/CANFD帧。一次性读取接收缓冲区中的数据。

    Args:
        device_type: 设备类型名称或ID
        channel: 通道号，默认0
        device_index: 设备索引号，默认0
        max_count: 最大接收帧数，默认100
        wait_ms: 等待超时(毫秒)，默认100
        filter_ids: CAN ID过滤列表，仅返回匹配的帧。例如 [0x100, 0x200]。为空时返回所有帧。
    """
    mgr = get_manager()
    try:
        result = mgr.receive(
            device_type=device_type,
            device_index=device_index,
            channel=channel,
            max_count=max_count,
            wait_ms=wait_ms,
            filter_ids=filter_ids,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    except CANError as e:
        return f"错误: {e}"


@mcp.tool()
def get_receive_count(
    device_type: str,
    channel: int = 0,
    device_index: int = 0,
) -> str:
    """查看接收缓冲区中有多少帧待读取。

    Args:
        device_type: 设备类型名称或ID
        channel: 通道号，默认0
        device_index: 设备索引号，默认0
    """
    mgr = get_manager()
    try:
        result = mgr.get_receive_count(device_type, device_index, channel)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except CANError as e:
        return f"错误: {e}"


@mcp.tool()
def clear_buffer(
    device_type: str,
    channel: int = 0,
    device_index: int = 0,
) -> str:
    """清空通道接收缓冲区。

    Args:
        device_type: 设备类型名称或ID
        channel: 通道号，默认0
        device_index: 设备索引号，默认0
    """
    mgr = get_manager()
    try:
        result = mgr.clear_buffer(device_type, device_index, channel)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except CANError as e:
        return f"错误: {e}"


# ════════════════════════════════════════
#  DBC 信号工具
# ════════════════════════════════════════

@mcp.tool()
def load_dbc(dbc_path: str) -> str:
    """加载DBC文件，后续 read_signal/search_signal 可用。

    Args:
        dbc_path: DBC文件的完整路径
    """
    mgr = get_manager()
    try:
        result = mgr.load_dbc(dbc_path)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"错误: {e}"


@mcp.tool()
def search_signal(keyword: str) -> str:
    """按关键词搜索DBC中的信号（支持信号名部分匹配和中文注释匹配）。

    Args:
        keyword: 搜索关键词，例如信号名 "BusVolt" 或中文 "母线电压"
    """
    mgr = get_manager()
    try:
        results = mgr.search_signal(keyword)
        if not results:
            return f"未找到匹配 \"{keyword}\" 的信号。"
        return json.dumps(results, ensure_ascii=False, indent=2)
    except CANError as e:
        return f"错误: {e}"


@mcp.tool()
def read_signal(
    signal_name: str,
    device_type: str,
    channel: int = 0,
    device_index: int = 0,
    wait_ms: int = 5000,
) -> str:
    """一次调用读取CAN信号物理值。自动完成：模糊搜索信号→清缓冲→接收→解码整个报文。

    需要先调用 load_dbc 加载DBC文件，且设备通道已初始化。

    Args:
        signal_name: 信号名关键词（模糊匹配），例如 "BusVolt"、"母线电压"
        device_type: 设备类型名称或ID
        channel: 通道号，默认0
        device_index: 设备索引号，默认0
        wait_ms: 等待接收超时(毫秒)，默认5000
    """
    mgr = get_manager()
    try:
        result = mgr.read_signal(
            signal_name=signal_name,
            device_type=device_type,
            device_index=device_index,
            channel=channel,
            wait_ms=wait_ms,
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    except CANError as e:
        return f"错误: {e}"


# ════════════════════════════════════════
#  入口
# ════════════════════════════════════════

def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
