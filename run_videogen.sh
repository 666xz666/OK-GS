model_path=./output/mipnerf360/bicycle

python render_video.py \
    -m ${model_path} \
    --load_vq \
    --video \
    --skip_train \
    --skip_test