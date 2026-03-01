# SeatGuard TODO 待办清单和日报周报功能 - 实施方案

## 一、现有代码结构分析

### 1.1 核心模块
| 模块 | 文件 | 功能 |
|------|------|------|
| main.py | 主程序 | 状态机、托盘菜单、监测循环 |
| config.py | 配置管理 | JSON 配置文件读写 |
| timer.py | 计时器 | 久坐计时功能 |
| notifier.py | 通知 | 跨平台系统通知 |
| detector.py | 人脸检测 | OpenCV 人脸识别 |

### 1.2 数据存储
- **配置**: `~/.seat_guard_config.json` (config.py)
- **截图**: 程序目录下 `capture/` 文件夹

### 1.3 状态机 (main.py)
- WORK → RELAX → CHECK → AWAY 四态转换
- 基于人脸检测自动切换

---

## 二、数据结构设计

### 2.1 任务模板 (task_templates)
```json
{
  "task_templates": [
    {"name": "写周报", "default_blocks": 4, "category": "工作"},
    {"name": "写日报", "default_blocks": 1, "category": "工作"},
    {"name": "学习新技术", "default_blocks": 2, "category": "学习"},
    {"name": "团队会议", "default_blocks": 1, "category": "会议"},
    {"name": "整理代码库", "default_blocks": 2, "category": "工作"}
  ]
}
```

### 2.2 每日任务计划 (daily_plans)
```json
{
  "2024-01-15": {
    "task_order": ["task_001", "task_002", "task_003"],
    "tasks": {
      "task_001": {
        "id": "task_001",
        "name": "写周报",
        "category": "工作",
        "estimated_blocks": 4,
        "completed_blocks": 2,
        "status": "进行中",
        "work_sessions": [
          {"start": "09:00", "end": "09:25", "interruptions": 0},
          {"start": "09:30", "end": "09:55", "interruptions": 1}
        ],
        "notes": "",
        "created_date": "2024-01-15",
        "completed_date": null
      }
    },
    "health_stats": {
      "breaks": 5,
      "leaves": 3,
      "leave_minutes": 12,
      "max_focus_minutes": 75
    },
    "daily_summary": {
      "total_work_minutes": 270,
      "total_blocks": 11,
      "completed_blocks": 9,
      "efficiency": "high"
    }
  }
}
```

### 2.3 历史数据 (history)
```json
{
  "weekly_reports": {
    "2024-W03": {
      "week_number": 3,
      "year": 2024,
      "start_date": "2024-01-15",
      "end_date": "2024-01-21",
      "total_work_minutes": 1470,
      "total_blocks": 59,
      "completed_blocks": 52,
      "task_category_distribution": {
        "工作": 45,
        "学习": 20,
        "会议": 15,
        "其他": 20
      },
      "daily_breakdown": {
        "2024-01-15": {"blocks": 8, "efficiency": "high"},
        "2024-01-16": {"blocks": 6, "efficiency": "medium"},
        "2024-01-17": {"blocks": 9, "efficiency": "high"},
        "2024-01-18": {"blocks": 4, "efficiency": "low"},
        "2024-01-19": {"blocks": 3, "efficiency": "low"}
      },
      "health_stats": {
        "avg_breaks_per_day": 7.2,
        "avg_leave_minutes": 18,
        "long_sit_count": 3
      }
    }
  },
  "daily_reports": {}
}
```

---

## 三、模块设计

### 3.1 新增文件结构
```
seat_guard_pure/
├── main.py              # 现有 - 添加任务板菜单项
├── config.py           # 现有 - 扩展配置
├── task_manager.py     # 新增 - 任务管理核心模块
├── report_generator.py # 新增 - 日报周报生成
├── data_store.py       # 新增 - 数据持久化
└── ui_console.py       # 新增 - 控制台UI交互
```

### 3.2 data_store.py - 数据持久化
```python
"""
数据存储模块 - 负责任务和报告数据的持久化
"""
import json
import os
from pathlib import Path
from datetime import datetime, date

class DataStore:
    """数据存储器 - 使用JSON文件"""

    DEFAULT_DATA = {
        "task_templates": [],
        "daily_plans": {},
        "history": {
            "weekly_reports": {},
            "daily_reports": {}
        }
    }

    DATA_FILE = os.path.join(os.path.expanduser('~'), '.seat_guard_data.json')

    def __init__(self):
        self.data = self.DEFAULT_DATA.copy()
        self.load()

    def load(self):
        """加载数据"""
        if os.path.exists(self.DATA_FILE):
            with open(self.DATA_FILE, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        else:
            self.data = self.DEFAULT_DATA.copy()
            # 添加默认模板
            self._init_default_templates()

    def save(self):
        """保存数据"""
        with open(self.DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def _init_default_templates(self):
        """初始化默认任务模板"""
        self.data["task_templates"] = [
            {"name": "写周报", "default_blocks": 4, "category": "工作"},
            {"name": "写日报", "default_blocks": 1, "category": "工作"},
            {"name": "学习新技术", "default_blocks": 2, "category": "学习"},
            {"name": "团队会议", "default_blocks": 1, "category": "会议"},
            {"name": "整理代码库", "default_blocks": 2, "category": "工作"}
        ]
        self.save()

    # ===== 任务模板管理 =====
    def get_task_templates(self):
        return self.data.get("task_templates", [])

    def add_task_template(self, template):
        self.data["task_templates"].append(template)
        self.save()

    # ===== 每日任务管理 =====
    def get_today_plan(self):
        today = date.today().isoformat()
        return self.data.get("daily_plans", {}).get(today, {"tasks": {}, "task_order": []})

    def save_today_plan(self, plan):
        today = date.today().isoformat()
        if "daily_plans" not in self.data:
            self.data["daily_plans"] = {}
        self.data["daily_plans"][today] = plan
        self.save()

    def get_task(self, task_id):
        today = self.get_today_plan()
        return today.get("tasks", {}).get(task_id)

    def update_task(self, task_id, task_data):
        today = self.get_today_plan()
        if "tasks" not in today:
            today["tasks"] = {}
        today["tasks"][task_id] = task_data
        self.save_today_plan(today)

    # ===== 健康统计 =====
    def get_health_stats(self):
        today = self.get_today_plan()
        return today.get("health_stats", {"breaks": 0, "leaves": 0, "leave_minutes": 0, "max_focus_minutes": 0})

    def update_health_stats(self, stats):
        today = self.get_today_plan()
        today["health_stats"] = stats
        self.save_today_plan(today)

    # ===== 日报周报 =====
    def get_daily_report(self, date_str):
        history = self.data.get("history", {})
        return history.get("daily_reports", {}).get(date_str)

    def save_daily_report(self, date_str, report):
        if "history" not in self.data:
            self.data["history"] = {"weekly_reports": {}, "daily_reports": {}}
        if "daily_reports" not in self.data["history"]:
            self.data["history"]["daily_reports"] = {}
        self.data["history"]["daily_reports"][date_str] = report
        self.save()

    def get_weekly_report(self, week_key):
        history = self.data.get("history", {})
        return history.get("weekly_reports", {}).get(week_key)

    def save_weekly_report(self, week_key, report):
        if "history" not in self.data:
            self.data["history"] = {"weekly_reports": {}, "daily_reports": {}}
        if "weekly_reports" not in self.data["history"]:
            self.data["history"]["weekly_reports"] = {}
        self.data["history"]["weekly_reports"][week_key] = report
        self.save()

    def get_week_range(self, week_number, year=None):
        """获取指定周的开始和结束日期"""
        if year is None:
            year = datetime.now().year
        # 计算该年的第1周开始日期
        jan1 = datetime(year, 1, 1)
        # 找到第一个周一
        first_monday = jan1 - timedelta(days=jan1.weekday())
        # 计算目标周的开始
        week_start = first_monday + timedelta(weeks=week_number - 1)
        week_end = week_start + timedelta(days=6)
        return week_start.date().isoformat(), week_end.date().isoformat()
```

### 3.3 task_manager.py - 任务管理核心
```python
"""
任务管理模块 - 负责任务板的核心逻辑
"""
import uuid
from datetime import datetime, date, timedelta
from data_store import DataStore

class TaskManager:
    """任务管理器"""

    BLOCK_DURATION_MINUTES = 25  # 一个时间块25分钟

    def __init__(self, log_callback=None):
        self.data_store = DataStore()
        self.log_callback = log_callback

        # 当前工作状态
        self.current_task_id = None
        self.current_block_start = None
        self.is_working = False

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)

    # ===== 任务板操作 =====
    def get_today_tasks(self):
        """获取今日任务列表"""
        plan = self.data_store.get_today_plan()
        tasks = plan.get("tasks", {})
        task_order = plan.get("task_order", [])

        # 按顺序返回任务
        result = []
        for task_id in task_order:
            if task_id in tasks:
                result.append(tasks[task_id])
        return result

    def add_task(self, name, estimated_blocks, category="工作"):
        """添加新任务"""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task = {
            "id": task_id,
            "name": name,
            "category": category,
            "estimated_blocks": estimated_blocks,
            "completed_blocks": 0,
            "status": "未开始",
            "work_sessions": [],
            "notes": "",
            "created_date": date.today().isoformat(),
            "completed_date": None
        }

        plan = self.data_store.get_today_plan()
        if "tasks" not in plan:
            plan["tasks"] = {}
        if "task_order" not in plan:
            plan["task_order"] = []

        plan["tasks"][task_id] = task
        plan["task_order"].append(task_id)
        self.data_store.save_today_plan(plan)

        self.log(f"添加任务: {name} ({estimated_blocks}块)")
        return task

    def delete_task(self, task_id):
        """删除任务"""
        plan = self.data_store.get_today_plan()
        if task_id in plan.get("tasks", {}):
            del plan["tasks"][task_id]
            if task_id in plan.get("task_order", []):
                plan["task_order"].remove(task_id)
            self.data_store.save_today_plan(plan)
            self.log(f"删除任务: {task_id}")

    def move_task(self, task_id, new_index):
        """调整任务顺序"""
        plan = self.data_store.get_today_plan()
        task_order = plan.get("task_order", [])
        if task_id in task_order:
            old_index = task_order.index(task_id)
            task_order.pop(old_index)
            task_order.insert(new_index, task_id)
            self.data_store.save_today_plan(plan)
            self.log(f"移动任务: {task_id} 从{old_index}到{new_index}")

    def edit_task(self, task_id, name=None, estimated_blocks=None, category=None):
        """编辑任务"""
        task = self.data_store.get_task(task_id)
        if task:
            if name is not None:
                task["name"] = name
            if estimated_blocks is not None:
                task["estimated_blocks"] = estimated_blocks
            if category is not None:
                task["category"] = category
            self.data_store.update_task(task_id, task)
            self.log(f"编辑任务: {task_id}")

    # ===== 工作会话 =====
    def start_task(self, task_id):
        """开始一个任务"""
        self.current_task_id = task_id
        self.current_block_start = datetime.now()
        self.is_working = True

        task = self.data_store.get_task(task_id)
        if task:
            task["status"] = "进行中"
            self.data_store.update_task(task_id, task)

        self.log(f"开始任务: {task_id}")

    def complete_block(self, interruptions=0):
        """完成一个时间块"""
        if not self.current_task_id or not self.current_block_start:
            return

        end_time = datetime.now()
        task = self.data_store.get_task(self.current_task_id)

        if task:
            # 记录工作时段
            session = {
                "start": self.current_block_start.strftime("%H:%M"),
                "end": end_time.strftime("%H:%M"),
                "interruptions": interruptions
            }
            if "work_sessions" not in task:
                task["work_sessions"] = []
            task["work_sessions"].append(session)

            # 更新完成块数
            task["completed_blocks"] = task.get("completed_blocks", 0) + 1

            # 检查是否完成
            if task["completed_blocks"] >= task["estimated_blocks"]:
                task["status"] = "已完成"
                task["completed_date"] = date.today().isoformat()

            self.data_store.update_task(self.current_task_id, task)
            self.log(f"完成时间块: {task['name']} ({task['completed_blocks']}/{task['estimated_blocks']})")

        self.current_block_start = None

    def switch_task(self, new_task_id):
        """切换任务"""
        if self.current_task_id and self.current_block_start:
            self.complete_block()

        self.start_task(new_task_id)

    # ===== 健康统计 =====
    def record_break(self):
        """记录一次休息"""
        plan = self.data_store.get_today_plan()
        if "health_stats" not in plan:
            plan["health_stats"] = {"breaks": 0, "leaves": 0, "leave_minutes": 0, "max_focus_minutes": 0}
        plan["health_stats"]["breaks"] += 1
        self.data_store.save_today_plan(plan)

    def record_leave(self, minutes):
        """记录离开时间"""
        plan = self.data_store.get_today_plan()
        if "health_stats" not in plan:
            plan["health_stats"] = {"breaks": 0, "leaves": 0, "leave_minutes": 0, "max_focus_minutes": 0}
        plan["health_stats"]["leaves"] += 1
        plan["health_stats"]["leave_minutes"] += minutes
        self.data_store.save_today_plan(plan)

    # ===== 推荐下一个任务 =====
    def recommend_next_task(self):
        """根据时间和历史推荐下一个任务"""
        current_hour = datetime.now().hour
        tasks = self.get_today_tasks()

        # 筛选未完成的任务
        unfinished = [t for t in tasks if t["status"] != "已完成"]

        if not unfinished:
            return None

        # 根据时间段推荐
        if 9 <= current_hour <= 11:
            # 上午黄金时间，推荐估计块数多的任务
            unfinished.sort(key=lambda t: t["estimated_blocks"], reverse=True)
        elif 14 <= current_hour <= 15:
            # 下午，推荐中等难度的任务
            unfinished.sort(key=lambda t: abs(t["estimated_blocks"] - 2))
        else:
            # 其他时间，按顺序
            pass

        return unfinished[0] if unfinished else None
```

### 3.4 report_generator.py - 报告生成
```python
"""
报告生成模块 - 生成日报和周报
"""
from datetime import datetime, date, timedelta
from data_store import DataStore

class ReportGenerator:
    """报告生成器"""

    def __init__(self, log_callback=None):
        self.data_store = DataStore()
        self.log_callback = log_callback

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)

    def generate_daily_report(self, target_date=None):
        """生成日报"""
        if target_date is None:
            target_date = date.today()

        date_str = target_date.isoformat()
        plan = self.data_store.data.get("daily_plans", {}).get(date_str)

        if not plan:
            return self._format_empty_daily(target_date)

        tasks = plan.get("tasks", {})
        health = plan.get("health_stats", {})

        # 计算统计数据
        total_blocks = sum(t.get("estimated_blocks", 0) for t in tasks.values())
        completed_blocks = sum(t.get("completed_blocks", 0) for t in tasks.values())
        total_minutes = completed_blocks * 25  # 每个块25分钟

        # 任务完成情况
        task_completion = []
        for task in tasks.values():
            status_icon = "✅" if task["status"] == "已完成" else "⏳"
            diff = task.get("completed_blocks", 0) - task.get("estimated_blocks", 0)
            diff_text = f"(比预计{'多' if diff > 0 else '少'}{abs(diff)}块)" if diff != 0 else ""
            task_completion.append({
                "name": task["name"],
                "completed": task.get("completed_blocks", 0),
                "total": task["estimated_blocks"],
                "status": task["status"],
                "icon": status_icon,
                "diff": diff_text
            })

        # 计算效率曲线
        efficiency = self._calculate_efficiency(plan)

        report = {
            "date": date_str,
            "total_minutes": total_minutes,
            "total_blocks": total_blocks,
            "completed_blocks": completed_blocks,
            "tasks": task_completion,
            "health": health,
            "efficiency": efficiency
        }

        return self._format_daily_report(target_date, report)

    def generate_weekly_report(self, week_number=None, year=None):
        """生成周报"""
        if week_number is None:
            today = date.today()
            week_number = today.isocalendar()[1]
        if year is None:
            year = date.today().year

        # 获取本周日期范围
        start_date, end_date = self._get_week_range(week_number, year)

        # 收集本周数据
        total_minutes = 0
        total_blocks = 0
        completed_blocks = 0
        daily_data = []
        category_stats = {}

        for i in range(7):
            day = start_date + timedelta(days=i)
            date_str = day.isoformat()
            plan = self.data_store.data.get("daily_plans", {}).get(date_str)

            if plan:
                tasks = plan.get("tasks", {})
                day_blocks = sum(t.get("completed_blocks", 0) for t in tasks.values())
                daily_data.append({
                    "date": date_str,
                    "weekday": day.strftime("%a"),
                    "blocks": day_blocks
                })
                total_blocks += sum(t.get("estimated_blocks", 0) for t in tasks.values())
                completed_blocks += day_blocks
                total_minutes += day_blocks * 25

                # 分类统计
                for task in tasks.values():
                    cat = task.get("category", "其他")
                    if cat not in category_stats:
                        category_stats[cat] = 0
                    category_stats[cat] += task.get("completed_blocks", 0)

        # 健康统计（简化）
        avg_breaks = 0  # 需要从历史数据计算
        avg_leave = 0

        report = {
            "week_number": week_number,
            "year": year,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_minutes": total_minutes,
            "total_blocks": total_blocks,
            "completed_blocks": completed_blocks,
            "daily_data": daily_data,
            "category_stats": category_stats,
            "health": {
                "avg_breaks": avg_breaks,
                "avg_leave_minutes": avg_leave
            }
        }

        return self._format_weekly_report(week_number, year, report)

    def _calculate_efficiency(self, plan):
        """计算效率曲线"""
        # 简化实现：基于工作会话的时间分布
        sessions = []
        for task in plan.get("tasks", {}).values():
            sessions.extend(task.get("work_sessions", []))

        if not sessions:
            return []

        # 按小时分组
        hour_blocks = {}
        for session in sessions:
            start_hour = int(session["start"].split(":")[0])
            if start_hour not in hour_blocks:
                hour_blocks[start_hour] = 0
            hour_blocks[start_hour] += 1

        efficiency = []
        for hour in sorted(hour_blocks.keys()):
            blocks = hour_blocks[hour]
            level = "高效" if blocks >= 3 else ("中等" if blocks >= 2 else "低效")
            efficiency.append({
                "hour": f"{hour:02d}:00",
                "blocks": blocks,
                "level": level
            })

        return efficiency

    def _get_week_range(self, week_number, year):
        """获取指定周的开始和结束日期"""
        jan1 = datetime(year, 1, 1)
        first_monday = jan1 - timedelta(days=jan1.weekday())
        week_start = first_monday + timedelta(weeks=week_number - 1)
        week_end = week_start + timedelta(days=6)
        return week_start.date(), week_end.date()

    def _format_daily_report(self, target_date, report):
        """格式化日报显示"""
        date_str = target_date.strftime("%Y-%m-%d")
        total_hours = report["total_minutes"] / 60

        lines = [
            f"╔════════════════════════════════════╗",
            f"║     📊 今日工作日报 ({date_str})    ║",
            f"╠════════════════════════════════════╣",
            f"║【今日概览】                          ║",
            f"║ 总工作时间: {total_hours:.1f}小时 ({report['completed_blocks']}个时间块)      ║",
            f"║ 完成进度: {report['completed_blocks']}/{report['total_blocks']}个                    ║",
            f"║                                      ║",
            f"║【任务完成情况】                       ║",
        ]

        for task in report["tasks"]:
            lines.append(f"║ {task['icon']} {task['name'][:10]:<10} ({task['completed']}/{task['total']}块) {task['diff'][:12]:<12}║")

        lines.extend([
            f"║                                      ║",
            f"║【健康数据】                           ║",
            f"║ 休息次数: {report['health'].get('breaks', 0)}次                       ║",
            f"║ 离开次数: {report['health'].get('leaves', 0)}次 (共{report['health'].get('leave_minutes', 0)}分钟)       ║",
            f"╚════════════════════════════════════╝",
        ])

        return "\n".join(lines)

    def _format_weekly_report(self, week_number, year, report):
        """格式化周报显示"""
        lines = [
            f"╔════════════════════════════════════╗",
            f"║     📈 本周工作周报 (第{week_number}周)          ║",
            f"╠════════════════════════════════════╣",
            f"║【本周总量】                           ║",
            f"║ 总工作时间: {report['total_minutes']/60:.1f}小时 ({report['completed_blocks']}个时间块)     ║",
            f"║ 完成率: {report['completed_blocks']*100//max(report['total_blocks'],1)}%                         ║",
            f"║                                      ║",
            f"║【每日对比】                           ║",
        ]

        for day_data in report["daily_data"]:
            level = "高效" if day_data["blocks"] >= 6 else ("中等" if day_data["blocks"] >= 4 else "低效")
            bar = "█" * min(day_data["blocks"], 10) + "░" * (10 - min(day_data["blocks"], 10))
            lines.append(f"║ {day_data['weekday']}: {day_data['blocks']}块 {bar} {level}   ║")

        lines.extend([
            f"║                                      ║",
            f"║【下周计划建议】                        ║",
            f"║ • 继续保持高效工作节奏                 ║",
            f"╚════════════════════════════════════╝",
        ])

        return "\n".join(lines)

    def _format_empty_daily(self, target_date):
        """格式化空日报"""
        return f"📊 今日工作日报 ({target_date.isoformat()})\n\n暂无任务数据"
```

---

## 四、与现有代码集成

### 4.1 托盘菜单扩展 (main.py)
在现有托盘菜单中添加：
```python
pystray.Menu.SEPARATOR,
pystray.MenuItem("📋 任务板", self._show_task_board),
pystray.MenuItem("📊 今日日报", self._show_daily_report),
pystray.MenuItem("📈 本周周报", self._show_weekly_report),
```

### 4.2 状态机集成
在现有的 WORK/RELAX/CHECK/AWAY 状态基础上，叠加任务工作状态：
- 用户开始任务时，记录当前任务 ID 和开始时间
- 用户离开座位时，暂停计时并记录
- 用户完成一个时间块时，更新任务进度

### 4.3 触发时机
| 事件 | 触发动作 |
|------|----------|
| 程序启动 | 检测是否有今日任务，有则显示任务板 |
| 用户落座 | 检测是否有进行中的任务，有则提示继续 |
| 时间块完成 | 显示完成确认，询问是否继续或切换 |
| 任务完成 | 显示任务完成统计，提示下一个推荐任务 |
| 下班/手动触发 | 显示今日日报 |
| 周一/手动触发 | 生成上周周报 |

---

## 五、实施计划

### 阶段1: 数据层 (1-2天)
- [ ] 创建 data_store.py
- [ ] 实现 JSON 数据持久化
- [ ] 添加默认任务模板

### 阶段2: 核心逻辑 (2-3天)
- [ ] 创建 task_manager.py
- [ ] 实现任务增删改查
- [ ] 实现工作会话跟踪
- [ ] 实现任务推荐算法

### 阶段3: 报告生成 (1-2天)
- [ ] 创建 report_generator.py
- [ ] 实现日报生成
- [ ] 实现周报生成

### 阶段4: UI集成 (2-3天)
- [ ] 扩展托盘菜单
- [ ] 添加任务板弹窗 UI
- [ ] 添加日报周报显示

### 阶段5: 测试与优化 (1天)
- [ ] 单元测试
- [ ] 集成测试
- [ ] 性能优化

---

## 六、技术要点

1. **数据存储**: 继续使用 JSON 文件（与现有 config.py 保持一致）
2. **时间块**: 固定 25 分钟一个块（番茄工作法）
3. **托盘菜单**: 使用 pystray.Menu 层级结构
4. **通知集成**: 复用现有的 Notifier 模块发送任务提醒

---

## 七、注意事项

1. 不影响现有的久坐提醒核心功能
2. 任务数据与配置数据分离存储
3. 保持向后兼容，历史数据可迁移
4. UI 交互尽量简洁，不增加复杂度
