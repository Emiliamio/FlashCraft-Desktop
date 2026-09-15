# -*- coding: utf-8 -*-
"""
core/license_guard.py - 商业级设备指纹与单机授权试用熔断锁
作者: Emiliamio <mio2110767128@163.com>

核心功能：
1. 提取 Windows 物理硬件与网卡指纹，生成独一无二的设备机器码 (如: FC-A89F-4C10)；
2. 试用期频次熔断锁：试用模式下限制单机最多运行 20 次，彻底防范客户编写脚本循环调用白嫖全量数据；
3. 支持离线卡密激活校验：可基于机器码生成正式商用授权码。
"""

import os
import sys
import uuid
import hashlib
import platform
from pathlib import Path

SALT = "Emiliamio_FlashCraft_Sovereignty_2026"
MAX_TRIAL_RUNS = 20
CACHE_FILE = Path.home() / ".flashcraft_license.dat"

def get_machine_fingerprint() -> str:
    """获取唯一的单机硬件指纹编码"""
    try:
        node = str(uuid.getnode())
        system_info = f"{platform.node()}-{platform.machine()}-{node}"
        h = hashlib.sha256(system_info.encode("utf-8")).hexdigest()
        part1 = h[0:4].upper()
        part2 = h[4:8].upper()
        return f"FC-{part1}-{part2}"
    except Exception:
        return "FC-8888-9999"

def generate_valid_key_for_machine(machine_code: str) -> str:
    """根据机器码生成合法的正式商用卡密"""
    raw = f"{machine_code}:{SALT}"
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"KEY-{h[0:4].upper()}-{h[4:8].upper()}-{h[8:12].upper()}"

def is_officially_activated() -> bool:
    """检测当前机器是否已输入有效授权卡密"""
    if not CACHE_FILE.exists():
        return False
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            # 格式：KEY|COUNT
            parts = content.split("|")
            key = parts[0]
            curr_mach = get_machine_fingerprint()
            expected_key = generate_valid_key_for_machine(curr_mach)
            return key == expected_key
    except Exception:
        return False

def get_trial_status() -> tuple[bool, int, int]:
    """
    检查试用期状态。
    返回: (是否允许继续运行, 当前已运行次数, 最大允许次数)
    """
    if is_officially_activated():
        return (True, 0, 999999)

    count = 0
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                parts = content.split("|")
                if len(parts) >= 2:
                    count = int(parts[1])
                elif content.isdigit():
                    count = int(content)
        except Exception:
            count = 0

    allowed = count < MAX_TRIAL_RUNS
    return (allowed, count, MAX_TRIAL_RUNS)

def record_trial_usage():
    """记录并累加一次试用执行"""
    if is_officially_activated():
        return

    allowed, count, max_runs = get_trial_status()
    new_count = count + 1
    
    # 保存计数
    try:
        key_part = "TRIAL"
        if CACHE_FILE.exists():
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if "|" in content:
                    key_part = content.split("|")[0]
                    
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            f.write(f"{key_part}|{new_count}")
    except Exception:
        pass