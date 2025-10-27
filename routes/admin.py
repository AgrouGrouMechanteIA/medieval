from flask import Blueprint, request, session, redirect, url_for, render_template
from models import User
from game_logic import resolve_all_tasks, create_news
admin_bp = Blueprint('admin', __name__)

def current_user():
    uid = session.get('user_id')
    if not uid: return None
    return User.query.get(uid)

@admin_bp.route('/next_turn', methods=['POST','GET'])
def next_turn():
    user = current_user()
    if not user or not user.is_admin:
        return 'forbidden', 403
    results = resolve_all_tasks()
    if results:
        create_news('Admin advanced turn', '\n'.join(results))
    return render_template('admin_done.html', results=results)
