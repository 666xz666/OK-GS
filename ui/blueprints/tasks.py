import queue
from flask import Blueprint, jsonify, render_template, Response

from ui.task_manager import TaskManager

tasks_bp = Blueprint('tasks', __name__)


@tasks_bp.route('/')
def list_tasks():
    tasks = TaskManager.instance().list_tasks()
    tasks_sorted = sorted(tasks, key=lambda t: t.created_at, reverse=True)
    return render_template('tasks.html', tasks=tasks_sorted)


@tasks_bp.route('/<task_id>/status')
def task_status(task_id):
    task = TaskManager.instance().get_task(task_id)
    if task is None:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify({
        'id': task.id,
        'type': task.type,
        'status': task.status,
        'params': task.params,
        'error': task.error,
        'result': task.result,
    })


@tasks_bp.route('/<task_id>/log')
def task_log(task_id):
    task = TaskManager.instance().get_task(task_id)
    if task is None:
        return Response('data: Task not found\n\n', mimetype='text/event-stream')

    def generate():
        while True:
            try:
                msg = task.log_queue.get(timeout=1)
                yield f'data: {msg}\n\n'
            except queue.Empty:
                if task.status in ('completed', 'failed'):
                    break
                yield ':\n\n'
        yield f'data: __STATUS__:{task.status}\n\n'
        if task.error:
            yield f'data: __ERROR__:{task.error}\n\n'

    return Response(generate(), mimetype='text/event-stream')
