from datetime import datetime
from extensions import db
from sqlalchemy.dialects.postgresql import JSON

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    player = db.relationship('Player', uselist=False, back_populates='user')

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
    nickname = db.Column(db.String(80))
    health = db.Column(db.Integer, default=5)
    hunger = db.Column(db.Integer, default=0)
    intelligence = db.Column(db.Integer, default=0)
    virtue = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    money_shillings = db.Column(db.Integer, default=10)
    location = db.Column(db.String(120), default='Ocean View')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', back_populates='player')
    inventory = db.relationship('Inventory', back_populates='player')
    properties = db.relationship('Property', back_populates='player')

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.String(255))
    edible_hunger = db.Column(db.Integer, default=0)

class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'))
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'))
    qty = db.Column(db.Integer, default=0)
    player = db.relationship('Player', back_populates='inventory')
    item = db.relationship('Item')

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'))
    location = db.Column(db.String(120))
    planted_item = db.Column(db.String(120))
    planted_at_turn = db.Column(db.Integer)
    ready_at_turn = db.Column(db.Integer)
    player = db.relationship('Player', back_populates='properties')

class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('player.id'))
    city = db.Column(db.String(120))
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'))
    qty = db.Column(db.Integer, default=0)
    price_shillings = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    item = db.relationship('Item')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    subject = db.Column(db.String(200))
    body = db.Column(db.Text)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)

class TavernMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(120))
    username = db.Column(db.String(120))
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'))
    task_type = db.Column(db.String(120))
    params = db.Column(JSON, default={})
    turn_number = db.Column(db.Integer)
    resolve_turn = db.Column(db.Integer)
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Boat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    route = db.Column(JSON, default=[])
    current_index = db.Column(db.Integer, default=0)

class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    body = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
