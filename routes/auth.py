from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from models import User, Player
from game_logic import seed_items

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET','POST'])
def register():
    error = None
    if request.method == 'POST':
        nickname = request.form.get('nickname')
        password = request.form.get('password')
        if not nickname or not password:
            error = 'Missing fields'
        elif User.query.filter_by(nickname=nickname).first():
            error = 'Nickname taken'
        else:
            u = User(nickname=nickname, password_hash=generate_password_hash(password))
            if User.query.count() == 0:
                u.is_admin = True
            db.session.add(u); db.session.commit()
            p = Player(user_id=u.id, nickname=nickname)
            db.session.add(p); db.session.commit()
            seed_items()
            session['user_id'] = u.id
            return redirect(url_for('world.game'))
    return render_template('register.html', error=error)

@auth_bp.route('/login', methods=['GET','POST'])
def login():
    error = None
    if request.method == 'POST':
        nickname = request.form.get('nickname')
        password = request.form.get('password')
        u = User.query.filter_by(nickname=nickname).first()
        if not u or not check_password_hash(u.password_hash, password):
            error = 'Invalid credentials'
        else:
            session['user_id'] = u.id
            return redirect(url_for('world.game'))
    return render_template('register.html', error=error)
