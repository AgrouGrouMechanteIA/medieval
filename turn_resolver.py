"""
Turn resolver script.

Two ways to call:
- from the web admin route: POST /admin/next-turn (calls process_turn(app))
- from shell / periodic task: run this file directly:
    $ python turn_resolver.py
It will load the Flask app via create_app()
"""

import os
from datetime import datetime, timezone
from flask import Flask
from app import create_app, db
from models import User, Task, Boat, Item, Inventory, Message

def process_turn(flask_app):
    with flask_app.app_context():
        epoch = datetime(1970,1,1, tzinfo=timezone.utc)
        turn = (datetime.now(timezone.utc) - epoch).days

        # 1) Resolve tasks that have resolve_turn <= current turn
        pending = Task.query.filter(Task.status == 'pending', Task.resolve_turn <= turn).all()
        for t in pending:
            u = User.query.get(t.user_id)
            if not u:
                t.status = 'failed'
                continue
            # small examples of resolving
            if t.task_type == 'gather_forest':
                # give mushrooms/chestnuts
                import random
                qty = random.randint(2,7)
                item = Item.get_or_create('Mushroom', edible_hunger=2)
                inv = Inventory.query.filter_by(user_id=u.id, item_id=item.id).first()
                if not inv:
                    inv = Inventory(user_id=u.id, item_id=item.id, qty=0)
                    db.session.add(inv)
                inv.qty += qty
                t.status = 'done'
            elif t.task_type == 'plant_wheat':
                import random
                qty = random.randint(2,7)
                item = Item.get_or_create('Bag of Wheat', edible_hunger=0)
                inv = Inventory.query.filter_by(user_id=u.id, item_id=item.id).first()
                if not inv:
                    inv = Inventory(user_id=u.id, item_id=item.id, qty=0)
                    db.session.add(inv)
                inv.qty += qty
                t.status = 'done'
            elif t.task_type == 'work_for_king':
                import random
                wage = random.randint(8,15) * 20  # convert to shillings
                u.money_shillings += wage
                t.status = 'done'
            elif t.task_type == 'study':
                # grant intel sometimes
                import random
                if random.random() < 0.5:
                    u.intelligence += 1
                t.status = 'done'
            else:
                t.status = 'done'
        db.session.commit()

        # 2) Move boat(s)
        boats = Boat.query.all()
        for b in boats:
            import random
            if b.route and len(b.route) > 0:
                # 50% chance boat gets stuck (only between some indexes)
                stuck_chance = 0.0
                # example rule: if next is Temple Island or Risible Rock, chance to get stuck
                next_idx = (b.current_index + 1) % len(b.route)
                next_stop = b.route[next_idx]
                if next_stop in ['Temple Island','Risible Rock']:
                    stuck_chance = 0.5
                if b.stuck_turns >= 2:
                    # if stuck too long, reset stuck and move
                    b.stuck_turns = 0
                    b.current_index = next_idx
                else:
                    if random.random() < stuck_chance:
                        b.stuck_turns += 1
                    else:
                        b.current_index = next_idx
                        b.stuck_turns = 0
        db.session.commit()

        # 3) Hunger consequences — if hunger < max_hunger, lose 1 health
        users = User.query.all()
        for u in users:
            if u.hunger < 1:
                u.health = max(0, u.health - 1)
            # optionally: restore some hunger / regen? (not by default)
        db.session.commit()

        # 4) Post a news message saying turn advanced
        msg = Message(sender_id=None, body=f"Turn {turn} processed.", is_news=True)
        db.session.add(msg)
        db.session.commit()

if __name__ == '__main__':
    app = create_app()
    process_turn(app)
    print("Turn processed.")
