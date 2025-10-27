from flask import Blueprint, render_template, request, redirect, url_for, session
from models import Listing, Item, Player
from extensions import db
market_bp = Blueprint('market', __name__)

@market_bp.route('/market')
def index():
    listings = Listing.query.order_by(Listing.created_at.desc()).limit(100).all()
    return render_template('market.html', listings=listings)
