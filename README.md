# SeatGuard -- 久坐提醒托盘软件

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://www.microsoft.com/windows/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

> ⚠️ **声明**: 此项目由 AI (Claude Code) 生成，使用请自行承担风险。
>
> ⚠️ 注意: 摄像头仅在检测时短暂打开（默认每 20 秒），检测完成后立即关闭。

## 简介

SeatGuard 是一款基于人脸检测的智能久坐提醒系统。通过摄像头实时检测用户是否在座位上，当用户坐的时间超过设定时长后自动发送提醒通知，帮助用户养成健康的工作习惯。

## 功能特点

### 核心功能
- **人脸检测**: 使用 OpenCV 进行实时人脸检测
- **低功耗设计**: 摄像头仅在检测时短暂打开（默认每 20 秒），检测完成后立即关闭
- **摄像头冗余**: 摄像头不可用时自动降级为"无人"模式，继续运行其他功能
- **智能计时**: 检测到人脸时自动开始计时，用户离开时自动暂停
- **状态机**: 四种工作状态 (WORK/RELAX/CHECK/AWAY)，自动切换

### 通知提醒
- **久坐超时提醒**: 工作一定时间后提醒用户休息
- **休息完成提醒**: 休息时间结束后提醒用户回到座位
- **休息不充分提醒**: 休息期间检测到人脸时提醒继续休息

### 跨平台支持
- **系统托盘**: 后台运行，点击托盘图标开始/停止监测
- **跨平台通知**:
  - Windows: 原生Toast通知
  - macOS: 系统通知中心
  - Linux: notify-send / plyer
- **开机自启**:
  - Windows: 注册表
  - macOS: launchd
  - Linux: autostart desktop文件
- **Web控制面板**: 通过浏览器访问设置、日志、报告

## 项目结构

```
seat_guard_pure/
├── main.py              # 主程序入口
├── config.py            # 配置模块
├── detector.py          # 人脸检测模块
├── timer.py             # 计时器模块
├── notifier.py          # 通知模块
├── autostart.py         # 开机自启管理
├── data_store.py        # 数据存储模块
├── report_generator.py  # 报告生成模块
├── state_machine.py     # 状态机模块
├── api_server.py        # FastAPI Web服务器
├── screenshot.py        # 截图模块
├── tray_icon.py         # 托盘图标
├── web/                 # Web前端
│   ├── index.html       # 首页/控制面板
│   ├── settings.html    # 设置
│   ├── logs.html        # 日志
│   └── reports.html     # 报告
├── requirements.txt     # Python依赖
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

### 方式一: 使用打包脚本

```bash
# 运行内置打包脚本
python build.py
```

可执行文件将生成在 `dist/SeatGuardPure.exe`

### 方式二: 手动打包

```bash
# 安装 PyInstaller
pip install pyinstaller

# 打包为单个可执行文件
pyinstaller --onefile --windowed --name SeatGuardPure --add-data "resources;resources" --add-data "web;web" --icon icon.ico main.py
```

### 打包说明

- `--onefile`: 打包成单个可执行文件
- `--windowed`: 无控制台窗口（GUI模式）
- 资源文件 (web, resources) 会自动打包到exe中

打包完成后:
1. 系统托盘图标出现
2. Web服务器自动启动于 `http://127.0.0.1:8765`
3. 点击托盘菜单打开Web控制面板

## Web控制面板

启动程序后，通过托盘菜单访问或直接访问 http://127.0.0.1:8765

| 页面 | 功能 |
|------|------|
| 首页 | 显示今日进度、导航 |
| 设置 | 修改提醒时长、截图开关 |
| 日志 | 实时运行日志 |
| 报告 | 查看日报/周报 |

## 使用说明

### 托盘菜单
1. **开始/停止监测**: 切换监测状态
2. **打开控制面板**: 在浏览器中打开Web界面
3. **设置**: 修改配置
4. **日志**: 查看运行日志
5. **今日日报/本周周报**: 查看工作统计
6. **开机自启**: 开启/关闭开机自启
7. **截图功能**: 开启/关闭截图功能

### 工作流程
1. 程序启动后自动开始监测
2. 检测到人脸 → 进入工作模式，开始计时
3. 久坐超时 → 进入休息模式，提醒用户休息
4. 休息完成 → 进入等待模式，检测用户是否回到座位
5. 用户回到座位 → 恢复工作模式

## 截图功能

开启后会自动保存截图:
- **进入工作模式**: `work_start_YYYYMMDD_HHMMSS.jpg`
- **工作结束(久坐超时)**: `work_end_YYYYMMDD_HHMMSS.jpg`

截图保存在程序目录下的 `capture/` 文件夹中。

## 配置说明

### 配置文件位置
- 配置: `~/.seat_guard_config.json`
- 数据: `~/.seat_guard_data.json`

### 配置选项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| reminder_duration | 40 | 久坐提醒时长(分钟) |
| rest_countdown | 120 | 休息倒计时(秒) |
| rest_reminder_interval | 20 | 休息期间提醒间隔(秒) |
| screenshot_enabled | false | 开启截图功能 |
| grace_period | 120 | 宽限期(秒) |
| detect_interval | 20 | 检测间隔(秒) |
| away_timeout | 300 | 离开超时(秒) |
| check_timeout | 180 | CHECK等待超时(秒) |
| max_relax_resets | 3 | 休息期间最大重置次数 |

## 状态机

SeatGuard 使用四状态状态机:

| 状态 | 说明 |
|------|------|
| WORK | 工作模式，正常计时 |
| RELAX | 休息模式，久坐超时后 |
| CHECK | 检测用户模式，检测用户是否返回 |
| AWAY | 离开模式，5分钟无人 |

### 状态转换图

```
                    ┌─────────────────┐
                    │                 │
                    ▼                 │
              ┌──────────┐    ┌──────────┐
  检测到人脸  │   WORK   │───▶│   RELAX  │  (久坐超时)
              │  工作模式 │    │  休息模式 │◀─────┐
              └──────────┘    └──────────┘      │
                    ▲            │              │
                    │            ▼              │
                    │      ┌──────────┐    休息倒计时结束
                    │      │  CHECK   │───────────┘
                    │      │ 等待模式 │
                    │      └──────────┘
                    │            │
                    │            ▼
                    │      ┌──────────┐
                    └─────▶│   AWAY   │   (连续5分钟无人)
                           │  离开模式 │
                           └──────────┘
```

## 技术栈

- **Python 3.11** - 编程语言
- **OpenCV** - 人脸检测
- **FastAPI** - Web服务器
- **pystray** - 系统托盘
- **plyer** - 跨平台通知

## 常见问题

### Q: 托盘图标不显示?
A: 请确保使用官方Python环境，而非Anaconda环境。

### Q: 通知不出现?
A: 检查系统通知权限是否开启。

### Q: 无法打开摄像头?
A: 确保摄像头未被其他程序占用。

### Q: 网页无法访问?
A: 确保8765端口未被占用，或在设置中更改端口。

## 许可证

此项目基于MIT许可证开源。详见 [LICENSE](LICENSE) 文件。

---

*想要长寿? 多喝水! 多站起来!*
