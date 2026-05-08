# 3D Gaussian Splatting — 项目文件树 & 部署运行指南

## 项目文件树

```
gaussian-splatting/                          # 项目根目录 (/data/project/GS/gaussian-splatting)
│
├── docs/                                    # 文档
│   ├── project_overview.md                  #   项目概述（流水线、模块、参数表）
│   ├── flask_web_ui_design.md               #   Flask Web UI 设计框架
│   ├── flask_web_ui_changelog.md            #   Web UI 开发日志
│   └── deployment.md                        #   本文件：文件树 & 部署指南
│
├── arguments/
│   └── __init__.py                          #   参数组定义 (ModelParams/PipelineParams/OptimizationParams)
│
├── scene/                                   # 场景模块
│   ├── __init__.py                          #   Scene 类（加载数据集、相机、高斯模型）
│   ├── cameras.py                           #   相机类型定义
│   ├── colmap_loader.py                     #   COLMAP 数据读取
│   ├── dataset_readers.py                   #   多格式数据集读取（Colmap/Blender）
│   └── gaussian_model.py                    #   GaussianModel（3D高斯参数管理 + VQ 加载）
│
├── gaussian_renderer/                       # CUDA 渲染器
│   ├── __init__.py                          #   render() / count_render() 入口
│   ├── gaussian_count.py                    #   f_count 模式（用于重要性分数计算）
│   └── network_gui.py                       #   TCP GUI 服务器（SIBR 实时预览）
│
├── utils/                                   # 工具函数
│   ├── camera_utils.py                      #   相机工具
│   ├── elbo.py                              #   ELBO 自适应早停
│   ├── general_utils.py                     #   safe_state（随机种子）
│   ├── graphics_utils.py                    #   图形工具
│   ├── image_utils.py                       #   图像工具
│   ├── loss_utils.py                        #   损失函数（l1, ssim）
│   ├── make_depth_scale.py                  #   深度尺度计算
│   ├── pose_utils.py                        #   相机轨迹生成（椭圆/圆形/螺旋）
│   ├── read_write_model.py                  #   COLMAP 模型 I/O
│   ├── sh_utils.py                          #   球谐函数工具
│   └── system_utils.py                      #   系统工具（searchForMaxIteration）
│
├── vectree/                                 # VQ 量化模块
│   ├── vectree.py                           #   Quantization 类（主流程：quantize + dequantize）
│   ├── vq.py                                #   VectorQuantize / EuclideanCodebook（EMA 码本）
│   └── utils.py                             #   read_ply_data / write_ply_data / load_vqgaussian
│
├── lpipsPyTorch/                            # LPIPS 感知损失
│   ├── __init__.py
│   └── modules/
│       ├── lpips.py
│       ├── networks.py
│       └── utils.py
│
├── assets/                                  # README 图片资源
│   └── ...
│
├── submodules/                              # CUDA 扩展子模块（需编译）
│   ├── diff-gaussian-rasterization/         #   可微 CUDA 光栅化器
│   ├── simple-knn/                          #   CUDA KNN
│   └── fused-ssim/                          #   CUDA SSIM
│
├── SIBR_viewers/                            # SIBR C++ 实时预览器子模块
│
├── ui/                                      # Flask Web UI（新增）
│   ├── __init__.py
│   ├── app.py                               #   Flask 应用工厂
│   ├── config.py                            #   配置（dataset_root / model_root / CUDA 设备）
│   ├── task_manager.py                      #   异步任务管理器（线程 + stdout 捕获 + SSE）
│   ├── forms.py                             #   数据集/模型扫描 & argparse Namespace 构建
│   ├── blueprints/                          #   Flask Blueprints
│   │   ├── __init__.py
│   │   ├── main.py                          #     / 仪表盘
│   │   ├── train.py                         #     /train 训练
│   │   ├── quantize.py                      #     /quantize 量化
│   │   ├── evaluate.py                      #     /eval 评估对比
│   │   ├── videogen.py                      #     /videogen 视频生成
│   │   ├── models.py                        #     /models 模型浏览 & 指标
│   │   └── tasks.py                         #     /tasks 任务列表 & SSE 日志
│   ├── templates/                           #   Jinja2 模板 (Bootstrap 5)
│   │   ├── base.html                        #     基础布局（导航栏）
│   │   ├── index.html                       #     仪表盘
│   │   ├── train.html                       #     训练表单
│   │   ├── quantize.html                    #     量化表单
│   │   ├── evaluate.html                    #     评估表单
│   │   ├── videogen.html                    #     视频生成表单
│   │   ├── models.html                      #     模型列表
│   │   ├── model_detail.html                #     模型详情（指标表格 + Chart.js 图表）
│   │   └── tasks.html                       #     任务列表
│   └── static/
│       ├── css/style.css
│       └── js/
│           ├── app.js                       #     SSE 客户端 & 表单提交
│           └── charts.js                    #     Chart.js 图表辅助函数
│
├── train.py                                 # 训练入口（核心训练循环）
├── render.py                                # 渲染入口（PLY → PNG 图像）
├── render_video.py                          # 视频渲染入口（PLY → MP4 视频）
├── metrics.py                               # 评估指标入口（SSIM/PSNR/LPIPS）
├── prune.py                                 # 剪枝 & 重要性分数计算
├── generate_imp_score.py                    # 独立重要性分数生成
├── full_eval.py                             # 全量评测流水线
├── convert.py                               # COLMAP 数据预处理
│
├── run_train.sh                             # 训练 shell 脚本
├── run_quantize.sh                          # VQ 量化 shell 脚本
├── run_eval.sh                              # 评估对比 shell 脚本
├── run_videogen.sh                          # 视频生成 shell 脚本
│
├── requirements.txt                         # pip 依赖（含 Flask Web UI 依赖段落）
├── environment.yml                          # conda 环境声明（参考）
├── .gitignore
├── .gitmodules
├── LICENSE.md
├── README.md
├── results.md
│
├── output/                                  # 模型输出根目录（.gitignore）
│   └── mipnerf360/
│       ├── bicycle/                         #   bicycle 场景模型
│       └── room/                            #   room 场景模型
│
└── scripts/                                 # 空目录（预留）
```

## 环境要求

| 组件 | 版本 | 说明 |
|------|------|------|
| OS | Linux (任意发行版) | |
| Python | 3.9 | conda 环境 `gs2` |
| PyTorch | 1.13.0+cu116 | 本地 wheel 安装 |
| CUDA | 11.6 | GPU 驱动兼容 |
| Flask | 3.1.3 | Web UI |
| GCC / NVCC | — | 编译 CUDA 子模块 |

## 部署步骤

### 1. 获取代码

```bash
cd /data/project/GS/gaussian-splatting
git submodule update --init --recursive   # 拉取 CUDA 扩展子模块
```

### 2. 配置 conda 环境

```bash
# 激活环境
conda activate gs2

# 编译 CUDA 扩展（如果尚未编译）
pip install submodules/diff-gaussian-rasterization
pip install submodules/simple-knn
pip install submodules/fused-ssim
```

### 3. 安装依赖

```bash
pip install -r requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple/
```

### 4. 准备数据

数据集应放在 `dataset_root`（默认 `/data/datasets/`）下，COLMAP 预处理后的目录结构：

```
/datasets/
  └── mipnerf360/
      ├── bicycle/
      │   ├── images/          # 原始图像
      │   ├── images_2/        # 下采样（分辨率因子 2）
      │   ├── images_4/        # 下采样（分辨率因子 4）
      │   ├── images_8/        # 下采样（分辨率因子 8）
      │   └── sparse/0/        # COLMAP 稀疏重建结果
      └── room/
          └── ...
```

如数据尚未预处理，运行：

```bash
python convert.py -s /data/datasets/mipnerf360/<scene_name>
```

### 5. 启动 Web UI

```bash
# 前台运行
CUDA_VISIBLE_DEVICES=0 conda run -n gs2 python ui/app.py

# 访问 http://localhost:5000
```

**可配置环境变量**：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `GS_DATASET_ROOT` | `/data/datasets` | 数据集根目录 |
| `GS_MODEL_ROOT` | `<项目>/output` | 模型输出根目录 |
| `GS_CUDA_DEVICE` | `0` | GPU 设备号 |
| `GS_HOST` | `0.0.0.0` | Flask 监听地址 |
| `GS_PORT` | `5000` | Flask 监听端口 |

示例：

```bash
conda activate gs2
GS_PORT=8080 CUDA_VISIBLE_DEVICES=0 python ui/app.py
```

### 6. 使用 CLI（可选）

Web UI 以外也可以直接使用 shell 脚本：

```bash
# 训练
bash run_train.sh

# 量化
bash run_quantize.sh

# 评估
bash run_eval.sh -m output/mipnerf360/room

# 视频生成
bash run_videogen.sh
```

## 运行流程

```
Web UI 入口: http://localhost:5000

1. 首页仪表盘 — 查看已有模型、数据集统计、运行中任务
2. /train     — 选择数据集 → 设置参数 → Start Training → 实时日志
3. /quantize  — 选择已训练模型 → 设置 VQ 参数 → Start Quantization → 实时日志
4. /eval      — 选择模型 → Start Evaluation → 渲染 + 指标计算 → 跳转结果
5. /videogen  — 选择模型 → Generate Video → 视频输出
6. /models    — 浏览所有模型 → 点击进入详情 → 查看指标图表
7. /tasks     — 查看所有任务状态 → 点击 View Log 查看实时日志
```

## 数据目录结构（模型输出）

```
output/
  └── mipnerf360/
      └── <scene>/
          ├── input.ply                  # SfM 初始点云
          ├── cameras.json               # 相机参数
          ├── cfg_args                   # 训练配置（序列化）
          ├── test_results.log           # 训练过程指标日志
          ├── point_cloud.ply            # 最终模型（副本）
          ├── imp_score.npz              # 重要性分数
          ├── point_cloud/
          │   └── iteration_30000/
          │       └── point_cloud.ply    # 最终模型
          ├── extreme_saving/            # VQ 量化数据
          │   ├── metadata.npz
          │   ├── codebook.npz
          │   ├── vq_indexs.npz
          │   ├── non_vq_mask.npz
          │   ├── non_vq_feats.npz
          │   ├── other_attribute.npz
          │   └── xyz.npz
          ├── extreme_saving.zip         # VQ 压缩包
          ├── test/                      # 评估渲染输出
          │   ├── ours_30000_original/renders/
          │   ├── ours_30000_vq/renders/
          │   └── gt/
          ├── results.json               # 聚合指标
          ├── per_view.json              # 逐视图指标
          ├── comparison_vq.json         # original vs VQ 对比
          └── video/                     # 视频输出
              ├── ours_30000/            # 视频帧
              └── ours_30000.mp4         # 合成视频
```

## 注意事项

- **不要删除** `/data/datasets/` 和 `output/` 中的已有数据
- Web UI 通过直接调用 Python 函数运行，不通过 subprocess 执行 shell 脚本
- 训练等 GPU 任务在后台线程中运行（单 GPU 串行），前端通过 SSE 获取实时日志
- 所有 UI 代码在 `ui/` 目录中，**不修改**已有项目代码
- 更改 `model_root` 后需重启 Flask 以扫描新路径下的模型
