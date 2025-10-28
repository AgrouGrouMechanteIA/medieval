# seed_items.py
from extensions import db
from models import Item

items_data = [
    {"key": "chestnut", "name": "Chestnut", "edible_hunger": 1,
     "description": "A small forest nut; plain but filling."},
    {"key": "mushroom", "name": "Mushroom", "edible_hunger": 2,
     "description": "Juicy fungi gathered in the Beautiful Forest."},
    {"key": "wild_herb", "name": "Wild Herbs", "edible_hunger": 0,
     "description": "Bitter plants used to brew healing potions."},
    {"key": "fruit", "name": "Fruit", "edible_hunger": 2,
     "description": "Sweet and sticky—grown in Not-New-Eden."},
    {"key": "fish", "name": "Fish", "edible_hunger": 2,
     "description": "Fresh catch from Ocean View."},
    {"key": "vegetable", "name": "Vegetables", "edible_hunger": 1,
     "description": "Common garden produce; carrots, onions, celery."},
    {"key": "bag_of_wheat", "name": "Bag of Wheat", "edible_hunger": 0,
     "description": "Grain for milling into flour."},
    {"key": "bag_of_flour", "name": "Bag of Flour", "edible_hunger": 0,
     "description": "White powder for baking bread."},
    {"key": "bread_loaf", "name": "Bread Loaf", "edible_hunger": 2,
     "description": "Warm bread, comforting and soft."},
    {"key": "health_potion", "name": "Health Potion", "edible_hunger": 0,
     "description": "Restores health when drunk."},
    {"key": "disgusting_insect", "name": "Disgusting Insects", "edible_hunger": 1,
     "description": "Crunchy, unpleasant, but edible."},
    {"key": "banana", "name": "Bananas", "edible_hunger": 1,
     "description": "Sweet fruit from the tropical forest."},
    {"key": "cactus", "name": "Cactus Slice", "edible_hunger": 1,
     "description": "Moist cactus flesh from the desert."},
    {"key": "corn_bag", "name": "Bag of Corn", "edible_hunger": 2,
     "description": "Maize kernels, staple crop of Tierra Firme."},
    {"key": "bean_bag", "name": "Bag of Beans", "edible_hunger": 2,
     "description": "Dried beans, nourishing but costly."},
    {"key": "wood_plank", "name": "Wood Plank", "edible_hunger": 0,
     "description": "Used to build boats and structures."},
]

def seed_items():
    for data in items_data:
        existing = Item.query.filter_by(key=data["key"]).first()
        if not existing:
            item = Item(**data)
            db.session.add(item)
            print(f"Added: {data['name']}")
        else:
            print(f"Skipped existing: {data['name']}")
    db.session.commit()
    print("✅ Item seeding complete.")

if __name__ == "__main__":
    from app import app
    with app.app_context():
        seed_items()
