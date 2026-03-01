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
        plan = self.data_store.get_daily_plan(date_str)

        if not plan or not plan.get("tasks"):
            return self._format_empty_daily(target_date)

        tasks = plan.get("tasks", {})
        health = plan.get("health_stats", {})

        total_blocks = sum(t.get("estimated_blocks", 0) for t in tasks.values())
        completed_blocks = sum(t.get("completed_blocks", 0) for t in tasks.values())
        total_minutes = completed_blocks * 25

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

        start_date, end_date = self._get_week_range(week_number, year)

        total_minutes = 0
        total_blocks = 0
        completed_blocks = 0
        daily_data = []
        category_stats = {}

        for i in range(7):
            day = start_date + timedelta(days=i)
            date_str = day.isoformat()
            plan = self.data_store.get_daily_plan(date_str)

            if plan and plan.get("tasks"):
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

                for task in tasks.values():
                    cat = task.get("category", "其他")
                    if cat not in category_stats:
                        category_stats[cat] = 0
                    category_stats[cat] += task.get("completed_blocks", 0)

        report = {
            "week_number": week_number,
            "year": year,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_minutes": total_minutes,
            "total_blocks": total_blocks,
            "completed_blocks": completed_blocks,
            "daily_data": daily_data,
            "category_stats": category_stats
        }

        return self._format_weekly_report(week_number, year, report)

    def _calculate_efficiency(self, plan):
        """计算效率曲线"""
        sessions = []
        for task in plan.get("tasks", {}).values():
            sessions.extend(task.get("work_sessions", []))

        if not sessions:
            return []

        hour_blocks = {}
        for session in sessions:
            try:
                start_hour = int(session["start"].split(":")[0])
                if start_hour not in hour_blocks:
                    hour_blocks[start_hour] = 0
                hour_blocks[start_hour] += 1
            except (ValueError, IndexError, AttributeError):
                continue

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
        completion_rate = report["completed_blocks"] * 100 // max(report["total_blocks"], 1)

        lines = [
            f"╔════════════════════════════════════╗",
            f"║     📊 今日工作日报 ({date_str})    ║",
            f"╠════════════════════════════════════╣",
            f"║【今日概览】                          ║",
            f"║ 总工作时间: {total_hours:.1f}小时 ({report['completed_blocks']}个时间块)      ║",
            f"║ 完成进度: {completion_rate}% ({report['completed_blocks']}/{report['total_blocks']}块)           ║",
            f"║                                      ║",
            f"║【任务完成情况】                       ║",
        ]

        for task in report["tasks"]:
            name = task["name"][:12] if len(task["name"]) > 12 else task["name"]
            lines.append(f"║ {task['icon']} {name:<12} ({task['completed']}/{task['total']}块) {task['diff'][:10]:<10}║")

        lines.extend([
            f"║                                      ║",
            f"║【健康数据】                           ║",
            f"║ 休息次数: {report['health'].get('breaks', 0):<3}次                       ║",
            f"║ 离开次数: {report['health'].get('leaves', 0):<3}次 (共{report['health'].get('leave_minutes', 0):<3}分钟)      ║",
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
            f"║ 完成率: {report['completed_blocks']*100//max(report['total_blocks'],1)}%                          ║",
            f"║                                      ║",
            f"║【每日对比】                           ║",
        ]

        weekday_map = {"Mon": "周一", "Tue": "周二", "Wed": "周三",
                       "Thu": "周四", "Fri": "周五", "Sat": "周六", "Sun": "周日"}

        for day_data in report["daily_data"]:
            weekday = weekday_map.get(day_data["weekday"], day_data["weekday"])
            level = "高效" if day_data["blocks"] >= 6 else ("中等" if day_data["blocks"] >= 4 else "低效")
            bar_len = min(day_data["blocks"], 10)
            bar = "█" * bar_len + "░" * (10 - bar_len)
            lines.append(f"║ {weekday}: {day_data['blocks']:>2}块 {bar} {level:<4}  ║")

        if report["category_stats"]:
            lines.append(f"║                                      ║")
            lines.append(f"║【任务分类】                           ║")
            total_cat = sum(report["category_stats"].values())
            for cat, blocks in report["category_stats"].items():
                pct = blocks * 100 // max(total_cat, 1)
                bar_len = pct // 10
                bar = "█" * bar_len + "░" * (10 - bar_len)
                lines.append(f"║ {cat:<4}: {blocks:>2}块 {bar} {pct:>3}%  ║")

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

    def _format_empty_weekly(self, week_number):
        """格式化空周报"""
        return f"📈 本周工作周报 (第{week_number}周)\n\n暂无任务数据"

    # ===== JSON 格式报告 API =====

    def generate_daily_json(self, target_date=None):
        """生成日报 JSON 数据"""
        if target_date is None:
            target_date = date.today()

        date_str = target_date.isoformat()
        plan = self.data_store.get_daily_plan(date_str)

        if not plan or not plan.get("tasks"):
            return {
                "type": "daily",
                "date": date_str,
                "hasData": False,
                "message": "暂无任务数据"
            }

        tasks = plan.get("tasks", {})
        health = plan.get("health_stats", {})

        total_blocks = sum(t.get("estimated_blocks", 0) for t in tasks.values())
        completed_blocks = sum(t.get("completed_blocks", 0) for t in tasks.values())
        total_minutes = completed_blocks * 25
        completion_rate = completed_blocks * 100 // max(total_blocks, 1)

        task_list = []
        for task in tasks.values():
            task_diff = task.get("completed_blocks", 0) - task.get("estimated_blocks", 0)
            task_list.append({
                "id": task["id"],
                "name": task["name"],
                "category": task.get("category", "工作"),
                "completed": task.get("completed_blocks", 0),
                "total": task["estimated_blocks"],
                "status": task["status"],
                "progress": task.get("completed_blocks", 0) * 100 // max(task["estimated_blocks"], 1),
                "diff": task_diff
            })

        efficiency = self._calculate_efficiency(plan)

        return {
            "type": "daily",
            "date": date_str,
            "hasData": True,
            "summary": {
                "totalHours": round(total_minutes / 60, 1),
                "totalBlocks": total_blocks,
                "completedBlocks": completed_blocks,
                "completionRate": completion_rate
            },
            "tasks": task_list,
            "health": {
                "breaks": health.get("breaks", 0),
                "leaves": health.get("leaves", 0),
                "leaveMinutes": health.get("leave_minutes", 0)
            },
            "efficiency": efficiency
        }

    def generate_weekly_json(self, week_number=None, year=None):
        """生成周报 JSON 数据"""
        if week_number is None:
            today = date.today()
            week_number = today.isocalendar()[1]
        if year is None:
            year = date.today().year

        start_date, end_date = self._get_week_range(week_number, year)

        total_minutes = 0
        total_blocks = 0
        completed_blocks = 0
        daily_data = []
        category_stats = {}

        weekday_map = {"Mon": "周一", "Tue": "周二", "Wed": "周三",
                       "Thu": "周四", "Fri": "周五", "Sat": "周六", "Sun": "周日"}

        for i in range(7):
            day = start_date + timedelta(days=i)
            date_str = day.isoformat()
            plan = self.data_store.get_daily_plan(date_str)

            day_blocks = 0
            day_tasks = []

            if plan and plan.get("tasks"):
                tasks = plan.get("tasks", {})
                day_blocks = sum(t.get("completed_blocks", 0) for t in tasks.values())
                for task in tasks.values():
                    cat = task.get("category", "其他")
                    if cat not in category_stats:
                        category_stats[cat] = 0
                    category_stats[cat] += task.get("completed_blocks", 0)

                    day_tasks.append({
                        "name": task["name"],
                        "completed": task.get("completed_blocks", 0)
                    })

            total_blocks += sum(t.get("estimated_blocks", 0) for t in plan.get("tasks", {}).values())
            completed_blocks += day_blocks
            total_minutes += day_blocks * 25

            daily_data.append({
                "date": date_str,
                "weekday": weekday_map.get(day.strftime("%a"), day.strftime("%a")),
                "blocks": day_blocks,
                "level": "high" if day_blocks >= 6 else ("medium" if day_blocks >= 4 else "low"),
                "tasks": day_tasks
            })

        completion_rate = completed_blocks * 100 // max(total_blocks, 1)

        # 分类统计数据
        category_list = []
        total_cat = sum(category_stats.values())
        for cat, blocks in category_stats.items():
            category_list.append({
                "name": cat,
                "blocks": blocks,
                "percentage": blocks * 100 // max(total_cat, 1)
            })

        return {
            "type": "weekly",
            "weekNumber": week_number,
            "year": year,
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "hasData": completed_blocks > 0,
            "summary": {
                "totalHours": round(total_minutes / 60, 1),
                "totalBlocks": total_blocks,
                "completedBlocks": completed_blocks,
                "completionRate": completion_rate
            },
            "dailyData": daily_data,
            "categoryStats": category_list
        }
