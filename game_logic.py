# game_logic.py
from datetime import datetime, timezone
import random
from extensions import db
from models import User, Task, Item, Inventory, Boat, City, Listing, News
from sqlalchemy import and_

# Constants (same as in models)
SHILLINGS_PER_POUND = 20
LEVEL2_PRICE_SHILLINGS = 55 * SHILLINGS_PER_POUND  # 1100
PROPERTY_PRICE_SHILLINGS = 45 * SHILLINGS_PER_POUND  # 900
GRAND_BOAT_CONSTRUCTION_UNITS = 10

# Boat immune legs set: any pair among these is immune (no stuck)
IMMUNE_BOAT_LEG_CITIES = {"ocean_view", "not_new_eden", "beautiful_forest"}

# Weighted distribution for "Work for the King" pay: bias to 8-10
KING_PAY_POUNDS = [8, 8, 8, 9, 9, 10, 10, 10, 11, 12, 13, 14, 15]

# ------ Turn / time helpers ------
def get_turn_number(now: datetime = None):
    """Return integer turn number as days since Unix epoch (UTC)."""
    now = now or datetime.now(timezone.utc)
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    delta = now - epoch
    return delta.days

# ------ Task management ------
def user_has_task_this_turn(user: User):
    current_turn = get_turn_number()
    existing = Task.query.filter_by(user_id=user.id, resolved=False).filter(Task.resolve_turn > current_turn - 1).first()
    return existing is not None

def start_task(user: User, action: str, params: dict = None, delay_turns: int = 1):
    """Start a task for user. Enforces one task per turn rule."""
    if user_has_task_this_turn(user):
        raise ValueError("You already have a task for this turn.")
    params = params or {}
    current_turn = get_turn_number()
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

# ------ Immediate actions ------
def eat_item(user: User, item_key: str, qty: int = 1):
    item = Item.query.filter_by(key=item_key).first()
    if not item:
        raise ValueError("Unknown item")
    inv = Inventory.query.filter_by(user_id=user.id, item_id=item.id).first()
    if not inv or inv.quantity < qty:
        raise ValueError("Not enough items")
    # Consume
    inv.quantity -= qty
    if inv.quantity <= 0:
        db.session.delete(inv)
    # Apply hunger gain immediately (cap at max_hunger)
    gain = (item.edible_hunger or 0) * qty
    user.hunger = min(user.max_hunger or 2, (user.hunger or 0) + gain)
    db.session.add(user)
    db.session.commit()
    return {"ok": True, "hunger": user.hunger}

def drink_health_potion(user: User, item_key="health_potion", qty: int = 1):
    item = Item.query.filter_by(key=item_key).first()
    if not item:
        raise ValueError("No such potion item")
    inv = Inventory.query.filter_by(user_id=user.id, item_id=item.id).first()
    if not inv or inv.quantity < qty:
        raise ValueError("Not enough potions")
    inv.quantity -= qty
    if inv.quantity <= 0:
        db.session.delete(inv)
    # Health increase is immediate, capped
    user.health = min(user.max_health or 5, (user.health or 0) + qty)
    db.session.add(user)
    db.session.commit()
    return {"ok": True, "health": user.health}

# ------ Inventory helpers ------
def add_item_to_user(user: User, item_key: str, qty: int = 1):
    item = Item.query.filter_by(key=item_key).first()
    if not item:
        return None
    inv = Inventory.query.filter_by(user_id=user.id, item_id=item.id).first()
    if inv:
        inv.quantity += qty
    else:
        inv = Inventory(user_id=user.id, item_id=item.id, quantity=qty)
        db.session.add(inv)
    db.session.commit()
    return inv

def remove_item_from_user(user: User, item_key: str, qty: int = 1):
    item = Item.query.filter_by(key=item_key).first()
    if not item:
        raise ValueError("Unknown item")
    inv = Inventory.query.filter_by(user_id=user.id, item_id=item.id).first()
    if not inv or inv.quantity < qty:
        raise ValueError("Not enough items")
    inv.quantity -= qty
    if inv.quantity <= 0:
        db.session.delete(inv)
    db.session.commit()
    return True

# ------ Leveling helpers (no XP) ------
def attempt_level_up_to_2(user: User):
    """
    Level 1 -> Level 2 requires:
      - intelligence >= 2 (user.can_level2())
      - pay 55 pounds (1100 shillings)
    This function attempts the payment and sets level to 2 if both conditions are met.
    """
    if user.level >= 2:
        return {"ok": False, "reason": "Already level 2 or higher"}
    if not user.can_level2():
        return {"ok": False, "reason": "Not enough intelligence"}
    if (user.money_shillings or 0) < LEVEL2_PRICE_SHILLINGS:
        return {"ok": False, "reason": "Not enough money to unlock Level 2"}
    # Charge
    user.remove_money(LEVEL2_PRICE_SHILLINGS)
    user.level = 2
    db.session.add(user)
    db.session.commit()
    return {"ok": True, "level": user.level}

def attempt_level_up_to_3(user: User):
    """
    Level 2 -> Level 3 requires:
      - virtue >= 3
      - intelligence >= 5
    No money cost specified in rules.
    """
    if user.level >= 3:
        return {"ok": False, "reason": "Already level 3"}
    if not user.can_level3():
        return {"ok": False, "reason": "Requirements not met (virtue/intelligence)"}
    user.level = 3
    db.session.add(user)
    db.session.commit()
    return {"ok": True, "level": user.level}

# ------ Task resolution ------
def resolve_all_tasks():
    """
    Resolve all tasks whose resolve_turn <= current turn.
    Then handle boats movement & stuck rules.
    Then apply starvation health loss and reset hunger to 0 for everyone.
    """
    current_turn = get_turn_number()
    tasks = Task.query.filter(Task.resolve_turn <= current_turn, Task.resolved == False).all()
    news_created = []
    for task in tasks:
        try:
            user = User.query.get(task.user_id)
            result = _resolve_task(user, task)
            task.result = result
            task.resolved = True
            db.session.add(task)
            # commit user changes inside _resolve_task where needed
        except Exception as e:
            print("Error resolving task", task.id, e)
    # Move boats and process stuck rules
    _process_boats(current_turn, news_created)
    # Starvation & hunger reset (apply health loss if hunger < 2, then set hunger=0)
    users = User.query.all()
    for u in users:
        if (u.hunger or 0) < 2:
            u.health = max(0, (u.health or 0) - 1)
        u.hunger = 0
        db.session.add(u)
    # Persist any generated news
    for n in news_created:
        news = News(title=n["title"], body=n["body"], meta=n.get("meta", {}))
        db.session.add(news)
    db.session.commit()

def _resolve_task(user: User, task: Task):
    """Internal task resolver. Returns a dict result."""
    action = task.action
    params = task.params or {}
    if action == "gather_mushrooms":
        qty = random.randint(2, 7)
        add_item_to_user(user, "mushroom", qty)
        return {"gained": {"mushroom": qty}}
    if action == "gather_chestnuts":
        qty = random.randint(2, 7)
        add_item_to_user(user, "chestnut", qty)
        return {"gained": {"chestnut": qty}}
    if action == "gather_wild_herbs":
        qty = random.randint(2, 4)
        add_item_to_user(user, "wild_herb", qty)
        return {"gained": {"wild_herb": qty}}
    if action == "gather_fruits":
        qty = random.randint(0, 3)
        add_item_to_user(user, "fruit", qty)
        return {"gained": {"fruit": qty}}
    if action == "plant_wheat":
        qty = random.randint(2, 7)
        add_item_to_user(user, "bag_of_wheat", qty)
        return {"gained": {"bag_of_wheat": qty}}
    if action == "plant_vegetable":
        qty = random.randint(1, 3)
        add_item_to_user(user, "vegetable", qty)
        return {"gained": {"vegetable": qty}}
    if action == "work_for_king":
        pounds = random.choice(KING_PAY_POUNDS)
        shillings = pounds * SHILLINGS_PER_POUND
        user.add_money(shillings)
        db.session.add(user)
        return {"earned_shillings": shillings}
    if action == "embark":
        # Mark user param 'aboard' (implementation detail: you can store flags in Task.result or a user field)
        return {"embarked": True}
    if action == "disembark":
        return {"disembarked": True}
    if action == "try_swim":
        if random.random() < 0.10:
            return {"swim": "success"}
        else:
            # immediate HP loss and relocation handled by caller/routes after reading result
            user.health = max(0, (user.health or 0) - 1)
            db.session.add(user)
            return {"swim": "failed", "hp_lost": 1}
    if action == "study_geography":
        discovered = random.random() < 0.5
        return {"discovered": discovered}
    # default no-op
    return {"ok": True}

# ------ Boat movement & stuck rules ------
def _process_boats(current_turn: int, news_accumulator: list):
    boats = Boat.query.all()
    for boat in boats:
        if boat.last_moved_turn == current_turn:
            continue
        route = boat.route or []
        if not route:
            continue
        next_index = (boat.current_index + 1) % len(route)
        from_city = route[boat.current_index]
        to_city = route[next_index]
        # Determine if stuck check applies
        if (from_city in IMMUNE_BOAT_LEG_CITIES and to_city in IMMUNE_BOAT_LEG_CITIES):
            stuck_check = False
        else:
            stuck_check = True
        if stuck_check:
            if not boat.stuck:
                if random.random() < 0.5:
                    boat.stuck = True
                    boat.stuck_turns = 1
                    boat.last_moved_turn = current_turn
                    db.session.add(boat)
                    news_accumulator.append({
                        "title": f"{boat.key} stuck at sea",
                        "body": f"The {boat.key} got stuck between {from_city} and {to_city}."
                    })
                    continue
            else:
                boat.stuck_turns += 1
                boat.last_moved_turn = current_turn
                db.session.add(boat)
                continue
        # move boat forward
        boat.current_index = next_index
        boat.last_moved_turn = current_turn
        boat.stuck = False
        boat.stuck_turns = 0
        db.session.add(boat)
        news_accumulator.append({
            "title": f"{boat.key} arrived at {route[boat.current_index]}",
            "body": f"The {boat.key} is now at {route[boat.current_index]}."
        })
    db.session.commit()
