# 数据分析系统

这是一个前后端分离的数据分析系统：

- 前端：Vue 3 + TypeScript + Vite + Ant Design Vue
- 后端：FastAPI + SQLAlchemy
- 前后端联调方式：前端开发服务器通过 `/api` 代理到后端 `8000` 端口

## 目录结构

```text
solo/
├─ frontend/   前端项目
├─ backend/    后端项目
├─ data/       项目数据目录
└─ .venv/      Python 虚拟环境
```

## 运行环境

- Windows PowerShell
- Node.js 与 npm
- Python 3.11

## 快速启动

### 1. 启动后端

在 `solo/backend` 目录执行：

```powershell
..\.venv\Scripts\python.exe run.py
```

如果你在 `solo` 目录执行，也可以使用：

```powershell
.\.venv\Scripts\python.exe .\backend\run.py
```

后端默认监听：

- `http://127.0.0.1:8000`
- 接口文档：`http://127.0.0.1:8000/docs`

### 2. 启动前端

在 `solo/frontend` 目录执行：

```powershell
npm run dev
```

前端开发服务器默认监听：

- `http://127.0.0.1:3000`

说明：

- Vite 已在 [vite.config.ts](D:/数据分析系统/solo/frontend/vite.config.ts) 中固定为 `3000` 端口
- 前端访问 `/api` 时会自动代理到 `http://127.0.0.1:8000`

## 已验证的启动结果

当前仓库实际启动方式已经验证可用：

- 前端首页返回 `200`
- 后端 `/docs` 返回 `200`

访问地址：

- 前端：`http://127.0.0.1:3000`
- 后端：`http://127.0.0.1:8000`
- 后端文档：`http://127.0.0.1:8000/docs`

## 日志位置

如果使用后台方式启动，可将日志输出到：

- [frontend.out.log](D:/数据分析系统/solo/.runlogs/frontend.out.log)
- [frontend.err.log](D:/数据分析系统/solo/.runlogs/frontend.err.log)
- [backend.out.log](D:/数据分析系统/solo/.runlogs/backend.out.log)
- [backend.err.log](D:/数据分析系统/solo/.runlogs/backend.err.log)

## 停止服务

可通过进程 ID 停止服务：

```powershell
Stop-Process -Id <前端PID>,<后端PID>
```

如果你需要先查询 PID，可以执行：

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 3000,8000 } | Select-Object LocalPort, OwningProcess
```

## 常见问题

### 1. 前端能打开，但接口报错

优先检查后端是否已启动，并确认 `8000` 端口可访问：

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/docs
```

### 2. 端口被占用

- 前端端口固定为 `3000`
- 后端端口固定为 `8000`

如果端口冲突，需要先结束占用进程，或修改对应配置后重新启动。

## 相关入口文件

- 后端入口：[run.py](D:/数据分析系统/solo/backend/run.py)
- 后端应用：[main.py](D:/数据分析系统/solo/backend/app/main.py)
- 前端配置：[vite.config.ts](D:/数据分析系统/solo/frontend/vite.config.ts)
- 前端脚本：[package.json](D:/数据分析系统/solo/frontend/package.json)
