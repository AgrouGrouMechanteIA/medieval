from flask import Blueprint, render_template, session, redirect, url_for
from models import Property, User
prop_bp = Blueprint('properties', __name__, url_prefix='/properties')

def current_user():
    uid = session.get('user_id'); 
    if not uid: return None
    return User.query.get(uid)

@prop_bp.route('/')
def list_props():
    user = current_user()
    if not user: return redirect(url_for('auth.login'))
    player = user.player
    props = Property.query.filter_by(player_id=player.id).all()
    return render_template('property.html', properties=props)
