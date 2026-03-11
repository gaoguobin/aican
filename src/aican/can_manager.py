"""CAN Manager - 设备池与通道管理层，封装 zlgcan.py"""

from __future__ import annotations

import os
import sys
import threading
import time
from ctypes import *
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import re

import cantools

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
        "See: https://github.com/gaoguobin/aican#installation"
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


class DeviceSeries(str, Enum):
    """设备系列，决定初始化流程"""
    USBCANFD = "usbcanfd"       # USBCANFD-100U/200U/400U/800U/MINI
    USBCAN_E_U = "usbcan_e_u"  # USBCAN-E-U/2E-U/4E-U/8E-U
    USBCAN_I = "usbcan_i"      # USBCAN-I/II (老设备)
    PCIE_CANFD = "pcie_canfd"   # PCIE-CANFD系列
    OTHER = "other"


# 设备类型号 → 系列映射
_DEVICE_SERIES_MAP: dict[int, DeviceSeries] = {}

def _register_series(series: DeviceSeries, *type_values: int):
    for v in type_values:
        _DEVICE_SERIES_MAP[v] = series

_register_series(DeviceSeries.USBCANFD, 41, 42, 43, 59, 76)  # 200U,100U,MINI,800U,400U
_register_series(DeviceSeries.USBCAN_E_U, 20, 21, 31, 34)     # E-U,2E-U,4E-U,8E-U
_register_series(DeviceSeries.USBCAN_I, 3, 4)                  # USBCAN1, USBCAN2
_register_series(DeviceSeries.PCIE_CANFD, 38, 39, 40, 60, 61, 62, 63)


# CAN/汽车领域中英术语词典（中文关键词 → 英文子串列表）
_CN_EN_TERMS: dict[str, list[str]] = {
    "电压": ["volt"],
    "电流": ["current", "curr"],
    "功率": ["power", "pwr"],
    "母线": ["bus"],
    "输入": ["input", "in"],
    "输出": ["output", "out"],
    "电机": ["motor", "mot"],
    "转速": ["speed", "spd", "rpm"],
    "扭矩": ["torque", "trq"],
    "转矩": ["torque", "trq"],
    "温度": ["temp"],
    "电池": ["batt"],
    "电量": ["soc"],
    "充电": ["charg"],
    "放电": ["discharg"],
    "档位": ["shift", "gear"],
    "助力": ["assist"],
    "模式": ["mode"],
    "状态": ["stat"],
    "故障": ["fault", "err"],
    "报警": ["alarm", "warn"],
    "踏板": ["pedal"],
    "刹车": ["brake"],
    "油门": ["throttle", "accel"],
    "心跳": ["heart"],
    "计数": ["cnt", "count"],
    "版本": ["ver"],
    "反馈": ["fb", "feedback"],
    "命令": ["cmd", "command"],
    "请求": ["req"],
    "响应": ["resp"],
    "使能": ["enable", "en"],
    "禁止": ["disable"],
    "目标": ["target", "tgt"],
    "实际": ["actual", "act"],
    "最大": ["max"],
    "最小": ["min"],
    "限制": ["limit", "lim"],
    "保护": ["protect", "prot"],
    "过压": ["ov"],
    "欠压": ["uv"],
    "过流": ["oc"],
    "过温": ["ot"],
    "方向": ["dir"],
    "角度": ["angle", "ang"],
    "位置": ["pos"],
    "压力": ["press"],
    "车速": ["veh", "speed"],
    "里程": ["odo", "mileage"],
    "时间": ["time"],
    "频率": ["freq"],
    "占空比": ["duty"],
    "信号": ["signal", "sig"],
    "通信": ["comm"],
    "生命": ["life"],
}

# 预编译：中文词按长度降序排列，优先匹配长词
_CN_TERMS_SORTED = sorted(_CN_EN_TERMS.keys(), key=len, reverse=True)
_CN_TERM_PATTERN = re.compile("|".join(re.escape(t) for t in _CN_TERMS_SORTED))


# 常用设备类型名称映射（自然语言 → 设备类型值）
DEVICE_NAME_MAP: dict[str, int] = {
    "USBCAN-I": 3,
    "USBCAN-II": 4,
    "USBCAN1": 3,
    "USBCAN2": 4,
    "USBCAN-E-U": 20,
    "USBCAN-2E-U": 21,
    "USBCAN-4E-U": 31,
    "USBCAN-8E-U": 34,
    "USBCANFD-100U": 42,
    "USBCANFD-200U": 41,
    "USBCANFD-400U": 76,
    "USBCANFD-800U": 59,
    "USBCANFD-MINI": 43,
    "PCIE-CANFD-100U": 38,
    "PCIE-CANFD-200U": 39,
    "PCIE-CANFD-400U": 40,
    "VIRTUAL": 99,
}


@dataclass
class ChannelState:
    """通道状态"""
    channel_index: int
    channel_handle: int
    is_canfd: bool
    baudrate: int
    data_baudrate: int | None = None  # CANFD 数据域波特率
    started: bool = False


@dataclass
class DeviceState:
    """设备状态"""
    device_type: int
    device_type_name: str
    device_index: int
    device_handle: int
    series: DeviceSeries
    channels: dict[int, ChannelState] = field(default_factory=dict)
    info: Any = None


class CANError(Exception):
    """CAN 操作错误"""
    def __init__(self, operation: str, detail: str):
        self.operation = operation
        self.detail = detail
        super().__init__(f"[{operation}] {detail}")


class CANManager:
    """CAN 设备管理器 — 设备池 + 通道管理"""

    def __init__(self):
        # zlgcan.py 用 "./zlgcan.dll" 加载，需要 CWD 指向 zlgcan 目录
        prev_cwd = os.getcwd()
        os.chdir(str(_zlgcan_dir))
        try:
            self._zcan = zlgcan.ZCAN()
        finally:
            os.chdir(prev_cwd)
        self._devices: dict[str, DeviceState] = {}  # key: "type_index" e.g. "41_0"
        self._lock = threading.Lock()
        self._receive_threads: dict[str, threading.Thread] = {}
        self._receive_flags: dict[str, bool] = {}
        self._dbc: cantools.Database | None = None
        self._dbc_path: str | None = None

    @staticmethod
    def _device_key(device_type: int, device_index: int) -> str:
        return f"{device_type}_{device_index}"

    @staticmethod
    def resolve_device_type(name_or_id: str) -> int:
        """解析设备类型：支持名称或数字"""
        upper = name_or_id.upper().strip()
        if upper in DEVICE_NAME_MAP:
            return DEVICE_NAME_MAP[upper]
        # 尝试直接解析为数字
        try:
            return int(name_or_id)
        except ValueError:
            # 模糊匹配
            for k, v in DEVICE_NAME_MAP.items():
                if upper in k or k in upper:
                    return v
            raise CANError("resolve_device_type", f"未知设备类型: {name_or_id}")

    @staticmethod
    def get_series(device_type: int) -> DeviceSeries:
        return _DEVICE_SERIES_MAP.get(device_type, DeviceSeries.OTHER)

    def list_devices(self) -> list[dict]:
        """列出已打开的设备"""
        result = []
        for key, dev in self._devices.items():
            channels = []
            for idx, ch in dev.channels.items():
                channels.append({
                    "index": idx,
                    "is_canfd": ch.is_canfd,
                    "baudrate": ch.baudrate,
                    "data_baudrate": ch.data_baudrate,
                    "started": ch.started,
                })
            result.append({
                "device_type": dev.device_type_name,
                "device_type_id": dev.device_type,
                "device_index": dev.device_index,
                "series": dev.series.value,
                "channels": channels,
            })
        return result

    # ── 设备操作 ──

    def open_device(self, device_type: int | str, device_index: int = 0) -> dict:
        """打开设备"""
        if isinstance(device_type, str):
            device_type = self.resolve_device_type(device_type)

        key = self._device_key(device_type, device_index)
        if key in self._devices:
            return {"status": "already_open", "device_key": key}

        handle = self._zcan.OpenDevice(device_type, device_index, 0)
        if handle == zlgcan.INVALID_DEVICE_HANDLE:
            raise CANError("open_device", f"打开设备失败: type={device_type}, index={device_index}")

        series = self.get_series(device_type)
        # 反查名称
        type_name = str(device_type)
        for name, val in DEVICE_NAME_MAP.items():
            if val == device_type:
                type_name = name
                break

        info = self._zcan.GetDeviceInf(handle)
        dev = DeviceState(
            device_type=device_type,
            device_type_name=type_name,
            device_index=device_index,
            device_handle=handle,
            series=series,
            info=info,
        )
        self._devices[key] = dev

        info_dict = {}
        if info:
            info_dict = {
                "hw_version": info.hw_version,
                "fw_version": info.fw_version,
                "serial": info.serial,
                "can_num": info.can_num,
                "hw_type": info.hw_type,
            }

        return {"status": "ok", "device_key": key, "series": series.value, "info": info_dict}

    def close_device(self, device_type: int | str, device_index: int = 0) -> dict:
        """关闭设备"""
        if isinstance(device_type, str):
            device_type = self.resolve_device_type(device_type)

        key = self._device_key(device_type, device_index)
        dev = self._devices.get(key)
        if not dev:
            return {"status": "not_open"}

        # 先停止所有通道的接收线程
        for ch_idx in list(dev.channels.keys()):
            self._stop_receive_thread(key, ch_idx)

        # 关闭所有通道
        for ch in dev.channels.values():
            if ch.started:
                self._zcan.ResetCAN(ch.channel_handle)

        self._zcan.CloseDevice(dev.device_handle)
        del self._devices[key]
        return {"status": "ok"}

    def _get_device(self, device_type: int | str, device_index: int = 0) -> DeviceState:
        if isinstance(device_type, str):
            device_type = self.resolve_device_type(device_type)
        key = self._device_key(device_type, device_index)
        dev = self._devices.get(key)
        if not dev:
            raise CANError("get_device", f"设备未打开: {key}")
        return dev

    # ── 通道操作 ──

    def init_channel(
        self,
        device_type: int | str,
        device_index: int = 0,
        channel: int = 0,
        baudrate: int = 500000,
        data_baudrate: int | None = None,
        is_canfd: bool = False,
        mode: int = 0,  # 0=正常, 1=只听
        resistance: bool = True,
    ) -> dict:
        """初始化并启动 CAN 通道"""
        dev = self._get_device(device_type, device_index)
        dh = dev.device_handle

        if channel in dev.channels:
            # 已初始化，先重置
            self._zcan.ResetCAN(dev.channels[channel].channel_handle)
            del dev.channels[channel]

        # 根据设备系列选择初始化流程
        if dev.series == DeviceSeries.USBCANFD:
            chn_handle = self._init_usbcanfd(dev, channel, baudrate, data_baudrate, mode, resistance)
            actual_canfd = True
        elif dev.series == DeviceSeries.USBCAN_E_U:
            chn_handle = self._init_usbcan_e_u(dev, channel, baudrate, mode, resistance)
            actual_canfd = False
        elif dev.series == DeviceSeries.USBCAN_I:
            chn_handle = self._init_usbcan_i(dev, channel, baudrate, mode)
            actual_canfd = False
        else:
            # 通用流程：尝试 CANFD 方式
            if is_canfd:
                chn_handle = self._init_usbcanfd(dev, channel, baudrate, data_baudrate, mode, resistance)
                actual_canfd = True
            else:
                chn_handle = self._init_usbcan_e_u(dev, channel, baudrate, mode, resistance)
                actual_canfd = False

        # 启动通道
        ret = self._zcan.StartCAN(chn_handle)
        if ret != zlgcan.ZCAN_STATUS_OK:
            raise CANError("start_channel", f"启动通道 {channel} 失败")

        ch_state = ChannelState(
            channel_index=channel,
            channel_handle=chn_handle,
            is_canfd=actual_canfd,
            baudrate=baudrate,
            data_baudrate=data_baudrate if actual_canfd else None,
            started=True,
        )
        dev.channels[channel] = ch_state

        return {
            "status": "ok",
            "channel": channel,
            "is_canfd": actual_canfd,
            "baudrate": baudrate,
            "data_baudrate": data_baudrate,
        }

    def _init_usbcanfd(self, dev: DeviceState, chn: int, baudrate: int,
                       data_baudrate: int | None, mode: int, resistance: bool) -> int:
        """USBCANFD 系列初始化"""
        dh = dev.device_handle
        data_baudrate = data_baudrate or 2000000

        # 仲裁域波特率
        ret = self._zcan.ZCAN_SetValue(dh, f"{chn}/canfd_abit_baud_rate", str(baudrate).encode("utf-8"))
        if ret != zlgcan.ZCAN_STATUS_OK:
            raise CANError("init_usbcanfd", f"设置仲裁域波特率失败: {baudrate}")

        # 数据域波特率
        ret = self._zcan.ZCAN_SetValue(dh, f"{chn}/canfd_dbit_baud_rate", str(data_baudrate).encode("utf-8"))
        if ret != zlgcan.ZCAN_STATUS_OK:
            raise CANError("init_usbcanfd", f"设置数据域波特率失败: {data_baudrate}")

        # 终端电阻
        ret = self._zcan.ZCAN_SetValue(dh, f"{chn}/initenal_resistance", ("1" if resistance else "0").encode("utf-8"))
        if ret != zlgcan.ZCAN_STATUS_OK:
            raise CANError("init_usbcanfd", "设置终端电阻失败")

        # 初始化通道
        cfg = zlgcan.ZCAN_CHANNEL_INIT_CONFIG()
        cfg.can_type = zlgcan.ZCAN_TYPE_CANFD
        cfg.config.canfd.mode = mode
        chn_handle = self._zcan.InitCAN(dh, chn, cfg)
        if chn_handle is None or chn_handle == zlgcan.INVALID_CHANNEL_HANDLE:
            raise CANError("init_usbcanfd", f"InitCAN 通道 {chn} 失败")

        return chn_handle

    def _init_usbcan_e_u(self, dev: DeviceState, chn: int, baudrate: int,
                         mode: int, resistance: bool) -> int:
        """USBCAN-xE-U 系列初始化"""
        dh = dev.device_handle

        ret = self._zcan.ZCAN_SetValue(dh, f"{chn}/baud_rate", str(baudrate).encode("utf-8"))
        if ret != zlgcan.ZCAN_STATUS_OK:
            raise CANError("init_usbcan_e_u", f"设置波特率失败: {baudrate}")

        # USBCAN-xE-U 终端电阻为硬件拨码开关，软件设置可能不支持，失败时忽略
        self._zcan.ZCAN_SetValue(dh, f"{chn}/initenal_resistance", ("1" if resistance else "0").encode("utf-8"))

        cfg = zlgcan.ZCAN_CHANNEL_INIT_CONFIG()
        cfg.can_type = zlgcan.ZCAN_TYPE_CAN
        cfg.config.can.mode = mode
        chn_handle = self._zcan.InitCAN(dh, chn, cfg)
        if chn_handle is None or chn_handle == zlgcan.INVALID_CHANNEL_HANDLE:
            raise CANError("init_usbcan_e_u", f"InitCAN 通道 {chn} 失败")

        return chn_handle

    def _init_usbcan_i(self, dev: DeviceState, chn: int, baudrate: int, mode: int) -> int:
        """USBCAN-I/II 系列初始化（老设备）"""
        dh = dev.device_handle

        # timing 值查表（常用波特率）
        timing_map = {
            1000000: (0x00, 0x14),
            800000:  (0x00, 0x16),
            500000:  (0x00, 0x1C),
            250000:  (0x01, 0x1C),
            125000:  (0x03, 0x1C),
            100000:  (0x04, 0x1C),
            50000:   (0x09, 0x1C),
            20000:   (0x18, 0x1C),
            10000:   (0x31, 0x1C),
            5000:    (0xBF, 0xFF),
        }
        if baudrate not in timing_map:
            raise CANError("init_usbcan_i", f"USBCAN-I/II 不支持波特率 {baudrate}，支持: {list(timing_map.keys())}")

        t0, t1 = timing_map[baudrate]
        cfg = zlgcan.ZCAN_CHANNEL_INIT_CONFIG()
        cfg.can_type = zlgcan.ZCAN_TYPE_CAN
        cfg.config.can.timing0 = t0
        cfg.config.can.timing1 = t1
        cfg.config.can.acc_code = 0
        cfg.config.can.acc_mask = 0xFFFFFFFF
        cfg.config.can.filter = 0
        cfg.config.can.mode = mode

        chn_handle = self._zcan.InitCAN(dh, chn, cfg)
        if chn_handle is None or chn_handle == zlgcan.INVALID_CHANNEL_HANDLE:
            raise CANError("init_usbcan_i", f"InitCAN 通道 {chn} 失败")

        return chn_handle

    def reset_channel(self, device_type: int | str, device_index: int = 0, channel: int = 0) -> dict:
        """复位通道"""
        dev = self._get_device(device_type, device_index)
        ch = dev.channels.get(channel)
        if not ch:
            raise CANError("reset_channel", f"通道 {channel} 未初始化")

        self._stop_receive_thread(self._device_key(dev.device_type, dev.device_index), channel)
        self._zcan.ResetCAN(ch.channel_handle)
        ch.started = False
        return {"status": "ok", "channel": channel}

    # ── 发送 ──

    def send_can(
        self,
        device_type: int | str,
        device_index: int = 0,
        channel: int = 0,
        can_id: int = 0,
        data: list[int] | bytes | None = None,
        is_extended: bool = False,
        is_remote: bool = False,
        count: int = 1,
    ) -> dict:
        """发送 CAN 帧"""
        dev = self._get_device(device_type, device_index)
        ch = dev.channels.get(channel)
        if not ch or not ch.started:
            raise CANError("send_can", f"通道 {channel} 未启动")

        data = data or []
        if isinstance(data, bytes):
            data = list(data)

        msgs = (zlgcan.ZCAN_Transmit_Data * count)()
        for i in range(count):
            frame_id = can_id & 0x1FFFFFFF
            if is_extended:
                frame_id |= (1 << 31)
            if is_remote:
                frame_id |= (1 << 30)

            msgs[i].frame.can_id = frame_id
            msgs[i].frame.can_dlc = min(len(data), 8)
            msgs[i].transmit_type = 0
            for j in range(msgs[i].frame.can_dlc):
                msgs[i].frame.data[j] = data[j]

        sent = self._zcan.Transmit(ch.channel_handle, msgs, count)
        return {"status": "ok", "sent": sent, "requested": count}

    def send_canfd(
        self,
        device_type: int | str,
        device_index: int = 0,
        channel: int = 0,
        can_id: int = 0,
        data: list[int] | bytes | None = None,
        is_extended: bool = False,
        brs: bool = True,
        count: int = 1,
    ) -> dict:
        """发送 CANFD 帧"""
        dev = self._get_device(device_type, device_index)
        ch = dev.channels.get(channel)
        if not ch or not ch.started:
            raise CANError("send_canfd", f"通道 {channel} 未启动")
        if not ch.is_canfd:
            raise CANError("send_canfd", f"通道 {channel} 不是 CANFD 模式")

        data = data or []
        if isinstance(data, bytes):
            data = list(data)

        msgs = (zlgcan.ZCAN_TransmitFD_Data * count)()
        for i in range(count):
            frame_id = can_id & 0x1FFFFFFF
            if is_extended:
                frame_id |= (1 << 31)

            msgs[i].frame.can_id = frame_id
            msgs[i].frame.len = min(len(data), 64)
            msgs[i].frame.flags = 0x01 if brs else 0x00  # BRS 加速
            msgs[i].transmit_type = 0
            for j in range(msgs[i].frame.len):
                msgs[i].frame.data[j] = data[j]

        sent = self._zcan.TransmitFD(ch.channel_handle, msgs, count)
        return {"status": "ok", "sent": sent, "requested": count}

    # ── 接收 ──

    def receive(
        self,
        device_type: int | str,
        device_index: int = 0,
        channel: int = 0,
        max_count: int = 100,
        wait_ms: int = 100,
        filter_ids: list[int] | None = None,
    ) -> dict:
        """一次性接收 CAN/CANFD 帧

        Args:
            filter_ids: CAN ID过滤列表，仅返回匹配的帧。为None时返回所有帧。
        """
        dev = self._get_device(device_type, device_index)
        ch = dev.channels.get(channel)
        if not ch or not ch.started:
            raise CANError("receive", f"通道 {channel} 未启动")

        filter_set = set(filter_ids) if filter_ids else None
        result = {"can_frames": [], "canfd_frames": []}

        # CAN 帧
        can_count = self._zcan.GetReceiveNum(ch.channel_handle, zlgcan.ZCAN_TYPE_CAN)
        if can_count > 0:
            fetch = can_count if filter_set else min(can_count, max_count)
            msgs, ret = self._zcan.Receive(ch.channel_handle, fetch, wait_ms)
            for i in range(ret):
                if len(result["can_frames"]) >= max_count:
                    break
                msg = msgs[i]
                frame = msg.frame
                fid = frame.can_id & 0x1FFFFFFF
                if filter_set and fid not in filter_set:
                    continue
                result["can_frames"].append({
                    "id": hex(fid),
                    "id_int": fid,
                    "dlc": frame.can_dlc,
                    "data": [f"{b:02X}" for b in frame.data[:frame.can_dlc]],
                    "data_hex": " ".join(f"{b:02X}" for b in frame.data[:frame.can_dlc]),
                    "is_extended": bool(frame.can_id & (1 << 31)),
                    "is_remote": bool(frame.can_id & (1 << 30)),
                    "timestamp": msg.timestamp,
                    "direction": "TX" if frame._pad & 0x20 else "RX",
                })

        # CANFD 帧
        if ch.is_canfd:
            canfd_count = self._zcan.GetReceiveNum(ch.channel_handle, zlgcan.ZCAN_TYPE_CANFD)
            if canfd_count > 0:
                fetch = canfd_count if filter_set else min(canfd_count, max_count)
                msgs, ret = self._zcan.ReceiveFD(ch.channel_handle, fetch, wait_ms)
                for i in range(ret):
                    if len(result["canfd_frames"]) >= max_count:
                        break
                    msg = msgs[i]
                    frame = msg.frame
                    fid = frame.can_id & 0x1FFFFFFF
                    if filter_set and fid not in filter_set:
                        continue
                    result["canfd_frames"].append({
                        "id": hex(fid),
                        "id_int": fid,
                        "len": frame.len,
                        "data": [f"{b:02X}" for b in frame.data[:frame.len]],
                        "data_hex": " ".join(f"{b:02X}" for b in frame.data[:frame.len]),
                        "is_extended": bool(frame.can_id & (1 << 31)),
                        "brs": bool(frame.flags & 0x01),
                        "timestamp": msg.timestamp,
                        "direction": "TX" if frame.flags & 0x20 else "RX",
                    })

        result["total"] = len(result["can_frames"]) + len(result["canfd_frames"])
        return result

    def get_receive_count(
        self,
        device_type: int | str,
        device_index: int = 0,
        channel: int = 0,
    ) -> dict:
        """获取接收缓冲区帧数"""
        dev = self._get_device(device_type, device_index)
        ch = dev.channels.get(channel)
        if not ch or not ch.started:
            raise CANError("get_receive_count", f"通道 {channel} 未启动")

        can_num = self._zcan.GetReceiveNum(ch.channel_handle, zlgcan.ZCAN_TYPE_CAN)
        canfd_num = 0
        if ch.is_canfd:
            canfd_num = self._zcan.GetReceiveNum(ch.channel_handle, zlgcan.ZCAN_TYPE_CANFD)

        return {"can": can_num, "canfd": canfd_num, "total": can_num + canfd_num}

    def clear_buffer(
        self,
        device_type: int | str,
        device_index: int = 0,
        channel: int = 0,
    ) -> dict:
        """清空接收缓冲区"""
        dev = self._get_device(device_type, device_index)
        ch = dev.channels.get(channel)
        if not ch:
            raise CANError("clear_buffer", f"通道 {channel} 未初始化")

        self._zcan.ClearBuffer(ch.channel_handle)
        return {"status": "ok"}

    # ── 接收线程管理 ──

    def _stop_receive_thread(self, device_key: str, channel: int):
        thread_key = f"{device_key}_{channel}"
        if thread_key in self._receive_flags:
            self._receive_flags[thread_key] = False
        if thread_key in self._receive_threads:
            self._receive_threads[thread_key].join(timeout=2)
            del self._receive_threads[thread_key]

    # ── 清理 ──

    def close_all(self):
        """关闭所有设备"""
        for key in list(self._devices.keys()):
            dev = self._devices[key]
            self.close_device(dev.device_type, dev.device_index)

    def get_supported_devices(self) -> list[dict]:
        """返回支持的设备列表"""
        return [{"name": k, "type_id": v, "series": self.get_series(v).value}
                for k, v in DEVICE_NAME_MAP.items()]

    # ── 复合操作 ──

    def auto_setup(
        self,
        device_type: int | str,
        device_index: int = 0,
        channel: int = 0,
        baudrate: int = 500000,
        dbc_path: str | None = None,
    ) -> dict:
        """一键初始化：打开设备→初始化通道→加载DBC（幂等，已完成的步骤自动跳过）"""
        steps = {}

        # 1. 打开设备
        if isinstance(device_type, str):
            type_id = self.resolve_device_type(device_type)
        else:
            type_id = device_type
        key = self._device_key(type_id, device_index)
        if key in self._devices:
            steps["open_device"] = "skipped"
        else:
            self.open_device(device_type, device_index)
            steps["open_device"] = "done"

        # 2. 初始化通道
        dev = self._devices[key]
        if channel in dev.channels and dev.channels[channel].started:
            steps["init_channel"] = "skipped"
        else:
            self.init_channel(device_type, device_index, channel, baudrate)
            steps["init_channel"] = "done"

        # 3. 加载DBC
        if dbc_path:
            if self._dbc is not None and self._dbc_path == dbc_path:
                steps["load_dbc"] = "skipped"
            else:
                self.load_dbc(dbc_path)
                steps["load_dbc"] = "done"
        else:
            steps["load_dbc"] = "no_path"

        return {"status": "ok", "steps": steps}

    # ── DBC 信号操作 ──

    def load_dbc(self, dbc_path: str) -> dict:
        """加载DBC文件"""
        self._dbc = cantools.database.load_file(dbc_path, strict=False, encoding='gbk')
        self._dbc_path = dbc_path
        return {
            "status": "ok",
            "messages": len(self._dbc.messages),
            "path": dbc_path,
        }

    def _ensure_dbc(self):
        if self._dbc is None:
            raise CANError("dbc", "DBC未加载，请先调用 load_dbc")

    def search_signal(self, keyword: str) -> list[dict]:
        """按关键词模糊搜索DBC中的信号（信号名 + 中文注释 + 中英术语翻译）"""
        self._ensure_dbc()
        keyword_lower = keyword.lower()
        results = []
        for msg in self._dbc.messages:
            can_id = msg.frame_id
            is_extended = msg.is_extended_frame
            for sig in msg.signals:
                name_match = keyword_lower in sig.name.lower()
                comment_match = sig.comment and keyword_lower in sig.comment.lower()
                if name_match or comment_match:
                    results.append({
                        "signal_name": sig.name,
                        "message_name": msg.name,
                        "can_id": hex(can_id),
                        "is_extended": is_extended,
                        "comment": sig.comment,
                        "unit": sig.unit,
                    })

        # 中文关键词翻译回退：原始搜索无结果时，尝试中英术语翻译
        if not results:
            cn_matches = _CN_TERM_PATTERN.findall(keyword)
            if cn_matches:
                # 每个中文词 → 对应的英文候选列表
                en_groups = [_CN_EN_TERMS[cn] for cn in cn_matches]
                for msg in self._dbc.messages:
                    can_id = msg.frame_id
                    is_extended = msg.is_extended_frame
                    for sig in msg.signals:
                        sig_lower = sig.name.lower()
                        # 每组英文候选至少命中一个
                        if all(
                            any(en in sig_lower for en in group)
                            for group in en_groups
                        ):
                            results.append({
                                "signal_name": sig.name,
                                "message_name": msg.name,
                                "can_id": hex(can_id),
                                "is_extended": is_extended,
                                "comment": sig.comment,
                                "unit": sig.unit,
                            })

        return results

    def read_signal(
        self,
        signal_name: str,
        device_type: int | str,
        device_index: int = 0,
        channel: int = 0,
        wait_ms: int = 5000,
    ) -> dict:
        """读取CAN信号物理值：模糊搜索信号→接收→解码整个报文"""
        self._ensure_dbc()

        # 模糊搜索信号
        matches = self.search_signal(signal_name)
        if not matches:
            raise CANError("read_signal", f"未找到匹配信号: {signal_name}")

        # 取第一个匹配
        match = matches[0]
        msg = self._dbc.get_message_by_name(match["message_name"])
        can_id = msg.frame_id
        is_extended = msg.is_extended_frame

        # 清缓冲→等待→接收
        self.clear_buffer(device_type, device_index, channel)
        time.sleep(wait_ms / 1000.0)
        recv = self.receive(
            device_type=device_type,
            device_index=device_index,
            channel=channel,
            max_count=50,
            wait_ms=wait_ms,
            filter_ids=[can_id],
        )

        # 从接收结果中找到目标帧
        frames = recv.get("can_frames", []) + recv.get("canfd_frames", [])
        if not frames:
            raise CANError("read_signal", f"未接收到 CAN ID {hex(can_id)} 的帧（等待 {wait_ms}ms）")

        # 取最新一帧
        frame = frames[-1]
        raw_bytes = bytes(int(b, 16) for b in frame["data"])

        # 解码整个报文
        decoded = msg.decode(raw_bytes)

        # 构建返回结果
        signals = {}
        for sig in msg.signals:
            if sig.name in decoded:
                val = decoded[sig.name]
                # NamedSignalValue (枚举) 转为字符串，其余保留原值
                if hasattr(val, 'name'):
                    val = str(val)
                signals[sig.name] = {
                    "value": val,
                    "unit": sig.unit or "",
                }

        return {
            "message_name": msg.name,
            "can_id": hex(can_id),
            "is_extended": is_extended,
            "signals": signals,
        }


# 全局单例
_manager: CANManager | None = None

def get_manager() -> CANManager:
    global _manager
    if _manager is None:
        _manager = CANManager()
    return _manager
