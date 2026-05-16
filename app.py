import os
from datetime import datetime
from functools import wraps

from flask import (Flask, render_template, redirect, url_for,
                   request, flash, Response)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user,
                         login_required, logout_user, current_user)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash

# ── App setup ──────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-before-deploying')

# Support both postgres:// (Render legacy) and postgresql:// (SQLAlchemy 1.4+)
db_url = os.environ.get('DATABASE_URL', 'sqlite:///sentinel.db')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db           = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view    = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Rate-limiter — brute-force protection on login
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri='memory://'
)

# ── Models ─────────────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80),  unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin      = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)


class AccessLog(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    timestamp  = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(100))
    username   = db.Column(db.String(80))
    action     = db.Column(db.String(300))
    success    = db.Column(db.Boolean)
    user_agent = db.Column(db.String(400))
    endpoint   = db.Column(db.String(200))


class SiteConfig(db.Model):
    """Key-value store for admin-editable settings (e.g. stream URL)."""
    id    = db.Column(db.Integer, primary_key=True)
    key   = db.Column(db.String(80), unique=True, nullable=False)
    value = db.Column(db.String(500))


# ── Helpers ────────────────────────────────────────────────────────────────────

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def get_client_ip():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    return ip.split(',')[0].strip() if ip else 'unknown'


def log_access(action, success, username='anonymous'):
    """Write every access attempt to the database."""
    try:
        db.session.add(AccessLog(
            ip_address=get_client_ip(),
            username=username,
            action=action,
            success=success,
            user_agent=request.headers.get('User-Agent', '')[:400],
            endpoint=request.path
        ))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Log write failed: {e}')


def get_config(key, default=None):
    row = SiteConfig.query.filter_by(key=key).first()
    return row.value if row else default


def set_config(key, value):
    row = SiteConfig.query.filter_by(key=key).first()
    if row:
        row.value = value
    else:
        db.session.add(SiteConfig(key=key, value=value))
    db.session.commit()


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            log_access('Unauthorised admin access attempt', False, current_user.username)
            flash('Administrator access required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


# ── Auth routes ────────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute')          # max 10 login attempts per minute per IP
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user     = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            log_access('Login successful', True, username)
            return redirect(request.args.get('next') or url_for('index'))

        log_access('Failed login attempt', False, username or 'unknown')
        flash('Invalid username or password.', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    log_access('Logout', True, current_user.username)
    logout_user()
    return redirect(url_for('login'))


# ── Main routes ────────────────────────────────────────────────────────────────

@app.route('/')
@login_required
def index():
    stream_url = get_config('stream_url', '')
    log_access('Viewed live feed', True, current_user.username)
    return render_template('index.html', stream_url=stream_url)


# ── Admin routes ───────────────────────────────────────────────────────────────

@app.route('/admin', methods=['GET', 'POST'])
@login_required
@admin_required
def admin():
    if request.method == 'POST':
        action = request.form.get('action')

        # ── Update stream URL ──
        if action == 'set_stream_url':
            url = request.form.get('stream_url', '').strip()
            set_config('stream_url', url)
            log_access(f'Updated stream URL', True, current_user.username)
            flash('Stream URL updated.', 'success')

        # ── Create user ──
        elif action == 'create_user':
            uname    = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            is_admin = request.form.get('is_admin') == 'on'

            if not uname or not password:
                flash('Username and password are required.', 'error')
            elif len(password) < 8:
                flash('Password must be at least 8 characters.', 'error')
            elif User.query.filter_by(username=uname).first():
                flash(f'Username "{uname}" already exists.', 'error')
            else:
                u = User(username=uname, is_admin=is_admin)
                u.set_password(password)
                db.session.add(u)
                db.session.commit()
                log_access(f'Created user: {uname}', True, current_user.username)
                flash(f'User "{uname}" created.', 'success')

        # ── Delete user ──
        elif action == 'delete_user':
            uid  = request.form.get('user_id')
            user = User.query.get(uid)
            if not user:
                flash('User not found.', 'error')
            elif user.id == current_user.id:
                flash('You cannot delete your own account.', 'error')
            else:
                name = user.username
                db.session.delete(user)
                db.session.commit()
                log_access(f'Deleted user: {name}', True, current_user.username)
                flash(f'User "{name}" deleted.', 'success')

    users      = User.query.order_by(User.created_at.desc()).all()
    logs       = AccessLog.query.order_by(AccessLog.timestamp.desc()).limit(100).all()
    stream_url = get_config('stream_url', '')
    return render_template('admin.html', users=users, logs=logs, stream_url=stream_url)


# ── Error handlers ─────────────────────────────────────────────────────────────

@app.errorhandler(429)
def rate_limited(e):
    log_access('Rate limit exceeded — possible brute force', False)
    flash('Too many attempts. Please wait a minute.', 'error')
    return render_template('login.html'), 429


@app.errorhandler(404)
def not_found(e):
    who = current_user.username if current_user.is_authenticated else 'anonymous'
    log_access('404 - page not found', False, who)
    return redirect(url_for('index'))


# ── Startup ────────────────────────────────────────────────────────────────────

def init_db():
    with app.app_context():
        db.create_all()
        # Seed default admin if database is empty
        if not User.query.first():
            admin = User(username='admin', is_admin=True)
            admin.set_password(os.environ.get('ADMIN_PASSWORD', 'Admin1234!'))
            db.session.add(admin)
            db.session.commit()
            app.logger.warning(
                'Default admin created. '
                'Change the password immediately via the admin panel.'
            )


init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
