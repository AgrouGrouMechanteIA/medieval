import os
from flask import Flask, session, redirect, url_for
from extensions import db, migrate
from config import Config

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)

    from routes.auth import auth_bp
    from routes.world import world_bp
    from routes.api import api_bp
    from routes.tavern import tavern_bp
    from routes.market import market_bp
    from routes.properties import prop_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(world_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(tavern_bp)
    app.register_blueprint(market_bp)
    app.register_blueprint(prop_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    with app.app_context():
        db.create_all()

    @app.route('/')
    def index():
        if session.get('user_id'):
            return redirect(url_for('world.game'))
        return redirect(url_for('auth.login'))

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
