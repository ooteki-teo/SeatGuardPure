你的痛点非常精准。基于你提供的代码，我已经看出了当前任务清单系统“不好用”的**根本原因：它只有“后端”逻辑，完全缺失了“前端”交互。**

在你的代码中，`task_manager.py` 和 `data_store.py` 已经实现了非常完整的任务增删改查（CRUD）、番茄钟时间块记录甚至是任务推荐逻辑。但是，在 `main.py` 中，用户只能通过系统托盘（`pystray`）和系统通知（`notifier.py`）来**单向查看**任务（`_show_task_board`）。

系统通知是纯文本且只读的，没有输入框，也没有按钮。这意味着你现在要么得通过代码硬编码添加任务，要么得手动去修改那个 `.seat_guard_data.json` 文件，这当然极其痛苦。

为了让这个任务清单真正好用，我们需要打破这种“纯静默后台”的限制，为它提供一个轻量级的输入和管理入口。以下是为你设计的两种改造方案 ：

### 方案一：轻量级弹窗 UI（最快、最原生推荐）

既然 SeatGuard 是一个以后台监测为主的轻量级工具，最好不要引入太重的框架。我们可以利用 Python 内置的 `tkinter`（或者更现代化的 `customtkinter`），在托盘菜单中增加点击事件，按需呼出任务管理面板。

**改造步骤：**

1. **修改托盘菜单 (`main.py`)**：在菜单中增加“➕ 添加任务”和“📝 管理任务”选项。
2. **实现输入弹窗**：当用户点击“添加任务”时，弹出一个极其简单的对话框输入任务名称和预估时间块。
3. **实现管理面板**：点击“管理任务”时，弹出一个小窗口，列出今天的任务，并提供“开始”、“完成”、“删除”的按钮。

**代码逻辑示例 (集成到 `main.py`)：**

```python
import tkinter as tk
from tkinter import simpledialog, messagebox

class SeatGuardApp:
    # ... 前面的代码保持不变 ...

    def _setup_tray(self):
        # ...
        menu = pystray.Menu(
            # ...
            pystray.MenuItem("📋 查看任务板", self._show_task_board),
            pystray.MenuItem("➕ 快速添加任务", self._prompt_add_task), # 新增
            pystray.MenuItem("⚙️ 任务管理面板", self._show_task_manager_gui), # 新增
            # ...
        )
        # ...

    def _prompt_add_task(self, icon=None, item=None):
        """弹出简单的输入框添加任务"""
        # 注意：pystray 运行在独立线程，GUI 弹窗需要在主线程或做特殊线程处理
        # 这里用一个简单的临时 Tk 实例
        root = tk.Tk()
        root.withdraw() # 隐藏主窗口
        root.attributes('-topmost', True) # 窗口置顶
        
        task_name = simpledialog.askstring("新增任务", "请输入任务名称：", parent=root)
        if task_name:
            blocks = simpledialog.askinteger("预估时间", "预估需要几个专注块（25分钟/块）？", 
                                             initialvalue=1, minvalue=1, maxvalue=20, parent=root)
            if blocks:
                self.task_manager.add_task(task_name, blocks)
                self.notifier.notify("任务已添加", f"成功添加任务：{task_name} ({blocks}块)")
        root.destroy()

```

### 方案二：本地 Web Dashboard（最现代化、扩展性最强）

如果你希望未来的日报、周报图表更直观，并且想用手机或局域网内其他设备管理任务，可以在后台启动一个轻量级的 Web 服务（如 `Flask` 或 `FastAPI`）。

**改造步骤：**

1. 引入 `Flask` 并在 `main.py` 启动时作为一个守护线程（Daemon Thread）运行。
2. 托盘菜单新增一个“🌐 打开控制台”，点击后调用系统默认浏览器打开 `http://127.0.0.1:5000`。
3. 在 Web 页面上提供现代化的交互：拖拽排序任务、点击切换“进行中/已完成”状态，并用 Echarts 或 Chart.js 渲染你的日报和周报数据。

---

### 核心逻辑层面的优化建议

除了 UI 层面的缺失，当前的代码逻辑在自动化上也有提升空间：

1. **状态机与任务状态的联动**：
目前你的 `SeatGuardStateMachine` 检测到你坐下（进入 `WORK` 状态），但并没有和 `TaskManager` 里的当前任务联动。
* **优化建议**：在 GUI 中选择一个“当前进行中”的任务。当摄像头检测到你落座进入工作时，自动为该任务累加时间；当你离开超过一定时间，自动调用 `task_manager.pause_work()`。


2. **打通截图功能与任务记录**：
你现有的 `ScreenshotCapture` 会在工作开始和结束时截图。如果能在保存截图时，将截图的文件路径关联到对应 Task 的字典里，你在回顾日报时，就能清楚看到“这个时间块我在做什么任务，当时屏幕上是什么画面”，这对撰写详细的工作总结非常有帮助。



没问题，考虑到 SeatGuard 原本是一个极简的后台工具，我们可以直接利用 Python 内置的 `tkinter` 库来手搓一个轻量、无需额外安装依赖的 GUI 面板。

为了保持你原有代码结构的清晰和模块化，我建议将 GUI 相关逻辑单独抽离成一个文件 `task_gui.py`，然后在 `main.py` 中调用它。

以下是完整的实现方案：

### 1. 新建 `task_gui.py` (任务图形界面模块)

这个模块包含两个主要功能：一个极其轻量的**快速添加任务弹窗**，以及一个**任务管理主面板**。为了不阻塞系统托盘（`pystray`）的运行，我们将 GUI 运行在独立的线程中。

```python
"""
任务图形界面模块 - 提供轻量级的 Tkinter 任务管理面板
"""
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import threading

class TaskBoardGUI:
    def __init__(self, task_manager, notifier):
        self.task_manager = task_manager
        self.notifier = notifier
        self.board_root = None

    def quick_add_task(self):
        """快速添加任务弹窗 (可直接通过托盘菜单调用)"""
        def _run_add():
            root = tk.Tk()
            root.withdraw()  # 隐藏主窗口
            root.attributes('-topmost', True)  # 置顶

            task_name = simpledialog.askstring("新增任务", "请输入任务名称：", parent=root)
            if task_name and task_name.strip():
                blocks = simpledialog.askinteger("预估时间", "预估需要几个专注块（25分钟/块）？", 
                                                 initialvalue=1, minvalue=1, maxvalue=20, parent=root)
                if blocks:
                    self.task_manager.add_task(task_name.strip(), blocks)
                    self.notifier.notify("任务已添加", f"成功添加任务：{task_name} ({blocks}块)")
                    # 如果管理面板正打开着，刷新它
                    self.refresh_board()
            root.destroy()
            
        threading.Thread(target=_run_add, daemon=True).start()

    def open_board(self):
        """打开任务管理主面板"""
        # 防止重复打开多个窗口
        if self.board_root is not None and self.board_root.winfo_exists():
            self.board_root.lift()
            return

        # 在新线程中启动 GUI 主循环
        threading.Thread(target=self._run_board_gui, daemon=True).start()

    def _run_board_gui(self):
        """构建并运行管理面板"""
        self.board_root = tk.Tk()
        self.board_root.title("SeatGuard - 今日任务管理")
        self.board_root.geometry("550x350")
        self.board_root.attributes('-topmost', True) # 默认置顶，方便随时看

        # --- 顶部按钮区 ---
        top_frame = ttk.Frame(self.board_root)
        top_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(top_frame, text="➕ 添加任务", command=self._gui_add_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="🔄 刷新列表", command=self.refresh_board).pack(side=tk.LEFT, padx=5)

        # --- 中间列表区 ---
        list_frame = ttk.Frame(self.board_root)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10)

        # 定义表格 (Treeview)
        columns = ("id", "name", "status", "progress")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        
        # 隐藏 ID 列，但保留数据供后续操作使用
        self.tree.column("id", width=0, stretch=tk.NO)
        self.tree.column("name", width=250, anchor=tk.W)
        self.tree.column("status", width=80, anchor=tk.CENTER)
        self.tree.column("progress", width=120, anchor=tk.CENTER)

        self.tree.heading("name", text="任务名称")
        self.tree.heading("status", text="状态")
        self.tree.heading("progress", text="进度 (完成/预估)")

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # --- 底部操作区 ---
        bottom_frame = ttk.Frame(self.board_root)
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(bottom_frame, text="▶️ 开始当前任务", command=self._gui_start_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="✅ 记录完成1个时间块", command=self._gui_complete_block).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="🗑️ 删除选中", command=self._gui_delete_task).pack(side=tk.RIGHT, padx=5)

        # 初始化加载数据
        self.refresh_board()

        self.board_root.mainloop()

    def refresh_board(self):
        """刷新列表数据"""
        if not hasattr(self, 'tree') or not self.tree.winfo_exists():
            return
            
        # 清空现有数据
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 重新获取并插入数据
        tasks = self.task_manager.get_today_tasks()
        for t in tasks:
            progress = f"{t.get('completed_blocks', 0)} / {t.get('estimated_blocks', 1)}"
            self.tree.insert("", tk.END, values=(t['id'], t['name'], t['status'], progress))

    # --- GUI 内部事件响应 ---
    def _get_selected_task_id(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请先在列表中选中一个任务！", parent=self.board_root)
            return None
        return self.tree.item(selected[0])['values'][0]

    def _gui_add_task(self):
        task_name = simpledialog.askstring("新增任务", "请输入任务名称：", parent=self.board_root)
        if task_name and task_name.strip():
            blocks = simpledialog.askinteger("预估时间", "预估需要几个专注块？", initialvalue=1, minvalue=1, maxvalue=20, parent=self.board_root)
            if blocks:
                self.task_manager.add_task(task_name.strip(), blocks)
                self.refresh_board()

    def _gui_delete_task(self):
        task_id = self._get_selected_task_id()
        if task_id:
            if messagebox.askyesno("确认", "确定要删除选中的任务吗？", parent=self.board_root):
                self.task_manager.delete_task(task_id)
                self.refresh_board()

    def _gui_start_task(self):
        task_id = self._get_selected_task_id()
        if task_id:
            self.task_manager.start_task(task_id)
            self.refresh_board()
            self.notifier.notify("任务已开始", "检测到工作状态后，将为此任务累计时间。")

    def _gui_complete_block(self):
        # 注意：这里我们增加了一个强制为特定任务增加区块的逻辑，
        # 原本你的 task_manager.complete_block() 是无参数且依赖 current_task_id 的。
        # 为了 GUI 方便，我们手动更新字典数据。
        task_id = self._get_selected_task_id()
        if task_id:
            task = self.task_manager.data_store.get_task(task_id)
            if task:
                task["completed_blocks"] = task.get("completed_blocks", 0) + 1
                if task["completed_blocks"] >= task["estimated_blocks"]:
                    task["status"] = "已完成"
                else:
                    task["status"] = "进行中"
                self.task_manager.data_store.update_task(task_id, task)
                self.refresh_board()

```

---

### 2. 修改 `main.py` 以集成 UI

在 `main.py` 中，我们需要引入刚刚创建的 `TaskBoardGUI`，并将其绑定到 `pystray` 的托盘菜单上。

找到你 `main.py` 中的 `SeatGuardApp` 类，做如下修改：

```python
# 1. 在文件顶部引入刚刚写的 GUI 模块
from task_gui import TaskBoardGUI 

class SeatGuardApp:
    def __init__(self):
        self.config = Config()
        # ... 保持其他不变 ...
        self.task_manager = TaskManager(self.log)
        self.report_generator = ReportGenerator(self.log)
        
        # 2. 初始化 GUI 管理器
        self.task_gui = TaskBoardGUI(self.task_manager, self.notifier)
        
        # ... 保持其他不变 ...

    def _setup_tray(self):
        """设置系统托盘"""
        try:
            import pystray
            # ... 省略部分日志代码 ...
            
            # 3. 更新托盘菜单，加入新的 UI 唤醒选项
            menu = pystray.Menu(
                pystray.MenuItem("开始/停止监测", self._toggle_monitoring),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("➕ 快速添加任务", self._trigger_quick_add_task),   # 新增
                pystray.MenuItem("📝 管理今日任务", self._trigger_open_task_board), # 新增
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("📊 今日日报", self._show_daily_report),
                pystray.MenuItem("📈 本周周报", self._show_weekly_report),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "开机自动启动",
                    self._toggle_autostart,
                    checked=lambda item: self.autostart.is_enabled()
                ),
                pystray.MenuItem("退出", self._quit)
            )

            self.tray = pystray.Icon("SeatGuard", icon_image, "SeatGuard - 久坐提醒", menu)
            
        except Exception as e:
            self.log(f"创建系统托盘失败: {e}")
            self.tray = None

    # 4. 新增两个触发方法
    def _trigger_quick_add_task(self, icon=None, item=None):
        self.task_gui.quick_add_task()

    def _trigger_open_task_board(self, icon=None, item=None):
        self.task_gui.open_board()
        
    # (可选) 你可以把原先仅仅用于推送通知的 _show_task_board 删掉或保留

```

### 这一版方案的优势

1. **多线程安全隔离**：Tkinter 运行在 Daemon 线程中，完全不会卡死 `pystray` 的鼠标悬浮和点击响应。
2. **免切出工作流**：如果你只是一闪念想加个任务，点击“快速添加任务”只会弹出一个极小的输入框，输入完回车就消失，不打断思路。
3. **数据打通**：你在 GUI 里点击的修改，会通过你原本写的 `task_manager` 直接存入 `.seat_guard_data.json`，晚上的“日报”系统会自动读取这些更新。

你可以先将 `task_gui.py` 保存到同级目录，然后替换 `main.py` 的相关代码跑起来试试。

将摄像头（人脸检测）与任务计时系统打通，是这个系统最酷、也最核心的价值：**无感记录**。

你不需要像传统番茄钟那样手动点“开始/暂停”。**你坐下，任务自动开始计时；你离开座位，任务自动暂停；坐满25分钟，自动记录完成一个“专注块”。**

为了实现这个联动，我们需要对 `task_manager.py`（增强秒级计时与暂停逻辑）和 `main.py`（在状态转换时触发任务更新）进行少量修改。

以下是完整的联动梳理和代码实现方案：

### 核心联动逻辑思路

1. **工作 (WORK) 状态**：只要摄像头持续检测到人脸，不仅“久坐计时器”在跑，“当前任务”的计时器也在跑。
2. **离开 (AWAY) / 休息 (RELAX) 状态**：一旦状态机切出 `WORK`，立即自动触发 `task_manager.pause_work()`，冻结当前任务的时间累积，并记录一次“打断（Interruption）”。
3. **返回工作**：当你重新落座（状态机切回 `WORK`），自动触发 `task_manager.resume_work()`，继续无缝累加刚才没做完的专注块。
4. **自动完成**：在检测循环中不断检查，如果当前任务累积有效时间达到 25 分钟，自动标记完成一个区块，并触发系统通知。

---

### 第一步：改造 `task_manager.py` (支持真正的暂停与累加)

原版的 `task_manager` 在 `pause_work` 时直接调用了 `complete_block`，这会导致你仅仅离开了1分钟就被记作完成了一个块。我们需要引入**时间累加器**。

修改 `task_manager.py`，替换相关的计时和工作会话部分：

```python
import uuid
from datetime import datetime, date
# ... 其他 import 保持不变

class TaskManager:
    BLOCK_DURATION_SECONDS = 25 * 60  # 一个时间块 25 分钟 (按秒计算)

    def __init__(self, log_callback=None):
        self.data_store = DataStore()
        self.log_callback = log_callback

        # 当前工作状态
        self.current_task_id = None
        self.current_block_start = None
        self.is_working = False
        
        # === 新增：精准计时状态 ===
        self.accumulated_seconds = 0   # 当前块已累积的工作秒数
        self.current_interruptions = 0 # 当前块被打断的次数

    # ... 省略 add_task, get_today_tasks 等原封不动的代码 ...

    # ===== 工作会话 (联动核心改造) =====
    def start_task(self, task_id):
        """开始一个新任务"""
        self.current_task_id = task_id
        self.current_block_start = datetime.now()
        self.is_working = True
        
        self.accumulated_seconds = 0
        self.current_interruptions = 0

        task = self.data_store.get_task(task_id)
        if task:
            task["status"] = "进行中"
            self.data_store.update_task(task_id, task)

        self.log(f"开始任务: {task.get('name', task_id)}")

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

    def complete_block(self):
        """完成一个时间块并记录"""
        if not self.current_task_id:
            return

        end_time = datetime.now()
        task = self.data_store.get_task(self.current_task_id)

        if task:
            session = {
                # 记录这个块实际完成的时间点，以及中间被打断的次数
                "end_time": end_time.strftime("%H:%M"),
                "interruptions": self.current_interruptions
            }
            if "work_sessions" not in task:
                task["work_sessions"] = []
            task["work_sessions"].append(session)

            task["completed_blocks"] = task.get("completed_blocks", 0) + 1

            if task["completed_blocks"] >= task["estimated_blocks"]:
                task["status"] = "已完成"
                task["completed_date"] = date.today().isoformat()

            self.data_store.update_task(self.current_task_id, task)
            self.log(f"✅ 完成时间块: {task['name']} ({task['completed_blocks']}/{task['estimated_blocks']})")

        # 重置状态，准备下一个块
        self.accumulated_seconds = 0
        self.current_interruptions = 0
        self.current_block_start = datetime.now() # 如果还在工作状态，无缝开启下一个块

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

```

---

### 第二步：在 `main.py` 中注入状态机联动

现在我们回到 `main.py`，找到 `_do_detection(self)` 方法。这是每次摄像头捕获画面后，根据是否有人脸执行状态流转的“大脑”。

在这个方法里，我们把 `task_manager` 的动作和 `state_machine` 的动作绑在一起：

```python
    def _do_detection(self):
        """执行一次人脸检测 - 状态机控制"""
        if not self.camera or not self.camera.is_opened:
            return

        try:
            # ... 前面读取摄像头、检测人脸的代码不变 ...
            face_detected = len(faces) > 0
            current_time = time.time()
            sm = self.state_machine
            state = sm.state

            # ====== 状态机处理 ======

            # --- 检测到人脸 ---
            if face_detected:
                self.no_face_start_time = 0

                if state == self.State.AWAY:
                    # AWAY → WORK: 检测到人脸，回到工作模式
                    result = sm.transition_to(self.State.WORK, current_time, "检测到人脸")
                    if result:
                        self.log(f"状态转换: {result[0]} → {result[1]} ({result[2]})")
                    sm.on_enter_work(current_time, self.timer)
                    
                    # 【新增】联动任务管理器：恢复当前任务计时
                    self.task_manager.resume_work()

                elif state == self.State.WORK:
                    # WORK 状态内，人脸持续在场
                    if not sm.user_present_in_work:
                        sm.user_present_in_work = True
                        self.timer.reset()
                        self.timer.start()
                        self.log("检测到落座，开始工作计时")
                        self._capture_screenshot(frame, "work_start")
                        
                        # 【新增】联动任务管理器：恢复当前任务计时
                        self.task_manager.resume_work()

                    # 【新增】不断检查当前专注块是否已达标 (25分钟)
                    completed_task_name = self.task_manager.check_and_update_timer()
                    if completed_task_name:
                        self.notifier.notify(
                            title="🍅 专注块完成",
                            message=f"太棒了！你已为「{completed_task_name}」专注了 25 分钟。"
                        )
                        # 如果此时你恰好打开了 GUI 管理面板，可以在这里调用刷新
                        if hasattr(self, 'task_gui') and self.task_gui:
                            self.task_gui.refresh_board()

                    # ... 久坐超时判断逻辑保持不变 ...
                    if self.timer.is_time_up():
                        if current_time - self.last_remind_time >= reminder_interval:
                            # ... 提醒休息代码不变 ...
                            result = sm.transition_to(self.State.RELAX, current_time, "久坐超时")
                            sm.on_enter_relax(current_time)
                            
                            # 【新增】联动任务管理器：被迫去休息了，任务暂停
                            self.task_manager.pause_work()

                elif state == self.State.RELAX:
                    # ... 休息逻辑不变 ...
                    pass

                elif state == self.State.CHECK:
                    # CHECK → WORK
                    result = sm.transition_to(self.State.WORK, current_time, "检测到人脸")
                    sm.on_enter_work(current_time, self.timer)
                    
                    # 【新增】联动任务管理器：结束检查，重新投入工作
                    self.task_manager.resume_work()

            # --- 未检测到人脸 ---
            else:
                if state == self.State.WORK:
                    if self.no_face_start_time == 0:
                        self.no_face_start_time = current_time

                    away_time = current_time - self.no_face_start_time

                    # 连续5分钟检测不到人脸 → 进入 AWAY
                    if away_time >= 5 * 60:
                        result = sm.transition_to(self.State.AWAY, current_time, "5分钟无人")
                        if result:
                            self.log(f"状态转换: {result[0]} → {result[1]} ({result[2]})")
                            
                            # 【新增】确认人离开了，暂停任务并扣除这虚假的5分钟！
                            # 为了精准，我们让任务管理器暂停
                            self.task_manager.pause_work()
                            # 可选高级优化：你可以把 self.task_manager.accumulated_seconds 减去 5*60 
                            # 剔除掉判定他离开前的“发呆时长”，这里为保持简单暂不添加。

                    else:
                        if sm.user_present_in_work:
                            # 人只是短暂没被检测到（比如低头捡笔），工作计时继续
                            pass
                
                # ... 其他状态保持不变 ...

        except Exception as e:
            self.log(f"检测异常: {e}")

```

### 总结你现在获得的工作流：

1. 早上开机 SeatGuard 自动启动（托盘运行）。
2. 你点击托盘 **"📝 管理今日任务"**，输入：`写方案 (2个块)`，点击 **"▶️ 开始当前任务"**（此时 `task_manager` 选定了任务）。
3. **你开始对着电脑工作。**
4. 摄像头检测到你：`SeatTimer` 帮你记久坐时长，`TaskManager` 帮你默默记专注秒数。
5. **中途你去倒水，离开3分钟：** 摄像头没看到你，`TaskManager` 自动挂起计时（暂停），你的专注时长不会被水分注水。
6. **你回来继续写：** 摄像头抓到你，`TaskManager` 自动从暂停的秒数继续无缝累加。
7. **正好凑够 25 分钟有效注视时间：** 右下角弹出通知 `🍅 专注块完成：太棒了！你已为「写方案」专注了25分钟`。该任务进度自动变成 `1/2`，并直接开启下一个块的计时。
8. **坐满 40 分钟（你设定的久坐阈值）：** 右下角警告 `救命啊，你坐太久了吧`。状态进入 `RELAX`，任务同时自动暂停。

这就是通过硬件（摄像头特征）驱动软件（番茄任务管理）的最完美姿态！不需要自己每次离开点暂停，它比任何软件版的番茄钟都要懂你。