"""
FastAPI 后端服务 - 为 Web 前端提供 REST API
纯久坐提醒应用，无需任务管理
"""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os
import sys
import webbrowser
import threading
import uvicorn

# 导入项目模块
from report_generator import ReportGenerator
from config import Config


# ===== Pydantic 模型 =====

class ConfigUpdate(BaseModel):
    reminder_duration: Optional[int] = None
    rest_countdown: Optional[int] = None
    screenshot_enabled: Optional[bool] = None
    detect_interval: Optional[int] = None
    away_timeout: Optional[int] = None
    check_timeout: Optional[int] = None
    max_relax_resets: Optional[int] = None


# ===== 全局状态 =====
_app_instance = None
_report_generator = None
_config = None
_log_callback = None


def init_app(report_generator: ReportGenerator, config: Config, log_callback=None):
    """初始化应用实例 - 由 main.py 调用"""
    global _report_generator, _config, _log_callback
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

    # ===== 前端页面路由 =====

    @app.get("/")
    @app.get("/settings")
    @app.get("/logs")
    @app.get("/reports")
    async def spa():
        """单页应用 - 所有页面路由返回 index.html"""
        index_path = os.path.join(web_dir, 'index.html')
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "SeatGuard API is running"}

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
            "grace_period": _config.grace_period,
            "detect_interval": _config.detect_interval,
            "away_timeout": _config.away_timeout,
            "check_timeout": _config.check_timeout,
            "max_relax_resets": _config.max_relax_resets
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
        if config_update.detect_interval is not None:
            _config.detect_interval = config_update.detect_interval
        if config_update.away_timeout is not None:
            _config.away_timeout = config_update.away_timeout
        if config_update.check_timeout is not None:
            _config.check_timeout = config_update.check_timeout
        if config_update.max_relax_resets is not None:
            _config.max_relax_resets = config_update.max_relax_resets

        _config.save()
        return {"success": True}

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
                logs = [line.strip() for line in recent_lines if line.strip()]
                return {"logs": logs}
        except Exception:
            return {"logs": []}

    # ===== 报告 API =====

    @app.get("/api/reports/daily")
    async def get_daily_report():
        """获取今日日报 JSON"""
        if _report_generator is None:
            raise HTTPException(status_code=500, detail="Report generator not initialized")
        report_data = _report_generator.generate_daily_json()
        return report_data

    @app.get("/api/reports/weekly")
    async def get_weekly_report():
        """获取本周周报 JSON"""
        if _report_generator is None:
            raise HTTPException(status_code=500, detail="Report generator not initialized")
        report_data = _report_generator.generate_weekly_json()
        return report_data

    return app


class APIServer:
    """API 服务器管理类"""

    def __init__(self, report_generator: ReportGenerator,
                 config: Config, host: str = "127.0.0.1", port: int = 8566):
        self.host = host
        self.port = port
        self.app = create_app()
        self.server = None
        self.thread = None

        # 初始化应用
        init_app(report_generator, config)

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
                    log_config=None
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
        pass

    def get_url(self, path: str = "") -> str:
        """获取 URL"""
        return f"http://{self.host}:{self.port}{path}"
