"""USBCAN-2E-U 实机测试脚本

测试流程:
1. 打开设备
2. 初始化通道0 (500Kbps)
3. 发送一帧 CAN 数据
4. 读取接收缓冲区
5. 关闭设备

使用前请确认:
- USBCAN-2E-U 已通过 USB 连接
- 已安装驱动
"""

from aican.can_manager import get_manager, CANError


def test_open_close():
    """测试1: 打开/关闭设备"""
    mgr = get_manager()
    print("=" * 50)
    print("测试1: 打开设备 USBCAN-2E-U")
    print("=" * 50)
    try:
        result = mgr.open_device("USBCAN-2E-U", 0)
        print(f"  结果: {result}")
        if result["status"] == "ok":
            print(f"  序列号: {result['info'].get('serial', 'N/A')}")
            print(f"  通道数: {result['info'].get('can_num', 'N/A')}")
    except CANError as e:
        print(f"  失败: {e}")
        print("  请检查: 设备是否已连接? 驱动是否已安装?")
        return False
    return True


def test_init_channel():
    """测试2: 初始化通道"""
    mgr = get_manager()
    print("\n" + "=" * 50)
    print("测试2: 初始化通道0 (500Kbps)")
    print("=" * 50)
    try:
        result = mgr.init_channel(
            device_type="USBCAN-2E-U",
            device_index=0,
            channel=0,
            baudrate=500000,
            resistance=True,
        )
        print(f"  结果: {result}")
    except CANError as e:
        print(f"  失败: {e}")
        return False
    return True


def test_send():
    """测试3: 发送 CAN 帧"""
    mgr = get_manager()
    print("\n" + "=" * 50)
    print("测试3: 发送 CAN 帧 (ID=0x100, data=01 02 03 04 05 06 07 08)")
    print("=" * 50)
    try:
        result = mgr.send_can(
            device_type="USBCAN-2E-U",
            channel=0,
            can_id=0x100,
            data=[0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08],
        )
        print(f"  结果: {result}")
    except CANError as e:
        print(f"  失败: {e}")
        return False
    return True


def test_receive():
    """测试4: 查看接收缓冲区"""
    mgr = get_manager()
    print("\n" + "=" * 50)
    print("测试4: 查看接收缓冲区")
    print("=" * 50)
    try:
        count = mgr.get_receive_count("USBCAN-2E-U", channel=0)
        print(f"  缓冲区帧数: {count}")

        if count["total"] > 0:
            result = mgr.receive("USBCAN-2E-U", channel=0, max_count=10)
            print(f"  接收到 {result['total']} 帧:")
            for f in result["can_frames"]:
                print(f"    ID={f['id']} DLC={f['dlc']} DATA={f['data_hex']} {f['direction']}")
        else:
            print("  缓冲区为空 (如果CAN总线上没有其他节点，这是正常的)")
    except CANError as e:
        print(f"  失败: {e}")
        return False
    return True


def test_close():
    """测试5: 关闭设备"""
    mgr = get_manager()
    print("\n" + "=" * 50)
    print("测试5: 关闭设备")
    print("=" * 50)
    try:
        result = mgr.close_device("USBCAN-2E-U")
        print(f"  结果: {result}")
    except CANError as e:
        print(f"  失败: {e}")
        return False
    return True


def test_device_list():
    """测试0: 设备名解析"""
    mgr = get_manager()
    print("=" * 50)
    print("测试0: 设备名解析")
    print("=" * 50)
    device_type = mgr.resolve_device_type("USBCAN-2E-U")
    print(f"  USBCAN-2E-U → type_id={device_type}")
    series = mgr.get_series(device_type)
    print(f"  设备系列: {series.value}")
    print()


if __name__ == "__main__":
    print("AICAN - USBCAN-2E-U 实机测试")
    print("请确认设备已通过USB连接并安装驱动\n")

    test_device_list()

    if not test_open_close():
        print("\n设备打开失败，终止测试。")
        exit(1)

    if test_init_channel():
        test_send()
        test_receive()

    test_close()

    print("\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)
