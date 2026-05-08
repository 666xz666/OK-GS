# Flask Web UI — Changelog

## 2026-05-08

### 初始开发 — Flask Web UI 0.1.0

**新增文件**:
- `docs/flask_web_ui_design.md` — 设计框架文档
- `docs/flask_web_ui_changelog.md` — 本日志
- `ui/__init__.py`, `ui/blueprints/__init__.py`
- `ui/config.py` — 配置管理 (dataset_root, model_root, CUDA device)
- `ui/task_manager.py` — 异步任务管理器 (后台线程 + SSE)
- `ui/forms.py` — 数据集/模型扫描, argparse Namespace 构建
- `ui/app.py` — Flask 应用工厂
- `ui/blueprints/main.py` — 仪表盘 `/`
- `ui/blueprints/train.py` — 训练 `/train/`
- `ui/blueprints/quantize.py` — 量化 `/quantize/`
- `ui/blueprints/evaluate.py` — 评估 `/eval/`
- `ui/blueprints/videogen.py` — 视频生成 `/videogen/`
- `ui/blueprints/models.py` — 模型浏览 `/models/`
- `ui/blueprints/tasks.py` — 任务管理 `/tasks/`
- `ui/templates/*.html` — 9 个 Jinja2 模板 (Bootstrap 5)
- `ui/static/css/style.css`, `ui/static/js/app.js`, `ui/static/js/charts.js`

**修改文件**:
- `requirements.txt` — 新增 Flask 3.1.3 及相关依赖

**未修改**: 所有已有代码均未改动

**测试结果**:
- ✅ 所有 9 个页面返回 200
- ✅ 模型浏览器正确显示 bicycle/room 模型及指标
- ✅ 模型详情页正确显示 comparison_vq.json 的 SSIM/PSNR/LPIPS 对比表格 + Chart.js 图表
- ✅ 训练/量化/评估/视频生成表单正确加载数据集和模型下拉列表
- ✅ 任务提交 (POST) 正常工作，后台线程启动
- ✅ 静态文件 (CSS/JS) 正常服务
