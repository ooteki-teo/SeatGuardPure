# Task Plan: SeatGuard 前端重构 - FastAPI + Web 前端

## Goal
将 SeatGuard 从 tkinter GUI 重构为 FastAPI + Web 前端架构，解决 macOS tkinter 兼容性问题，同时提升用户体验

## Phases
- [ ] Phase 1: 分析现有架构，设计前后端分离方案
- [ ] Phase 2: 创建 FastAPI 后端服务 (api_server.py)
- [ ] Phase 3: 创建 Web 前端 (web/ 目录)
- [ ] Phase 4: 修改 main.py 集成 API 服务
- [ ] Phase 5: 修改托盘菜单打开网页
- [ ] Phase 6: 测试和修复

## Key Questions
1. FastAPI 服务如何与主程序共享 TaskManager 状态？
2. 前端需要哪些页面（任务板、设置、日志、日报周报）？
3. 如何处理前后端通信（共享内存/文件 vs HTTP）？

## Decisions Made
- 使用 FastAPI 作为后端框架（轻量、异步、自带 docs）
- 前端使用纯 HTML + CSS + JavaScript（无需复杂框架）
- 通过共享 TaskManager 实例实现状态同步
- 使用固定端口 + 浏览器打开方式显示页面

## 架构设计

### 当前架构（tkinter）
```
main.py → task_gui.py (tkinter) → ~/.seat_guard_data.json
```

### 目标架构（FastAPI + Web）
```
main.py → api_server.py (FastAPI) → web/ (静态文件)
                    ↓
              TaskManager 实例共享
```

### API 端点设计
- GET  /api/tasks - 获取今日任务
- POST /api/tasks - 添加任务
- PUT  /api/tasks/{id} - 更新任务
- DELETE /api/tasks/{id} - 删除任务
- POST /api/tasks/{id}/start - 开始任务
- POST /api/tasks/{id}/complete - 完成一块
- GET  /api/status - 获取状态
- GET  /api/config - 获取配置
- PUT  /api/config - 更新配置
- GET  /api/logs - 获取日志
- GET  /api/reports/daily - 日报
- GET  /api/reports/weekly - 周报

## 页面设计
1. **任务板页面** (/tasks) - 任务列表、操作
2. **设置页面** (/settings) - 配置修改
3. **日志页面** (/logs) - 实时日志查看
4. **报告页面** (/reports) - 日报周报

## Status
**全部完成** - FastAPI + Web 前端重构已完成

## 实现的功能
1. **api_server.py** - FastAPI 后端服务
   - REST API: 任务、配置、日志、报告
   - APIServer 类管理服务器生命周期
2. **web/** - Web 前端
   - index.html - 首页/控制面板
   - tasks.html - 任务板
   - settings.html - 设置
   - logs.html - 日志
   - reports.html - 报告
3. **main.py** - 集成
   - 启动 API 服务器
   - 托盘菜单改为打开网页
4. **requirements.txt** - 添加依赖
   - fastapi, uvicorn, pydantic
