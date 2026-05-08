import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from flask import Flask

from ui.config import FLASK_HOST, FLASK_PORT, CUDA_DEVICE


def create_app():
    os.environ.setdefault('CUDA_VISIBLE_DEVICES', CUDA_DEVICE)

    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.secret_key = os.environ.get('GS_SECRET_KEY', 'gs-web-ui-dev-key')

    from ui.blueprints.main import main_bp
    from ui.blueprints.train import train_bp
    from ui.blueprints.quantize import quantize_bp
    from ui.blueprints.evaluate import eval_bp
    from ui.blueprints.videogen import videogen_bp
    from ui.blueprints.models import models_bp
    from ui.blueprints.tasks import tasks_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(train_bp, url_prefix='/train')
    app.register_blueprint(quantize_bp, url_prefix='/quantize')
    app.register_blueprint(eval_bp, url_prefix='/eval')
    app.register_blueprint(videogen_bp, url_prefix='/videogen')
    app.register_blueprint(models_bp, url_prefix='/models')
    app.register_blueprint(tasks_bp, url_prefix='/tasks')

    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template('base.html', content='<div class="alert alert-warning">Page not found.</div>'), 404

    return app


def main():
    app = create_app()
    print(f"Starting 3DGS Web UI on http://{FLASK_HOST}:{FLASK_PORT}")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False, threaded=True)


if __name__ == '__main__':
    main()
