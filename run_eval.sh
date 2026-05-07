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
python "$SCRIPT_DIR/render.py" -m "$MODEL_PATH" --iteration "$ITERATION" --skip_train

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
python "$SCRIPT_DIR/render.py" -m "$MODEL_PATH" --iteration "$ITERATION" --skip_train --load_vq

VQ_DIR=$(ls -dt "$TEST_DIR"/ours_* 2>/dev/null | head -1)
VQ_RENAMED="${TEST_DIR}/${ITER_NAME}_vq"
mv "$VQ_DIR" "$VQ_RENAMED"
echo "  -> $VQ_RENAMED"

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
import json

with open('$MODEL_PATH/results.json') as f:
    data = json.load(f)

orig = data['$ORIG_KEY']
vq   = data['$VQ_KEY']

print()
print(f\"  {'Metric':<8} {'Original':>10} {'VQ':>10} {'Delta':>10}\")
print('  ' + '-' * 42)
for m in ['SSIM', 'PSNR', 'LPIPS']:
    o = orig[m]
    v = vq[m]
    d = v - o
    arrow = '↓' if m == 'LPIPS' else '↑'
    print(f\"  {m:<8} {o:>10.4f} {v:>10.4f} {d:>+10.4f} {arrow}\")
print()
print('  (SSIM/PSNR ↑ is better, LPIPS ↓ is better)')

comp = {
    'original': orig,
    'vq': vq,
    'delta': {
        'SSIM': vq['SSIM'] - orig['SSIM'],
        'PSNR': vq['PSNR'] - orig['PSNR'],
        'LPIPS': vq['LPIPS'] - orig['LPIPS']
    }
}
with open('$MODEL_PATH/comparison_vq.json', 'w') as f:
    json.dump(comp, f, indent=True)
print(f'\nComparison saved to: $MODEL_PATH/comparison_vq.json')
"
