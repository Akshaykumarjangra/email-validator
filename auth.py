import os
from flask import Blueprint, url_for, redirect, session, flash, request
from authlib.integrations.flask_client import OAuth
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
from database import Database
from dotenv import load_dotenv

load_dotenv()

auth_bp = Blueprint('auth', __name__)
db = Database("saas_results.db")

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

class User(UserMixin):
    def __init__(self, user_row):
        self.id = user_row[0]
        self.email = user_row[1]
        self.name = user_row[2]
        self.picture = user_row[3]
        self.role = user_row[4]
        self.credits_total = user_row[5]
        self.credits_used = user_row[6]

@login_manager.user_loader
def load_user(user_id):
    # In a real app, query by ID. Here we query by row for simplicity.
    import sqlite3
    conn = sqlite3.connect("saas_results.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return User(row)
    return None

def setup_oauth(app):
    oauth = OAuth(app)
    oauth.register(
        name='google',
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )
    return oauth

@auth_bp.route('/login')
def login():
    from flask import current_app
    oauth = setup_oauth(current_app)
    redirect_uri = url_for('auth.authorize', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/authorize')
def authorize():
    from flask import current_app
    oauth = setup_oauth(current_app)
    token = oauth.google.authorize_access_token()
    user_info = token.get('userinfo')
    
    if user_info:
        email = user_info['email']
        name = user_info['name']
        picture = user_info['picture']
        
        # Admin check
        role = 'admin' if email == os.getenv("ADMIN_EMAIL") else 'user'
        
        db.create_or_update_user(email, name, picture, role)
        user_row = db.get_user_by_email(email)
        user_obj = User(user_row)
        login_user(user_obj)
        
        return redirect('/')
    return 'Auth failed', 400

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect('/')

# Mock Login for development if OAuth is not configured
@auth_bp.route('/dev-login')
def dev_login():
    email = request.args.get('email', os.getenv("ADMIN_EMAIL"))
    db.create_or_update_user(email, "Dev User", "", 'admin' if email == os.getenv("ADMIN_EMAIL") else 'user')
    user_row = db.get_user_by_email(email)
    login_user(User(user_row))
    return redirect('/')
