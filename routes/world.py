from flask import Blueprint, render_template, session, redirect, url_for
from models import Player, Boat
from game_logic import ensure_world, get_turn_number, add_item_to_player
world_bp = Blueprint('world', __name__)

def current_user():
    from models import User
    uid = session.get('user_id')
    if not uid:
        return None
    return User.query.get(uid)

@world_bp.route('/game')
def game():
    user = current_user()
    if not user:
        return redirect(url_for('auth.login'))
    player = user.player
    ensure_world()
    boat = Boat.query.first()
    boat_pos = boat.route[boat.current_index] if boat and boat.route else 'Unknown'
    if sum(i.qty for i in player.inventory) == 0:
        add_item_to_player(player, 'Chestnut', 2)
    turn = get_turn_number()
    return render_template('base.html', player=player, boat_pos=boat_pos, turn=turn)
