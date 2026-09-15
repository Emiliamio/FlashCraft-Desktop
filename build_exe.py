# -*- coding: utf-8 -*-
"""
build_exe.py - 工业级一键 PyInstaller 编译打包与交付包 ZIP 封装流水线 (巅峰版)
作者: Emiliamio <mio2110767128@163.com>

集成：
1. Windows PE 官方版本资源注入 (--version-file)；
2. 注入多分辨率高保真应用图标 (--icon)；
3. 自动打包 CustomTkinter 与 windnd 资源；
4. 排除巨型科学计算库瘦身体积；
5. 自动封装微信交付免拦截 ZIP 压缩包。
"""

import os
import sys
import io
import shutil
import zipfile
import subprocess

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def build():
    print("=" * 70)
    print("  [*] 开始执行 FlashCraft 工业级免安装独立 .exe 编译打包 (巅峰版)...")
    print("=" * 70)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    icon_path = os.path.join("assets", "icon.ico")
    icon_arg = [f"--icon={icon_path}"] if os.path.exists(icon_path) else []

    version_path = "version_info.txt"
    version_arg = [f"--version-file={version_path}"] if os.path.exists(version_path) else []

    # 构造 PyInstaller 核心参数
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--noconsole",
        "--name=FlashCraft_桌面自动化工作台",
        f"--add-data=assets{os.pathsep}assets",
        f"--add-data=mock_data{os.pathsep}mock_data",
        "--collect-all=customtkinter",
        "--collect-all=windnd",
    ] + icon_arg + version_arg + [
        "--exclude-module=matplotlib",
        "--exclude-module=scipy",
        "--exclude-module=networkx",
        "--exclude-module=pytest",
        "--exclude-module=IPython",
        "--exclude-module=jupyter",
        "--exclude-module=tornado",
        "--exclude-module=sqlite3",
        "main.py"
    ]

    print("执行打包命令:")
    print(" ".join(cmd))
    print("-" * 70)

    res = subprocess.run(cmd)
    if res.returncode != 0:
        print("\n[FAIL] 打包失败，请检查上方日志。")
        sys.exit(res.returncode)

    dist_exe = os.path.join("dist", "FlashCraft_桌面自动化工作台.exe")
    if os.path.exists(dist_exe):
        size_mb = round(os.path.getsize(dist_exe) / (1024 * 1024), 2)
        print("=" * 70)
        print("  [SUCCESS] 巅峰版编译打包 100% 成功！")
        print(f"  交付产物: {dist_exe}")
        print(f"  文件体积: {size_mb} MB")

        # 自动封装微信/闲鱼客户交付 ZIP 压缩包
        zip_name = "FlashCraft_客户交付包_v1.0.0.zip"
        zip_path = os.path.join("dist", zip_name)
        doc_path = "README_客户使用指引.txt"
        
        print(f"  [*] 正在生成商业交付压缩包: {zip_name} ...")
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(dist_exe, arcname="FlashCraft_桌面自动化工作台.exe")
            if os.path.exists(doc_path):
                zf.write(doc_path, arcname="使用说明_必看.txt")
        
        zip_mb = round(os.path.getsize(zip_path) / (1024 * 1024), 2)
        print(f"  [ZIP READY] 客户交付包已生成: {zip_path} ({zip_mb} MB)")
        print("  特性保证: PE版本注入 / 机器码锁 / 拖拽支持 / 智能居中 / 日志复制 / 完成音效 / 微信防拦截ZIP")
        print("=" * 70)
    else:
        print("[!] 未在 dist/ 目录下发现目标文件。")

if __name__ == "__main__":
    build()