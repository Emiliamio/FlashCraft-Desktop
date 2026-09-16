# -*- coding: utf-8 -*-
"""
tests/test_license_guard.py - 单机设备指纹与授权防刷熔断器单元测试
作者: Emiliamio <mio2110767128@163.com>
"""

import os
import pytest
from pathlib import Path
from core.license_guard import (
    get_machine_fingerprint,
    generate_valid_key_for_machine,
    get_trial_status,
    record_trial_usage,
    verify_and_activate,
    is_officially_activated,
    CACHE_FILE,
    BACKUP_CACHE_FILE
)

@pytest.fixture(autouse=True)
def clean_license_environment():
    """在每个测试前后清理授权缓存文件，保证无状态纯净测试"""
    for p in (CACHE_FILE, BACKUP_CACHE_FILE):
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass
    yield
    for p in (CACHE_FILE, BACKUP_CACHE_FILE):
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass

def test_machine_fingerprint():
    code = get_machine_fingerprint()
    assert code.startswith("FC-")
    assert len(code) == 12

def test_key_generation():
    code = "FC-A1B2-C3D4"
    key = generate_valid_key_for_machine(code)
    assert key.startswith("KEY-")
    assert len(key) == 18

def test_trial_status_lifecycle():
    allowed, count, max_runs = get_trial_status()
    assert isinstance(allowed, bool)
    assert isinstance(count, int)
    assert max_runs == 20
    
    # 模拟累加一次
    record_trial_usage()
    allowed_after, count_after, _ = get_trial_status()
    assert count_after >= 1

def test_verify_and_activate_flow():
    mach = get_machine_fingerprint()
    valid_key = generate_valid_key_for_machine(mach)
    
    # 测试错误卡密
    ok_fail, msg_fail = verify_and_activate("KEY-0000-0000-0000")
    assert ok_fail is False
    assert "不匹配" in msg_fail

    # 测试正确卡密
    ok_succ, msg_succ = verify_and_activate(valid_key)
    assert ok_succ is True
    assert "成功" in msg_succ
    assert is_officially_activated() is True