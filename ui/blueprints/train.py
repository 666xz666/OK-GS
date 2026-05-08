import os
import sys
from argparse import Namespace
from unittest.mock import patch

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from ui.config import DATASET_ROOT, MODEL_ROOT
from ui.forms import scan_datasets, scan_models, build_train_args
from ui.task_manager import TaskManager

train_bp = Blueprint('train', __name__)


@train_bp.route('/', methods=['GET'])
def train_form():
    datasets = scan_datasets(DATASET_ROOT)
    models = scan_models(MODEL_ROOT)
    return render_template('train.html', datasets=datasets, models=models,
                           dataset_root=DATASET_ROOT, model_root=MODEL_ROOT)


@train_bp.route('/start', methods=['POST'])
def start_train():
    data = request.form
    scene_path = data.get('source_path', '')
    if not scene_path or not os.path.isdir(scene_path):
        return jsonify({'error': 'Invalid dataset path'}), 400

    scene_rel = os.path.relpath(scene_path, DATASET_ROOT) if scene_path.startswith(DATASET_ROOT) else os.path.basename(scene_path)
    model_path = data.get('model_path', '').strip()
    if not model_path:
        model_path = os.path.join(MODEL_ROOT, scene_rel)

    task_manager = TaskManager.instance()
    task_id = task_manager.start_task(
        'train',
        {
            'source_path': scene_path,
            'model_path': model_path,
            'resolution': data.get('resolution', '-1'),
            'sh_degree': data.get('sh_degree', '3'),
            'iterations': data.get('iterations', '30000'),
            'v_pow': data.get('v_pow', '0.1'),
            'eval': data.get('eval', 'true'),
        },
        lambda task: _run_training(task)
    )
    return jsonify({'task_id': task_id, 'redirect': url_for('tasks.list_tasks')})


def _run_training(task):
    from arguments import ModelParams, PipelineParams, OptimizationParams
    from argparse import ArgumentParser

    parser = ArgumentParser(add_help=False)
    ModelParams(parser, sentinel=True)
    OptimizationParams(parser)
    PipelineParams(parser)

    defaults = parser.parse_args([])
    args_dict = vars(defaults)

    args_dict['source_path'] = task.params['source_path']
    args_dict['model_path'] = task.params['model_path']
    args_dict['resolution'] = int(task.params.get('resolution', -1))
    args_dict['sh_degree'] = int(task.params.get('sh_degree', 3))
    args_dict['iterations'] = int(task.params.get('iterations', 30000))
    args_dict['v_pow'] = float(task.params.get('v_pow', 0.1))
    args_dict['eval'] = task.params.get('eval', 'true').lower() == 'true'
    args_dict['ip'] = '127.0.0.1'
    args_dict['port'] = 6009

    args = Namespace(**args_dict)
    args.save_iterations = [30000]
    args.test_iterations = [30000]
    args.checkpoint_iterations = []
    args.start_checkpoint = None
    args.debug_from = -1
    args.detect_anomaly = False
    args.quiet = False
    args.save_iterations.append(args.iterations)

    print(f"Optimizing {args.model_path}")
    print(f"Source: {args.source_path}")
    print(f"Resolution: {args.resolution}, SH Degree: {args.sh_degree}, Iterations: {args.iterations}")

    from utils.general_utils import safe_state
    safe_state(args.quiet)

    import gaussian_renderer.network_gui as network_gui
    original_init = network_gui.init
    network_gui.init = lambda *a, **kw: None

    try:
        from train import training
        training(
            lp.extract(args), op.extract(args), pp.extract(args),
            args.test_iterations, args.save_iterations,
            args.checkpoint_iterations, args.start_checkpoint, args.debug_from
        )
    finally:
        network_gui.init = original_init

    print("Training complete.")

    # Verify outputs
    imp_path = os.path.join(args.model_path, 'imp_score.npz')
    ply_dir = os.path.join(args.model_path, 'point_cloud')
    if os.path.isfile(imp_path):
        print(f"Importance scores saved: {imp_path}")
    if os.path.isdir(ply_dir):
        print(f"Model directory: {ply_dir}")
