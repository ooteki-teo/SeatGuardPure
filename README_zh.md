# SeatGuard - 智能久坐提醒系统

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://www.microsoft.com/windows/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

> ⚠️ **AI 声明**：本项目由 AI（Claude Code）完全生成，使用需谨慎，风险自担。
>
> ⚠️ 注意：摄像头仅在检测时短暂开启（默认每20秒检测一次），检测完成后立即关闭。

## 简介

SeatGuard 是一款基于人脸检测的智能久坐提醒系统，通过摄像头实时检测用户是否坐在座位上，当用户连续坐着超过设定时间后，会自动发送提醒通知，帮助用户养成健康的生活习惯。

同时，SeatGuard 还提供**任务管理功能**，基于番茄工作法（25分钟专注块），帮助您更高效地完成工作任务。

## 功能特性

### 核心功能
- **人脸检测**：使用 OpenCV 进行实时人脸检测
- **低功耗设计**：摄像头仅在检测时短暂开启（默认每20秒检测一次），检测完成后立即关闭
- **摄像头冗余**：摄像头不可用时自动降级为无人在座模式，继续运行其他功能
- **智能计时**：检测到人脸后自动开始计时，离开后自动重置

### 任务管理
- **番茄工作法**：25分钟专注块，自动计时
- **任务面板**：可视化任务列表，支持添加、开始、完成、删除
- **无感计时**：基于状态机联动，检测到人脸自动开始/暂停计时
- **日报周报**：自动生成工作统计报告

### 跨平台特性
- **系统托盘**：后台运行，点击托盘图标即可开始/停止监测
- **跨平台通知**：
  - Windows: 原生 Toast 通知 / 消息框
  - macOS: 系统通知中心
  - Linux: notify-send / plyer
- **跨平台自启动**：
  - Windows: 注册表
  - macOS: launchd
  - Linux: autostart desktop 文件
- **Web 控制面板**：通过浏览器访问任务板、设置、日志、报告

## 项目结构

```
seat_guard_pure/
├── main.py              # 主程序入口
├── config.py            # 配置文件
├── detector.py          # 人脸检测模块
├── timer.py             # 计时器模块
├── notifier.py          # 通知模块
├── autostart.py         # 开机自启管理
├── task_manager.py      # 任务管理模块
├── data_store.py        # 数据存储模块
├── report_generator.py   # 报告生成模块
├── state_machine.py     # 状态机模块
├── api_server.py        # FastAPI Web 服务
├── screenshot.py        # 截图模块
├── tray_icon.py         # 托盘图标
├── web/                 # Web 前端
│   ├── index.html       # 首页/控制面板
│   ├── tasks.html       # 任务板
│   ├── settings.html    # 设置
│   ├── logs.html        # 日志
│   └── reports.html     # 报告
├── requirements.txt      # Python 依赖
└── resources/           # 资源文件夹
```

## 环境要求

- Windows 10/11 / macOS 10.14+ / Linux (Ubuntu 18.04+)
- Python 3.11+
- 支持摄像头的设备

## 安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/SeatGuard.git
cd SeatGuard
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行程序

```bash
python main.py
```

## 打包步骤

### 方式一：直接运行打包脚本

```bash
# 使用项目自带的打包脚本
python build.py
```

打包完成后，可执行文件位于 `dist/SeatGuardPure.exe`

### 方式二：手动打包

```bash
# 安装 PyInstaller（如果未安装）
pip install pyinstaller

# 打包成单个可执行文件
pyinstaller --onefile --windowed --name SeatGuardPure --add-data "resources;resources" --add-data "web;web" --icon icon.ico main.py
```

### 打包说明

- `--onefile`: 打包成单个可执行文件
- `--windowed`: 不显示控制台窗口（GUI 模式）
- 资源文件（web、resources）会自动包含在 exe 中

打包后的文件位于 `dist/` 目录下。

程序启动后：
1. 系统托盘显示图标
2. Web 服务自动启动于 `http://127.0.0.1:8765`
3. 点击托盘菜单可打开 Web 控制面板

## Web 控制面板

启动程序后，通过托盘菜单或直接访问 http://127.0.0.1:8765

| 页面 | 功能 |
|------|------|
| 首页 | 显示今日进度，导航入口 |
| 任务板 | 添加、开始、完成、删除任务 |
| 设置 | 修改提醒时长、截图开关等 |
| 日志 | 实时查看运行日志 |
| 报告 | 查看日报、周报统计 |

## 使用说明

### 托盘菜单
1. **开始/停止监测**：切换监测状态
2. **打开控制面板**：在浏览器中打开 Web 界面
3. **任务板**：查看和管理今日任务
4. **设置**：修改配置
5. **日志**：查看运行日志
6. **日报/周报**：查看工作统计
7. **开机自动启动**：开机自启开关
8. **启用截图**：截图功能开关

### 任务管理流程
1. 打开任务板，添加今日任务（预估需要的专注块数）
2. 开始监测，当检测到人脸时，选择任务点击"开始"
3. 系统自动计时，25分钟完成一个专注块
4. 状态机联动：离开座位自动暂停，回到座位自动继续

## 截图功能

启用截图功能后，会在以下时机自动保存截图：
- **进入工作模式**：`work_start_YYYYMMDD_HHMMSS.jpg`
- **工作结束（久坐超时）**：`work_end_YYYYMMDD_HHMMSS.jpg`

截图会保存到程序目录下 `capture/` 文件夹中，图片左上角会添加时间戳水印。

## 配置说明

### 配置文件位置
- 配置：`~/.seat_guard_config.json`
- 数据：`~/.seat_guard_data.json`

### 配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| reminder_duration | 40 | 久坐提醒时长（分钟） |
| rest_countdown | 120 | 休息倒计时（秒） |
| rest_reminder_interval | 20 | 休息期间提醒间隔（秒） |
| screenshot_enabled | false | 是否启用截图功能 |
| grace_period | 10 | 宽限期（秒） |

## 状态机说明

SeatGuard 采用四态状态机设计：

| 状态 | 说明 |
|------|------|
| WORK | 工作模式，正常计时 |
| RELAX | 休息模式，久坐超时后进入 |
| CHECK | 检测用户模式，休息后检测是否回来 |
| AWAY | 离开模式，连续5分钟无人 |

## 技术栈

- **Python 3.11** - 编程语言
- **OpenCV** - 人脸检测
- **FastAPI** - Web 服务
- **pystray** - 系统托盘
- **plyer** - 跨平台通知

## 常见问题

### Q: 托盘图标不显示？
A: 确保使用官方 Python 而非 Anaconda 环境进行打包。

### Q: 通知不弹出？
A: 检查系统通知权限是否开启。

### Q: 摄像头无法打开？
A: 确保摄像头未被其他程序占用，或在代码中调整 camera_index。

### Q: Web 页面无法访问？
A: 确保 8765 端口未被占用，或在设置中修改端口。

## 许可证

本项目基于 MIT 许可证开源，详见 [LICENSE](LICENSE) 文件。

---

*想要活得久，喝杯水！站起来！*
