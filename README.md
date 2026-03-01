# SeatGuard - 久坐提醒

## ！！ 这个是纯ai写的！！
## ！！ 能用，cpu占用不算高，每秒一次检测。
## ！！ 但是会一直占用摄像头！！

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

## 简介

SeatGuard 是一款基于人脸检测的智能久坐提醒系统，通过摄像头实时检测用户是否坐在座位上，当用户连续坐着超过设定时间后，会自动发送提醒通知，帮助用户养成健康的生活习惯。

## 功能特性

- **人脸检测**：使用 OpenCV 进行实时人脸检测
- **智能计时**：检测到人脸后自动开始计时，离开后自动重置
- **多种提醒方式**：
  - Windows 原生 Toast 通知
  - 系统托盘气泡提醒
  - 消息框提醒（备用）
- **系统托盘**：后台运行，点击托盘图标即可开始/停止监测
- **开机自启**：支持开机自动启动（可通过托盘菜单设置）
- **配置灵活**：提醒时长、休息宽限期均可配置

## 项目结构

```
seat_guard_pure/
├── main.py          # 主程序入口
├── config.py        # 配置文件
├── detector.py       # 人脸检测模块
├── timer.py         # 计时器模块
├── notifier.py      # 通知模块
├── autostart.py     # 开机自启管理
├── requirements.txt  # Python 依赖
└── resources/       # 资源文件夹
```

## 环境要求

- Windows 10/11
- Python 3.11+
- 支持 DirectShow 的摄像头

## 安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/SeatGuard.git
cd SeatGuard
```

### 2. 安装依赖

```bash
pip install -r seat_guard_pure/requirements.txt
```

### 3. 运行程序

```bash
python seat_guard_pure/main.py
```

## 打包为 EXE

```bash
cd seat_guard_pure
pyinstaller SeatGuardPure.spec --clean
```

打包完成后，可执行文件位于 `dist/SeatGuardPure.exe`

## 使用说明

1. **启动程序**：运行后程序会在系统托盘显示图标
2. **开始监测**：点击托盘图标 → "开始/停止监测"
3. **查看状态**：点击托盘图标 → "查看状态"
4. **设置自启**：点击托盘图标 → 勾选"开机自动启动"
5. **截图功能**：点击托盘图标 → 勾选"启用截图"（默认关闭）
6. **退出程序**：点击托盘图标 → "退出"

## 截图功能

启用截图功能后，会在以下时机自动保存截图：
- **进入工作模式**：`work_start_YYYYMMDD_HHMMSS.jpg`
- **工作结束（久坐超时）**：`work_end_YYYYMMDD_HHMMSS.jpg`

截图会保存到程序目录下 `capture/` 文件夹中，图片左上角会添加时间戳水印。

## 配置说明

配置文件位于 `C:\Users\YourUsername\.seat_guard_config.json`

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| reminder_duration | 40 | 提醒时长/久坐时间（分钟） |
| rest_countdown | 120 | 休息倒计时（秒），久坐超时后进入休息模式的倒计时 |
| rest_reminder_interval | 20 | 休息期间再次坐下提醒间隔（秒） |
| screenshot_enabled | false | 是否启用截图功能 |

## 状态机说明

SeatGuard 采用四态状态机设计，状态转换清晰可靠：

### 状态定义

| 状态 | 说明 | 备注 |
|------|------|------|
| WORK | 工作模式 | 正常计时，久坐超时后进入 RELAX |
| RELAX | 休息模式 | 2分钟倒计时，期间检测到人脸重置倒计时 |
| CHECK | 检测用户模式 | 休息2分钟后检测3分钟，看用户是否回来 |
| AWAY | 离开模式 | 连续5分钟无人，暂停提醒 |

### 状态转换图

```mermaid
stateDiagram-v2
    [*] --> WORK: 启动/检测到人脸

    state WORK {
        [*] --> 正常计时
        正常计时 --> 久坐超时: 坐满设定时长
        久坐超时 --> [*]: 提醒后进入RELAX
    }

    WORK --> AWAY: 连续5分钟无人

    state RELAX {
        [*] --> 休息倒计时2分钟
        休息倒计时2分钟 --> 重新开始2分钟: ⚠️ 检测到人脸
    }

    RELAX --> CHECK: 2分钟倒计时结束

    state CHECK {
        [*] --> 检测用户3分钟
        检测用户3分钟 --> WORK: ✅ 检测到人脸
    }

    CHECK --> AWAY: 3分钟倒计时结束

    AWAY --> WORK: 再次检测到人脸
```

### 状态流转逻辑

1. **WORK（工作模式）**
   - 进入条件：程序启动、检测到人脸、CHECK 状态检测到人脸
   - 退出条件：
     - 久坐超时 → RELAX
     - 连续5分钟无人 → AWAY

2. **RELAX（休息模式）**
   - 进入条件：久坐超时后自动进入
   - 行为：2分钟倒计时，期间检测到人脸重置倒计时并提醒
   - 退出条件：2分钟倒计时结束 → CHECK

3. **CHECK（检测用户模式）**
   - 进入条件：RELAX 倒计时结束
   - 行为：检测3分钟，看用户是否回来
   - 退出条件：
     - 检测到人脸 → WORK
     - 3分钟无人 → AWAY

4. **AWAY（离开模式）**
   - 进入条件：WORK 连续5分钟无人、CHECK 3分钟无人
   - 行为：静默挂起，不发送任何提醒
   - 退出条件：检测到人脸 → WORK

### 技术实现

状态机核心代码位于 `main.py` 中的 `SeatGuardStateMachine` 类，实现了：
- 状态枚举定义
- 状态转换方法 `transition_to()`
- 状态进入回调 `on_enter_work/relax/check/away()`
- 倒计时检查方法（作为条件判断工具）

## 技术栈

- **Python 3.11** - 编程语言
- **OpenCV (cv2)** - 人脸检测
- **Pillow** - 图像处理
- **pystray** - 系统托盘
- **win10toast** / **plyer** - 系统通知

## 常见问题

### Q: 托盘图标不显示？
A: 确保使用官方 Python 而非 Anaconda 环境进行打包。

### Q: 通知不弹出？
A: 检查系统通知权限是否开启，或尝试重新安装 win10toast。

### Q: 摄像头无法打开？
A: 确保摄像头未被其他程序占用，或在代码中调整 camera_index。

## 许可证

本项目基于 MIT 许可证开源，详见 [LICENSE](LICENSE) 文件。

---

*想要活得久，喝杯水！站起来！*
