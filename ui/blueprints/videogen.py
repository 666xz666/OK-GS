import os
import sys
from argparse import Namespace

from flask import Blueprint, render_template, request, jsonify, url_for

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from ui.config import DATASET_ROOT, MODEL_ROOT
from ui.forms import scan_models
from ui.task_manager import TaskManager

videogen_bp = Blueprint('videogen', __name__)


@videogen_bp.route('/', methods=['GET'])
def videogen_form():
    models = scan_models(MODEL_ROOT)
    renderable = [m for m in models if m['has_ply']]
    return render_template('videogen.html', models=renderable, model_root=MODEL_ROOT)


@videogen_bp.route('/start', methods=['POST'])
def start_videogen():
    data = request.form
    model_rel = data.get('model_path', '')
    model_abs = os.path.join(MODEL_ROOT, model_rel)
    if not model_rel or not os.path.isdir(model_abs):
        return jsonify({'error': 'Invalid model path'}), 400

    iterations = [d for d in os.listdir(os.path.join(model_abs, 'point_cloud'))
                  if os.path.isfile(os.path.join(model_abs, 'point_cloud', d, 'point_cloud.ply'))]
    if not iterations:
        return jsonify({'error': 'No PLY checkpoint found'}), 400
    if 'iteration_30000' in iterations:
        iter_name = 'iteration_30000'
    else:
        iter_name = sorted(iterations)[-1]

    iteration = int(data.get('iteration', iter_name.replace('iteration_', '')))

    task_manager = TaskManager.instance()
    task_id = task_manager.start_task(
        'videogen',
        {
            'model_path': model_rel,
            'iteration': iteration,
            'load_vq': data.get('load_vq', 'true').lower() == 'true',
            'video': data.get('video', 'true').lower() == 'true',
            'circular': data.get('circular', 'false').lower() == 'true',
            'radius': data.get('radius', '5'),
            'fps': data.get('fps', '30'),
            'skip_train': data.get('skip_train', 'true').lower() == 'true',
            'skip_test': data.get('skip_test', 'true').lower() == 'true',
        },
        lambda task: _run_videogen(task)
    )
    return jsonify({'task_id': task_id, 'redirect': url_for('tasks.list_tasks')})


def _run_videogen(task):
    model_abs = os.path.join(MODEL_ROOT, task.params['model_path'])
    iteration = task.params['iteration']
    load_vq = task.params.get('load_vq', True)
    do_video = task.params.get('video', True)
    do_circular = task.params.get('circular', False)
    radius = float(task.params.get('radius', 5))
    fps = int(task.params.get('fps', 30))
    skip_train = task.params.get('skip_train', True)
    skip_test = task.params.get('skip_test', True)

    # Read cfg_args
    cfg_path = os.path.join(model_abs, 'cfg_args')
    with open(cfg_path) as f:
        cfg_str = f.read()
    cfg_ns = eval(cfg_str)

    from arguments import ModelParams, PipelineParams
    from argparse import ArgumentParser

    parser = ArgumentParser(add_help=False)
    ModelParams(parser, sentinel=True)
    PipelineParams(parser)
    defaults = parser.parse_args([])
    args_dict = vars(defaults)
    args_dict['source_path'] = cfg_ns.source_path
    args_dict['model_path'] = model_abs
    args_dict['white_background'] = getattr(cfg_ns, 'white_background', False)
    args_dict['eval'] = getattr(cfg_ns, 'eval', True)
    args_dict['sh_degree'] = getattr(cfg_ns, 'sh_degree', 3)
    args_dict['resolution'] = getattr(cfg_ns, 'resolution', -1)
    args_dict['data_device'] = 'cuda'
    args_dict['load_vq'] = load_vq
    args_dict['gaussians'] = False
    args_dict['mean'] = 0
    args_dict['std'] = 0.03
    args = Namespace(**args_dict)

    from render_video import render_sets

    print(f"Generating video for: {model_abs}")
    print(f"Iteration: {iteration}, Load VQ: {load_vq}")
    print(f"Video: {do_video}, Circular: {do_circular}, FPS: {fps}, Radius: {radius}")

    render_sets(
        args, iteration, args,
        skip_train=skip_train,
        skip_test=skip_test,
        video=do_video,
        circular=do_circular,
        radius=radius,
        fps=fps,
        args=args,
    )

    print("Video generation complete.")
    video_dir = os.path.join(model_abs, 'video')
    if os.path.isdir(video_dir):
        mp4s = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
        for mp4 in mp4s:
            size_mb = os.path.getsize(os.path.join(video_dir, mp4)) / 1024 / 1024
            print(f"Output video: {mp4} ({size_mb:.1f} MB)")
