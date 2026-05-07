#!/bin/bash

# path_base=<dataset_base_path>
output_base=/data/project/GS/gaussian-splatting/output
path_base=/data/datasets

cuda_device=0
port=4060
########################
# tandt
########################
# dset=tandt

# scenes=(
#   "bicycle" "bonsai" "counter" "flowers" "garden"
#   "stump" "treehill" "kitchen" "room"
#   "Auditorium" "Ballroom" "Barn" "Caterpillar" "Church"
#   "Courthouse" "Courtroom" "Family" "Francis" "Horse"
#   "Ignatius" "Lighthouse" "M60" "Meetingroom" "Museum"
#   "Palace" "Panther" "Playground" "Temple" "Train" "Truck"
# )

# factors=(4 2 2 4 4 4 4 2 2 $(for i in {1..21}; do echo 1; done))

########################
# mipnerf
########################
# dset=mipnerf360

# scenes=(
#   "bicycle" "garden" "stump" "treehill" "bonsai"  # 5个室外场景
#   "counter" "kitchen" "room" "flowers"            # 4个室内场景
# )

# factors=(4 4 4 4 2 2 2 2 2)

########################
# part of dataset for testing
########################
dset=mipnerf360

scenes=(
  "bicycle" 
)

factors=(4)
########################


for idx in "${!scenes[@]}"; do
  scene="${scenes[$idx]}"
  factor="${factors[$idx]}"

  path_output="$output_base/$dset/$scene"

  echo "Start: $scene"

  CUDA_VISIBLE_DEVICES="$cuda_device" python train.py \
    --port "$port" \
    --resolution "$factor" \
    -s "${path_base}/${dset}/${scene}" \
    -m "$path_output" \
    --eval \
    # --use_elbo_adaptive 

  ########################
  # testing
  # CUDA_VISIBLE_DEVICES="$cuda_device" python train.py \
  #   --port "$port" \
  #   --iteration 1000 \
  #   --test_iterations 500 1000 \
  #   --save_iterations 1000 \
  #   --densify_until_iter 500 \
  #   --opacity_reset_interval 300 \
  #   --resolution "$factor" \
  #   -s "${path_base}/${dset}/${scene}" \
  #   -m "$path_output" \
  #   --eval \
    # --use_elbo_adaptive 
  ########################

  ((port++))
  sleep 5
done

echo "Done"