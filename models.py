# models.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from extensions import db

# Constants
SHILLINGS_PER_POUND = 20
LEVEL2_PRICE_SHILLINGS = 55 * SHILLINGS_PER_POUND  # 1100
PROPERTY_PRICE_SHILLINGS = 45 * SHILLINGS_PER_POUND  # 900
GRAND_BOAT_CONSTRUCTION_UNITS = 10

class User(db.Model):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Currency stored in shillings (int)
    money_shillings = Column(Integer, default=10)  # starts with 10 shillings

    # Stats
    hunger = Column(Integer, default=0)      # starting hunger 0 (max is below)
    max_hunger = Column(Integer, default=2)  # fixed max hunger = 2
    health = Column(Integer, default=5)
    max_health = Column(Integer, default=5)

    intelligence = Column(Integer, default=0)
    virtue = Column(Integer, default=0)      # appears in UI at level >= 2
    level = Column(Integer, default=1)       # 1, 2, 3 supported

    # Simple mailbox (JSON list of messages; each message can be a dict)
    mailbox = Column(JSON, default=list)

    # Relationships
    inventory = relationship("Inventory", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    properties = relationship("Property", back_populates="owner", cascade="all, delete-orphan")

    # Helpers
    def add_money(self, shillings: int):
        self.money_shillings = (self.money_shillings or 0) + int(shillings)

    def remove_money(self, shillings: int):
        if (self.money_shillings or 0) < shillings:
            raise ValueError("Insufficient funds")
        self.money_shillings -= shillings

    def can_level2(self):
        """Return True if user meets level2 static criteria (intelligence & money payment separate)."""
        return (self.intelligence or 0) >= 2

    def can_level3(self):
        """Return True if user meets level3 criteria (virtue + intelligence)."""
        return (self.virtue or 0) >= 3 and (self.intelligence or 0) >= 5

class Item(db.Model):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    key = Column(String(80), unique=True, nullable=False)   # e.g. 'chestnut'
    name = Column(String(120), nullable=False)
    edible_hunger = Column(Integer, default=0)              # hunger restored if eaten
    description = Column(Text, default="")
    stackable = Column(Boolean, default=True)

class Inventory(db.Model):
    __tablename__ = "inventories"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity = Column(Integer, default=0)

    user = relationship("User", back_populates="inventory")
    item = relationship("Item")

class Task(db.Model):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    action = Column(String(120), nullable=False)  # e.g. 'gather_mushrooms'
    params = Column(JSON, default={})
    start_turn = Column(Integer, nullable=False)
    resolve_turn = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)
    result = Column(JSON, nullable=True)

    user = relationship("User", back_populates="tasks")

class City(db.Model):
    __tablename__ = "cities"
    id = Column(Integer, primary_key=True)
    key = Column(String(80), unique=True, nullable=False)  # internal key
    name = Column(String(120), nullable=False)
    region = Column(String(80), nullable=False)
    description = Column(Text, default="")
    has_market = Column(Boolean, default=True)
    has_tavern = Column(Boolean, default=True)
    is_colonisable = Column(Boolean, default=False)
    founder_id = Column(Integer, ForeignKey("users.id"), nullable=True)

class Listing(db.Model):
    __tablename__ = "listings"
    id = Column(Integer, primary_key=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity = Column(Integer, default=0)
    price_shillings = Column(Integer, default=0)  # price for the lot in shillings
    city_id = Column(Integer, ForeignKey("cities.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Boat(db.Model):
    __tablename__ = "boats"
    id = Column(Integer, primary_key=True)
    key = Column(String(80), unique=True, nullable=False)  # 'boat' or 'grand_boat_1'
    route = Column(JSON, default=list)   # ordered list of city keys
    current_index = Column(Integer, default=0)
    stuck = Column(Boolean, default=False)
    stuck_turns = Column(Integer, default=0)
    last_moved_turn = Column(Integer, default=0)
    has_tavern = Column(Boolean, default=True)
    is_grand = Column(Boolean, default=False)  # grand vs normal boat

class Property(db.Model):
    __tablename__ = "properties"
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    city_id = Column(Integer, ForeignKey("cities.id"))
    name = Column(String(120), default="Property")
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="properties")

class News(db.Model):
    __tablename__ = "news"
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    title = Column(String(240))
    body = Column(Text)
    meta = Column(JSON, default={})
