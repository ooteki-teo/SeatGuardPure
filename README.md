# SeatGuard - Smart Sedentary Reminder

## this package is totaly by ai, be carefully!

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://www.microsoft.com/windows/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

> ⚠️ Note: The camera is only briefly opened during detection (default: every 15 seconds), and is closed immediately after detection.

## Introduction

SeatGuard is an intelligent sedentary reminder system based on face detection. It uses the camera to detect whether the user is seated in real-time, and automatically sends reminder notifications when the user has been sitting for a configured duration, helping users develop healthy habits.

## Features

- **Face Detection**: Real-time face detection using OpenCV
- **Low Power Design**: Camera is only briefly opened during detection (default: every 15 seconds), and closed immediately after detection
- **Camera Redundancy**: When camera is unavailable, automatically degrades to "no person seated" mode and continues running other functions
- **Smart Timer**: Automatically starts timing when face is detected, resets when user leaves
- when **Cross-Platform Notifications**:
  - Windows: Native Toast notifications / Message boxes
  - macOS: System Notification Center / terminal-notifier
  - Linux: notify-send / plyer
- **System Tray**: Runs in background, click tray icon to start/stop monitoring
- **Cross-Platform Auto-Start**:
  - Windows: Registry
  - macOS: launchd
  - Linux: autostart desktop file
- **Flexible Configuration**: Reminder duration, grace period, and detection interval are all configurable

## Project Structure

```
seat_guard_pure/
├── main.py           # Main program entry
├── config.py         # Configuration module
├── detector.py      # Face detection module
├── timer.py         # Timer module
├── notifier.py      # Notification module
├── autostart.py     # Auto-start manager
├── requirements.txt # Python dependencies
└── resources/       # Resource folder
```

## Requirements

- Windows 10/11 / macOS 10.14+ / Linux (Ubuntu 18.04+)
- Python 3.11+
- Device with camera support

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/SeatGuard.git
cd SeatGuard
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the program

```bash
python main.py
```

## Build EXE

```bash
pyinstaller SeatGuardPure.spec --clean
```

The executable will be located in `dist/SeatGuardPure.exe`

## Usage

1. **Start program**: After running, the program displays an icon in the system tray
2. **Start monitoring**: Click tray icon → "Start/Stop Monitoring"
3. **View status**: Click tray icon → "View Status"
4. **Set auto-start**: Click tray icon → Check "Auto-start on boot"
5. **Screenshot feature**: Click tray icon → Check "Enable Screenshot" (default off)
6. **Exit program**: Click tray icon → "Exit"

## Screenshot Feature

When enabled, screenshots are automatically saved at the following moments:
- **Enter work mode**: `work_start_YYYYMMDD_HHMMSS.jpg`
- **Work end (sedentary timeout)**: `work_end_YYYYMMDD_HHMMSS.jpg`

Screenshots are saved in the `capture/` folder under the program directory, with timestamp watermark in the top-left corner.

## Configuration

Config file is located at `~/.seat_guard_config.json`

| Config | Default | Description |
|--------|---------|-------------|
| reminder_duration | 40 | Reminder duration / sedentary time (minutes) |
| rest_countdown | 120 | Rest countdown (seconds), countdown after sedentary timeout |
| rest_reminder_interval | 20 | Reminder interval when sitting again during rest (seconds) |
| screenshot_enabled | false | Enable screenshot feature |

> Note: Detection interval is configured in code, default value is 15 seconds (`DETECT_INTERVAL` in `main.py`).

## State Machine

SeatGuard uses a four-state state machine design with clear and reliable state transitions:

### State Definitions

| State | Description | Notes |
|-------|-------------|-------|
| WORK | Work mode | Normal timing, enters RELAX after sedentary timeout |
| RELAX | Rest mode | 2-minute countdown, resets if face detected |
| CHECK | Check user mode | 3-minute detection after rest to see if user returns |
| AWAY | Away mode | Paused after 5 minutes of no one |

### State Transition Diagram

```mermaid
stateDiagram-v2
    [*] --> WORK: Start/Face detected

    state WORK {
        [*] --> Timing
        Timing --> Timeout: Sitting duration reached
        Timeout --> [*]: Enter RELAX after notification
    }

  state CHECK {
        [*] --> Detect for 3 minutes
        Detect for 3 minutes --> WORK: Face detected
    }

    state RELAX {
        [*] --> 2-minute countdown
        2-minute countdown --> Reset: Face detected
    }

    state AWAY {
        [*] --> Detect face
    }

    WORK --> AWAY: 5 minutes no one

    RELAX --> CHECK: 2-minute countdown ends

    CHECK --> AWAY: 3-minute countdown ends

    AWAY --> WORK: Face detected again
```

### State Transition Logic

1. **WORK (Work Mode)**
   - Enter: Program start, face detected, face detected in CHECK
   - Exit:
     - Sedentary timeout → RELAX
     - 5 minutes no one → AWAY

2. **RELAX (Rest Mode)**
   - Enter: Automatically after sedentary timeout
   - Behavior: 2-minute countdown, resets if face detected and reminds
   - Exit: 2-minute countdown ends → CHECK

3. **CHECK (Check User Mode)**
   - Enter: RELAX countdown ends
   - Behavior: Detect for 3 minutes to see if user returns
   - Exit:
     - Face detected → WORK
     - 3 minutes no one → AWAY

4. **AWAY (Away Mode)**
   - Enter: 5 minutes no one in WORK, 3 minutes no one in CHECK
   - Behavior: Silent, no reminders sent
   - Exit: Face detected → WORK

## Tech Stack

- **Python 3.11** - Programming language
- **OpenCV (cv2)** - Face detection
- **Pillow** - Image processing
- **pystray** - System tray
- **plyer** - Cross-platform notifications

## FAQ

### Q: Tray icon not showing?
A: Make sure to use official Python instead of Anaconda environment for packaging.

### Q: Notifications not appearing?
A: Check if system notification permissions are enabled.

### Q: Camera cannot be opened?
A: Ensure the camera is not occupied by other programs, or adjust camera_index in the code.

## License

This project is open source under the MIT license. See [LICENSE](LICENSE) file for details.

---

*Want to live longer? Drink water! Stand up!*
