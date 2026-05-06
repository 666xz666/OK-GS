"""
从指定 PLY 生成重要性分数并保存为 npz。
"""

import math
import os
import sys
from argparse import ArgumentParser, Namespace
from types import SimpleNamespace

import numpy as np
import torch
from torch import nn

from arguments import ModelParams, PipelineParams
from prune import prune_list, calculate_v_imp_score
from scene import GaussianModel
from scene.dataset_readers import sceneLoadTypeCallbacks
from utils.camera_utils import cameraList_from_camInfos
from utils.general_utils import safe_state
from vectree.utils import read_ply_data


class _SceneForPrune:
    def __init__(self, train_cameras):
        self._train_cameras = train_cameras

    def getTrainCameras(self, scale=1.0):
        if scale != 1.0:
            raise ValueError("Only scale=1.0 is supported in generate_imp_score.")
        return self._train_cameras


def _load_cfg_namespace(base_path):
    cfg_path = os.path.join(base_path, "cfg_args")
    if not os.path.isfile(cfg_path):
        raise FileNotFoundError(f"cfg_args not found: {cfg_path}")

    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg_text = f.read()

    try:
        cfg_ns = eval(cfg_text, {"Namespace": Namespace})
    except Exception as exc:
        raise ValueError(f"Failed to parse cfg_args at {cfg_path}: {exc}") from exc

    if not isinstance(cfg_ns, Namespace):
        raise ValueError(f"cfg_args content is not argparse.Namespace: {cfg_path}")
    return cfg_ns


def _build_dataset_and_pipe_args(base_path):
    parser = ArgumentParser(add_help=False)
    lp = ModelParams(parser, sentinel=True)
    pp = PipelineParams(parser)

    default_ns = parser.parse_args([])
    cfg_ns = _load_cfg_namespace(base_path)

    merged = vars(default_ns).copy()
    merged.update(vars(cfg_ns))

    # base_path 语义：cfg_args 根目录 + npz 输出目录
    merged["model_path"] = os.path.abspath(base_path)

    merged_ns = Namespace(**merged)
    dataset = lp.extract(merged_ns)
    pipe = pp.extract(merged_ns)
    return dataset, pipe


def _load_scene_info(dataset):
    if os.path.exists(os.path.join(dataset.source_path, "sparse")):
        return sceneLoadTypeCallbacks["Colmap"](
            dataset.source_path,
            dataset.images,
            dataset.depths,
            dataset.eval,
            dataset.train_test_exp,
        )
    if os.path.exists(os.path.join(dataset.source_path, "transforms_train.json")):
        return sceneLoadTypeCallbacks["Blender"](
            dataset.source_path,
            dataset.white_background,
            dataset.depths,
            dataset.eval,
        )
    raise RuntimeError(f"Could not recognize scene type for source_path: {dataset.source_path}")


def _infer_sh_degree_from_rest(rest_count, fallback_degree):
    if rest_count % 3 != 0:
        return fallback_degree
    order_square = rest_count // 3 + 1
    degree = int(round(math.sqrt(order_square) - 1))
    if degree >= 0 and (degree + 1) * (degree + 1) == order_square:
        return degree
    return fallback_degree


def _load_gaussians_from_ply(ply_path, fallback_sh_degree):
    feats = read_ply_data(ply_path)
    feats = torch.tensor(feats, dtype=torch.float32, device="cuda")
    if feats.ndim != 2 or feats.shape[1] < 18:
        raise ValueError(f"Invalid gaussian ply attributes shape: {tuple(feats.shape)}")

    total_dim = feats.shape[1]
    rest_dim = total_dim - 3 - 3 - 3 - 1 - 3 - 4
    if rest_dim < 0 or rest_dim % 3 != 0:
        raise ValueError(f"Invalid ply feature dimension: {total_dim}, rest_dim={rest_dim}")

    sh_degree = _infer_sh_degree_from_rest(rest_dim, fallback_sh_degree)
    gaussians = GaussianModel(sh_degree)

    n = feats.shape[0]
    xyz = feats[:, 0:3]
    f_dc = feats[:, 6:9].reshape(n, 3, 1).transpose(1, 2).contiguous()
    f_rest = feats[:, 9 : 9 + rest_dim].reshape(n, 3, rest_dim // 3).transpose(1, 2).contiguous()
    opacity = feats[:, 9 + rest_dim : 10 + rest_dim]
    scaling = feats[:, 10 + rest_dim : 13 + rest_dim]
    rotation = feats[:, 13 + rest_dim : 17 + rest_dim]

    gaussians._xyz = nn.Parameter(xyz.requires_grad_(True))
    gaussians._features_dc = nn.Parameter(f_dc.requires_grad_(True))
    gaussians._features_rest = nn.Parameter(f_rest.requires_grad_(True))
    gaussians._opacity = nn.Parameter(opacity.requires_grad_(True))
    gaussians._scaling = nn.Parameter(scaling.requires_grad_(True))
    gaussians._rotation = nn.Parameter(rotation.requires_grad_(True))
    gaussians.max_radii2D = torch.zeros((n,), device="cuda")
    gaussians.active_sh_degree = gaussians.max_sh_degree
    return gaussians


def generate_importance_scores(model_path, base_path, v_pow):
    dataset, pipe = _build_dataset_and_pipe_args(base_path)
    scene_info = _load_scene_info(dataset)
    train_cameras = cameraList_from_camInfos(
        scene_info.train_cameras,
        1.0,
        dataset,
        scene_info.is_nerf_synthetic,
        False,
    )
    scene = _SceneForPrune(train_cameras)

    gaussians = _load_gaussians_from_ply(model_path, dataset.sh_degree)

    bg_color = [1, 1, 1] if dataset.white_background else [0, 0, 0]
    background = torch.tensor(bg_color, dtype=torch.float32, device="cuda")

    print("Computing importance scores...")
    gaussian_list, imp_list = prune_list(gaussians, scene, pipe, background)
    v_list = calculate_v_imp_score(gaussians, imp_list, v_pow)

    output_path = os.path.join(base_path, "imp_score.npz")
    np.savez(output_path, v_list.detach().cpu().numpy())

    print(f"Importance scores saved to: {output_path}")
    print(f"Shape of importance scores: {tuple(v_list.shape)}")
    print(f"Min score: {v_list.min().item():.6f}, Max score: {v_list.max().item():.6f}")


def main():
    parser = ArgumentParser(description="Generate imp_score.npz from a specific gaussian PLY")
    parser.add_argument("--model_path", type=str, required=True, help="Path to gaussian point_cloud.ply")
    parser.add_argument("--base_path", type=str, required=True, help="Directory containing cfg_args, and output dir for imp_score.npz")
    parser.add_argument("--v_pow", type=float, default=0.1, help="Power parameter for volume in score computation")
    parser.add_argument("--quiet", action="store_true", help="Silence timestamped stdout wrapper")
    args = parser.parse_args()

    args.model_path = os.path.abspath(args.model_path)
    args.base_path = os.path.abspath(args.base_path)

    if not os.path.isfile(args.model_path):
        print(f"Error: model_path is not a file: {args.model_path}")
        sys.exit(1)
    if not args.model_path.lower().endswith(".ply"):
        print(f"Error: model_path must point to a .ply file: {args.model_path}")
        sys.exit(1)
    if not os.path.isdir(args.base_path):
        print(f"Error: base_path is not a directory: {args.base_path}")
        sys.exit(1)

    if not torch.cuda.is_available():
        print("Error: CUDA is required by this script.")
        sys.exit(1)

    safe_state(args.quiet)

    try:
        generate_importance_scores(args.model_path, args.base_path, args.v_pow)
        print("Successfully generated importance scores!")
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
