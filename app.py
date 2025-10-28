import os
from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()
migrate = None

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object('config.Config')

    global migrate
    db.init_app(app)
    migrate = Migrate(app, db)

    # Import models after db initialization
    from models import User, Item, Inventory, Task, Boat, City, Listing, Property, Message

    # ---------------------------
    # Authentication
    # ---------------------------
    @app.route('/register', methods=['GET','POST'])
    def register():
        if request.method == 'POST':
            nickname = request.form.get('nickname', '').strip()
            password = request.form.get('password', '')
            if not nickname or not password:
                return render_template('register.html', error='Missing fields')
            if User.query.filter_by(nickname=nickname).first():
                return render_template('register.html', error='Nickname taken')
            u = User(nickname=nickname, password_hash=generate_password_hash(password))
            # First user becomes admin
            if User.query.count() == 0:
                u.is_admin = True
            # give starting resources
            u.money_shillings = 10  # 10 shillings = 0 pounds 10s
            db.session.add(u)
            db.session.commit()
            # give starting items: 2 chestnuts
            chestnut = Item.get_or_create('Chestnut', edible_hunger=1)
            inv = Inventory(user_id=u.id, item_id=chestnut.id, qty=2)
            db.session.add(inv)
            db.session.commit()
            session['user_id'] = u.id
            return redirect(url_for('game'))
        return render_template('register.html')

    @app.route('/login', methods=['GET','POST'])
    def login():
        if request.method == 'POST':
            nickname = request.form.get('nickname','').strip()
            password = request.form.get('password','')
            u = User.query.filter_by(nickname=nickname).first()
            if not u or not check_password_hash(u.password_hash, password):
                return render_template('login.html', error='Invalid credentials')
            session['user_id'] = u.id
            return redirect(url_for('game'))
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session.pop('user_id', None)
        return redirect(url_for('login'))

    def current_user():
        uid = session.get('user_id')
        if not uid:
            return None
        return User.query.get(uid)

    # ---------------------------
    # App routes
    # ---------------------------
    @app.route('/')
    def index():
        if current_user():
            return redirect(url_for('game'))
        return redirect(url_for('login'))

    @app.route('/game')
    def game():
        u = current_user()
        if not u:
            return redirect(url_for('login'))
        # Make sure boat and cities exist
        if not Boat.query.first():
            boat = Boat(name='The Boat', route=['Beautiful Forest','Not-New-Eden','Ocean View','Temple Island','Risible Rock'], current_index=2)
            db.session.add(boat)
        city_names = ['Beautiful Forest','Not-New-Eden','Ocean View','Temple Island','Risible Rock']
        for n in city_names:
            if not City.query.filter_by(name=n).first():
                db.session.add(City(name=n))
        db.session.commit()

        city = City.query.filter_by(name='Ocean View').first()
        # inventory details
        invs = Inventory.query.filter_by(user_id=u.id).all()
        inventory = [{'name': Item.query.get(i.item_id).name if Item.query.get(i.item_id) else 'Unknown', 'qty': i.qty} for i in invs]
        boat = Boat.query.first()
        boat_pos = boat.route[boat.current_index] if boat and boat.route else 'Unknown'
        epoch = datetime(1970,1,1, tzinfo=timezone.utc)
        turn = (datetime.now(timezone.utc)-epoch).days

        notification = None
        if u.hunger < 1:
            notification = '⚠️ Your hunger bar is empty! Eat something or lose 1 health at midnight.'

        # small context for template
        return render_template('game.html', player=u, city=city, city_desc=city.description or '', inventory=inventory, boat_position=boat_pos, turn=turn, notification=notification)

    @app.route('/inventory')
    def inventory_page():
        u = current_user()
        if not u:
            return redirect(url_for('login'))
        invs = Inventory.query.filter_by(user_id=u.id).all()
        items = []
        for i in invs:
            item = Item.query.get(i.item_id)
            items.append({'id': i.id, 'name': item.name if item else 'unknown', 'qty': i.qty, 'edible': item.edible_hunger if item else 0})
        return render_template('inventory.html', player=u, items=items)

    @app.route('/market')
    def market_page():
        u = current_user()
        if not u:
            return redirect(url_for('login'))
        listings = Listing.query.all()
        enriched = []
        for l in listings:
            seller = User.query.get(l.seller_id)
            item = Item.query.get(l.item_id)
            enriched.append({'id': l.id, 'seller': seller.nickname if seller else 'unknown','item': item.name if item else 'unknown','qty': l.qty,'price_pounds': l.price_shillings//20,'price_shillings': l.price_shillings%20})
        return render_template('market.html', player=u, listings=enriched)

    @app.route('/tavern')
    def tavern_page():
        u = current_user()
        if not u:
            return redirect(url_for('login'))
        # show last 50 tavern messages (for demo kept local)
        msgs = Message.query.filter_by(is_tavern=True).order_by(Message.created_at.desc()).limit(50).all()
        return render_template('tavern.html', player=u, messages=reversed(msgs))

    @app.route('/info')
    def info_page():
        u = current_user()
        if not u:
            return redirect(url_for('login'))
        # show global news from Message table with is_news flag
        news = Message.query.filter_by(is_news=True).order_by(Message.created_at.desc()).limit(50).all()
        return render_template('info.html', news=reversed(news))

    # ---------------------------
    # API endpoints (simplified)
    # ---------------------------
    @app.route('/api/action/eat', methods=['POST'])
    def api_eat():
        u = current_user()
        if not u:
            return jsonify({'error':'unauthenticated'}),401
        data = request.json or {}
        item_name = data.get('item')
        item = Item.query.filter_by(name=item_name).first()
        if not item:
            return jsonify({'error':'no such item'}),400
        inv = Inventory.query.filter_by(user_id=u.id, item_id=item.id).first()
        if not inv or inv.qty <= 0:
            return jsonify({'error':'not enough items'}),400
        inv.qty -= 1
        u.hunger = min(u.max_hunger, u.hunger + (item.edible_hunger or 0))
        db.session.commit()
        return jsonify({'ok':True, 'hunger':u.hunger})

    @app.route('/api/market/buy', methods=['POST'])
    def api_buy():
        u = current_user()
        if not u:
            return jsonify({'error':'unauthenticated'}),401
        data = request.json or {}
        listing_id = int(data.get('listing_id',0))
        qty = int(data.get('qty',1))
        listing = Listing.query.get(listing_id)
        if not listing or listing.qty < qty:
            return jsonify({'error':'invalid listing or qty'}),400
        total_price_shillings = listing.price_shillings * qty
        if u.money_shillings < total_price_shillings:
            return jsonify({'error':'not enough money'}),400
        # transfer money
        seller = User.query.get(listing.seller_id)
        u.money_shillings -= total_price_shillings
        seller.money_shillings += total_price_shillings
        # move items to buyer
        inv_b = Inventory.query.filter_by(user_id=u.id, item_id=listing.item_id).first()
        if not inv_b:
            inv_b = Inventory(user_id=u.id, item_id=listing.item_id, qty=0)
            db.session.add(inv_b)
        inv_b.qty += qty
        listing.qty -= qty
        if listing.qty <= 0:
            db.session.delete(listing)
        db.session.commit()
        return jsonify({'ok':True})

    @app.route('/api/message/send', methods=['POST'])
    def api_message_send():
        u = current_user()
        if not u:
            return jsonify({'error':'unauthenticated'}),401
        to_name = request.json.get('to')
        body = request.json.get('body','')
        is_tavern = bool(request.json.get('is_tavern', False))
        is_news = bool(request.json.get('is_news', False))
        to = User.query.filter_by(nickname=to_name).first() if to_name else None
        if to_name and not to:
            return jsonify({'error':'no such user'}),400
        m = Message(sender_id=u.id, receiver_id=to.id if to else None, body=body, is_tavern=is_tavern, is_news=is_news)
        db.session.add(m)
        db.session.commit()
        return jsonify({'ok':True})

    # Admin: manual next turn
    @app.route('/admin/next-turn', methods=['POST','GET'])
    def admin_next_turn():
        u = current_user()
        if not u or not u.is_admin:
            abort(403)
        # import here to avoid circular import when module imported elsewhere
        from turn_resolver import process_turn
        process_turn(app)
        flash('Next turn processed.')
        return redirect(url_for('game'))

    # Initialize DB tables and some seed data
    with app.app_context():
        from models import Item
        db.create_all()
        # ensure some basic items exist
        Item.get_or_create('Chestnut', edible_hunger=1)
        Item.get_or_create('Bread', edible_hunger=2)
        Item.get_or_create('Fish', edible_hunger=2)
        Item.get_or_create('Mushroom', edible_hunger=2)
        Item.get_or_create('Health Potion', edible_hunger=0)
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
