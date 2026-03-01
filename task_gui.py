"""
任务图形界面模块 - 提供轻量级的 Tkinter 任务管理面板
使用 subprocess 启动独立进程避免 macOS tkinter 线程问题
"""
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import subprocess
import sys
import os
import threading


def create_gui_script():
    """创建独立的 GUI 脚本"""
    script = '''
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import sys
import os
import json

if __name__ == "__main__":
    # macOS 设置
    if sys.platform == "darwin":
        os.environ['TK_SILENCE_DEPRECATION_WARNING'] = '1'

    # 获取数据文件路径
    data_file = os.path.expanduser("~/.seat_guard_data.json")

    def load_data():
        if os.path.exists(data_file):
            with open(data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"task_templates": [], "daily_plans": {}, "history": {"weekly_reports": {}, "daily_reports": {}}}

    def save_data(data):
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    root = tk.Tk()
    root.title("SeatGuard - 今日任务管理")
    root.geometry("550x400")
    root.attributes('-topmost', True)

    data = load_data()
    today = __import__("datetime").date.today().isoformat()

    tree = None

    def get_tasks():
        plan = data.get("daily_plans", {}).get(today, {"tasks": {}, "task_order": []})
        tasks = plan.get("tasks", {})
        order = plan.get("task_order", [])
        return [tasks[tid] for tid in order if tid in tasks]

    def refresh():
        nonlocal tree
        if tree is None:
            return
        for item in tree.get_children():
            tree.delete(item)
        for t in get_tasks():
            progress = f"{t.get('completed_blocks', 0)} / {t.get('estimated_blocks', 1)}"
            tree.insert("", tk.END, values=(t['id'], t['name'], t['status'], progress))

    def get_selected():
        selected = tree.selection()
        if not selected:
            return None
        return tree.item(selected[0])['values'][0]

    def add_task():
        name = simpledialog.askstring("新增任务", "请输入任务名称：", parent=root)
        if name and name.strip():
            blocks = simpledialog.askinteger("预估时间", "预估需要几个专注块？",
                initialvalue=1, minvalue=1, maxvalue=20, parent=root)
            if blocks:
                import uuid
                task_id = f"task_{uuid.uuid4().hex[:8]}"
                task = {
                    "id": task_id,
                    "name": name.strip(),
                    "category": "工作",
                    "estimated_blocks": blocks,
                    "completed_blocks": 0,
                    "status": "未开始",
                    "work_sessions": [],
                    "notes": "",
                    "created_date": today,
                    "completed_date": None
                }
                if "daily_plans" not in data:
                    data["daily_plans"] = {}
                if today not in data["daily_plans"]:
                    data["daily_plans"][today] = {"tasks": {}, "task_order": []}
                if "tasks" not in data["daily_plans"][today]:
                    data["daily_plans"][today] = {"tasks": {}, "task_order": []}
                data["daily_plans"][today]["tasks"][task_id] = task
                data["daily_plans"][today]["task_order"].append(task_id)
                save_data(data)
                refresh()

    def delete_task():
        task_id = get_selected()
        if task_id:
            if messagebox.askyesno("确认", "确定要删除选中的任务吗？", parent=root):
                if task_id in data["daily_plans"][today]["tasks"]:
                    del data["daily_plans"][today]["tasks"][task_id]
                    if task_id in data["daily_plans"][today]["task_order"]:
                        data["daily_plans"][today]["task_order"].remove(task_id)
                    save_data(data)
                    refresh()

    def start_task():
        task_id = get_selected()
        if task_id:
            if task_id in data["daily_plans"][today]["tasks"]:
                data["daily_plans"][today]["tasks"][task_id]["status"] = "进行中"
                save_data(data)
                refresh()

    def complete_block():
        task_id = get_selected()
        if task_id:
            if task_id in data["daily_plans"][today]["tasks"]:
                task = data["daily_plans"][today]["tasks"][task_id]
                task["completed_blocks"] = task.get("completed_blocks", 0) + 1
                if task["completed_blocks"] >= task["estimated_blocks"]:
                    task["status"] = "已完成"
                else:
                    task["status"] = "进行中"
                save_data(data)
                refresh()

    # UI
    top = ttk.Frame(root)
    top.pack(fill=tk.X, padx=10, pady=10)
    ttk.Button(top, text="+ 添加任务", command=add_task).pack(side=tk.LEFT, padx=5)
    ttk.Button(top, text="+ 刷新列表", command=refresh).pack(side=tk.LEFT, padx=5)

    mid = ttk.Frame(root)
    mid.pack(fill=tk.BOTH, expand=True, padx=10)
    cols = ("id", "name", "status", "progress")
    tree = ttk.Treeview(mid, columns=cols, show="headings", selectmode="browse")
    tree.column("id", width=0, stretch=False)
    tree.column("name", width=250)
    tree.column("status", width=80)
    tree.column("progress", width=120)
    tree.heading("name", text="任务名称")
    tree.heading("status", text="状态")
    tree.heading("progress", text="进度")
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    ttk.Scrollbar(mid, orient=tk.VERTICAL, command=tree.yview).pack(side=tk.RIGHT, fill=tk.Y)
    tree.configure(yscrollcommand=lambda f, l: f)

    bot = ttk.Frame(root)
    bot.pack(fill=tk.X, padx=10, pady=10)
    ttk.Button(bot, text="开始任务", command=start_task).pack(side=tk.LEFT, padx=5)
    ttk.Button(bot, text="完成1块", command=complete_block).pack(side=tk.LEFT, padx=5)
    ttk.Button(bot, text="删除", command=delete_task).pack(side=tk.RIGHT, padx=5)

    refresh()
    root.mainloop()
'''
    return script


class TaskBoardGUI:
    """任务管理 GUI 面板"""

    def __init__(self, task_manager, notifier):
        self.task_manager = task_manager
        self.notifier = notifier

    def quick_add_task(self):
        """快速添加任务弹窗"""
        # 使用简单的通知提示用户打开面板
        self.notifier.notify(
            "添加任务",
            "请点击「任务管理面板」来添加和管理任务"
        )

    def open_board(self):
        """打开任务管理主面板"""
        # 创建临时脚本文件
        import tempfile
        import os

        script = create_gui_script()
        # 写入临时文件
        temp_dir = tempfile.gettempdir()
        script_file = os.path.join(temp_dir, 'seatguard_task_gui.py')

        with open(script_file, 'w', encoding='utf-8') as f:
            f.write(script)

        # 使用 subprocess 启动独立进程
        try:
            # 尝试使用系统 Python (更可能有 tkinter)
            subprocess.Popen([sys.executable, script_file])
        except Exception as e:
            # 如果失败，尝试使用 python3
            try:
                subprocess.Popen(['python3', script_file])
            except Exception as e2:
                self.notifier.notify("错误", f"无法打开任务面板: {e2}")

    def refresh_board(self):
        """刷新列表（预留接口）"""
        pass
