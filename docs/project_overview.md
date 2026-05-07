# Gaussian Splatting with VQ Quantization — 项目全景

## 实验全流程

```
原始图片 → COLMAP → 训练 3DGS → 计算重要性分数 → VQ 量化压缩 → 渲染对比评估
```

---

## 各阶段详解

### 阶段 0：数据准备 — [convert.py](../convert.py)

对原始图片运行 COLMAP（特征提取 → 匹配 → 稀疏重建 → 去畸变），可选地对图片做多分辨率缩放。

```bash
python convert.py -s <source_path> [--no_gpu] [--camera OPENCV]
```

输出：`sparse/0/`（相机参数 + 稀疏点云）

### 阶段 1：训练 — [train.py](../train.py)，由 [run_train.sh](../run_train.sh) 启动

从 SfM 点云初始化 Gaussian，用 L1 + D-SSIM 混合 loss 做梯度下降优化。训练过程中进行自适应密度控制，并在保存 checkpoint 时计算每个 Gaussian 的重要性分数。

**核心机制：**

- **优化目标**：`(1 - λ) * L1 + λ * (1 - SSIM)`，λ 默认 0.2
- **自适应密度控制**：每 100 步根据位置梯度 clone（欠重建区）或 split（过重建区），每 3000 步重置 opacity
- **重要性分数**：通过 CUDA rasterizer 的 `f_count` 模式，统计每个 Gaussian 在所有训练视角下的可见次数和渲染贡献
- **ELBO 早停**（可选）：基于 ELBO 收敛自动判断何时停止 densification

```bash
python train.py -s <source_path> -m <model_path> [--eval] [--v_pow 0.1]
```

输出：
- `point_cloud/iteration_30000/point_cloud.ply` — 训练好的 Gaussian 模型
- `imp_score.npz` — 逐 Gaussian 重要性分数
- `test_results.log` — 训练过程中各迭代的 PSNR/SSIM/LPIPS 日志

### 阶段 2：VQ 量化 — [vectree/vectree.py](../vectree/vectree.py)，由 [run_quantize.sh](../run_quantize.sh) 启动

按重要性分数排序，保留高重要性 Gaussian 的全精度，对低重要性 Gaussian 的 SH 特征做向量量化压缩。

**核心机制：**

1. 按 `importance_score * volume^v_pow` 排序所有 Gaussian
2. 前 `(1 - vq_ratio)` 的高重要性 Gaussian → 保留 fp16 精度（non-VQ 集）
3. 剩余 `vq_ratio` 的 Gaussian → SH 特征用 VQ 压缩，训练 codebook（EMA 更新，8192 个码字）
4. 所有属性分别存储：xyz（全精度）、非 SH 属性（opacity/scale/rotation，fp16）、VQ索引（位压缩）

```bash
python vectree/vectree.py \
    --important_score_npz_path <path>/imp_score.npz \
    --input_path <path>/point_cloud.ply \
    --save_path <model_path> \
    --vq_ratio 0.6 \
    --codebook_size 8192
```

输出：
- `extreme_saving/` — 7 个 npz 文件：
  - `metadata.npz` — 维度/数量/码本大小等元信息
  - `codebook.npz` — 学习到的码本向量 (fp16)
  - `vq_indexs.npz` — 每个被量化 Gaussian 的码字索引（位压缩）
  - `non_vq_mask.npz` — 哪些 Gaussian 未被量化
  - `non_vq_feats.npz` — 未量化 Gaussian 的 SH 特征 (fp16)
  - `other_attribute.npz` — opacity + scale + rotation (fp16)
  - `xyz.npz` — 位置坐标
- `extreme_saving.zip` — 上述目录的 zip 压缩包

### 阶段 3：对比评估 — [run_eval.sh](../run_eval.sh)

分别渲染原始 PLY 模型和 VQ 解压模型，计算五个指标并输出对比。

```bash
bash run_eval.sh -m <model_path> [-i <iteration>]
```

评估指标：**SSIM** / **PSNR** / **LPIPS** / **MEM**（存储大小）/ **FPS**（渲染速度）

对比表示例：
```
  Metric     Original            VQ          Delta
  ------------------------------------------------------
  SSIM             0.8000        0.7500       -0.0500 ↑
  PSNR            28.0000       26.5000       -1.5000 ↑
  LPIPS            0.1500        0.2000       +0.0500 ↓
  MEM           201.00 MB      49.60 MB
  FPS               1.14          1.10
```

指标说明：
- **SSIM / PSNR**：↑ 越高越好
- **LPIPS / MEM**：↓ 越低越好（MEM 原始 = PLY 文件大小，MEM VQ = `extreme_saving.zip` 大小）
- **FPS**：↑ 越高越好，按 `1.0 / 平均单帧渲染时间` 计算（仅计 GPU 渲染，不含模型加载和写盘 I/O）

输出：
- `results.json` — 各模型各指标
- `per_view.json` — 逐视角指标
- `comparison_vq.json` — 原始 vs VQ 对比（含 SSIM/PSNR/LPIPS 差值、MEM 压缩率、FPS）

### 阶段 4（可选）：视频生成 — [render_video.py](../render_video.py)

生成新视角视频漫游，支持椭圆轨迹和圆形轨迹。渲染完成后自动使用 `imageio` 将 PNG 帧序列合成为 `.mp4` 视频。

```bash
# 椭圆轨迹（默认600帧）
python render_video.py -m <model_path> --video [--fps 30] [--load_vq]

# 圆形轨迹（默认240帧）
python render_video.py -m <model_path> --circular --radius 3.0 [--load_vq]

# 高斯扰动采样（对前10个视角各生成10个随机扰动视角）
python render_video.py -m <model_path> --gaussians --std 0.05

# 组合使用：VQ 模型 + 标准渲染 + 椭圆视频
python render_video.py -m <model_path> --load_vq --video
```

输出：
- `video/ours_XXXXX/` — 椭圆轨迹帧序列 (PNG)
- `video/ours_XXXXX.mp4` — 合成视频
- `circular/ours_XXXXX/` — 圆形轨迹帧序列 (PNG)
- `circular/ours_XXXXX.mp4` — 合成视频

---

## 项目目录结构

```
gaussian-splatting/
├── train.py                  # 训练主脚本
├── render.py                 # 渲染到图片
├── render_video.py           # 渲染到视频（含 imageio 合成 .mp4）
├── metrics.py                # SSIM / PSNR / LPIPS 评估
├── full_eval.py              # 全场景批量评估
├── convert.py                # COLMAP 数据预处理
├── prune.py                  # 剪枝逻辑 + 重要性分数计算
├── generate_imp_score.py     # 独立的 imp_score 生成脚本
├── run_train.sh              # 训练启动脚本
├── run_quantize.sh           # VQ 量化启动脚本
├── run_eval.sh               # 原始 vs VQ 对比评估脚本
├── requirements.txt          # pip 依赖
├── environment.yml           # Conda 环境
│
├── arguments/                # CLI 参数定义
│   └── __init__.py           # ModelParams / PipelineParams / OptimizationParams
│
├── scene/                    # 场景与模型数据结构
│   ├── __init__.py           # Scene 类：加载相机、管理 PLY/VQ 加载
│   ├── gaussian_model.py     # GaussianModel：所有参数张量 + 训练逻辑 + VQ 解压
│   ├── cameras.py            # 相机数据结构
│   ├── colmap_loader.py      # COLMAP 数据读取
│   └── dataset_readers.py    # 场景信息读取器（Colmap / Blender）
│
├── gaussian_renderer/        # CUDA 可微光栅化
│   ├── __init__.py           # render() / count_render()（后者返回逐 Gaussian 重要性）
│   └── network_gui.py        # 训练过程中的 Web GUI
│
├── vectree/                  # VQ 量化模块
│   ├── vectree.py            # 主量化脚本：Quantization 类（训练 codebook + 存储/解压）
│   ├── vq.py                 # VectorQuantize / EuclideanCodebook（EMA 更新 + 重要性加权）
│   └── utils.py              # PLY ↔ numpy 转换 / 位压缩索引 / load_vqgaussian 解压
│
├── utils/                    # 工具函数
│   ├── graphics_utils.py     # 投影矩阵 / 坐标变换
│   ├── pose_utils.py         # 相机轨迹生成（椭圆/圆形/螺旋）
│   ├── sh_utils.py           # 球谐函数求值
│   ├── loss_utils.py         # L1 / SSIM / 正则化项
│   ├── system_utils.py       # 搜索最新 iteration
│   ├── image_utils.py        # PSNR 计算
│   └── elbo.py               # ELBO 自适应早停
│
├── lpipsPyTorch/             # LPIPS 感知损失模块
│   └── modules/              # VGG/AlexNet 网络 + 空间归一化
│
├── submodules/               # Git 子模块（CUDA 扩展）
│   ├── diff-gaussian-rasterization/  # CUDA 光栅化（含 f_count 模式）
│   ├── simple-knn/                   # distCUDA2 近邻搜索
│   └── fused-ssim/                   # 融合 CUDA SSIM
│
├── output/                   # 训练输出（示例）
│   └── <scene>/
│       ├── input.ply         # SfM 输入点云
│       ├── cameras.json      # 相机参数
│       ├── cfg_args          # 训练配置
│       ├── test_results.log  # 训练过程指标日志
│       ├── point_cloud/iteration_30000/point_cloud.ply  # 训练产物
│       ├── imp_score.npz     # 重要性分数
│       ├── extreme_saving/   # VQ 压缩产物（7 个 npz 文件）
│       ├── extreme_saving.zip
│       ├── test/             # 渲染测试图像（含 ours_*_original / ours_*_vq）
│       ├── video/            # 渲染视频帧 + mp4
│       ├── circular/         # 圆形轨迹视频帧 + mp4
│       ├── results.json      # 评估指标
│       ├── per_view.json     # 逐视角指标
│       └── comparison_vq.json # 原始 vs VQ 对比
│
└── docs/                     # 文档
    └── project_overview.md   # 本文档
```

---

## 核心模块详解

### GaussianModel（[scene/gaussian_model.py](../scene/gaussian_model.py)）

管理所有 Gaussian 的可学习参数：

| 参数 | 维度 | 说明 |
|---|---|---|
| `_xyz` | N × 3 | 位置 |
| `_features_dc` | N × 1 × 3 | SH 直流分量（RGB） |
| `_features_rest` | N × 15 × 3 | SH 高阶分量 |
| `_opacity` | N × 1 | 不透明度 |
| `_scaling` | N × 3 | 协方差缩放 |
| `_rotation` | N × 4 | 协方差旋转（四元数） |

提供 `load_vq(path)` 方法从 `extreme_saving/` 目录解压重建所有参数。

### 重要性分数（[prune.py](../prune.py)）

```
importance(g) = (volume(g) / Kth_largest_volume)^v_pow × Σ vis(g, camera_i) × contrib(g, camera_i)
```

- `volume = prod(scaling)` — Gaussian 在空间中的体积
- `vis_count` — 该 Gaussian 在所有训练视角下的可见次数
- `important_score` — CUDA rasterizer 累加的逐像素渲染贡献
- `v_pow` — 体积加权指数（默认 0.1），越大越偏向大体积 Gaussian

### VQ 压缩流程（[vectree/](../vectree/)）

```
PLY → 分离属性 → SH特征按重要性排序
                    ├── 高重要性 (1-vq_ratio) → fp16 直接存储
                    └── 低重要性 (vq_ratio)   → VQ 训练 codebook → 位压缩索引
              → 所有属性分别存为 npz → zip 打包
```

解压时（`load_vqgaussian`）：
```
extreme_saving/ → 读 metadata → 重建全零矩阵
    → xyz / other_attribute 直接填入
    → VQ部分：codebook[vq_indexs] 查表恢复 SH 特征
    → non-VQ 部分：直接填入 fp16 特征
    → 组装完整 Gaussian 参数
```

### 关键参数速查

| 参数 | 默认值 | 含义 | 所在脚本 |
|---|---|---|---|
| `--iterations` | 30000 | 训练总迭代数 | train.py |
| `--sh_degree` | 3 | 球谐函数阶数 | train.py |
| `--v_pow` | 0.1 | 重要性分数的体积加权指数 | train.py |
| `--vq_ratio` | 0.6 | 被量化的 Gaussian 比例 | vectree.py |
| `--codebook_size` | 8192 | VQ 码本大小 | vectree.py |
| `--iteration_num` | 1000 | VQ 训练迭代数 | vectree.py |
| `--fps` | 30 | 输出视频帧率 | render_video.py |
| `--load_vq` | — | 加载 VQ 压缩模型（而非 PLY） | render.py / render_video.py / run_eval.sh |

---

## 一键运行

```bash
# 1. 训练
bash run_train.sh

# 2. VQ 量化
bash run_quantize.sh

# 3. 原始 vs VQ 对比评估
bash run_eval.sh -m output/<scene_name>

# 4. 生成视频（可选）
python render_video.py -m output/<scene_name> --video
```
