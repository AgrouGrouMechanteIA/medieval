# models.py
from datetime import datetime
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy import Integer, Column, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from extensions import db

# Helper tables and simple models

class User(db.Model):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Currency (stored in shillings)
    money_shillings = Column(Integer, default=10)  # user starts with 10 shillings (as requested)
    # stats
    hunger = Column(Integer, default=0)           # starts at 0 per your ruling
    max_hunger = Column(Integer, default=2)       # fixed max hunger = 2
    health = Column(Integer, default=5)
    max_health = Column(Integer, default=5)

    intelligence = Column(Integer, default=0)
    virtue = Column(Integer, default=0)           # appears at level >= 2 (but stored always)
    level = Column(Integer, default=1)
    xp = Column(Integer, default=0)

    # misc
    mailbox = Column(JSON, default=list)          # simple JSON list of messages (could be normalized later)

    # relationships
    inventory = relationship("Inventory", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    properties = relationship("Property", back_populates="owner", cascade="all, delete-orphan")

    def add_money(self, shillings: int):
        self.money_shillings = max(0, (self.money_shillings or 0) + int(shillings))

    def remove_money(self, shillings: int):
        if (self.money_shillings or 0) < shillings:
            raise ValueError("Insufficient funds")
        self.money_shillings -= shillings

    def xp_to_next_level(self):
        # Example simple formula, tweakable
        return 10 * self.level

    def maybe_level_up(self):
        # If xp reaches threshold, level up until xp < threshold
        leveled = False
        while self.xp >= self.xp_to_next_level():
            self.xp -= self.xp_to_next_level()
            self.level += 1
            leveled = True
            # grant a small reward for leveling (1 intelligence point by default)
            self.intelligence = (self.intelligence or 0) + 1
            # expand max_hunger or health at certain levels if desired
            # note: Level 2 unlocks virtue UI (but we keep virtue stored always)
        return leveled

class Item(db.Model):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    key = Column(String(80), unique=True, nullable=False)  # e.g. 'chestnut', 'bread'
    display_name = Column(String(120), nullable=False)
    edible_hunger = Column(Integer, default=0)  # hunger points restored if eaten
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
    action = Column(String(120), nullable=False)  # e.g. 'plant_wheat', 'gather_mushrooms', 'embark'
    params = Column(MutableDict.as_mutable(JSON), default={})
    start_turn = Column(Integer, nullable=False)
    resolve_turn = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)
    result = Column(JSON, nullable=True)

    user = relationship("User", back_populates="tasks")

class City(db.Model):
    __tablename__ = "cities"
    id = Column(Integer, primary_key=True)
    key = Column(String(80), unique=True, nullable=False)   # internal key e.g. 'beautiful_forest'
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
    price_shillings = Column(Integer, default=0)  # price for whole lot (expressed in shillings)
    city_id = Column(Integer, ForeignKey("cities.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Boat(db.Model):
    __tablename__ = "boats"
    id = Column(Integer, primary_key=True)
    key = Column(String(80), unique=True, nullable=False)  # 'boat', 'grand_boat_1', etc.
    route = Column(JSON, default=list)   # ordered list of city keys for the loop
    current_index = Column(Integer, default=0)
    stuck = Column(Boolean, default=False)
    stuck_turns = Column(Integer, default=0)
    last_moved_turn = Column(Integer, default=0)
    has_tavern = Column(Boolean, default=True)

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
