#!/bin/bash
# Compare original PLY model vs VQ quantized model quality.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODEL_PATH=""
ITERATION=-1

usage() {
    echo "Usage: $0 -m <model_path> [-i <iteration>]"
    exit 1
}

while getopts "m:i:h" opt; do
    case $opt in
        m) MODEL_PATH="$OPTARG" ;;
        i) ITERATION="$OPTARG" ;;
        *) usage ;;
    esac
done

if [ -z "$MODEL_PATH" ]; then
    usage
fi

MODEL_PATH="$(realpath "$MODEL_PATH")"
TEST_DIR="$MODEL_PATH/test"

# Clean old comparison directories
echo "Cleaning old comparison directories..."
rm -rf "$TEST_DIR"/ours_*_original "$TEST_DIR"/ours_*_vq

# ---- Step 1: Render original PLY model ----
echo ""
echo "============================================================"
echo "Step 1/4: Rendering original (PLY) model ..."
echo "============================================================"
RENDER_OUT=$(python "$SCRIPT_DIR/render.py" -m "$MODEL_PATH" --iteration "$ITERATION" --skip_train 2>&1)
echo "$RENDER_OUT"
ORIG_FPS=$(echo "$RENDER_OUT" | grep -oP 'FPS:\s*\K[\d.]+')

ORIG_DIR=$(ls -dt "$TEST_DIR"/ours_* 2>/dev/null | head -1)
if [ -z "$ORIG_DIR" ]; then
    echo "ERROR: No ours_* directory found in $TEST_DIR"
    exit 1
fi
ITER_NAME=$(basename "$ORIG_DIR")
ORIG_RENAMED="${ORIG_DIR}_original"
mv "$ORIG_DIR" "$ORIG_RENAMED"
echo "  -> $ORIG_RENAMED"

# ---- Step 2: Render VQ model ----
echo ""
echo "============================================================"
echo "Step 2/4: Rendering VQ quantized model ..."
echo "============================================================"
RENDER_OUT=$(python "$SCRIPT_DIR/render.py" -m "$MODEL_PATH" --iteration "$ITERATION" --skip_train --load_vq 2>&1)
echo "$RENDER_OUT"
VQ_FPS=$(echo "$RENDER_OUT" | grep -oP 'FPS:\s*\K[\d.]+')

VQ_DIR=$(ls -dt "$TEST_DIR"/ours_* 2>/dev/null | head -1)
VQ_RENAMED="${TEST_DIR}/${ITER_NAME}_vq"
mv "$VQ_DIR" "$VQ_RENAMED"
echo "  -> $VQ_RENAMED"

# ---- Compute MEM (storage) sizes ----
ACTUAL_ITER="${ITER_NAME#ours_}"
ORIG_PLY="$MODEL_PATH/point_cloud/iteration_$ACTUAL_ITER/point_cloud.ply"
VQ_ZIP="$MODEL_PATH/extreme_saving.zip"

ORIG_MEM=$(stat -c%s "$ORIG_PLY" 2>/dev/null || echo 0)
VQ_MEM=$(stat -c%s "$VQ_ZIP" 2>/dev/null || echo 0)

echo ""
echo "  Original PLY : $(numfmt --to=iec $ORIG_MEM) ($ORIG_PLY)"
echo "  VQ zip       : $(numfmt --to=iec $VQ_MEM) ($VQ_ZIP)"

# ---- Step 3: Run metrics on both ----
echo ""
echo "============================================================"
echo "Step 3/4: Computing metrics ..."
echo "============================================================"
python "$SCRIPT_DIR/metrics.py" -m "$MODEL_PATH"

# ---- Step 4: Print comparison ----
echo ""
echo "============================================================"
echo "Step 4/4: Comparison results"
echo "============================================================"

ORIG_KEY="${ITER_NAME}_original"
VQ_KEY="${ITER_NAME}_vq"

# Use python inline to parse and print
python -c "
import json, os

with open('$MODEL_PATH/results.json') as f:
    data = json.load(f)

orig = data['$ORIG_KEY']
vq   = data['$VQ_KEY']

orig_mem = $ORIG_MEM
vq_mem   = $VQ_MEM
orig_fps = $ORIG_FPS
vq_fps   = $VQ_FPS

def fmt_mem(b):
    return f'{b / 1024 / 1024:.2f} MB'

print()
print(f\"  {'Metric':<8} {'Original':>14} {'VQ':>14} {'Delta':>14}\")
print('  ' + '-' * 54)
for m in ['SSIM', 'PSNR', 'LPIPS']:
    o = orig[m]
    v = vq[m]
    d = v - o
    arrow = '↓' if m == 'LPIPS' else '↑'
    print(f\"  {m:<8} {o:>14.4f} {v:>14.4f} {d:>+14.4f} {arrow}\")
# MEM row
mem_o = fmt_mem(orig_mem)
mem_v = fmt_mem(vq_mem)
print(f\"  {'MEM':<8} {mem_o:>14} {mem_v:>14} {'':>14}\")
# FPS row
print(f\"  {'FPS':<8} {orig_fps:>13.2f}  {vq_fps:>13.2f}  {'':>14}\")
print()
print('  (SSIM/PSNR/FPS ↑ is better, LPIPS/MEM ↓ is better)')

comp = {
    'original': orig,
    'vq': vq,
    'delta': {
        'SSIM': vq['SSIM'] - orig['SSIM'],
        'PSNR': vq['PSNR'] - orig['PSNR'],
        'LPIPS': vq['LPIPS'] - orig['LPIPS']
    },
    'mem': {
        'original_bytes': orig_mem,
        'vq_bytes': vq_mem,
        'original_mb': round(orig_mem / 1024 / 1024, 2),
        'vq_mb': round(vq_mem / 1024 / 1024, 2),
        'compression_ratio': round(orig_mem / vq_mem, 2) if vq_mem > 0 else 0
    },
    'fps': {
        'original': orig_fps,
        'vq': vq_fps
    }
}
with open('$MODEL_PATH/comparison_vq.json', 'w') as f:
    json.dump(comp, f, indent=True)
print(f'\nComparison saved to: $MODEL_PATH/comparison_vq.json')
"
