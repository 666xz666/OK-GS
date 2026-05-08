import os
from flask import Blueprint, render_template

from ui.config import DATASET_ROOT, MODEL_ROOT
from ui.forms import scan_datasets, scan_models
from ui.task_manager import TaskManager

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    datasets = scan_datasets(DATASET_ROOT)
    models = scan_models(MODEL_ROOT)
    tasks = TaskManager.instance().list_tasks()
    running = [t for t in tasks if t.status == 'running']
    completed = [t for t in tasks if t.status == 'completed']
    failed = [t for t in tasks if t.status == 'failed']

    total_scenes = sum(len(d['scenes']) for d in datasets)
    models_with_vq = sum(1 for m in models if m['has_vq'])
    models_with_results = sum(1 for m in models if m['has_results'])

    return render_template('index.html',
                           datasets=datasets,
                           total_scenes=total_scenes,
                           models=models,
                           models_count=len(models),
                           models_with_vq=models_with_vq,
                           models_with_results=models_with_results,
                           running_tasks=running,
                           completed_tasks=completed[-5:],
                           failed_tasks=failed[-5:])
