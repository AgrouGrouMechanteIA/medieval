from flask import Blueprint, request, jsonify, session
from models import User, Player, Item, Inventory
from game_logic import consume_item, add_item_to_player
api_bp = Blueprint('api', __name__)

def current_player():
    uid = session.get('user_id')
    if not uid: return None
    u = User.query.get(uid)
    return u.player if u else None

@api_bp.route('/player')
def player_info():
    p = current_player()
    if not p: return jsonify({'error':'unauthenticated'}),401
    inv = [{'name':it.item.name, 'qty':it.qty} for it in p.inventory]
    return jsonify({'nickname':p.nickname,'health':p.health,'hunger':p.hunger,'inventory':inv})

@api_bp.route('/eat', methods=['POST'])
def eat():
    p = current_player()
    if not p: return jsonify({'error':'unauthenticated'}),401
    item = request.json.get('item')
    ok, res = consume_item(p, item)
    if not ok: return jsonify({'error':res}),400
    return jsonify({'ok':True,'hunger':res['hunger']})
