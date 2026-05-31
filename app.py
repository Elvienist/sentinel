import os
import re
import uuid
from datetime import datetime, timedelta
from functools import wraps

from flask import (Flask, render_template, redirect, url_for,
                   request, flash, session)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user,
                         login_required, logout_user, current_user)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash

# ── App setup ──────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-before-deploying')

db_url = os.environ.get('DATABASE_URL', 'sqlite:///sentinel.db')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ── SECURITY: Session timeout — sessions expire after 30 minutes of inactivity ──
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

try:
    from psycopg2cffi import compat
    compat.register()
except ImportError:
    pass

db            = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view    = 'login'
login_manager.login_message = 'Please log in to access this page.'

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
    failed_attempts = db.Column(db.Integer, default=0)
    locked_until    = db.Column(db.DateTime, nullable=True)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    def is_locked(self):
        if self.locked_until and datetime.utcnow() < self.locked_until:
            return True
        if self.locked_until and datetime.utcnow() >= self.locked_until:
            self.failed_attempts = 0
            self.locked_until = None
            db.session.add(self)
            db.session.commit()
        return False

    def register_failed_attempt(self):
        self.failed_attempts = (self.failed_attempts or 0) + 1
        if self.failed_attempts >= 5:
            self.locked_until = datetime.utcnow() + timedelta(minutes=15)
        db.session.add(self)
        db.session.commit()

    def reset_failed_attempts(self):
        self.failed_attempts = 0
        self.locked_until    = None
        db.session.add(self)
        db.session.commit()

    def lockout_remaining(self):
        if self.locked_until and datetime.utcnow() < self.locked_until:
            return int((self.locked_until - datetime.utcnow()).total_seconds() // 60) + 1
        return 0

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
    id    = db.Column(db.Integer, primary_key=True)
    key   = db.Column(db.String(80), unique=True, nullable=False)
    value = db.Column(db.String(500))

class ActiveSession(db.Model):
    """One row per live login. Cleared on logout or when a new login supersedes it."""
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    session_token = db.Column(db.String(64), unique=True, nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    last_active   = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address    = db.Column(db.String(100))
    username      = db.Column(db.String(80))  # denormalised for easy admin display

# ── Helpers ────────────────────────────────────────────────────────────────────

@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    if user is None:
        return None
    # If no token in session yet (e.g. mid-request before login completes), pass through
    token = session.get('session_token')
    if token:
        record = ActiveSession.query.filter_by(user_id=user.id, session_token=token).first()
        if not record:
            # Token not in DB — session was superseded by a newer login or kicked by admin
            return None
    return user


def get_client_ip():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    return ip.split(',')[0].strip() if ip else 'unknown'


def log_access(action, success, username='anonymous'):
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

def validate_password(password):
    errors = []
    if len(password) < 8:
        errors.append('at least 8 characters')
    if not re.search(r'[A-Z]', password):
        errors.append('at least one uppercase letter')
    if not re.search(r'[0-9]', password):
        errors.append('at least one number')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append('at least one special character')
    return errors

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            log_access('Unauthorised admin access attempt', False, current_user.username)
            flash('Administrator access required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


# ── SECURITY: Apply security headers to every response ────────────────────────
@app.after_request
def set_security_headers(response):
    # Prevents the page being loaded in an iframe — stops clickjacking attacks
    response.headers['X-Frame-Options'] = 'DENY'
    # Stops browsers guessing the content type — prevents MIME sniffing attacks
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # Enables browser's built-in XSS filter
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # Tells browsers to only connect via HTTPS for the next year
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    # Controls what info is sent in the Referer header when navigating away
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # Restricts what browser features the page can use
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    return response


# ── SECURITY: HTTPS enforcement — redirect HTTP to HTTPS in production ─────────
@app.before_request
def enforce_https():
    # Only enforce on Render (not locally) — checks for Render's forwarded proto header
    if request.headers.get('X-Forwarded-Proto') == 'http':
        return redirect(request.url.replace('http://', 'https://'), code=301)


# ── SECURITY: Session timeout — check activity on every request ────────────────
@app.before_request
def check_session_timeout():
    if current_user.is_authenticated:
        last_active = session.get('last_active')
        now = datetime.utcnow()
        if last_active:
            last_active_dt = datetime.fromisoformat(last_active)
            if (now - last_active_dt).total_seconds() > 1800:  # 30 minutes
                log_access('Session expired — auto logout', True, current_user.username)
                logout_user()
                session.clear()
                flash('Your session expired. Please log in again.', 'info')
                return redirect(url_for('login'))
        session['last_active'] = now.isoformat()
        session.permanent = True
        # Keep the ActiveSession row's last_active in sync
        token = session.get('session_token')
        if token:
            rec = ActiveSession.query.filter_by(session_token=token).first()
            if rec:
                rec.last_active = now
                db.session.commit()


# ── Auth routes ────────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit('20 per minute')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user     = User.query.filter_by(username=username).first()

        if user and user.is_locked():
            mins = user.lockout_remaining()
            log_access('Login attempt on locked account', False, username)
            flash(f'Account locked. Try again in {mins} minute(s).', 'error')
            return render_template('login.html')

        if user and user.check_password(password):
            user.reset_failed_attempts()
            # Invalidate any existing sessions for this user (concurrent session control)
            ActiveSession.query.filter_by(user_id=user.id).delete()
            db.session.commit()
            # Create a new session record
            token = str(uuid.uuid4())
            db.session.add(ActiveSession(
                user_id=user.id,
                session_token=token,
                ip_address=get_client_ip(),
                username=user.username
            ))
            db.session.commit()
            login_user(user)
            session['session_token'] = token
            session['last_active']   = datetime.utcnow().isoformat()
            session.permanent = True
            log_access('Login successful', True, username)
            return redirect(request.args.get('next') or url_for('index'))

        if user:
            user.register_failed_attempt()
            if user.is_locked():
                log_access('Account locked after repeated failures', False, username)
                flash('Account locked for 15 minutes due to too many failed attempts.', 'error')
            else:
                remaining = 5 - user.failed_attempts
                log_access(f'Failed login attempt ({user.failed_attempts}/5)', False, username)
                flash(f'Invalid password. {remaining} attempt(s) remaining before lockout.', 'error')
        else:
            log_access('Failed login — unknown username', False, username or 'unknown')
            flash('Invalid username or password.', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    log_access('Logout', True, current_user.username)
    token = session.get('session_token')
    if token:
        ActiveSession.query.filter_by(session_token=token).delete()
        db.session.commit()
    logout_user()
    session.clear()
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

        if action == 'set_stream_url':
            url = request.form.get('stream_url', '').strip()
            set_config('stream_url', url)
            log_access('Updated stream URL', True, current_user.username)
            flash('Stream URL updated.', 'success')

        elif action == 'create_user':
            uname    = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            is_admin = request.form.get('is_admin') == 'on'

            if not uname or not password:
                flash('Username and password are required.', 'error')
            else:
                errors = validate_password(password)
                if errors:
                    flash(f'Password must contain: {", ".join(errors)}.', 'error')
                elif User.query.filter_by(username=uname).first():
                    flash(f'Username "{uname}" already exists.', 'error')
                else:
                    u = User(username=uname, is_admin=is_admin)
                    u.set_password(password)
                    db.session.add(u)
                    db.session.commit()
                    log_access(f'Created user: {uname}', True, current_user.username)
                    flash(f'User "{uname}" created.', 'success')

        elif action == 'unlock_user':
            uid  = request.form.get('user_id')
            user = User.query.get(uid)
            if user:
                user.reset_failed_attempts()
                log_access(f'Admin unlocked account: {user.username}', True, current_user.username)
                flash(f'Account "{user.username}" unlocked.', 'success')

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
        
        elif action == 'kick_session':
            sid = request.form.get('session_id')
            rec = ActiveSession.query.get(sid)
            if rec and rec.user_id != current_user.id:
                kicked_user = rec.username
                db.session.delete(rec)
                db.session.commit()
                log_access(f'Admin kicked session for: {kicked_user}', True, current_user.username)
                flash(f'Session for "{kicked_user}" terminated.', 'success')
            elif rec and rec.user_id == current_user.id:
                flash('You cannot kick your own session.', 'error')

   # AFTER
    users           = User.query.order_by(User.created_at.desc()).all()
    logs            = AccessLog.query.order_by(AccessLog.timestamp.desc()).limit(100).all()
    active_sessions = ActiveSession.query.order_by(ActiveSession.created_at.desc()).all()
    stream_url      = get_config('stream_url', '')
    return render_template('admin.html', users=users, logs=logs,
                           active_sessions=active_sessions, stream_url=stream_url)

# ── Error handlers ─────────────────────────────────────────────────────────────

@app.errorhandler(429)
def rate_limited(e):
    log_access('Rate limit exceeded — possible brute force', False)
    flash('Too many attempts. Please wait a minute.', 'error')
    return render_template('login.html'), 429


# ── SECURITY: Hardened error handlers — no stack traces exposed ────────────────
@app.errorhandler(404)
def not_found(e):
    who = current_user.username if current_user.is_authenticated else 'anonymous'
    log_access('404 - page not found', False, who)
    return redirect(url_for('index'))


@app.errorhandler(500)
def server_error(e):
    who = current_user.username if current_user.is_authenticated else 'anonymous'
    log_access('500 - internal server error', False, who)
    app.logger.error(f'500 error: {e}')
    flash('An unexpected error occurred.', 'error')
    return redirect(url_for('index'))


@app.errorhandler(403)
def forbidden(e):
    who = current_user.username if current_user.is_authenticated else 'anonymous'
    log_access('403 - forbidden access attempt', False, who)
    return redirect(url_for('index'))

# ── Startup ────────────────────────────────────────────────────────────────────

def init_db():
    with app.app_context():
        if not os.environ.get('DATABASE_URL', '').startswith('postgresql'):
            db.drop_all()
        db.create_all()
        # ── Migration: add new columns if they don't exist ─────────────────
        with db.engine.connect() as conn:
            try:
                conn.execute(db.text('ALTER TABLE "user" ADD COLUMN failed_attempts INTEGER DEFAULT 0'))
                conn.commit()
            except Exception:
                conn.rollback()
            try:
                conn.execute(db.text('ALTER TABLE "user" ADD COLUMN locked_until TIMESTAMP'))
                conn.commit()
            except Exception:
                conn.rollback()
        if not User.query.first():
            admin = User(username='admin', is_admin=True)
            admin.set_password(os.environ.get('ADMIN_PASSWORD', 'Admin1234!'))
            db.session.add(admin)
            db.session.commit()
            app.logger.warning('Default admin created. Change the password immediately.')

init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
