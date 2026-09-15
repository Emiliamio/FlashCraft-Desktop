# -*- coding: utf-8 -*-
"""
tests/test_license_guard.py - 单机设备指纹与授权防刷熔断器单元测试
作者: Emiliamio <mio2110767128@163.com>
"""

import pytest
from core.license_guard import (
    get_machine_fingerprint,
    generate_valid_key_for_machine,
    get_trial_status,
    record_trial_usage
)

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
    assert count_after >= count