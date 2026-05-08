import os
import re
import sys
import shutil
import json
from argparse import Namespace

from flask import Blueprint, render_template, request, jsonify, url_for, session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from ui.config import DATASET_ROOT, MODEL_ROOT
from ui.forms import scan_models
from ui.task_manager import TaskManager
from ui.translations import make_translator

eval_bp = Blueprint('eval', __name__)


@eval_bp.route('/', methods=['GET'])
def eval_form():
    models = scan_models(MODEL_ROOT)
    renderable = [m for m in models if m['has_ply']]
    return render_template('evaluate.html', models=renderable, model_root=MODEL_ROOT)


@eval_bp.route('/start', methods=['POST'])
def start_eval():
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
    compare_vq = data.get('compare_vq', 'true').lower() == 'true'
    has_vq = os.path.isfile(os.path.join(model_abs, 'extreme_saving.zip'))

    task_manager = TaskManager.instance()
    task_id = task_manager.start_task(
        'eval',
        {
            'model_path': model_rel,
            'iteration': iteration,
            'compare_vq': compare_vq and has_vq,
            'skip_train': data.get('skip_train', 'true').lower() == 'true',
            'lang': session.get('lang', 'zh'),
        },
        lambda task: _run_evaluation(task)
    )
    return jsonify({'task_id': task_id, 'redirect': url_for('tasks.list_tasks')})


def _run_evaluation(task):
    _ = make_translator(task.params.get('lang', 'zh'))
    model_abs = os.path.join(MODEL_ROOT, task.params['model_path'])
    iteration = task.params['iteration']
    compare_vq = task.params.get('compare_vq', True)
    skip_train = task.params.get('skip_train', True)
    loaded_iter = iteration

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
    args = Namespace(**args_dict)

    test_dir = os.path.join(model_abs, 'test')
    if os.path.isdir(test_dir):
        for entry in os.listdir(test_dir):
            entry_path = os.path.join(test_dir, entry)
            if os.path.isdir(entry_path) and ('_original' in entry or '_vq' in entry):
                shutil.rmtree(entry_path)
                print(_('log.cleaned_old_dir', entry=entry))

    from render import render_sets

    # Step 1: Render original PLY
    print(_('log.rendering_original'))
    render_sets(args, loaded_iter, args, skip_train=skip_train, skip_test=False, load_vq=False)

    ours_dir_original = None
    for entry in os.listdir(test_dir):
        entry_path = os.path.join(test_dir, entry)
        if os.path.isdir(entry_path) and entry.startswith('ours_') and '_original' not in entry and '_vq' not in entry:
            new_name = entry + '_original'
            shutil.move(entry_path, os.path.join(test_dir, new_name))
            ours_dir_original = new_name
            print(_('log.renamed', old=entry, new=new_name))
            break

    original_fps = None
    if ours_dir_original:
        render_log_path = os.path.join(test_dir, ours_dir_original, 'renders')
        if os.path.isdir(render_log_path):
            n_frames = len([f for f in os.listdir(render_log_path) if f.endswith('.png')])
            print(_('log.original_frames', n=n_frames))

    # Step 2: Render VQ model
    if compare_vq:
        print(_('log.rendering_vq'))
        render_sets(args, loaded_iter, args, skip_train=skip_train, skip_test=False, load_vq=True)

        for entry in os.listdir(test_dir):
            entry_path = os.path.join(test_dir, entry)
            if os.path.isdir(entry_path) and entry.startswith('ours_') and '_original' not in entry and '_vq' not in entry:
                new_name = entry + '_vq'
                shutil.move(entry_path, os.path.join(test_dir, new_name))
                print(_('log.renamed', old=entry, new=new_name))
                break

    # Step 3: Compute metrics
    print(_('log.computing_metrics'))
    from metrics import evaluate
    evaluate([model_abs])

    # Step 4: Compute file sizes
    results_path = os.path.join(model_abs, 'results.json')
    if os.path.isfile(results_path):
        with open(results_path) as f:
            results = json.load(f)
    else:
        results = {}

    ply_path = os.path.join(model_abs, 'point_cloud', f'iteration_{loaded_iter}', 'point_cloud.ply')
    zip_path = os.path.join(model_abs, 'extreme_saving.zip')

    comparison = {}
    iter_str = str(loaded_iter)

    for scene_name, methods in results.items():
        orig_key = f'ours_{iter_str}_original'
        vq_key = f'ours_{iter_str}_vq'
        if orig_key in methods:
            comparison['original'] = methods[orig_key]
        if vq_key in methods:
            comparison['vq'] = methods[vq_key]

    if comparison.get('original') and comparison.get('vq'):
        comparison['delta'] = {
            'SSIM': round(comparison['vq']['SSIM'] - comparison['original']['SSIM'], 4),
            'PSNR': round(comparison['vq']['PSNR'] - comparison['original']['PSNR'], 2),
            'LPIPS': round(comparison['vq']['LPIPS'] - comparison['original']['LPIPS'], 4),
        }

    comparison['mem'] = {}
    if os.path.isfile(ply_path):
        comparison['mem']['original_bytes'] = os.path.getsize(ply_path)
        comparison['mem']['original_mb'] = round(os.path.getsize(ply_path) / 1024 / 1024, 2)
    if os.path.isfile(zip_path):
        comparison['mem']['vq_bytes'] = os.path.getsize(zip_path)
        comparison['mem']['vq_mb'] = round(os.path.getsize(zip_path) / 1024 / 1024, 2)

    if comparison['mem'].get('original_bytes') and comparison['mem'].get('vq_bytes'):
        ratio = comparison['mem']['vq_bytes'] / comparison['mem']['original_bytes'] * 100
        comparison['mem']['compression_ratio'] = round(ratio, 1)

    cmp_path = os.path.join(model_abs, 'comparison_vq.json')
    with open(cmp_path, 'w') as f:
        json.dump(comparison, f, indent=2)

    # Print summary table
    print("\n" + "=" * 60)
    if comparison:
        print(f"  {'Metric':<12} {'Original':<12} {'VQ':<12} {'Delta':<12}")
        print(f"  {'-'*50}")
        for metric in ['SSIM', 'PSNR', 'LPIPS']:
            if 'original' in comparison and 'vq' in comparison:
                orig_val = comparison['original'][metric]
                vq_val = comparison['vq'][metric]
                delta_val = comparison['delta'][metric]
                print(f"  {metric:<12} {orig_val:<12.4f} {vq_val:<12.4f} {delta_val:<+12.4f}")
        if 'mem' in comparison:
            print(f"  {'MEM':<12} {comparison['mem'].get('original_mb', 'N/A'):<12} {comparison['mem'].get('vq_mb', 'N/A'):<12}")
    print("=" * 60)
    print(_('log.eval_complete'))
