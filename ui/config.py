import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

DATASET_ROOT = os.environ.get('GS_DATASET_ROOT', '/data/datasets')
MODEL_ROOT = os.environ.get('GS_MODEL_ROOT', os.path.join(PROJECT_ROOT, 'output'))
CUDA_DEVICE = os.environ.get('GS_CUDA_DEVICE', '0')
FLASK_HOST = os.environ.get('GS_HOST', '0.0.0.0')
FLASK_PORT = int(os.environ.get('GS_PORT', '8000'))
