from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import JSON
from app import db  # careful: this file is imported after create_app init; in migrations it'll be fine

# NOTE: to avoid circular import when running tests, you can import db from app after factory init.
# For clarity we assume app imports models after db.init_app(app) as in app.py.

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    # stats
    hunger = db.Column(db.Integer, default=0)  # 0..max_hunger
    max_hunger = db.Column(db.Integer, default=2)  # for now 2
    health = db.Column(db.Integer, default=5)
    intelligence = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    virtue = db.Column(db.Integer, default=0)
    # money stored as shillings (1 pound = 20 shillings)
    money_shillings = db.Column(db.Integer, default=10)  # 10 shillings to start

    def display_money(self):
        pounds = self.money_shillings // 20
        shillings = self.money_shillings % 20
        return f"{pounds}£ {shillings}s"

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    edible_hunger = db.Column(db.Integer, default=0)  # hunger points restored by eating
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def get_or_create(cls, name, edible_hunger=0):
        it = cls.query.filter_by(name=name).first()
        if it:
            return it
        it = cls(name=name, edible_hunger=edible_hunger)
        db.session.add(it)
        db.session.commit()
        return it

class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    qty = db.Column(db.Integer, default=0)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task_type = db.Column(db.String(120))
    params = db.Column(JSON, default={})
    turn_number = db.Column(db.Integer)
    resolve_turn = db.Column(db.Integer)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Boat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    route = db.Column(JSON, default=[])  # list of city names
    current_index = db.Column(db.Integer, default=0)
    stuck_turns = db.Column(db.Integer, default=0)

class City(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True)
    description = db.Column(db.Text)

class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'))
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'))
    qty = db.Column(db.Integer, default=0)
    price_shillings = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'))
    name = db.Column(db.String(200))

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    body = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_tavern = db.Column(db.Boolean, default=False)
    is_news = db.Column(db.Boolean, default=False)
