# SENTINEL — File Documentation
A line-by-line reference for every file in the project.

---

# 1. app.py

## Tools, Methods, Functions & Keywords Used

| Name | Type | What it is |
|---|---|---|
| `os` | Module | Built-in Python module for reading environment variables and file paths |
| `datetime` | Module | Built-in Python module for getting the current date and time |
| `wraps` | Function | Preserves original function name when wrapping with decorators |
| `Flask` | Class | The core web framework — creates and runs the app |
| `render_template` | Function | Loads an HTML file, fills in variables, returns it to the browser |
| `redirect` | Function | Sends the browser to a different URL |
| `url_for` | Function | Generates a URL for a named route function |
| `request` | Object | Contains everything about the incoming HTTP request (form data, IP, headers) |
| `flash` | Function | Stores a one-time message to show on the next page load |
| `SQLAlchemy` | Class | The database connection and ORM (Object Relational Mapper) |
| `LoginManager` | Class | Manages user sessions — tracks who is logged in |
| `UserMixin` | Class | Provides required login methods to the User model |
| `login_user` | Function | Creates a session for a user after successful login |
| `login_required` | Decorator | Blocks a route if the user is not logged in |
| `logout_user` | Function | Destroys the current user session |
| `current_user` | Object | The currently logged-in user, available on every request |
| `Limiter` | Class | Rate limiter — counts and limits requests per IP |
| `get_remote_address` | Function | Extracts the IP address from the incoming request |
| `generate_password_hash` | Function | Converts a plain password into a secure hash |
| `check_password_hash` | Function | Compares a plain password against a stored hash |
| `@app.route` | Decorator | Maps a URL path to a Python function |
| `@login_required` | Decorator | Protects a route — redirects to login if not authenticated |
| `@limiter.limit` | Decorator | Sets a request rate limit on a specific route |
| `db.Column` | Method | Defines a column in a database table |
| `db.session.add` | Method | Stages a new row to be saved |
| `db.session.commit` | Method | Permanently writes staged changes to the database |
| `db.session.rollback` | Method | Cancels staged changes if something went wrong |
| `db.create_all` | Method | Creates all database tables if they don't already exist |
| `User.query` | Method | Queries the User table in the database |
| `request.form.get` | Method | Reads a value submitted from an HTML form |
| `request.headers.get` | Method | Reads an HTTP header from the incoming request |
| `os.environ.get` | Method | Reads an environment variable with an optional fallback default |

---

## Line by Line

```python
import os
```
Imports Python's built-in `os` module. Used to read environment variables like `SECRET_KEY`, `DATABASE_URL`, and `ADMIN_PASSWORD` that are set outside the code on Render.

```python
from datetime import datetime
```
Imports `datetime` so we can record the exact time of every database entry — users created, access logs written.

```python
from functools import wraps
```
Imports `wraps` — needed when building the `admin_required` decorator. Without it Flask gets confused because multiple decorated functions would appear to have the same name internally.

```python
from flask import (Flask, render_template, redirect, url_for, request, flash)
```
Imports the core Flask tools:
- `Flask` — creates the app itself
- `render_template` — loads and fills HTML template files
- `redirect` — sends the browser to another URL
- `url_for` — generates URLs from function names instead of hardcoding strings
- `request` — gives access to incoming request data (forms, headers, IP)
- `flash` — stores one-time messages shown on the next page

```python
from flask_sqlalchemy import SQLAlchemy
```
Imports SQLAlchemy — the tool that connects Python to the database and lets you define tables as Python classes.

```python
from flask_login import (LoginManager, UserMixin, login_user, login_required, logout_user, current_user)
```
Imports all the Flask-Login tools for session management:
- `LoginManager` — the central manager that tracks sessions
- `UserMixin` — gives the User class the methods Flask-Login needs
- `login_user` — creates the session on successful login
- `login_required` — decorator that blocks unauthenticated users
- `logout_user` — destroys the session on logout
- `current_user` — the logged-in user object, available everywhere

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
```
Imports the rate limiter and the function that extracts the user's IP address — used to count requests per IP and block brute force attempts.

```python
from werkzeug.security import generate_password_hash, check_password_hash
```
Imports the password hashing tools. `generate_password_hash` turns a plain password into a secure irreversible hash. `check_password_hash` compares a plain password against a stored hash at login time.

---

```python
app = Flask(__name__)
```
Creates the Flask application object. `__name__` tells Flask the name of the current file so it knows where to look for templates and static files.

```python
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-before-deploying')
```
Sets the secret key Flask uses to sign session cookies. Reads from the `SECRET_KEY` environment variable on Render. Falls back to the string `'change-this-before-deploying'` if not set — this fallback is only safe for local testing.

```python
db_url = os.environ.get('DATABASE_URL', 'sqlite:///sentinel.db')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
```
Reads the database URL from the environment. Locally this falls back to `sqlite:///sentinel.db` — a simple file-based database. On Render it uses PostgreSQL. The `if` block fixes a legacy URL format Render sometimes provides that SQLAlchemy no longer accepts.

```python
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
```
Tells SQLAlchemy which database to connect to. `TRACK_MODIFICATIONS` is set to False to disable an unnecessary feature that uses extra memory.

```python
db = SQLAlchemy(app)
```
Creates the SQLAlchemy database object and connects it to the Flask app. From here `db` is used to define tables and run queries.

```python
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
```
Creates the login manager and connects it to the app. `login_view = 'login'` tells Flask-Login to redirect unauthenticated users to the `login` route function. `login_message` is the message shown when that redirect happens.

```python
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri='memory://'
)
```
Creates the rate limiter. `get_remote_address` is how it identifies who's making the request — by IP address. `default_limits=[]` means no global limit — limits are set per route. `storage_uri='memory://'` stores the counts in the app's memory.

---

```python
class User(UserMixin, db.Model):
```
Defines the User database table as a Python class. Inheriting from `UserMixin` adds the methods Flask-Login requires. Inheriting from `db.Model` tells SQLAlchemy this is a database table.

```python
    id            = db.Column(db.Integer, primary_key=True)
```
The `id` column — an integer that auto-increments for each new user. `primary_key=True` means it uniquely identifies each row.

```python
    username      = db.Column(db.String(80),  unique=True, nullable=False)
```
The `username` column — text up to 80 characters. `unique=True` prevents two users having the same username. `nullable=False` means it must have a value.

```python
    password_hash = db.Column(db.String(256), nullable=False)
```
Stores the hashed password — never the real password. 256 characters because hashes are long strings.

```python
    is_admin      = db.Column(db.Boolean, default=False)
```
A true/false flag. `default=False` means new users are not admins unless explicitly set.

```python
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
```
Automatically records when the user was created using the current UTC time.

```python
    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)
```
A method on the User class. Takes a plain password, hashes it, and stores the hash. Never stores the original.

```python
    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)
```
At login time — takes what the user typed, hashes it, and compares it to the stored hash. Returns True if they match, False if not.

---

```python
class AccessLog(db.Model):
```
Defines the AccessLog table — every access event gets one row here.

```python
    id         = db.Column(db.Integer, primary_key=True)
    timestamp  = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(100))
    username   = db.Column(db.String(80))
    action     = db.Column(db.String(300))
    success    = db.Column(db.Boolean)
    user_agent = db.Column(db.String(400))
    endpoint   = db.Column(db.String(200))
```
Each column records a piece of information about the access event:
- `timestamp` — when it happened
- `ip_address` — where it came from
- `username` — who did it (or 'anonymous' if not logged in)
- `action` — what they did in plain English
- `success` — whether it succeeded
- `user_agent` — their browser and OS info
- `endpoint` — which URL they hit

---

```python
class SiteConfig(db.Model):
    id    = db.Column(db.Integer, primary_key=True)
    key   = db.Column(db.String(80), unique=True, nullable=False)
    value = db.Column(db.String(500))
```
A simple key-value settings table. Currently used to store the stream URL so it can be updated from the admin panel without changing code or environment variables.

---

```python
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
```
Flask-Login calls this function on every single request. It takes the user ID stored in the session cookie, looks up that user in the database, and returns them as `current_user`. If the user doesn't exist it returns None.

```python
def get_client_ip():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    return ip.split(',')[0].strip() if ip else 'unknown'
```
Gets the real IP address. On Render, requests pass through a proxy — the real IP is in the `X-Forwarded-For` header, not `remote_addr`. The `.split(',')[0]` takes the first IP if multiple are listed.

```python
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
```
Creates a new AccessLog row and saves it. The `try/except` means if the database write fails for any reason the app doesn't crash — it just logs the error and continues. `[:400]` trims the user agent string to 400 characters maximum.

```python
def get_config(key, default=None):
    row = SiteConfig.query.filter_by(key=key).first()
    return row.value if row else default
```
Reads a value from the SiteConfig table by its key name. Returns the default if that key doesn't exist yet.

```python
def set_config(key, value):
    row = SiteConfig.query.filter_by(key=key).first()
    if row:
        row.value = value
    else:
        db.session.add(SiteConfig(key=key, value=value))
    db.session.commit()
```
Writes a value to the SiteConfig table. If the key already exists it updates it. If not it creates a new row. Then commits to save.

```python
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            log_access('Unauthorised admin access attempt', False, current_user.username)
            flash('Administrator access required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated
```
A custom decorator. When put above a route it wraps it — first checks `current_user.is_admin`. If False it logs the attempt, flashes a message, and redirects away. If True it runs the original route function normally. `@wraps(f)` preserves the function's original name internally.

---

```python
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute')
def login():
```
The login route. Accepts both GET (show the form) and POST (process the form). Rate limited to 10 requests per minute per IP.

```python
    if current_user.is_authenticated:
        return redirect(url_for('index'))
```
If someone who is already logged in visits `/login`, skip straight to the feed. Prevents double login.

```python
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user     = User.query.filter_by(username=username).first()
```
When the form is submitted — reads the username and password from the form data. `.strip()` removes any accidental spaces. Queries the database for a user with that username.

```python
        if user and user.check_password(password):
            login_user(user)
            log_access('Login successful', True, username)
            return redirect(request.args.get('next') or url_for('index'))
```
If the user exists AND the password matches — creates the session, logs the success, redirects to the feed. `request.args.get('next')` sends them to the page they originally tried to visit before being redirected to login.

```python
        log_access('Failed login attempt', False, username or 'unknown')
        flash('Invalid username or password.', 'error')
```
If login failed — logs it as a failed attempt and queues an error message to show on the login page.

```python
    return render_template('login.html')
```
For GET requests (first visit) and failed POST requests — renders the login page HTML.

---

```python
@app.route('/logout')
@login_required
def logout():
    log_access('Logout', True, current_user.username)
    logout_user()
    return redirect(url_for('login'))
```
Logs the logout, destroys the session, redirects to login. `@login_required` means you can't hit this route if you're not logged in.

---

```python
@app.route('/')
@login_required
def index():
    stream_url = get_config('stream_url', '')
    log_access('Viewed live feed', True, current_user.username)
    return render_template('index.html', stream_url=stream_url)
```
The main page. Reads the stream URL from the database and passes it to the template as a variable. Logs every view. `@login_required` redirects unauthenticated visitors to login.

---

```python
@app.route('/admin', methods=['GET', 'POST'])
@login_required
@admin_required
def admin():
```
The admin route. Protected by both decorators — must be logged in AND be an admin.

```python
    if request.method == 'POST':
        action = request.form.get('action')
```
When a form is submitted, reads the hidden `action` field to determine which form was submitted — the admin page has three different forms.

```python
        if action == 'set_stream_url':
            url = request.form.get('stream_url', '').strip()
            set_config('stream_url', url)
            log_access('Updated stream URL', True, current_user.username)
            flash('Stream URL updated.', 'success')
```
Stream URL form — reads the URL, saves it to the database, logs it, shows a success message.

```python
        elif action == 'create_user':
            uname    = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            is_admin = request.form.get('is_admin') == 'on'
```
Create user form — reads username, password, and whether the admin checkbox was ticked. `== 'on'` is how HTML checkboxes send their value when checked.

```python
            if not uname or not password:
                flash('Username and password are required.', 'error')
            elif len(password) < 8:
                flash('Password must be at least 8 characters.', 'error')
            elif User.query.filter_by(username=uname).first():
                flash(f'Username "{uname}" already exists.', 'error')
```
Validation checks before creating the user — ensures fields aren't empty, password is long enough, and username isn't already taken.

```python
            else:
                u = User(username=uname, is_admin=is_admin)
                u.set_password(password)
                db.session.add(u)
                db.session.commit()
                log_access(f'Created user: {uname}', True, current_user.username)
                flash(f'User "{uname}" created.', 'success')
```
If all validation passes — creates the user object, hashes the password, saves to database, logs it.

```python
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
```
Delete user form — finds the user by ID, prevents self-deletion, removes from database, logs it.

```python
    users      = User.query.order_by(User.created_at.desc()).all()
    logs       = AccessLog.query.order_by(AccessLog.timestamp.desc()).limit(100).all()
    stream_url = get_config('stream_url', '')
    return render_template('admin.html', users=users, logs=logs, stream_url=stream_url)
```
After handling any POST action — fetches all users (newest first), last 100 log entries (newest first), and the current stream URL, then passes all three to the admin template.

---

```python
@app.errorhandler(429)
def rate_limited(e):
    log_access('Rate limit exceeded — possible brute force', False)
    flash('Too many attempts. Please wait a minute.', 'error')
    return render_template('login.html'), 429
```
When the rate limiter triggers — logs it as a possible brute force attempt and shows the login page with an error message. The `429` in the return is the HTTP status code for "Too Many Requests."

```python
@app.errorhandler(404)
def not_found(e):
    who = current_user.username if current_user.is_authenticated else 'anonymous'
    log_access('404 - page not found', False, who)
    return redirect(url_for('index'))
```
When someone hits a URL that doesn't exist — logs who tried it and redirects to the home page. This catches people probing for hidden URLs.

---

```python
def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.first():
            admin = User(username='admin', is_admin=True)
            admin.set_password(os.environ.get('ADMIN_PASSWORD', 'Admin1234!'))
            db.session.add(admin)
            db.session.commit()
            app.logger.warning('Default admin created. Change the password immediately.')

init_db()
```
Runs once at startup. `app_context()` is required for database operations outside of a request. `db.create_all()` creates tables if they don't exist. `if not User.query.first()` — only seeds the admin if the table is completely empty, so it doesn't duplicate on every restart.

```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
```
Runs the app when the file is executed directly (`python app.py`). `host='0.0.0.0'` makes it accessible on the network, not just localhost. `PORT` reads from the environment — Render sets this automatically. `debug=False` disables the debug mode that should never be on in production.

---
---

# 2. base.html

## Tools, Methods, Functions & Keywords Used

| Name | Type | What it is |
|---|---|---|
| `{% block %}` | Jinja2 tag | Defines a replaceable section child templates can fill in |
| `{% extends %}` | Jinja2 tag | Tells a template to inherit from another template |
| `{% if %}` | Jinja2 tag | Conditional — only renders content if condition is true |
| `{% endif %}` | Jinja2 tag | Closes an if block |
| `{% with %}` | Jinja2 tag | Creates a temporary variable scope |
| `{% for %}` | Jinja2 tag | Loops over a list |
| `{% endfor %}` | Jinja2 tag | Closes a for loop |
| `{{ }}` | Jinja2 syntax | Outputs a variable's value into the HTML |
| `current_user` | Flask-Login object | The currently logged-in user |
| `current_user.is_authenticated` | Property | True if someone is logged in |
| `current_user.is_admin` | Property | True if the logged-in user is an admin |
| `current_user.username` | Property | The logged-in user's username string |
| `request.endpoint` | Flask property | The name of the current route function |
| `url_for()` | Flask function | Generates a URL from a route function name |
| `get_flashed_messages()` | Flask function | Retrieves queued flash messages |
| `:root` | CSS | Defines global CSS variables |
| `var()` | CSS | Uses a CSS variable |
| `@keyframes` | CSS | Defines an animation sequence |
| `@media` | CSS | Applies styles only at certain screen sizes |
| `position: sticky` | CSS | Keeps the navbar at the top while scrolling |
| `display: flex` | CSS | Flexbox layout — arranges children in a row or column |
| `z-index` | CSS | Controls which elements appear on top of others |

---

## Line by Line

```html
<!DOCTYPE html>
```
Tells the browser this is an HTML5 document. Must be the very first line.

```html
<html lang="en">
```
Root element of the page. `lang="en"` tells the browser and screen readers the language is English.

```html
<head>
```
Opens the invisible setup section — nothing inside here is shown directly on the page.

```html
  <meta charset="UTF-8"/>
```
Sets the character encoding to UTF-8 — ensures all characters including special symbols display correctly.

```html
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
```
Makes the page scale correctly on mobile screens. Without this the page appears zoomed out on phones.

```html
  <title>{% block title %}SENTINEL{% endblock %}</title>
```
The browser tab title. The `{% block title %}` lets child templates override it. If they don't, it defaults to `SENTINEL`.

```html
  <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;500;600;700&display=swap" rel="stylesheet">
```
Loads two fonts from Google Fonts over the internet:
- `Share Tech Mono` — the monospace font used for labels, timestamps, and technical text
- `Rajdhani` — the sans-serif font used for navigation and headings

```html
  <style>
    :root { --bg:#07090a; --bg2:#0c1014; ... }
```
Opens the CSS section. `:root` defines CSS custom properties (variables) — colors, fonts, and measurements used throughout. Defining them once here means changing a color in one place updates it everywhere.

```html
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
```
A CSS reset applied to every element. `box-sizing: border-box` makes width calculations include padding and borders. `margin: 0; padding: 0` removes default browser spacing so everything starts from a clean baseline.

```html
    html, body { height: 100%; background: var(--bg); color: var(--text); font-family: var(--sans); font-size: 15px; }
```
Makes the page fill the full viewport height. Sets the background color, default text color, default font, and base font size for the entire page.

```html
    body::before { content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 9000;
      background: repeating-linear-gradient(...); }
```
A pseudo-element (not a real HTML element — created by CSS). Creates horizontal scanlines across the entire screen by repeating a thin gradient stripe. `position: fixed; inset: 0` pins it to cover the whole viewport. `pointer-events: none` makes it invisible to mouse clicks so it doesn't block anything. `z-index: 9000` puts it in front of everything else.

```html
    body::after { content: ''; position: fixed; inset: 0; pointer-events: none;
      background-image: linear-gradient(...), linear-gradient(...); background-size: 48px 48px; }
```
Another pseudo-element. Creates the green grid pattern in the background using two overlapping linear gradients — one horizontal, one vertical — tiled every 48 pixels.

```html
    nav { position: sticky; top: 0; z-index: 100; display: flex; align-items: center;
          justify-content: space-between; padding: 0 2rem; height: 54px;
          background: var(--bg2); border-bottom: 1px solid var(--border); }
```
Styles the navigation bar. `position: sticky; top: 0` keeps it at the top of the screen while scrolling. `display: flex; justify-content: space-between` puts the brand on the left, links in the middle, username on the right. `z-index: 100` keeps it above page content.

```html
    .brand-dot { width: 8px; height: 8px; background: var(--green); border-radius: 50%;
                 animation: blink 1.4s step-end infinite; }
    @keyframes blink { 50% { opacity: 0; } }
```
The small green blinking dot next to SENTINEL in the nav. `border-radius: 50%` makes a square div appear circular. The `@keyframes blink` animation makes it invisible at the 50% mark, creating a step blink effect, looping infinitely.

```html
  </style>
  {% block head %}{% endblock %}
</head>
```
Closes the style block. `{% block head %}` lets child templates inject additional CSS or scripts into the head — used by `index.html` and `admin.html` for their page-specific styles.

---

```html
<body>
{% if current_user.is_authenticated %}
<nav>
```
Only renders the navigation bar if someone is logged in. On the login page `current_user.is_authenticated` is False so the nav is completely absent.

```html
  <div class="brand"><span class="brand-dot"></span>SENTINEL</div>
```
The left side of the nav — the blinking dot and the app name.

```html
  <div class="nav-links">
    <a href="{{ url_for('index') }}" {% if request.endpoint=='index' %}class="active"{% endif %}>Live Feed</a>
```
A nav link to the Live Feed. `url_for('index')` generates the correct URL for the `index` route function. The `{% if request.endpoint=='index' %}` check adds the `active` CSS class when you're currently on that page, making the link highlight green.

```html
    {% if current_user.is_admin %}
    <a href="{{ url_for('admin') }}" {% if request.endpoint=='admin' %}class="active"{% endif %}>Admin</a>
    {% endif %}
```
The Admin link only renders in the HTML if the logged-in user is an admin. Non-admin users never even see this link in the page source.

```html
    <a href="{{ url_for('logout') }}">Logout</a>
  </div>
  <div class="nav-user">{{ current_user.username }}</div>
</nav>
{% endif %}
```
Logout link and the username display on the right side of the nav. `{{ current_user.username }}` outputs the actual username string.

---

```html
<main>
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
    <div class="flash-list">
      {% for cat, msg in messages %}
      <div class="flash {{ cat }}">▶ {{ msg }}</div>
      {% endfor %}
    </div>
    {% endif %}
  {% endwith %}
```
The flash message system. `get_flashed_messages(with_categories=true)` retrieves all queued messages from Flask — each has a category (`error`, `success`, `info`) and a message string. The `{% for %}` loop renders one div per message. `{{ cat }}` in `class="flash {{ cat }}"` adds the category as a CSS class, which the CSS uses to color it red for errors and green for success.

```html
  {% block content %}{% endblock %}
</main>
```
The main content slot. Every child template fills this block with its own unique content. This is where the live feed, admin panel, or any other page content appears.

---
---

# 3. login.html

## Tools, Methods, Functions & Keywords Used

| Name | Type | What it is |
|---|---|---|
| `get_flashed_messages()` | Flask function | Retrieves error messages from Flask to display |
| `{% with %}` | Jinja2 tag | Temporary variable scope |
| `{% for %}` | Jinja2 tag | Loops over messages |
| `{{ msg }}` | Jinja2 syntax | Outputs the message text |
| `method="POST"` | HTML attribute | Sends form data to the server |
| `type="text"` | HTML attribute | A plain text input field |
| `type="password"` | HTML attribute | A password input — characters are hidden |
| `name=""` | HTML attribute | The key Flask uses to read this field via `request.form.get()` |
| `required` | HTML attribute | Browser prevents form submission if this field is empty |
| `autofocus` | HTML attribute | Automatically focuses this input when the page loads |
| `autocomplete` | HTML attribute | Hints to the browser about autofill behavior |
| `@keyframes` | CSS | The slide-up entrance animation |
| `::before` / `::after` | CSS | Pseudo-elements for scanlines and grid background |
| `animation` | CSS | Applies a keyframe animation to an element |

---

## Line by Line

```html
<!DOCTYPE html>
<html lang="en">
<head>
```
Standalone page — does NOT extend `base.html`. It has its own complete HTML structure because it needs a completely different layout (centered card, no navbar).

```html
  <title>SENTINEL — Access</title>
```
Browser tab title for the login page specifically.

```html
  <link href="https://fonts.googleapis.com/...">
```
Same Google Fonts as base.html — loads the monospace and sans-serif fonts.

```html
  <style>
    :root { --bg:#07090a; --bg2:#0c1014; --green:#00e676; ... }
```
Redefines the same CSS variables as base.html. Because this page doesn't extend base.html it needs its own copy.

```html
    html, body { height: 100%; ... display: flex; align-items: center; justify-content: center; }
```
Makes the page full height and uses flexbox to perfectly center the login card both vertically and horizontally.

```html
    body::before { ... repeating-linear-gradient ... }
    body::after  { ... grid background ... }
```
Same scanline and grid effects as base.html — keeps the visual style consistent on the login page.

```html
    .wrap { width: 100%; max-width: 360px; padding: 1.5rem;
            position: relative; z-index: 1; animation: rise .45s ease both; }
    @keyframes rise { from { opacity: 0; transform: translateY(16px) } to { opacity: 1; transform: none } }
```
The login card container. `max-width: 360px` keeps it narrow. `z-index: 1` puts it above the background effects. The `rise` animation slides it up from 16px below and fades it in over 0.45 seconds when the page loads.

```html
    .logo-icon { width: 48px; height: 48px; border: 1px solid var(--border); ... }
    .logo-icon::before { width: 18px; height: 2px; }
    .logo-icon::after  { width: 2px;  height: 18px; }
```
The crosshair/plus icon above the SENTINEL title. A square div with two pseudo-elements — a horizontal bar and a vertical bar — forming a + shape using the green color.

```html
    input[type="text"], input[type="password"] {
      background: var(--bg); border: 1px solid var(--border); color: var(--text);
      font-family: var(--mono); padding: .6rem .8rem; outline: none; transition: border-color .15s;
    }
    input:focus { border-color: var(--green); }
```
Styles the input fields with a dark background and subtle border. `outline: none` removes the browser's default blue focus ring. `input:focus` replaces it with a green border when the field is active.

---

```html
<body>
<div class="wrap">
  <div class="logo">
    <div class="logo-icon"></div>
    <h1>SENTINEL</h1>
    <p>SECURE CAMERA MONITORING SYSTEM</p>
  </div>
```
The centered logo section. The `logo-icon` div has no content — its cross shape comes entirely from the CSS `::before` and `::after` pseudo-elements.

```html
  <div class="card">
    <div class="card-hdr">Authentication Required</div>
```
The login card box. The header row says "Authentication Required" with a decorative line after it (created by `card-hdr::after` in CSS).

```html
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% for cat, msg in messages %}
        <div class="error">▶ {{ msg }}</div>
      {% endfor %}
    {% endwith %}
```
Displays any flash messages from Flask — specifically the "Invalid username or password" error when login fails. Only renders if there are messages — otherwise this section produces no HTML at all.

```html
    <form method="POST" autocomplete="off">
```
Opens the login form. `method="POST"` sends data to the server securely in the request body. `autocomplete="off"` disables browser autofill suggestions on the overall form.

```html
      <div class="field">
        <label>Username</label>
        <input type="text" name="username" required autofocus autocomplete="username"/>
      </div>
```
The username field. `name="username"` is the key Flask uses — `request.form.get('username')`. `required` prevents empty submission. `autofocus` places the cursor here automatically when the page loads.

```html
      <div class="field">
        <label>Password</label>
        <input type="password" name="password" required autocomplete="current-password"/>
      </div>
```
The password field. `type="password"` hides characters as dots. `name="password"` is how Flask reads it.

```html
      <button type="submit" class="btn-submit">▶ AUTHENTICATE</button>
    </form>
```
The submit button. `type="submit"` triggers form submission when clicked. The `▶` is a Unicode character used as a decorative arrow.

```html
  <div class="footer">ALL ACCESS ATTEMPTS ARE LOGGED</div>
```
A warning message below the card reminding users the system logs everything.

---
---

# 4. index.html

## Tools, Methods, Functions & Keywords Used

| Name | Type | What it is |
|---|---|---|
| `{% extends "base.html" %}` | Jinja2 | Inherits the full base layout |
| `{% block head %}` | Jinja2 | Injects page-specific CSS into base.html's head |
| `{% block content %}` | Jinja2 | The main content slot from base.html |
| `{% if stream_url %}` | Jinja2 | Checks if a stream URL has been configured |
| `{{ stream_url }}` | Jinja2 | Outputs the stream URL into the img src |
| `{{ current_user.username }}` | Jinja2 | Outputs the logged-in username |
| `{{ current_user.is_admin }}` | Jinja2 | Checks admin status for conditional links |
| `url_for()` | Flask | Generates URL for the admin route |
| `onerror` | HTML event | Runs JavaScript if the image fails to load |
| `aspect-ratio` | CSS | Maintains 16:9 ratio for the video screen |
| `display: grid` | CSS | Two-column layout for screen and sidebar |
| `setInterval()` | JavaScript | Runs a function repeatedly at a set interval |
| `Date()` | JavaScript | Gets the current date and time |
| `document.getElementById()` | JavaScript | Finds an HTML element by its id attribute |
| `document.createElement()` | JavaScript | Creates a new HTML element dynamically |
| `appendChild()` | JavaScript | Adds a new element inside another element |

---

## Line by Line

```html
{% extends "base.html" %}
```
This page inherits everything from base.html — the nav bar, CSS variables, flash messages, fonts, scanlines. Only the content block needs to be defined here.

```html
{% block title %}SENTINEL — Live Feed{% endblock %}
```
Overrides the `title` block from base.html. The browser tab shows "SENTINEL — Live Feed" instead of the default "SENTINEL".

```html
{% block head %}
<style>
  .feed-wrap { display: grid; grid-template-columns: 1fr 280px; gap: 1.5rem; align-items: start; }
  @media (max-width: 800px) { .feed-wrap { grid-template-columns: 1fr; } }
```
Page-specific styles injected into base.html's head. `display: grid; grid-template-columns: 1fr 280px` creates a two-column layout — the stream takes all remaining space, the sidebar is fixed at 280px wide. The `@media` rule collapses to a single column on screens narrower than 800px (phones and tablets).

```html
  .screen { background: #000; border: 1px solid var(--border); aspect-ratio: 16/9; ... }
```
The video screen container. `aspect-ratio: 16/9` maintains the widescreen ratio regardless of width. Black background so letterboxed streams look correct.

```html
  .live-badge { position: absolute; top: .7rem; left: .7rem; ... }
  .live-badge .dot { ... animation: blink 1s step-end infinite; }
```
The red LIVE badge in the top-left corner of the screen. `position: absolute` places it relative to the `.screen` container (which has `position: relative`). The dot blinks using the same keyframe animation as the brand dot in the nav.

```html
  .ts-overlay { position: absolute; bottom: .6rem; right: .7rem; ... }
```
The timestamp overlay in the bottom-right corner of the screen. Updated every second by JavaScript.

---

```html
{% block content %}
<div class="section-hdr"><h2>Live Camera Feed</h2></div>
```
Opens the content block. The section header with the decorative line after it is defined in base.html's CSS.

```html
<div class="feed-wrap">
  <div>
    <div class="screen" id="screen">
```
The two-column grid wrapper. The first column contains the screen div. `id="screen"` lets JavaScript reference it to add the offline message dynamically.

```html
      {% if stream_url %}
        <img id="stream-img" src="{{ stream_url }}" alt="Live feed" onerror="showOffline()" />
```
If a stream URL is configured — renders an `<img>` tag with the URL as its source. The browser continuously requests MJPEG frames from that URL and displays them as live video. `onerror="showOffline()"` runs the JavaScript function if the stream fails to load.

```html
        <div class="live-badge"><span class="dot"></span>LIVE</div>
        <div class="ts-overlay" id="ts"></div>
```
The LIVE badge and empty timestamp div. The timestamp content is filled in by JavaScript every second.

```html
      {% else %}
        <div class="offline">
          <div class="icon">⊘</div>
          <div>NO STREAM CONFIGURED</div>
          {% if current_user.is_admin %}
            <a href="{{ url_for('admin') }}">Set stream URL in admin panel</a>
          {% else %}
            <div>Contact administrator</div>
          {% endif %}
        </div>
      {% endif %}
```
If no stream URL is set — shows an offline placeholder. Admins see a link to the admin panel. Regular users see a message to contact the admin. The `{% if current_user.is_admin %}` check happens on the server — non-admins never receive the admin link in their HTML.

---

```html
  <div>
    <div class="section-hdr"><h2>Status</h2></div>
    <div class="card">
      <div class="info-row">
        <span class="info-label">User</span>
        <span class="info-val">{{ current_user.username }}</span>
      </div>
```
The sidebar status panel. Each `info-row` has a label and a value. `{{ current_user.username }}` is replaced by Flask with the actual username before sending to the browser.

```html
      <div class="info-row">
        <span class="info-label">Role</span>
        <span class="info-val">
          {% if current_user.is_admin %}<span class="tag tag-amber">Admin</span>
          {% else %}<span class="tag tag-dim">Viewer</span>{% endif %}
        </span>
      </div>
```
Role display. Shows an amber "Admin" tag or a dim "Viewer" tag depending on the user's `is_admin` flag.

```html
      <div class="info-row">
        <span class="info-label">Session</span>
        <span class="info-val" id="uptime">00:00</span>
      </div>
```
Session timer. Starts at `00:00` — JavaScript updates this every second with the elapsed time since the page loaded.

---

```html
<script>
  function tick() {
    const el = document.getElementById('ts');
    if (el) el.textContent = new Date().toLocaleString();
  }
  setInterval(tick, 1000); tick();
```
The timestamp function. `new Date().toLocaleString()` gets the current local date and time as a formatted string. `setInterval(tick, 1000)` runs it every 1000 milliseconds (1 second). The final `tick()` runs it immediately on load so there's no 1-second delay.

```html
  const start = Date.now();
  function uptime() {
    const s = Math.floor((Date.now() - start) / 1000);
    const m = Math.floor(s / 60), sec = s % 60;
    document.getElementById('uptime').textContent =
      String(m).padStart(2,'0') + ':' + String(sec).padStart(2,'0');
  }
  setInterval(uptime, 1000);
```
The session uptime counter. `Date.now()` records the page load time. Every second it calculates elapsed time in seconds, converts to minutes and seconds, and formats as `MM:SS`. `padStart(2,'0')` adds a leading zero so `5` becomes `05`.

```html
  function showOffline() {
    document.getElementById('stream-img').style.display = 'none';
    const d = document.createElement('div');
    d.className = 'offline';
    d.innerHTML = '<div class="icon">⊘</div><div>STREAM OFFLINE</div>...';
    document.getElementById('screen').appendChild(d);
  }
```
Called when the stream image fails to load. Hides the broken image, creates a new div with the offline message, and appends it inside the screen container. This runs entirely in the browser — no server request needed.

---
---

# 5. admin.html

## Tools, Methods, Functions & Keywords Used

| Name | Type | What it is |
|---|---|---|
| `{% extends "base.html" %}` | Jinja2 | Inherits base layout |
| `{% block content %}` | Jinja2 | Main content slot |
| `{% for u in users %}` | Jinja2 | Loops over every user passed from app.py |
| `{% for log in logs %}` | Jinja2 | Loops over every log entry passed from app.py |
| `{{ u.username }}` | Jinja2 | Outputs each user's username |
| `{{ u.created_at.strftime() }}` | Jinja2 | Formats the datetime into a readable string |
| `{% if u.id != current_user.id %}` | Jinja2 | Prevents showing delete button for own account |
| `{{ log.success }}` | Jinja2 | True/False — used to show OK or FAIL tag |
| `name="action"` | HTML | Hidden field that tells app.py which form was submitted |
| `type="hidden"` | HTML | A form field the user cannot see |
| `onsubmit="return confirm()"` | HTML event | Shows a confirmation dialog before deleting |
| `display: grid` | CSS | Two-column layout for add-user and user-list sections |
| `overflow: hidden; text-overflow: ellipsis` | CSS | Truncates long text with `...` |

---

## Line by Line

```html
{% extends "base.html" %}
{% block title %}SENTINEL — Admin{% endblock %}
```
Inherits base layout. Sets the browser tab title.

```html
{% block head %}
<style>
  .admin-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }
  @media(max-width:900px) { .admin-grid { grid-template-columns: 1fr; } }
  .truncate { max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
{% endblock %}
```
Page-specific styles. `grid-template-columns: 1fr 1fr` creates two equal-width columns for the add-user form and user list. `.truncate` cuts long action text in the log table with `...` so it doesn't break the layout.

---

```html
{% block content %}
<div class="section-hdr"><h2>Stream Configuration</h2></div>
<div class="card">
  <form method="POST">
    <input type="hidden" name="action" value="set_stream_url"/>
```
The stream URL form. `type="hidden"` is invisible to the user — it tells `app.py` which of the three forms was submitted (`set_stream_url`, `create_user`, or `delete_user`). This is how one route handles multiple forms.

```html
    <input type="url" name="stream_url" value="{{ stream_url }}" placeholder="https://xxxx.trycloudflare.com/stream"/>
```
The stream URL input. `type="url"` tells the browser to validate it as a URL. `value="{{ stream_url }}"` pre-fills the field with whatever is currently saved in the database — so you can see the current value when editing.

---

```html
<div class="admin-grid">
  <div>
    <div class="section-hdr"><h2>Add User</h2></div>
    <div class="card">
      <form method="POST" autocomplete="off">
        <input type="hidden" name="action" value="create_user"/>
```
The create user form. Hidden action field tells `app.py` this is a `create_user` submission.

```html
        <input type="text" name="username" required autocomplete="off"/>
        <input type="password" name="password" required autocomplete="new-password"/>
```
Username and password fields. `autocomplete="new-password"` hints to the browser this is for creating a new password, not filling an existing one — prevents the browser from suggesting the admin's own saved password.

```html
        <div class="check-row">
          <input type="checkbox" name="is_admin" id="is_admin"/>
          <label for="is_admin">Grant admin access</label>
        </div>
```
The admin checkbox. When checked, the browser sends `is_admin=on` in the form data. In `app.py`: `request.form.get('is_admin') == 'on'` evaluates to True. `for="is_admin"` on the label links it to the checkbox so clicking the label text also toggles the checkbox.

---

```html
  <div>
    <div class="section-hdr"><h2>Users ({{ users|length }})</h2></div>
```
`{{ users|length }}` uses a Jinja2 filter — `length` counts the number of items in the `users` list passed from `app.py`. Shows the total user count in the header.

```html
    <tbody>
      {% for u in users %}
      <tr>
        <td>{{ u.username }}</td>
        <td>{% if u.is_admin %}<span class="tag tag-amber">Admin</span>{% else %}<span class="tag tag-dim">Viewer</span>{% endif %}</td>
        <td>{{ u.created_at.strftime('%Y-%m-%d') }}</td>
```
Loops over every user and creates one table row per user. `strftime('%Y-%m-%d')` formats the datetime object into a readable date string like `2025-01-15`.

```html
        <td>
          {% if u.id != current_user.id %}
          <form method="POST" style="display:inline" onsubmit="return confirm('Delete {{ u.username }}?')">
            <input type="hidden" name="action" value="delete_user"/>
            <input type="hidden" name="user_id" value="{{ u.id }}"/>
            <button class="btn btn-danger btn-sm">Delete</button>
          </form>
```
The delete button — only shown if this row is NOT the currently logged-in user (prevents self-deletion). `onsubmit="return confirm(...)"` shows a browser confirmation dialog before submitting — if the admin clicks Cancel, `confirm()` returns false and the form doesn't submit. Two hidden fields send the action type and the user's database ID to `app.py`.

---

```html
<div class="section-hdr" style="margin-top:2rem"><h2>Access Log (last 100)</h2></div>
<div class="card" style="padding:0">
  <div class="table-wrap">
    <table>
      <thead><tr><th>Timestamp</th><th>IP</th><th>User</th><th>Action</th><th>Result</th></tr></thead>
      <tbody>
        {% for log in logs %}
        <tr>
          <td>{{ log.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</td>
          <td>{{ log.ip_address }}</td>
          <td>{{ log.username }}</td>
          <td class="truncate" title="{{ log.action }}">{{ log.action }}</td>
          <td>{% if log.success %}<span class="tag tag-green">OK</span>{% else %}<span class="tag tag-red">FAIL</span>{% endif %}</td>
        </tr>
        {% endfor %}
```
The access log table. Loops over the last 100 log entries passed from `app.py`. `strftime('%Y-%m-%d %H:%M:%S')` formats the timestamp with hours, minutes, and seconds. The `truncate` class cuts long action strings — `title="{{ log.action }}"` shows the full text on hover. The Result column shows a green OK tag for successes and a red FAIL tag for failures.

```html
        {% if not logs %}
        <tr><td colspan="5" style="color:var(--dim);text-align:center;padding:1rem">No logs yet.</td></tr>
        {% endif %}
```
If the log table is empty — shows a centered "No logs yet" message spanning all 5 columns (`colspan="5"`).
