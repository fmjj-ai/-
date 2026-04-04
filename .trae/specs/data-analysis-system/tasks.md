# Tasks

- [x] Task 1: 初始化项目基础设施
  - [x] SubTask 1.1: 搭建后端 FastAPI 基础骨架（目录结构、配置、SQLite、日志、错误结构）
  - [x] SubTask 1.2: 搭建前端 Vue3+Vite+Pinia 基础骨架（路由、请求封装、Ant Design Vue 主题配置）
- [x] Task 2: 核心底座开发 - 数据集与项目管理
  - [x] SubTask 2.1: 实现项目管理的 CRUD 接口与前端页面
  - [x] SubTask 2.2: 实现文件上传、解析（CSV/Excel）与本地存储机制
  - [x] SubTask 2.3: 实现数据集快照与版本管理机制
  - [x] SubTask 2.4: 前端实现数据表格分页展示与编辑功能
- [x] Task 3: 核心底座开发 - 任务调度与导出中心
  - [x] SubTask 3.1: 后端实现基于 ProcessPoolExecutor 的异步任务调度与 SSE 进度推送
  - [x] SubTask 3.2: 前端实现全局任务中心浮层/页面
  - [x] SubTask 3.3: 后端实现导出产物管理（CSV/图表/PDF），前端实现导出中心页面
- [x] Task 4: 业务模块 - 数据处理分析
  - [x] SubTask 4.1: 后端实现数据清洗、变换（Polars/Pandas）接口
  - [x] SubTask 4.2: 前端实现数据处理交互界面与结果预览
- [x] Task 5: 业务模块 - 数据统计分析与图表系统
  - [x] SubTask 5.1: 前端集成 ECharts 5，实现 2D/3D 图表组件及主题切换
  - [x] SubTask 5.2: 后端实现基础统计算法与聚合逻辑
  - [x] SubTask 5.3: 前端实现图表渲染、交互与导出（SVG/PNG）
- [x] Task 6: 业务模块 - 情感分析
  - [x] SubTask 6.1: 后端集成 jieba 和 SnowNLP，实现分词、情感打分、关键词提取
  - [x] SubTask 6.2: 前端实现情感分析配置页、结果展示页（词云、分布图）
- [x] Task 7: 质量优化与测试
  - [x] SubTask 7.1: 前端实现防卡顿策略（视口渲染、骨架屏）
  - [x] SubTask 7.2: 按《测试方案》完成核心闭环回归测试
  - [x] SubTask 7.3: 按《审查方案》执行 5 轮自审自测并修复缺陷
- [x] Task 8: 最终验收与部署准备
  - [x] SubTask 8.1: 确保所有日志、审计追踪完善
  - [x] SubTask 8.2: 确认 P0/P1 问题清零，系统达到长期自用标准

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 2]
- [Task 4] depends on [Task 3]
- [Task 5] depends on [Task 3]
- [Task 6] depends on [Task 3]
- [Task 7] depends on [Task 4], [Task 5], [Task 6]
- [Task 8] depends on [Task 7]