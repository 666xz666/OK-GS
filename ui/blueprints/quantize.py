import os
import sys
from argparse import Namespace
from unittest.mock import patch

from flask import Blueprint, render_template, request, jsonify, url_for, session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from ui.config import DATASET_ROOT, MODEL_ROOT
from ui.forms import scan_models
from ui.task_manager import TaskManager, TaskConflictError
from ui.translations import make_translator

quantize_bp = Blueprint('quantize', __name__)


@quantize_bp.route('/', methods=['GET'])
def quantize_form():
    models = scan_models(MODEL_ROOT)
    quantizable = [m for m in models if m['has_ply'] and m['has_imp']]
    return render_template('quantize.html', models=quantizable, model_root=MODEL_ROOT)


@quantize_bp.route('/start', methods=['POST'])
def start_quantize():
    _ = make_translator(session.get('lang', 'zh'))
    data = request.form
    model_rel = data.get('model_path', '')
    model_abs = os.path.join(MODEL_ROOT, model_rel)
    if not model_rel or not os.path.isdir(model_abs):
        return jsonify({'error': 'Invalid model path'}), 400

    imp_path = os.path.join(model_abs, 'imp_score.npz')
    if not os.path.isfile(imp_path):
        return jsonify({'error': 'Model has no importance scores. Run training first.'}), 400
    if os.path.isfile(os.path.join(model_abs, 'extreme_saving.zip')):
        return jsonify({'error': _('quantize.already_exists')}), 400

    iterations = [d for d in os.listdir(os.path.join(model_abs, 'point_cloud'))
                  if os.path.isfile(os.path.join(model_abs, 'point_cloud', d, 'point_cloud.ply'))]
    if not iterations:
        return jsonify({'error': 'No PLY checkpoint found'}), 400
    if 'iteration_30000' in iterations:
        iter_name = 'iteration_30000'
    else:
        iter_name = sorted(iterations)[-1]

    input_ply = os.path.join(model_abs, 'point_cloud', iter_name, 'point_cloud.ply')

    task_manager = TaskManager.instance()
    try:
        task_id = task_manager.start_task(
            'quantize',
            {
                'model_path': model_rel,
                'input_path': input_ply,
                'important_score_npz_path': model_abs,
                'save_path': model_abs,
                'sh_degree': data.get('sh_degree', '3'),
                'vq_ratio': data.get('vq_ratio', '0.6'),
                'codebook_size': data.get('codebook_size', '8192'),
                'iteration_num': data.get('iteration_num', '1000'),
                'lang': session.get('lang', 'zh'),
            },
            lambda task: _run_quantization(task)
        )
    except TaskConflictError:
        return jsonify({'error': _('task.active_blocked')}), 409
    return jsonify({'task_id': task_id, 'redirect': url_for('tasks.list_tasks')})


def _run_quantization(task):
    _ = make_translator(task.params.get('lang', 'zh'))

    import torch
    torch.cuda.set_device(0)

    import vectree.vectree as vq_module
    vq_module.device = torch.device('cuda')

    opt = Namespace(
        important_score_npz_path=task.params['important_score_npz_path'],
        input_path=task.params['input_path'],
        save_path=task.params['save_path'],
        sh_degree=int(task.params.get('sh_degree', 3)),
        vq_ratio=float(task.params.get('vq_ratio', 0.6)),
        codebook_size=int(task.params.get('codebook_size', 8192)),
        iteration_num=int(task.params.get('iteration_num', 1000)),
        no_IS=False,
        no_load_data=False,
        no_save_ply=False,
        vq_way='half',
    )

    print(_('log.quantizing_model', path=opt.input_path))
    print(_('log.vq_config', ratio=opt.vq_ratio, codebook=opt.codebook_size, iters=opt.iteration_num))
    print(_('log.save_path', path=opt.save_path))

    q = vq_module.Quantization(opt)
    q.quantize()

    import zipfile
    save_path = opt.save_path
    zip_path = os.path.join(save_path, 'extreme_saving.zip')
    src_dir = os.path.join(save_path, 'extreme_saving')
    if os.path.isdir(src_dir):
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(src_dir):
                for fn in files:
                    abs_fn = os.path.join(root, fn)
                    arcname = os.path.relpath(abs_fn, save_path)
                    zf.write(abs_fn, arcname)
        size_mb = os.path.getsize(zip_path) / 1024 / 1024
        print(_('log.size_mb', size=size_mb))

    q.dequantize()
    print(_('log.quantization_complete'))
