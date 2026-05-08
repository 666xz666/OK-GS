# 3D Gaussian Splatting Web UI — Design Framework

## 概述

基于 Flask 的 Web 可视化界面，覆盖 3D Gaussian Splatting 完整流水线：训练 → VQ量化 → 评估对比 → 视频生成。

**设计原则**:
- 不修改已有代码，所有 UI 代码在 `ui/` 目录
- 直接调用已有 Python 函数，不通过 subprocess 运行 shell/py 文件
- 参数可调、路径可选，默认值与现有 shell 脚本一致
- 支持指标可视化和已有模型浏览

## 架构

```
Browser (Bootstrap 5 + Chart.js)
     │
     ├── SSE (Server-Sent Events) ─── 实时日志流
     │
     ▼
Flask App (ui/app.py)
     │
     ├── Blueprints: main / train / quantize / eval / videogen / models / tasks
     │
     ├── TaskManager (ui/task_manager.py) ─── 后台线程 + stdout/stderr 捕获
     │
     ▼
Existing Python Modules (train.py, vectree/vectree.py, render.py, etc.)
```

## 路由设计

| 路由 | 方法 | 说明 |
|---|---|---|
| `/` | GET | 流水线概览面板 |
| `/train` | GET/POST | 训练表单/启动训练 |
| `/quantize` | GET/POST | 量化表单/启动作业 |
| `/eval` | GET/POST | 评估表单/启动评估 |
| `/videogen` | GET/POST | 视频生成表单/启动 |
| `/models` | GET | 已有模型列表浏览 |
| `/models/<path>` | GET | 模型详情+指标图表 |
| `/tasks` | GET | 任务列表 |
| `/tasks/<id>/log` | GET | SSE 实时日志流 |

## 异步执行

后台线程 (threading.Thread)，每个任务重定向 stdout/stderr 到 queue.Queue，
通过 SSE (Server-Sent Events) 推送到前端实时显示。

## 参数表单

各阶段参数默认值与 `run_train.sh` / `run_quantize.sh` / `run_eval.sh` / `run_videogen.sh` 保持一致。

## 指标可视化

使用 Chart.js 展示：
- SSIM/PSNR/LPIPS 柱状图（原始 vs VQ）
- 存储空间对比（PLY vs extreme_saving.zip）
- FPS 对比
- 完整指标表格
