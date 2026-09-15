# FlashCraft 桌面自动化工作台 (Industrial Desktop Automation Scaffolding)

> **工业级桌面业务自动化与商业变现交付脚手架**  
> 唯一作者与主权人: **Emiliamio <mio2110767128@163.com>**  
> 遵循法典: **Mio-Charter (MIO-CHARTER)** 终极总宪

---

## 🌟 核心特性与工业级防线

1. **现代暗黑高质感 GUI (CustomTkinter)**：
   - 深度炭黑配色 (`#12131A` / `#1E202E`) 搭配电光青蓝 (`#38BDF8`) 状态指示；
   - 支持高 DPI 屏幕自动清晰度适配，杜绝 4K 屏模糊与排版错位。
2. **多线程并发与 UIQueue 削峰保护**：
   - 后台任务在独立守护线程 (`daemon=True`) 中运行，界面**绝对不卡死、不假死**；
   - 采用生产者-消费者消息队列架构，日志流与进度平滑消费，**彻底杜绝 Tkinter 跨线程内存段错误**。
3. **商业防御铁律：防白嫖试用锁 (Commercial Trial Defense)**：
   - `config.py` 内置 `IS_TRIAL = True` 试用开关；
   - 开启时仅输出前 10 行数据并植入专属水印，尾款结清后 30 秒一键编译正式全量版。
4. **全局异常熔断器 (Fail-Safe)**：
   - 自动转译底层 Python 异常为客户看得懂的人性化提示（如“文件被 Excel 打开占用”）；
   - 自动持久化保存 `error.log`，界面永不闪退。
5. **免配置一键编译打包 (`build_exe.py`)**：
   - 内置 CustomTkinter 全套样式资源收集；
   - 自动排除 matplotlib/scipy 等巨型依赖，体积从 200MB 骤降至 42MB；
   - 注入多分辨率高保真应用图标 (`assets/icon.ico`)。

---

## 📂 工程分层架构

```text
FlashCraft-Desktop/
├── config.py                 # 全局配置、路径解析与试用锁 (IS_TRIAL)
├── main.py                   # 程序启动入口 (高 DPI 适配与异常守护)
├── build_exe.py              # 一键编译免安装 .exe 打包流水线
├── requirements.txt          # 生产依赖清单
├── assets/                   # 视觉资产 (icon.ico, app_logo.png)
├── core/                     # 核心架构底座
│   ├── base_worker.py        # 业务 Worker 基类 (生命周期与中断保护)
│   ├── logger.py             # 双向日志系统 (UI 队列 + 文件)
│   └── fail_safe.py          # 异常熔断器与白话转译
├── gui/                      # 视图层 (CustomTkinter)
│   ├── app_window.py         # 主窗口交互与布局
│   └── ui_queue.py           # 线程安全 UI 调度中枢
├── tasks/                    # 业务插槽 (即插即用)
│   └── demo_excel_merger.py  # 示例任务：多表格批量清洗与合并引擎
└── tests/                    # 自动化回归测试套件 (100% 通过)
    ├── test_scaffold.py      # 执行引擎与业务逻辑测试
    └── test_gui.py           # GUI 窗口无头生命周期测试
```

---

## 🚀 快速启动与编译

### 1. 本地源码运行
```powershell
python main.py
```

### 2. 运行自动化测试
```powershell
pytest tests/ -v
```

### 3. 一键编译独立单文件 .exe
```powershell
python build_exe.py
```
编译产物位于 `dist/FlashCraft_桌面自动化工作台.exe`，体积约 42MB，双击即可在任意 Windows 机器运行。

---

## 📜 商业变现交付 SOP 规范

- **定金防线**：300 元以下全额托管，300 元以上收取 30%~50% 定金；
- **验收防线**：试用模式交付或录屏验证，杜绝提前给出完整程序；
- **交付闭环**：结清尾款后，改 `IS_TRIAL = False` 重新运行 `build_exe.py` 交付正式版。