import os
import sys
from argparse import ArgumentParser, Namespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def has_model_video(model_path):
    for subdir in ('video', 'circular'):
        video_dir = os.path.join(model_path, subdir)
        if os.path.isdir(video_dir):
            if any(name.endswith('.mp4') for name in os.listdir(video_dir)):
                return True
    return False


def scan_datasets(dataset_root):
    entries = []
    if not os.path.isdir(dataset_root):
        return entries
    for dset_name in sorted(os.listdir(dataset_root)):
        dset_path = os.path.join(dataset_root, dset_name)
        if not os.path.isdir(dset_path):
            continue
        scenes = []
        for scene_name in sorted(os.listdir(dset_path)):
            scene_path = os.path.join(dset_path, scene_name)
            if os.path.isdir(scene_path):
                has_colmap = (
                    os.path.isdir(os.path.join(scene_path, 'sparse')) or
                    os.path.isfile(os.path.join(scene_path, 'transforms_train.json'))
                )
                scenes.append({
                    'name': scene_name,
                    'path': scene_path,
                    'has_colmap': has_colmap,
                })
        if scenes:
            entries.append({'name': dset_name, 'path': dset_path, 'scenes': scenes})
    return entries


def scan_models(model_root):
    models = []
    if not os.path.isdir(model_root):
        return models
    for dirpath, dirnames, filenames in os.walk(model_root):
        has_cfg = 'cfg_args' in filenames
        if not has_cfg:
            continue
        rel_path = os.path.relpath(dirpath, model_root)

        pcd_dir = os.path.join(dirpath, 'point_cloud')
        iterations = []
        if os.path.isdir(pcd_dir):
            for name in sorted(os.listdir(pcd_dir)):
                iter_dir = os.path.join(pcd_dir, name)
                ply_path = os.path.join(iter_dir, 'point_cloud.ply')
                if os.path.isfile(ply_path):
                    iterations.append(name)

        has_ply = any(
            os.path.isfile(os.path.join(pcd_dir, it, 'point_cloud.ply'))
            for it in iterations
        ) if iterations else os.path.isfile(os.path.join(dirpath, 'point_cloud.ply'))

        has_vq = os.path.isfile(os.path.join(dirpath, 'extreme_saving.zip'))
        has_imp = os.path.isfile(os.path.join(dirpath, 'imp_score.npz'))
        has_results = os.path.isfile(os.path.join(dirpath, 'results.json'))
        has_comparison = os.path.isfile(os.path.join(dirpath, 'comparison_vq.json'))
        has_video = has_model_video(dirpath)

        models.append({
            'rel_path': rel_path,
            'abs_path': dirpath,
            'iterations': iterations,
            'has_ply': has_ply,
            'has_vq': has_vq,
            'has_imp': has_imp,
            'has_results': has_results,
            'has_comparison': has_comparison,
            'has_video': has_video,
        })
        dirnames[:] = []
    return sorted(models, key=lambda m: m['rel_path'])


def build_train_args(form_data, dataset_root, model_root):
    from arguments import ModelParams, PipelineParams, OptimizationParams

    parser = ArgumentParser(add_help=False)
    lp = ModelParams(parser, sentinel=True)
    op = OptimizationParams(parser)
    pp = PipelineParams(parser)

    defaults = parser.parse_args([])
    args_dict = vars(defaults)

    scene_path = form_data.get('source_path', '')
    scene_rel = os.path.relpath(scene_path, dataset_root) if scene_path.startswith(dataset_root) else os.path.basename(scene_path)
    model_path = form_data.get('model_path', os.path.join(model_root, scene_rel))

    args_dict['source_path'] = scene_path
    args_dict['model_path'] = model_path
    args_dict['resolution'] = int(form_data.get('resolution', -1))
    args_dict['sh_degree'] = int(form_data.get('sh_degree', 3))
    args_dict['iterations'] = int(form_data.get('iterations', 30000))
    args_dict['eval'] = form_data.get('eval', 'true').lower() == 'true'

    return Namespace(**args_dict)


def build_quantize_args(form_data):
    args = Namespace(
        important_score_npz_path=form_data.get('important_score_npz_path', ''),
        input_path=form_data.get('input_path', ''),
        save_path=form_data.get('save_path', ''),
        sh_degree=int(form_data.get('sh_degree', 3)),
        vq_ratio=float(form_data.get('vq_ratio', 0.6)),
        codebook_size=int(form_data.get('codebook_size', 8192)),
        iteration_num=int(form_data.get('iteration_num', 1000)),
        no_IS=False,
        no_load_data=False,
        no_save_ply=False,
        vq_way='half',
    )
    return args


def build_render_args(model_path, iteration, load_vq, skip_train=True, skip_test=False):
    from arguments import ModelParams, PipelineParams

    parser = ArgumentParser(add_help=False)
    ModelParams(parser, sentinel=True)
    PipelineParams(parser)
    defaults = parser.parse_args([])
    args_dict = vars(defaults)
    args_dict['source_path'] = ''
    args_dict['model_path'] = model_path
    args_dict['iteration'] = iteration
    args_dict['load_vq'] = load_vq
    args_dict['skip_train'] = skip_train
    args_dict['skip_test'] = skip_test
    args_dict['quiet'] = False
    return Namespace(**args_dict)
