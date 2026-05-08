import os
import json
from flask import Blueprint, render_template, abort, send_from_directory

from ui.config import MODEL_ROOT
from ui.forms import scan_models

models_bp = Blueprint('models', __name__)


@models_bp.route('/')
def list_models():
    models = scan_models(MODEL_ROOT)
    for m in models:
        if m['has_results']:
            results_path = os.path.join(m['abs_path'], 'results.json')
            try:
                with open(results_path) as f:
                    m['results'] = json.load(f)
            except Exception:
                m['results'] = None
        if m['has_comparison']:
            cmp_path = os.path.join(m['abs_path'], 'comparison_vq.json')
            try:
                with open(cmp_path) as f:
                    m['comparison'] = json.load(f)
            except Exception:
                m['comparison'] = None
    return render_template('models.html', models=models, model_root=MODEL_ROOT)


@models_bp.route('/<path:model_rel_path>')
def model_detail(model_rel_path):
    abs_path = os.path.join(MODEL_ROOT, model_rel_path)
    if not os.path.isdir(abs_path) or not os.path.isfile(os.path.join(abs_path, 'cfg_args')):
        abort(404)

    info = {'rel_path': model_rel_path, 'abs_path': abs_path}

    results = None
    results_path = os.path.join(abs_path, 'results.json')
    if os.path.isfile(results_path):
        try:
            with open(results_path) as f:
                results = json.load(f)
        except Exception:
            pass

    comparison = None
    cmp_path = os.path.join(abs_path, 'comparison_vq.json')
    if os.path.isfile(cmp_path):
        try:
            with open(cmp_path) as f:
                comparison = json.load(f)
        except Exception:
            pass

    per_view = None
    pv_path = os.path.join(abs_path, 'per_view.json')
    if os.path.isfile(pv_path):
        try:
            with open(pv_path) as f:
                raw = json.load(f)
            per_view = []
            count = 0
            for method, metrics in raw.items():
                ssim_dict = metrics.get('SSIM', {})
                psnr_dict = metrics.get('PSNR', {})
                lpips_dict = metrics.get('LPIPS', {})
                for img_name in sorted(ssim_dict.keys()):
                    if count >= 20:
                        break
                    per_view.append({
                        'method': method,
                        'image': img_name,
                        'SSIM': ssim_dict.get(img_name),
                        'PSNR': psnr_dict.get(img_name),
                        'LPIPS': lpips_dict.get(img_name),
                    })
                    count += 1
        except Exception:
            pass

    test_log = None
    log_path = os.path.join(abs_path, 'test_results.log')
    if os.path.isfile(log_path):
        try:
            with open(log_path) as f:
                test_log = f.read()
        except Exception:
            pass

    has_ply = os.path.isfile(os.path.join(abs_path, 'point_cloud.ply'))
    has_vq = os.path.isfile(os.path.join(abs_path, 'extreme_saving.zip'))
    has_video = False
    video_mp4 = None
    video_rel_dir = None
    for sub in ['video', 'circular']:
        d = os.path.join(abs_path, sub)
        if os.path.isdir(d):
            mp4s = [f for f in os.listdir(d) if f.endswith('.mp4')]
            if mp4s:
                has_video = True
                video_mp4 = mp4s[0]
                video_rel_dir = sub
                break

    render_samples = []
    for method_dir_name in ['ours_30000_original', 'ours_30000_vq', 'ours_30000']:
        method_path = os.path.join(abs_path, 'test', method_dir_name)
        if os.path.isdir(method_path):
            renders_dir = os.path.join(method_path, 'renders')
            if os.path.isdir(renders_dir):
                images = sorted(os.listdir(renders_dir))[:6]
                render_samples.append({
                    'method': method_dir_name,
                    'images': images,
                    'renders_dir': renders_dir,
                })

    return render_template('model_detail.html',
                           info=info,
                           results=results,
                           comparison=comparison,
                           per_view=per_view,
                           test_log=test_log,
                           has_ply=has_ply,
                           has_vq=has_vq,
                           has_video=has_video,
                           video_mp4=video_mp4,
                           video_rel_dir=video_rel_dir,
                           render_samples=render_samples,
                           model_rel_path=model_rel_path)


@models_bp.route('/<path:model_rel_path>/video/<filename>')
def serve_video(model_rel_path, filename):
    directory = os.path.join(MODEL_ROOT, model_rel_path, 'video')
    return send_from_directory(directory, filename)


@models_bp.route('/<path:model_rel_path>/circular/<filename>')
def serve_circular_video(model_rel_path, filename):
    directory = os.path.join(MODEL_ROOT, model_rel_path, 'circular')
    return send_from_directory(directory, filename)


@models_bp.route('/<path:model_rel_path>/test/<method>/renders/<filename>')
def serve_render(model_rel_path, method, filename):
    directory = os.path.join(MODEL_ROOT, model_rel_path, 'test', method, 'renders')
    return send_from_directory(directory, filename)
