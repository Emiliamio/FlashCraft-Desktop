# -*- coding: utf-8 -*-
"""
core/license_guard.py - 商业级设备指纹与单机授权试用熔断锁 (增强版)
作者: Emiliamio <mio2110767128@163.com>

核心功能：
1. 提取 Windows 物理硬件与网卡指纹，生成独一无二的设备机器码 (如: FC-A89F-4C10)；
2. 试用期频次熔断锁：试用模式下限制单机最多运行 20 次，彻底防范客户编写脚本循环调用白嫖全量数据；
3. 支持离线卡密激活校验：可基于机器码生成并校验正式商用授权码，支持多级持久化存储。
"""

import os
import sys
import uuid
import hashlib
import platform
from pathlib import Path
from typing import Tuple

SALT = "Emiliamio_FlashCraft_Sovereignty_2026"
MAX_TRIAL_RUNS = 20

# 主缓存文件与备份缓存文件（防篡改与防单点误删）
CACHE_FILE = Path.home() / ".flashcraft_license.dat"
BACKUP_CACHE_FILE = Path(os.environ.get("APPDATA", str(Path.home()))) / "FlashCraft" / "license.dat"

def _ensure_backup_dir():
    try:
        BACKUP_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

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

def _read_persisted_key() -> str:
    """读取已激活的卡密"""
    for p in (CACHE_FILE, BACKUP_CACHE_FILE):
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    parts = content.split("|")
                    if parts and parts[0].startswith("KEY-"):
                        return parts[0]
            except Exception:
                pass
    return ""

def is_officially_activated() -> bool:
    """检测当前机器是否已激活为正式商业授权版"""
    persisted_key = _read_persisted_key()
    if not persisted_key:
        return False
    curr_mach = get_machine_fingerprint()
    expected_key = generate_valid_key_for_machine(curr_mach)
    return persisted_key == expected_key

def verify_and_activate(license_key: str) -> Tuple[bool, str]:
    """
    验证并激活卡密。
    返回: (是否激活成功, 提示消息)
    """
    cleaned_key = license_key.strip().upper()
    curr_mach = get_machine_fingerprint()
    expected_key = generate_valid_key_for_machine(curr_mach)

    if cleaned_key != expected_key:
        return (False, f"授权卡密不匹配！\n当前本机设备码为: {curr_mach}\n请核对是否由工程师 Emiliamio 针对该机器码签发。")

    # 持久化写入授权文件
    _ensure_backup_dir()
    for p in (CACHE_FILE, BACKUP_CACHE_FILE):
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write(f"{cleaned_key}|999999")
        except Exception:
            pass

    return (True, "恭喜您！商业正式版已成功永久激活！\n所有功能已解除限制，感谢支持正版原创。")

def get_trial_status() -> Tuple[bool, int, int]:
    """
    检查试用期状态。
    返回: (是否允许继续运行, 当前已运行次数, 最大允许次数)
    """
    if is_officially_activated():
        return (True, 0, 999999)

    count = 0
    for p in (CACHE_FILE, BACKUP_CACHE_FILE):
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    parts = content.split("|")
                    if len(parts) >= 2 and parts[1].isdigit():
                        count = max(count, int(parts[1]))
                    elif content.isdigit():
                        count = max(count, int(content))
            except Exception:
                pass

    allowed = count < MAX_TRIAL_RUNS
    return (allowed, count, MAX_TRIAL_RUNS)

def record_trial_usage():
    """记录并累加一次试用执行"""
    if is_officially_activated():
        return

    allowed, count, max_runs = get_trial_status()
    new_count = count + 1
    
    _ensure_backup_dir()
    key_part = "TRIAL"
    for p in (CACHE_FILE, BACKUP_CACHE_FILE):
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write(f"{key_part}|{new_count}")
        except Exception:
            pass