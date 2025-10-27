import random
from datetime import datetime, timezone
from extensions import db
from models import Item, Inventory, Player, Boat, Task, News, Listing, Property

def get_turn_number():
    epoch = datetime(1970,1,1, tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - epoch).days

WORLD_CITIES = ['Beautiful Forest','Not-New-Eden','Ocean View','Temple Island','Risible Rock']

def ensure_world():
    if not Boat.query.first():
        b = Boat(name='The Boat', route=WORLD_CITIES, current_index=2)
        db.session.add(b)
        db.session.commit()

def seed_items():
    names = [
        ('Chestnut',1), ('Bread',2), ('Fish',2), ('Mushroom',2),
        ('Wild Herb',0), ('Health Potion',0), ('Bag of Wheat',0), ('Bag of Flour',0),
        ('Corn Bag',2), ('Bean Bag',2), ('Banana',1), ('Cactus',1), ('Disgusting Insect',1)
    ]
    for n,h in names:
        if not Item.query.filter_by(name=n).first():
            db.session.add(Item(name=n, edible_hunger=h))
    db.session.commit()

def add_item_to_player(player, item_name, qty=1):
    item = Item.query.filter_by(name=item_name).first()
    if not item:
        item = Item(name=item_name)
        db.session.add(item); db.session.commit()
    inv = Inventory.query.filter_by(player_id=player.id, item_id=item.id).first()
    if not inv:
        inv = Inventory(player_id=player.id, item_id=item.id, qty=qty)
        db.session.add(inv)
    else:
        inv.qty += qty
    db.session.commit()
    return inv

def consume_item(player, item_name):
    item = Item.query.filter_by(name=item_name).first()
    if not item:
        return False, 'no such item'
    inv = Inventory.query.filter_by(player_id=player.id, item_id=item.id).first()
    if not inv or inv.qty <= 0:
        return False, 'not enough items'
    inv.qty -= 1
    player.hunger = min(2, player.hunger + (item.edible_hunger or 0))
    db.session.commit()
    return True, {'hunger': player.hunger}

def start_task(player, task_type, params=None):
    if params is None: params = {}
    turn = get_turn_number()
    existing = Task.query.filter_by(player_id=player.id, turn_number=turn, status='pending').first()
    if existing:
        return False, 'already have a task this turn'
    resolve_after = {'plant_wheat':4, 'plant_vegetable':2}.get(task_type, 1)
    t = Task(player_id=player.id, task_type=task_type, params=params, turn_number=turn, resolve_turn=turn+resolve_after)
    db.session.add(t); db.session.commit()
    return True, t.id

def resolve_all_tasks():
    turn = get_turn_number()
    tasks = Task.query.filter(Task.resolve_turn <= turn).all()
    results = []
    for t in tasks:
        p = Player.query.get(t.player_id)
        if not p:
            db.session.delete(t); continue
        if t.task_type == 'work_king':
            wage = random.randint(8,15) * 20
            p.money_shillings += wage
            results.append(f'Player {p.nickname} earned {wage//20}£ {wage%20}s from king work')
        elif t.task_type == 'plant_wheat':
            prop = Property(player_id=p.id, location=p.location, planted_item='Bag of Wheat', planted_at_turn=t.turn_number, ready_at_turn=t.resolve_turn)
            db.session.add(prop)
            results.append(f'{p.nickname} planted wheat')
        elif t.task_type == 'harvest':
            qty = random.randint(2,7)
            add_item_to_player(p, 'Bag of Wheat', qty)
            results.append(f'{p.nickname} harvested {qty} Bag(s) of Wheat')
        db.session.delete(t)
    db.session.commit()
    move_boat()
    for p in Player.query.all():
        if p.hunger <= 0:
            p.health = max(0, p.health - 1)
    db.session.commit()
    for r in results:
        db.session.add(News(title='Task result', body=r))
    db.session.commit()
    return results

def move_boat():
    b = Boat.query.first()
    if not b: return
    b.current_index = (b.current_index + 1) % len(b.route)
    db.session.commit()

def create_news(title, body):
    n = News(title=title, body=body)
    db.session.add(n); db.session.commit()
    return n
