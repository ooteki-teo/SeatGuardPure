"""
数据存储模块 - 负责任务和报告数据的持久化
"""
import json
import os
from datetime import datetime, date, timedelta


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
            try:
                with open(self.DATA_FILE, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.data = self.DEFAULT_DATA.copy()
                self._init_default_templates()
        else:
            self.data = self.DEFAULT_DATA.copy()
            self._init_default_templates()

    def save(self):
        """保存数据"""
        try:
            with open(self.DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except IOError:
            pass

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

    def remove_task_template(self, name):
        templates = self.data.get("task_templates", [])
        self.data["task_templates"] = [t for t in templates if t["name"] != name]
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

    def increment_break(self):
        """增加一次休息记录"""
        today = self.get_today_plan()
        if "health_stats" not in today:
            today["health_stats"] = {"breaks": 0, "leaves": 0, "leave_minutes": 0, "max_focus_minutes": 0}
        today["health_stats"]["breaks"] = today["health_stats"].get("breaks", 0) + 1
        self.save_today_plan(today)

    def add_leave_minutes(self, minutes):
        """增加离开时间"""
        today = self.get_today_plan()
        if "health_stats" not in today:
            today["health_stats"] = {"breaks": 0, "leaves": 0, "leave_minutes": 0, "max_focus_minutes": 0}
        today["health_stats"]["leaves"] = today["health_stats"].get("leaves", 0) + 1
        today["health_stats"]["leave_minutes"] = today["health_stats"].get("leave_minutes", 0) + minutes
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
        jan1 = datetime(year, 1, 1)
        first_monday = jan1 - timedelta(days=jan1.weekday())
        week_start = first_monday + timedelta(weeks=week_number - 1)
        week_end = week_start + timedelta(days=6)
        return week_start.date().isoformat(), week_end.date().isoformat()

    def get_all_daily_plans(self):
        """获取所有每日计划"""
        return self.data.get("daily_plans", {})

    def get_daily_plan(self, date_str):
        """获取指定日期的计划"""
        return self.data.get("daily_plans", {}).get(date_str, {"tasks": {}, "task_order": []})
