# Flask Web UI — Changelog

## 2026-05-09

### UI 现代化 — Flask Web UI 0.2.0

视觉风格全面升级，提升界面质感与交互体验。

**修改文件**:
- `ui/static/css/style.css` — 全面重写 CSS
  - 引入 CSS 自定义属性设计系统 (--primary, --radius, --shadow 等)
  - 导航栏：深靛蓝渐变背景 + 渐变文字 Logo
  - 卡片：12px 圆角、增强阴影、hover 微浮动效果 + 平滑过渡
  - 按钮：8px 圆角、渐变主色调、hover 缩放
  - 表格：圆角、大写表头、hover 高亮行
  - 仪表盘统计卡片：四色渐变（紫/绿/蓝/橙）、图标水印、hover 上浮动画
  - 全局 fadeInUp 入场动画，卡片按顺序渐次入场
  - 表单控件：聚焦时紫色光晕、滑块主题色
- `ui/translations.py` — 中文翻译全部重写
  - 去掉机翻感，语气更自然亲和
  - 导航标签更准确（"量化"→"量化压缩"，"评估"→"质量评估"）
  - 按钮文案更简洁（"开始训练"、"开始压缩"、"开始评估"）
  - 日志消息更口语化
- `ui/templates/index.html` — 仪表盘重构
  - 统计卡片改为渐变彩色卡片 + 图标
  - 两个主要区域采用更合理宽度分配 (5/7 分栏)
  - 添加 animate-in 入场动画
- `ui/templates/model_detail.html` — 模型详情页重构
  - 修复图表被压缩的问题：从 col-md-4 改为全宽，chart-container 固定最小高度
  - 画质对比表格与柱状图并排 (5/7 分栏)
  - 新增「逐视角画质曲线」：替换原有表格，使用 Chart.js 折线图展示 SSIM/PSNR/LPIPS 随视角变化
  - 渲染样张 hover 放大效果
  - 视频播放器嵌入存储卡片旁边，利用空余空间
  - 添加 section-title 左侧色条装饰
  - Badge 改为 pill 圆角形状
- `ui/static/js/charts.js` — 新增图表函数
  - `renderPerViewChart()`: 折线图，SSIM(紫色实线)/PSNR(绿色实线)/LPIPS(粉色虚线)，平滑曲线 + 半透明填充
  - `renderMetricsBarChart()` / `renderStorageChart()`: 增加圆角柱状图、点状图例
- `ui/templates/train.html` / `quantize.html` / `evaluate.html` / `videogen.html` / `models.html` / `tasks.html` — 统一使用 page-heading 标题 + animate-in 动画

**设计要点**:
- 主色调：靛蓝(#4f46e5) + 青色(#0ea5e9) 渐变体系
- 圆角体系：8px(小) / 12px(标准) / 16px(大)
- 动画：fadeInUp 0.4s ease-out，卡片按顺序延迟入场
- 零额外依赖

---

## 2026-05-08

### 中英文切换 (i18n) — Flask Web UI 0.1.1

**新增文件**:
- `ui/translations.py` — 中英文翻译字典 (~120 个翻译键) + `make_translator()` 工厂函数
- `ui/language.py` — 语言切换 Blueprint (`/set_lang/<lang>`) + Jinja2 上下文处理器，注入 `_()` 和 `current_lang`

**修改文件**:
- `ui/app.py` — 注册 `language_bp`，初始化 i18n 上下文处理器，修复 404 使用翻译
- `ui/templates/base.html` — 导航栏文本 i18n，新增语言切换按钮 (中文/EN)，注入 `window.I18N` JS 对象
- `ui/templates/index.html` — `train.html` — `quantize.html` — `evaluate.html` — `videogen.html` — `models.html` — `model_detail.html` — `tasks.html` — 全部 8 个页面模板：硬编码英文 → `{{ _('key') }}`
- `ui/static/js/app.js` — JS 字符串改用 `window.I18N` 查找
- `ui/blueprints/train.py` — `ui/blueprints/quantize.py` — `ui/blueprints/evaluate.py` — `ui/blueprints/videogen.py` — 任务创建时传入 `lang` 参数，`print()` 日志消息中文化
- `ui/task_manager.py` — 异常处理中的 `ERROR:` 前缀使用翻译

**设计**:
- 零额外依赖（仅使用 Flask 内置 session）
- 中文为默认语言（`session['lang']` 默认 `'zh'`）
- 语言偏好通过 cookie 持久化
- 后台任务的日志消息通过 `task.params['lang']` 获取当前语言

**测试结果**:
- ✅ 默认显示中文，所有 7 个路由标题正确翻译
- ✅ 切换到 English 后所有页面显示英文，导航栏出现"中文"切换链接
- ✅ 切换回中文正常
- ✅ 语言偏好跨页面保持（session cookie）
- ✅ 404 页面中英文正确显示
- ✅ `window.I18N` JS 对象中英文正确注入

---

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
