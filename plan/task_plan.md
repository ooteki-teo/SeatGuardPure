# Task Plan: SeatGuard TODO & Report Feature Implementation

## Goal
为 SeatGuard 添加 TODO 待办清单和日报周报功能，实现灵活可调的工作流管理

## Phases
- [x] Phase 1: 分析现有代码结构，设计数据模型
- [x] Phase 2: 编写详细实施方案 (implementation_plan.md)
- [x] Phase 3: 等待用户审核方案
- [x] Phase 4a: 创建 data_store.py (数据层)
- [x] Phase 4b: 创建 task_manager.py (核心逻辑)
- [x] Phase 4c: 创建 report_generator.py (报告生成)
- [x] Phase 4d: 修改 main.py (UI集成)
- [x] Phase 5: 添加 task_gui.py (任务管理 GUI)
- [x] Phase 6: 状态机联动 (无感计时)

## Key Questions
1. 如何在现有状态机基础上添加任务管理功能？
2. 数据存储使用 JSON 还是 SQLite？
3. 如何与现有托盘菜单集成？

## Decisions Made
- 初始评估：需要激活 architecture-design 和 planning-with-files 技能
- 当前状态：已完成所有功能实现

## Errors Encountered
- task_manager.py 中 add_task 方法有语法错误，已修复

## 实现的功能
1. **任务 GUI 面板** (task_gui.py)
   - 快速添加任务弹窗
   - 任务管理主面板（列表、开始、完成、删除）
2. **秒级精准计时** (task_manager.py)
   - accumulated_seconds 累加工作秒数
   - current_interruptions 记录打断次数
   - check_and_update_timer() 检测25分钟完成
3. **状态机联动** (main.py)
   - AWAY→WORK: resume_work()
   - WORK 中持续检测: check_and_update_timer()
   - WORK→RELAY: pause_work()
   - WORK→AWAY: pause_work()
   - CHECK→WORK: resume_work()

## Status
**全部完成** - FastAPI + Web 前端重构已完成（解决 tkinter macOS 兼容性问题）

## 新增功能 (Refactor)
1. **Web 控制面板** - FastAPI + 纯 HTML/CSS/JS
   - 任务板、设置、日志、报告页面
   - 托盘菜单点击打开浏览器页面
2. **保留核心能力**
   - 状态机联动（无感计时）
   - 任务管理
   - 日报周报
   - 托盘图标

## 方案文件
- [plan/implementation_plan.md](plan/implementation_plan.md) - 详细实施方案
