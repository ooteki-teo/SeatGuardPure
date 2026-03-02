"""
FastAPI 后端服务 - 为 Web 前端提供 REST API
"""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List
import os
import sys
import webbrowser
import threading
import uvicorn

# 导入项目模块
from task_manager import TaskManager
from data_store import DataStore
from report_generator import ReportGenerator
from config import Config


# ===== Pydantic 模型 =====

class TaskCreate(BaseModel):
    name: str
    estimated_blocks: int = 1
    category: str = "工作"


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    estimated_blocks: Optional[int] = None
    category: Optional[str] = None
    status: Optional[str] = None


class ConfigUpdate(BaseModel):
    reminder_duration: Optional[int] = None
    rest_countdown: Optional[int] = None
    screenshot_enabled: Optional[bool] = None


# ===== 全局状态 =====
# 这些将由 main.py 注入
_app_instance = None
_task_manager = None
_report_generator = None
_config = None
_log_callback = None


def init_app(task_manager: TaskManager, report_generator: ReportGenerator, config: Config, log_callback=None):
    """初始化应用实例 - 由 main.py 调用"""
    global _task_manager, _report_generator, _config, _log_callback
    _task_manager = task_manager
    _report_generator = report_generator
    _config = config
    _log_callback = log_callback


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(title="SeatGuard API", version="1.0.0")

    # 获取 web 目录的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 打包后资源在 _MEIPASS 目录中
    if hasattr(sys, '_MEIPASS'):
        current_dir = sys._MEIPASS

    web_dir = os.path.join(current_dir, 'web')

    # 挂载静态文件目录
    if os.path.exists(web_dir):
        app.mount("/static", StaticFiles(directory=web_dir), name="static")

    # ===== 前端页面路由 (SPA - 所有路由返回 index.html) =====

    @app.get("/")
    @app.get("/tasks")
    @app.get("/settings")
    @app.get("/logs")
    @app.get("/reports")
    async def spa():
        """单页应用 - 所有页面路由返回 index.html"""
        index_path = os.path.join(web_dir, 'index.html')
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "SeatGuard API is running", "docs": "/docs"}

    # ===== 任务 API =====

    @app.get("/api/tasks")
    async def get_tasks():
        """获取今日任务列表"""
        if _task_manager is None:
            raise HTTPException(status_code=500, detail="Task manager not initialized")
        return _task_manager.get_today_tasks()

    @app.get("/api/tasks/summary")
    async def get_tasks_summary():
        """获取任务摘要"""
        if _task_manager is None:
            raise HTTPException(status_code=500, detail="Task manager not initialized")
        return _task_manager.get_today_summary()

    @app.post("/api/tasks")
    async def create_task(task: TaskCreate):
        """创建新任务"""
        if _task_manager is None:
            raise HTTPException(status_code=500, detail="Task manager not initialized")
        new_task = _task_manager.add_task(
            name=task.name,
            estimated_blocks=task.estimated_blocks,
            category=task.category
        )
        return new_task

    @app.put("/api/tasks/{task_id}")
    async def update_task(task_id: str, task: TaskUpdate):
        """更新任务"""
        if _task_manager is None:
            raise HTTPException(status_code=500, detail="Task manager not initialized")
        _task_manager.edit_task(
            task_id,
            name=task.name,
            estimated_blocks=task.estimated_blocks,
            category=task.category
        )
        return {"success": True}

    @app.delete("/api/tasks/{task_id}")
    async def delete_task(task_id: str):
        """删除任务"""
        if _task_manager is None:
            raise HTTPException(status_code=500, detail="Task manager not initialized")
        _task_manager.delete_task(task_id)
        return {"success": True}

    @app.post("/api/tasks/{task_id}/start")
    async def start_task(task_id: str):
        """开始任务"""
        if _task_manager is None:
            raise HTTPException(status_code=500, detail="Task manager not initialized")
        _task_manager.start_task(task_id)
        return {"success": True}

    @app.post("/api/tasks/{task_id}/complete")
    async def complete_block(task_id: str):
        """完成任务一块"""
        if _task_manager is None:
            raise HTTPException(status_code=500, detail="Task manager not initialized")
        _task_manager.start_task(task_id)  # 确保当前任务正确
        _task_manager.complete_block()
        return {"success": True}

    @app.get("/api/tasks/current")
    async def get_current_task():
        """获取当前进行中的任务"""
        if _task_manager is None:
            raise HTTPException(status_code=500, detail="Task manager not initialized")
        return _task_manager.get_current_task()

    @app.get("/api/tasks/templates")
    async def get_templates():
        """获取任务模板"""
        if _task_manager is None:
            raise HTTPException(status_code=500, detail="Task manager not initialized")
        return _task_manager.get_templates()

    # ===== 配置 API =====

    @app.get("/api/config")
    async def get_config():
        """获取配置"""
        if _config is None:
            raise HTTPException(status_code=500, detail="Config not initialized")
        return {
            "reminder_duration": _config.reminder_duration,
            "rest_countdown": _config.rest_countdown,
            "rest_reminder_interval": _config.rest_reminder_interval,
            "screenshot_enabled": _config.screenshot_enabled,
            "grace_period": _config.grace_period
        }

    @app.put("/api/config")
    async def update_config(config_update: ConfigUpdate):
        """更新配置"""
        if _config is None:
            raise HTTPException(status_code=500, detail="Config not initialized")

        if config_update.reminder_duration is not None:
            _config.reminder_duration = config_update.reminder_duration
        if config_update.rest_countdown is not None:
            _config.rest_countdown = config_update.rest_countdown
        if config_update.screenshot_enabled is not None:
            _config.screenshot_enabled = config_update.screenshot_enabled

        # 保存配置
        _config.save()
        return {"success": True}

    # ===== 状态 API =====

    @app.get("/api/status")
    async def get_status():
        """获取当前状态"""
        if _task_manager is None or _config is None:
            raise HTTPException(status_code=500, detail="Not initialized")

        # 计算当前任务进度
        current_task = _task_manager.get_current_task()
        timer_info = {}

        if current_task and _task_manager.is_working:
            # 计算当前块已用时间
            from datetime import datetime
            if _task_manager.current_block_start:
                elapsed = (datetime.now() - _task_manager.current_block_start).total_seconds()
                total_elapsed = _task_manager.accumulated_seconds + elapsed
                remaining = _task_manager.BLOCK_DURATION_SECONDS - total_elapsed
                timer_info = {
                    "is_working": True,
                    "current_task": current_task,
                    "elapsed_seconds": int(total_elapsed),
                    "remaining_seconds": int(remaining) if remaining > 0 else 0,
                    "interruptions": _task_manager.current_interruptions
                }
            else:
                timer_info = {
                    "is_working": False,
                    "current_task": current_task,
                    "accumulated_seconds": int(_task_manager.accumulated_seconds)
                }
        else:
            timer_info = {"is_working": False}

        return {
            "task_timer": timer_info,
            "summary": _task_manager.get_today_summary()
        }

    # ===== 日志 API =====

    @app.get("/api/logs")
    async def get_logs(lines: int = 100):
        """获取最近的日志"""
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'seat_guard.log')
        if not os.path.exists(log_file):
            return {"logs": []}

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:]
                # 解析日志行
                logs = []
                for line in recent_lines:
                    line = line.strip()
                    if line:
                        logs.append(line)
                return {"logs": logs}
        except Exception:
            return {"logs": []}

    # ===== 报告 API =====

    @app.get("/api/reports/daily")
    async def get_daily_report():
        """获取今日日报 JSON"""
        if _report_generator is None:
            raise HTTPException(status_code=500, detail="Report generator not initialized")
        # 返回 JSON 格式的原始数据
        report_data = _report_generator.generate_daily_json()
        return report_data

    @app.get("/api/reports/weekly")
    async def get_weekly_report():
        """获取本周周报 JSON"""
        if _report_generator is None:
            raise HTTPException(status_code=500, detail="Report generator not initialized")
        # 返回 JSON 格式的原始数据
        report_data = _report_generator.generate_weekly_json()
        return report_data

    return app


class APIServer:
    """API 服务器管理类"""

    def __init__(self, task_manager: TaskManager, report_generator: ReportGenerator,
                 config: Config, host: str = "127.0.0.1", port: int = 8566):
        self.host = host
        self.port = port
        self.app = create_app()
        self.server = None
        self.thread = None

        # 初始化应用
        init_app(task_manager, report_generator, config)

    def start(self, open_browser: bool = False):
        """启动 API 服务器"""
        if self.thread is not None:
            return  # 已经在运行

        import logging
        import asyncio
        logger = logging.getLogger(__name__)

        def run_server():
            try:
                # 配置 uvicorn 日志
                uvicorn_logger = logging.getLogger("uvicorn")
                uvicorn_logger.setLevel(logging.WARNING)

                # 使用 asyncio 运行 uvicorn
                config = uvicorn.Config(
                    self.app,
                    host=self.host,
                    port=self.port,
                    log_level="warning",
                    access_log=False,
                    use_colors=False,
                    log_config=None  # 阻止 uvicorn 挂载 sys.stdout
                )
                server = uvicorn.Server(config)

                # 获取事件循环并运行
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(server.serve())
            except Exception as e:
                logger.error(f"API 服务器启动失败: {e}")

        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()

        # 等待服务器启动
        import time
        time.sleep(1)

        if open_browser:
            self.open_browser()

    def open_browser(self, path: str = "/"):
        """打开浏览器"""
        url = f"http://{self.host}:{self.port}{path}"
        threading.Thread(target=lambda: webbrowser.open(url), daemon=True).start()

    def stop(self):
        """停止服务器"""
        # uvicorn 需要特殊方式停止，这里简化为设置标志
        pass

    def get_url(self, path: str = "") -> str:
        """获取 URL"""
        return f"http://{self.host}:{self.port}{path}"
