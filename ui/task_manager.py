import threading
import queue
import uuid
import sys
import time
from io import StringIO

from ui.translations import make_translator


class TaskConflictError(RuntimeError):
    def __init__(self, active_task):
        super().__init__('Another task is already active')
        self.active_task = active_task


class StreamCapture:
    def __init__(self, log_queue, orig_stream):
        self._queue = log_queue
        self._orig = orig_stream
        self._buf = ''

    def write(self, s):
        if s is None:
            return
        self._orig.write(s)
        self._buf += s
        while '\n' in self._buf:
            line, self._buf = self._buf.split('\n', 1)
            line = line.replace('\r', '')
            if line.strip():
                self._queue.put(line + '\n')

    def flush(self):
        self._orig.flush()
        if self._buf.strip():
            self._queue.put(self._buf + '\n')
            self._buf = ''

    def isatty(self):
        return False


class TaskInfo:
    def __init__(self, task_id, task_type, params, log_queue):
        self.id = task_id
        self.type = task_type
        self.params = params
        self.status = 'pending'
        self.log_queue = log_queue
        self.result = None
        self.error = None
        self.created_at = time.time()
        self.finished_at = None


class TaskManager:
    _instance = None

    def __init__(self):
        self.tasks = {}
        self._lock = threading.Lock()

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start_task(self, task_type, params, run_fn):
        with self._lock:
            active_task = self._find_active_task_locked()
            if active_task is not None:
                raise TaskConflictError(active_task)

            task_id = str(uuid.uuid4())[:8]
            log_queue = queue.Queue()
            task = TaskInfo(task_id, task_type, params, log_queue)
            self.tasks[task_id] = task

        thread = threading.Thread(
            target=self._run_task,
            args=(task, run_fn),
            daemon=True,
        )
        thread.start()
        return task_id

    def get_task(self, task_id):
        with self._lock:
            return self.tasks.get(task_id)

    def list_tasks(self):
        with self._lock:
            return list(self.tasks.values())

    def get_active_task(self):
        with self._lock:
            return self._find_active_task_locked()

    def has_active_task(self):
        return self.get_active_task() is not None

    def _find_active_task_locked(self):
        active_tasks = [
            task for task in self.tasks.values()
            if task.status in ('pending', 'running')
        ]
        if not active_tasks:
            return None
        return min(active_tasks, key=lambda task: task.created_at)

    def _run_task(self, task, run_fn):
        task.status = 'running'
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        capture_out = StreamCapture(task.log_queue, old_stdout)
        capture_err = StreamCapture(task.log_queue, old_stderr)
        sys.stdout = capture_out
        sys.stderr = capture_err
        try:
            result = run_fn(task)
            task.result = result
            task.status = 'completed'
        except Exception as e:
            import traceback
            _ = make_translator(task.params.get('lang', 'zh'))
            task.log_queue.put(f'{_("misc.error")}: {e}\n{traceback.format_exc()}\n')
            task.error = str(e)
            task.status = 'failed'
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            task.finished_at = time.time()
