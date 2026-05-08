# OK-GS: Lightweight 3D Gaussian Splatting via Opacity Control and K-means Quantization

**OK-GS** (Orange-Kumiko Gaussian Splatting) is a lightweight 3D Gaussian Splatting framework that achieves extreme model compression following a "prior optimization, post quantization" paradigm. On standard benchmarks, it reduces model size by **99.4%** (Mip-NeRF 360: 827MB → 5MB) and **99.1%** (Tanks & Temples: 454MB → 4MB) with minor quality degradation, reaching up to **596 FPS**.

## Key Idea

Vanilla 3D Gaussian Splatting (3DGS) requires millions of Gaussians per scene, causing heavy memory overhead that hinders edge deployment. OK-GS addresses this with two complementary innovations:

1. **Opacity-aware Gaussian Reduction** — An opacity regularization loss guides adaptive densification and pruning, eliminating redundant Gaussians while regularizing parameter distributions.
2. **K-means-based Parameter Quantization** — Spherical harmonic (SH) coefficients of low-importance Gaussians are compressed into a compact codebook with low-bit indices, dramatically reducing storage.

## Quantitative Results

| Dataset | Method | PSNR↑ | SSIM↑ | LPIPS↓ | Train Time | Memory | FPS↑ |
|---------|--------|-------|-------|--------|------------|--------|------|
| Mip-NeRF 360 | 3DGS (baseline) | 27.23 | 0.81 | 0.22 | 29 min | 827 MB | 105 |
| | **OK-GS** | 25.88 | 0.74 | 0.34 | 27 min | **5 MB** | 276 |
| Tanks&Temples | 3DGS (baseline) | 23.42 | 0.84 | 0.17 | 15 min | 454 MB | 143 |
| | **OK-GS** | 22.96 | 0.78 | 0.29 | 17 min | **4 MB** | **596** |

## Pipeline

```
Raw Images → COLMAP (convert.py) → Train with Opacity Optimization (train.py)
    → Compute Importance Scores → VQ Quantization (vectree/vectree.py)
    → Comparison Evaluation (run_eval.sh) → Video Generation (render_video.py)
```

## Quick Start

### 1. Clone (with submodules)

```bash
git clone --recursive https://github.com/666xz666/OK-GS.git
cd OK-GS
```

If you cloned without `--recursive`:

```bash
git submodule update --init --recursive
```

### 2. Environment

```bash
# CUDA 11.6 + PyTorch 1.13 required
conda env create -f environment.yml
conda activate gs2
pip install -r requirements.txt
```

### 3. Data Preparation

```bash
# Run COLMAP on your images
python convert.py -s <path_to_images>
```

### 4. Training

```bash
bash run_train.sh
# or manually:
python train.py -s <source_path> -m <output_path> --eval --v_pow 0.1
```

### 5. VQ Compression

```bash
bash run_quantize.sh
# or manually:
python vectree/vectree.py \
    --important_score_npz_path <path>/imp_score.npz \
    --input_path <path>/point_cloud.ply \
    --save_path <path> \
    --vq_ratio 0.6 --codebook_size 8192
```

### 6. Evaluation

```bash
bash run_eval.sh -m output/<scene_name>
```

### 7. Video Generation

```bash
# Ellipse trajectory
python render_video.py -m <model_path> --load_vq --video --skip_train --skip_test

# Circular trajectory
python render_video.py -m <model_path> --circular --radius 3.0 --load_vq
```

### 8. Web UI

```bash
CUDA_VISIBLE_DEVICES=0 python ui/app.py
# Open http://localhost:5000
```

The Flask-based Web UI provides a bilingual (zh/en) dashboard for the full pipeline: training, quantization, evaluation, and video generation, with real-time log streaming via SSE.

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--iterations` | 30000 | Total training iterations |
| `--sh_degree` | 3 | Spherical harmonics degree |
| `--v_pow` | 0.1 | Volume weighting exponent for importance scoring |
| `--vq_ratio` | 0.6 | Fraction of Gaussians to quantize |
| `--codebook_size` | 8192 | VQ codebook size |
| `--load_vq` | — | Load VQ-compressed model instead of PLY |

## Project Structure

```
OK-GS/
├── train.py                    # Main training script
├── render.py                   # Render PLY/VQ model to images
├── render_video.py             # Novel-view video generation
├── metrics.py                  # SSIM / PSNR / LPIPS computation
├── full_eval.py                # Batch evaluation across datasets
├── convert.py                  # COLMAP preprocessing
├── prune.py                    # Pruning logic & importance scoring
├── generate_imp_score.py       # Standalone importance score generator
├── run_train.sh                # Training launcher
├── run_quantize.sh             # VQ quantization launcher
├── run_eval.sh                 # Comparison evaluation launcher
├── run_videogen.sh             # Video generation launcher
├── arguments/                  # CLI argument definitions
├── scene/                      # Scene & GaussianModel data structures
├── gaussian_renderer/          # CUDA differentiable rasterizer
├── vectree/                    # VQ quantization module
│   ├── vectree.py              # Main quantization pipeline
│   ├── vq.py                   # VectorQuantize / EuclideanCodebook (EMA)
│   └── utils.py                # PLY ↔ numpy conversion & VQ decompression
├── utils/                      # Utility functions (pose, SH, loss, ELBO, etc.)
├── lpipsPyTorch/               # LPIPS perceptual loss
├── ui/                         # Flask Web UI (Bootstrap 5, zh/en)
├── submodules/                 # CUDA extension submodules
│   ├── diff-gaussian-rasterization/
│   ├── compress-diff-gaussian-rasterization/
│   ├── simple-knn/
│   └── fused-ssim/
├── docs/                       # Documentation
│   ├── project_overview.md     # Full pipeline documentation
│   ├── deployment.md           # Deployment guide
│   ├── flask_web_ui_design.md  # Web UI design
│   └── flask_web_ui_changelog.md
├── output/                     # Trained models & evaluation results
└── assets/                     # Images, charts, logos
```

## License

This project is built upon [3D Gaussian Splatting](https://github.com/graphdeco-inria/gaussian-splatting) (Inria / GRAPHDECO). See [LICENSE](LICENSE) and [LICENSE.md](LICENSE.md) for details.

## Citation

If you use this work, please cite:

```bibtex
@article{chen2025lightweight,
  title={Lightweight 3D Gaussian Splatting via Opacity Control and K-means Quantization},
  author={Chen, Zhen and Xu, Zhan and Sun, Fengze and Zhao, Xuyang and Jin, Yi and Yu, Hui},
  year={2025}
}
```
