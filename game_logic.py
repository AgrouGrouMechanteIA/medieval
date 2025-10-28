# game_logic.py
from datetime import datetime, timezone, timedelta
import random
from extensions import db
from models import User, Task, Item, Inventory, Boat, City, Listing, News
from sqlalchemy import and_

# Global constants (tweakable)
SHILLINGS_PER_POUND = 20
LEVEL2_PRICE_SHILLINGS = 55 * SHILLINGS_PER_POUND  # 1100 shillings
PROPERTY_PRICE_SHILLINGS = 45 * SHILLINGS_PER_POUND  # 900 shillings
GRAND_BOAT_CONSTRUCTION_UNITS = 10

# Boat immune legs set: any pair among these is immune
IMMUNE_BOAT_LEG_CITIES = {"ocean_view", "not_new_eden", "beautiful_forest"}

# Weighted distribution for "Work for the King" pay:
# more weight for 8-10 shillings
KING_PAY_POUNDS = [8, 8, 8, 9, 9, 10, 10, 10, 11, 12, 13, 14, 15]  # 8-10 more probable

# Helper: compute current turn number (days since epoch UTC)
def get_turn_number(now: datetime = None):
    now = now or datetime.now(timezone.utc)
    # Count days from Unix epoch in UTC
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    delta = now - epoch
    return delta.days

# Start a task for a user; enforces one task per user per turn
def start_task(user: User, action: str, params: dict = None, delay_turns: int = 1):
    params = params or {}
    current_turn = get_turn_number()
    # Check existing tasks for this turn (unresolved)
    existing = Task.query.filter_by(user_id=user.id, resolved=False).filter(Task.resolve_turn > current_turn - 1).first()
    if existing:
        raise ValueError("You already have a task in progress for this turn.")
    task = Task(
        user_id=user.id,
        action=action,
        params=params,
        start_turn=current_turn,
        resolve_turn=current_turn + delay_turns
    )
    db.session.add(task)
    db.session.commit()
    return task

# Immediate actions
def eat_item(user: User, item_key: str, quantity: int = 1):
    # Find item & inventory entry
    item = Item.query.filter_by(key=item_key).first()
    if not item:
        raise ValueError("Unknown item")
    inv = Inventory.query.filter_by(user_id=user.id, item_id=item.id).first()
    if not inv or inv.quantity < quantity:
        raise ValueError("Not enough items")
    # consume items
    inv.quantity -= quantity
    if inv.quantity == 0:
        db.session.delete(inv)
    # hunger restored immediately (up to max_hunger)
    hunger_gain = item.edible_hunger * quantity
    user.hunger = min(user.max_hunger, (user.hunger or 0) + hunger_gain)
    db.session.commit()
    return {"ok": True, "hunger": user.hunger}

def drink_health_potion(user: User, item_key="health_potion", quantity: int = 1):
    # uses same mechanics, restores health immediately
    item = Item.query.filter_by(key=item_key).first()
    if not item:
        raise ValueError("No such potion")
    inv = Inventory.query.filter_by(user_id=user.id, item_id=item.id).first()
    if not inv or inv.quantity < quantity:
        raise ValueError("Not enough potions")
    inv.quantity -= quantity
    if inv.quantity == 0:
        db.session.delete(inv)
    user.health = min(user.max_health, (user.health or 0) + 1 * quantity)
    db.session.commit()
    return {"ok": True, "health": user.health}

# Resolve tasks at turn end
def resolve_all_tasks():
    current_turn = get_turn_number()
    tasks = Task.query.filter(Task.resolve_turn <= current_turn, Task.resolved == False).all()
    news_items = []
    for task in tasks:
        try:
            user = User.query.get(task.user_id)
            result = resolve_task_for_user(user, task)
            task.result = result
            task.resolved = True
            db.session.add(task)
            # give xp for completing tasks
            xp_gain = determine_xp_for_action(task.action)
            user.xp = (user.xp or 0) + xp_gain
            leveled = user.maybe_level_up()
            if leveled:
                news_items.append({
                    "title": f"{user.username} leveled up to {user.level}!",
                    "body": f"{user.username} reached level {user.level}.",
                    "meta": {"user_id": user.id}
                })
            db.session.add(user)
        except Exception as e:
            # log error and continue
            print("Error resolving task", task.id, e)
    # Boat movement and stuck logic (handled independently)
    process_boats(current_turn, news_items)
    # Starvation and hunger reset: apply health loss for hunger < 2, then set hunger = 0
    users = User.query.all()
    for u in users:
        if (u.hunger or 0) < 2:
            u.health = max(0, (u.health or 0) - 1)  # lose 1 HP
        u.hunger = 0
        db.session.add(u)
    # persist news items
    for n in news_items:
        news = News(title=n["title"], body=n["body"], meta=n.get("meta", {}))
        db.session.add(news)
    db.session.commit()

def resolve_task_for_user(user: User, task: Task):
    action = task.action
    params = task.params or {}
    # Basic set of actions we understand from your spec
    if action == "gather_mushrooms":
        # yields 2-7 mushrooms
        qty = random.randint(2, 7)
        add_item_to_user(user, "mushroom", qty)
        return {"gained": {"mushroom": qty}}
    elif action == "gather_chestnuts":
        qty = random.randint(2, 7)
        add_item_to_user(user, "chestnut", qty)
        return {"gained": {"chestnut": qty}}
    elif action == "gather_wild_herbs":
        qty = random.randint(2, 4)
        add_item_to_user(user, "wild_herb", qty)
        return {"gained": {"wild_herb": qty}}
    elif action == "gather_fruits":
        qty = random.randint(0, 3)
        add_item_to_user(user, "fruit", qty)
        return {"gained": {"fruit": qty}}
    elif action == "plant_wheat":
        # delay handled via task delay; on completion give 2-7 wheat bags
        qty = random.randint(2, 7)
        add_item_to_user(user, "bag_of_wheat", qty)
        return {"gained": {"bag_of_wheat": qty}}
    elif action == "plant_vegetable":
        qty = random.randint(1, 3)
        add_item_to_user(user, "vegetable", qty)
        return {"gained": {"vegetable": qty}}
    elif action == "work_for_king":
        # weighted distribution
        pounds = random.choice(KING_PAY_POUNDS)
        shillings = pounds * SHILLINGS_PER_POUND
        user.add_money(shillings)
        return {"paid_shillings": shillings}
    elif action == "embark":
        # mark user as aboard: we'll store a flag in params or a DB field in a real schema
        # Here we set user param -> 'on_boat' true; in production this should be normalized
        # For now, mark in mailbox or news (placeholder)
        return {"embarked": True}
    elif action == "disembark":
        return {"disembarked": True}
    elif action == "try_swim":
        # Swim success 10% chance
        roll = random.random()
        if roll <= 0.10:
            return {"swim_result": "success"}
        else:
            # place player at Lost Point on the Coast, apply -1 HP instantly
            user.health = max(0, (user.health or 0) - 1)
            db.session.add(user)
            return {"swim_result": "drowned", "hp_lost": 1}
    elif action == "study_geography":
        # 50% chance discover new road
        if random.random() < 0.5:
            # create news about discovery (handled above)
            return {"discovered": True}
        else:
            return {"discovered": False}
    else:
        # unknown action defaults to no-op
        return {"ok": True}

def determine_xp_for_action(action: str):
    # Simple XP mapping, tweakable
    mapping = {
        "gather_mushrooms": 1,
        "gather_chestnuts": 1,
        "gather_wild_herbs": 1,
        "gather_fruits": 1,
        "plant_wheat": 3,
        "plant_vegetable": 2,
        "work_for_king": 2,
        "study_geography": 5,
        "embark": 0,
        "disembark": 0,
        "try_swim": 0,
    }
    return mapping.get(action, 1)

# Inventory helpers
def add_item_to_user(user: User, item_key: str, quantity: int = 1):
    item = Item.query.filter_by(key=item_key).first()
    if not item:
        return None
    inv = Inventory.query.filter_by(user_id=user.id, item_id=item.id).first()
    if inv:
        inv.quantity += quantity
    else:
        inv = Inventory(user_id=user.id, item_id=item.id, quantity=quantity)
        db.session.add(inv)
    db.session.commit()
    return inv

def remove_item_from_user(user: User, item_key: str, quantity: int = 1):
    item = Item.query.filter_by(key=item_key).first()
    if not item:
        raise ValueError("Item unknown")
    inv = Inventory.query.filter_by(user_id=user.id, item_id=item.id).first()
    if not inv or inv.quantity < quantity:
        raise ValueError("Not enough items")
    inv.quantity -= quantity
    if inv.quantity <= 0:
        db.session.delete(inv)
    db.session.commit()
    return True

# Boat processing: movement + stuck logic
def process_boats(current_turn: int, news_accumulator: list):
    boats = Boat.query.all()
    for boat in boats:
        # only move boats once per turn
        if boat.last_moved_turn == current_turn:
            continue
        route = boat.route or []
        if not route:
            continue
        # Decide if stuck check applies: check current leg (from current_index to next_index)
        next_index = (boat.current_index + 1) % len(route)
        from_city = route[boat.current_index]
        to_city = route[next_index]
        # If either from or to is in immune set pairs (both being in IMMUNE set),
        # skip stuck check
        if (from_city in IMMUNE_BOAT_LEG_CITIES and to_city in IMMUNE_BOAT_LEG_CITIES):
            stuck_check = False
        else:
            stuck_check = True
        if stuck_check:
            if not boat.stuck:
                # check initial stuck roll
                if random.random() < 0.5:
                    boat.stuck = True
                    boat.stuck_turns = 1
                    boat.last_moved_turn = current_turn
                    db.session.add(boat)
                    # news
                    news_accumulator.append({
                        "title": f"{boat.key} is stuck at sea",
                        "body": f"The {boat.key} seems stuck between {from_city} and {to_city}.",
                        "meta": {"boat": boat.key}
                    })
                    continue  # boat didn't move this turn
            else:
                # already stuck: increment stuck_turns
                boat.stuck_turns += 1
                # If stuck for 2 or more turns, it remains stuck until some event (players may attempt swim)
                boat.last_moved_turn = current_turn
                db.session.add(boat)
                continue
        # If not stuck, move the boat forward
        boat.current_index = next_index
        boat.last_moved_turn = current_turn
        boat.stuck = False
        boat.stuck_turns = 0
        db.session.add(boat)
        news_accumulator.append({
            "title": f"{boat.key} moved to {route[boat.current_index]}",
            "body": f"The {boat.key} arrived at {route[boat.current_index]}.",
            "meta": {"boat": boat.key, "city": route[boat.current_index]}
        })
    db.session.commit()
