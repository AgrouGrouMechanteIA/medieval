from flask import Blueprint, render_template, request, session, redirect, url_for
from models import TavernMessage, User
from extensions import db
tavern_bp = Blueprint('tavern', __name__)

def current_user():
    uid = session.get('user_id'); 
    if not uid: return None
    return User.query.get(uid)

@tavern_bp.route('/tavern/<location>', methods=['GET','POST'])
def tavern(location):
    user = current_user()
    if request.method == 'POST' and user:
        text = request.form.get('message')
        if text:
            m = TavernMessage(location=location, username=user.nickname, message=text)
            db.session.add(m); db.session.commit()
    messages = TavernMessage.query.filter_by(location=location).order_by(TavernMessage.created_at.desc()).limit(50).all()
    return render_template('tavern.html', location=location, messages=messages)
