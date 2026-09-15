# -*- coding: utf-8 -*-
"""
tests/test_gui.py - GUI 主窗口初始化与生命周期无头 Smoke 测试
"""
import pytest
from gui.app_window import AppWindow

def test_app_window_lifecycle():
    app = AppWindow()
    # 强制让 Tkinter 刷新一帧以校验所有组件布局无语法或排版错误
    app.update()
    
    assert app.title() != ""
    assert app.status_badge.cget("text") == "● 待机就绪"
    assert app.trial_badge is not None
    assert app.btn_run is not None
    assert app.btn_stop is not None
    
    # 优雅销毁
    app.destroy()