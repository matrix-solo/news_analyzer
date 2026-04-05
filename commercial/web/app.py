#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask Webåºç¨
åä¸çWebçé
"""

import logging
import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from functools import wraps

base_path = Path(__file__).parent.parent
sys.path.insert(0, str(base_path))

from compliance import CommercialSourceFilter, SensitiveContentFilter, FieldMapper
from subscription import SubscriberManager
from services import CommercialEmailService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("WebApp")

app = Flask(
    __name__,
    template_folder=str(base_path / "web" / "templates"),
    static_folder=str(base_path / "web" / "static")
)
app.secret_key = 'your-secret-key-change-in-production'

source_filter = CommercialSourceFilter(
    config_path=str(base_path / "config" / "sources_commercial.yaml")
)
content_filter = SensitiveContentFilter(
    keywords_path=str(base_path / "compliance" / "keywords.yaml")
)
field_mapper = FieldMapper(
    config_path=str(base_path / "compliance" / "keywords.yaml")
)
subscriber_manager = SubscriberManager()
email_service = CommercialEmailService()

def admin_required(f):
    """ç®¡çåæéè£é¥°å¨"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        is_admin = request.args.get('admin') == 'true'
        if not is_admin:
            return jsonify({'error': 'éè¦ç®¡çåæé'}), 403
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """é¦é¡µ"""
    stats = subscriber_manager.get_subscriber_count()
    sources = source_filter.get_allowed_sources()
    return render_template('index.html', stats=stats, sources=sources)

@app.route('/subscribe', methods=['GET', 'POST'])
def subscribe():
    """è®éé¡µé"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()

        if not email or '@' not in email:
            flash('è¯·è¾å¥ææçé®ç®±å°å', 'error')
            return render_template('subscribe.html')

        if subscriber_manager.add_subscriber(email):
            flash('è®éæåïæ¨å°æ¶å°æ¯æ¥æ°éåææ¥åã?, 'success'')
        else:
            flash('è®éå¤±è'¥ïè¯·ç¨åéè¯', 'error'')

        return render_template('subscribe.html')

    return render_template('subscribe.html')

@app.route('/unsubscribe', methods=['GET', 'POST'])
def unsubscribe():
    """åæ¶è®é"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()

        if subscriber_manager.remove_subscriber(email):
            flash('å·²æååæ¶è®é?, 'success'')
        else:
            flash('åæ¶è®éå¤±è'¥ïè¯·æ£æ¥é®ç®±æ¯å¦æ­£ç¡?, 'error')

        return render_template('unsubscribe.html')

    return render_template('unsubscribe.html')

@app.route('/admin')
@admin_required
def admin():
    """ç®¡çåå°"""
    stats = subscriber_manager.get_subscriber_count()
    subscribers = subscriber_manager.get_active_subscribers()
    return render_template('admin.html', stats=stats, subscribers=subscribers)

@app.route('/api/stats', methods=['GET'])
def api_stats():
    """è·åçè®¡æ°æ®"""
    stats = subscriber_manager.get_subscriber_count()
    return jsonify({
        'success': True,
        'data': stats
    })

@app.route('/api/subscribers', methods=['GET'])
@admin_required
def api_subscribers():
    """è·åè®éèåè¡?""
    subscribers = subscriber_manager.get_active_subscribers()
    return jsonify({
        'success': True,
        'data': [
            {
                'email': s.email,
                'subscription_type': s.subscription_type,
                'created_at': s.created_at
            }
            for s in subscribers
        ]
    })

@app.route('/api/subscribe', methods=['POST'])
def api_subscribe():
    """APIè®é"""
    data = request.get_json() or {}
    email = data.get('email', '').strip()

    if not email or '@' not in email:
        return jsonify({'success': False, 'error': 'æ æçé®ç®±å°å'}), 400

    if subscriber_manager.add_subscriber(email):
        return jsonify({'success': True, 'message': 'è®éæå'})
    else:
        return jsonify({'success': False, 'error': 'è®éå¤±è'¥'}), 500'

@app.route('/api/unsubscribe', methods=['POST'])
def api_unsubscribe():
    """APIåæ¶è®é"""
    data = request.get_json() or {}
    email = data.get('email', '').strip()

    if subscriber_manager.remove_subscriber(email):
        return jsonify({'success': True, 'message': 'å·²åæ¶è®é?}')
    else:
        return jsonify({'success': False, 'error': 'åæ¶è®éå¤±è'¥'}), 500'

@app.route('/api/check-content', methods=['POST'])
def api_check_content():
    """æ£æµåå®åèæ?""
    data = request.get_json() or {}
    title = data.get('title', '')
    content = data.get('content', '')

    full_content = f"{title} {content}"
    result = content_filter.filter_content(full_content)

    return jsonify({
        'success': True,
        'data': {
            'passed': result.passed,
            'action': result.action,
            'reason': result.reason
        }
    })

@app.route('/api/check-source', methods=['POST'])
def api_check_source():
    """æ£æµä¿¡æº?""
    data = request.get_json() or {}
    source = data.get('source', '')

    result = source_filter.filter_source(source)

    return jsonify({
        'success': True,
        'data': {
            'passed': result.passed,
            'reason': result.reason
        }
    })

@app.route('/api/map-field', methods=['POST'])
def api_map_field():
    """éåæ å°"""
    data = request.get_json() or {}
    field = data.get('field', '')

    mapped = field_mapper.map_field(field)

    return jsonify({
        'success': True,
        'data': {
            'original': field,
            'mapped': mapped
        }
    })

def create_app():
    """ååºåºç¨å®ä¾"""
    return app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
