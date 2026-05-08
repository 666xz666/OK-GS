from flask import Blueprint, session, redirect, request

from ui.translations import translations, make_translator

language_bp = Blueprint('language', __name__)

SUPPORTED_LANGS = {'zh', 'en'}
DEFAULT_LANG = 'zh'


def get_current_lang():
    lang = session.get('lang', DEFAULT_LANG)
    if lang not in SUPPORTED_LANGS:
        lang = DEFAULT_LANG
    return lang


def init_i18n(app):
    @app.before_request
    def set_lang_default():
        if 'lang' not in session or session['lang'] not in SUPPORTED_LANGS:
            session['lang'] = DEFAULT_LANG

    @app.context_processor
    def inject_i18n():
        lang = get_current_lang()
        return {
            '_': make_translator(lang),
            'current_lang': lang,
        }


@language_bp.route('/set_lang/<lang>')
def set_lang(lang):
    if lang in SUPPORTED_LANGS:
        session['lang'] = lang
    return redirect(request.referrer or '/')
