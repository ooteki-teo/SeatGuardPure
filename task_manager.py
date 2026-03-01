"""
任务管理模块 - 负责任务板的核心逻辑
"""
import uuid
from datetime import datetime, date
from data_store import DataStore


class TaskManager:
    """任务管理器"""

    BLOCK_DURATION_MINUTES = 25  # 一个时间块25分钟
    BLOCK_DURATION_SECONDS = 25 * 60  # 一个时间块25分钟（秒）

    def __init__(self, log_callback=None):
        self.data_store = DataStore()
        self.log_callback = log_callback

        # 当前工作状态
        self.current_task_id = None
        self.current_block_start = None
        self.is_working = False

        # === 精准计时状态 ===
        self.accumulated_seconds = 0   # 当前块已累积的工作秒数
        self.current_interruptions = 0 # 当前块被打断的次数

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)
        print(f"[TaskManager] {message}")

    # ===== 任务板操作 =====
    def get_today_tasks(self):
        """获取今日任务列表"""
        plan = self.data_store.get_today_plan()
        tasks = plan.get("tasks", {})
        task_order = plan.get("task_order", [])

        result = []
        for task_id in task_order:
            if task_id in tasks:
                result.append(tasks[task_id])
        return result

    def get_today_summary(self):
        """获取今日任务摘要"""
        tasks = self.get_today_tasks()
        if not tasks:
            return {"total": 0, "completed": 0, "in_progress": 0, "not_started": 0}

        total = len(tasks)
        completed = sum(1 for t in tasks if t["status"] == "已完成")
        in_progress = sum(1 for t in tasks if t["status"] == "进行中")
        not_started = sum(1 for t in tasks if t["status"] == "未开始")

        total_blocks = sum(t.get("estimated_blocks", 0) for t in tasks)
        completed_blocks = sum(t.get("completed_blocks", 0) for t in tasks)

        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "not_started": not_started,
            "total_blocks": total_blocks,
            "completed_blocks": completed_blocks
        }

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
            # 限制范围
            new_index = max(0, min(new_index, len(task_order)))
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
        """开始一个新任务"""
        self.current_task_id = task_id
        self.current_block_start = datetime.now()
        self.is_working = True

        # 重置计时状态
        self.accumulated_seconds = 0
        self.current_interruptions = 0

        task = self.data_store.get_task(task_id)
        if task:
            task["status"] = "进行中"
            self.data_store.update_task(task_id, task)

        self.log(f"开始任务: {task_id}")

    def complete_block(self, interruptions=None):
        """完成一个时间块并记录"""
        if not self.current_task_id:
            return

        # 如果没有传入 interruptions，使用当前块的打断次数
        if interruptions is None:
            interruptions = self.current_interruptions

        end_time = datetime.now()
        task = self.data_store.get_task(self.current_task_id)

        if task:
            # 计算实际开始时间（从当前时间往前推算）
            total_seconds = self.accumulated_seconds
            if self.current_block_start:
                current_elapsed = (datetime.now() - self.current_block_start).total_seconds()
                total_seconds += current_elapsed

            start_time = end_time.fromtimestamp(end_time.timestamp() - total_seconds)

            session = {
                "start": start_time.strftime("%H:%M"),
                "end": end_time.strftime("%H:%M"),
                "interruptions": interruptions,
                "duration_minutes": int(total_seconds / 60)
            }
            if "work_sessions" not in task:
                task["work_sessions"] = []
            task["work_sessions"].append(session)

            task["completed_blocks"] = task.get("completed_blocks", 0) + 1

            if task["completed_blocks"] >= task["estimated_blocks"]:
                task["status"] = "已完成"
                task["completed_date"] = date.today().isoformat()

            self.data_store.update_task(self.current_task_id, task)
            self.log(f"完成时间块: {task['name']} ({task['completed_blocks']}/{task['estimated_blocks']})")

        # 重置状态，准备下一个块
        self.accumulated_seconds = 0
        self.current_interruptions = 0
        if self.is_working:
            self.current_block_start = datetime.now()  # 如果还在工作状态，无缝开启下一个块
        else:
            self.current_block_start = None

    def switch_task(self, new_task_id):
        """切换任务"""
        if self.current_task_id and self.current_block_start:
            self.complete_block()

        self.start_task(new_task_id)

    def pause_work(self):
        """暂停工作 (人离开座位或进入休息状态时调用)"""
        if self.is_working and self.current_block_start:
            # 计算这次坐了多久
            elapsed = (datetime.now() - self.current_block_start).total_seconds()
            self.accumulated_seconds += elapsed
            self.current_interruptions += 1

            self.is_working = False
            self.current_block_start = None

            self.log(f"任务自动暂停，当前块已累计: {self.accumulated_seconds/60:.1f} 分钟")

    def resume_work(self):
        """恢复工作 (人回到座位时调用)"""
        if self.current_task_id and not self.is_working:
            self.current_block_start = datetime.now()
            self.is_working = True
            self.log("任务自动恢复计时")

    def check_and_update_timer(self):
        """由主循环调用：检查当前累计时间是否达到 25 分钟"""
        if not self.is_working or not self.current_block_start:
            return None

        # 计算总有效时长 = 之前暂存的累加时长 + 本次连续时长
        current_elapsed = (datetime.now() - self.current_block_start).total_seconds()
        total_active_seconds = self.accumulated_seconds + current_elapsed

        # 判断是否达到一个时间块
        if total_active_seconds >= self.BLOCK_DURATION_SECONDS:
            self.complete_block()
            # 返回任务名称，方便外面触发通知
            task = self.data_store.get_task(self.current_task_id)
            return task.get('name', '未知任务') if task else "任务"

        return None

    def get_current_task(self):
        """获取当前任务"""
        if not self.current_task_id:
            return None
        return self.data_store.get_task(self.current_task_id)

    # ===== 推荐下一个任务 =====
    def recommend_next_task(self):
        """根据时间和历史推荐下一个任务"""
        current_hour = datetime.now().hour
        tasks = self.get_today_tasks()

        unfinished = [t for t in tasks if t["status"] != "已完成"]

        if not unfinished:
            return None

        if 9 <= current_hour <= 11:
            unfinished.sort(key=lambda t: t["estimated_blocks"], reverse=True)
        elif 14 <= current_hour <= 15:
            unfinished.sort(key=lambda t: abs(t["estimated_blocks"] - 2))

        return unfinished[0] if unfinished else None

    # ===== 模板操作 =====
    def get_templates(self):
        """获取任务模板"""
        return self.data_store.get_task_templates()

    def add_template(self, name, default_blocks, category):
        """添加任务模板"""
        template = {
            "name": name,
            "default_blocks": default_blocks,
            "category": category
        }
        self.data_store.add_task_template(template)
        self.log(f"添加模板: {name}")

    def remove_template(self, name):
        """删除任务模板"""
        self.data_store.remove_task_template(name)
        self.log(f"删除模板: {name}")
