from flask import Flask, render_template, request, redirect, url_for, session, flash
import json, os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'change-me-to-a-random-secret'  # change in production
DATA_FILE = 'data.json'
USERS_FILE = 'users.json'

def load_properties():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_properties(properties):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(properties, f, ensure_ascii=False, indent=4)

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

def current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    users = load_users()
    for u in users:
        if u['id'] == uid:
            return u
    return None

@app.context_processor
def inject_user():
    return {'current_user': current_user()}

@app.route('/')
def index():
    query = request.args.get('q','')
    sort = request.args.get('sort','none')
    props = load_properties()
    if query:
        props = [p for p in props if query.lower() in p.get('title','').lower()]
    if sort == 'asc':
        props = sorted(props, key=lambda p: p.get('price',0))
    elif sort == 'desc':
        props = sorted(props, key=lambda p: p.get('price',0), reverse=True)
    return render_template('index.html', properties=props, query=query, sort=sort)

@app.route('/property/<int:prop_id>')
def property_view(prop_id):
    props = load_properties()
    prop = next((p for p in props if p.get('id')==prop_id), None)
    if not prop:
        return "Лот не найден", 404
    return render_template('property.html', prop=prop)

@app.route('/property/<int:prop_id>/bid', methods=['POST'])
def bid(prop_id):
    user = current_user()
    if not user:
        flash("Требуется авторизация для ставки")
        return redirect(url_for('login', next=url_for('property_view', prop_id=prop_id)))
    amount = request.form.get('amount')
    # For demo, we won't persist bids; just flash a confirmation
    flash(f"Ставка {amount}₽ принята для лота #{prop_id} — отправлено на обработку")
    return redirect(url_for('property_view', prop_id=prop_id))

@app.route('/add', methods=['GET','POST'])
def add_property():
    user = current_user()
    if not user:
        flash("Требуется авторизация для добавления лота")
        return redirect(url_for('login', next=url_for('add_property')))
    if request.method == 'POST':
        props = load_properties()
        new_id = max([p.get('id',0) for p in props] + [0]) + 1
        title = request.form.get('title','').strip()
        price = int(request.form.get('price') or 0)
        description = request.form.get('description','').strip()
        image = request.form.get('image') or '/static/images/default.svg'
        props.append({'id': new_id, 'title': title, 'price': price, 'description': description, 'image': image, 'owner': user['username']})
        save_properties(props)
        flash("Лот добавлен")
        return redirect(url_for('index'))
    return render_template('add_property.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        users = load_users()
        user = next((u for u in users if u['username']==username), None)
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            flash('Вы успешно вошли')
            next_url = request.args.get('next') or url_for('index')
            return redirect(next_url)
        flash('Неверное имя пользователя или пароль')
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        if not username or not password:
            flash('Введите имя и пароль')
            return redirect(url_for('register'))
        users = load_users()
        if any(u['username']==username for u in users):
            flash('Пользователь с таким именем уже существует')
            return redirect(url_for('register'))
        new_id = max([u.get('id',0) for u in users] + [0]) + 1
        users.append({'id': new_id, 'username': username, 'password_hash': generate_password_hash(password)})
        save_users(users)
        flash('Регистрация прошла успешно — войдите в систему')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/profile')
def profile():
    user = current_user()
    if not user:
        return redirect(url_for('login', next=url_for('profile')))
    # show user's listings
    props = load_properties()
    my_props = [p for p in props if p.get('owner')==user['username']]
    return render_template('profile.html', user=user, properties=my_props)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Вы вышли')
    return redirect(url_for('index'))

if __name__ == '__main__':
    # create sample data if missing
    if not os.path.exists(DATA_FILE):
        sample = [
            {"id": 1, "title": "Квартира в центре", "price": 7500000, "description": "2 комнаты, метро 5 минут", "image": "/static/images/flat.svg", "owner": "admin"},
            {"id": 2, "title": "Дом у озера", "price": 12500000, "description": "Участок, сад, гараж", "image": "/static/images/house.svg", "owner": "admin"},
            {"id": 3, "title": "Апартаменты у моря", "price": 9800000, "description": "Балкон с видом на закат", "image": "/static/images/seaside.svg", "owner": "admin"}
        ]
        save_properties(sample)
    if not os.path.exists(USERS_FILE):
        save_users([{'id':1,'username':'admin','password_hash':generate_password_hash('admin')}])
    app.run(debug=True, host='0.0.0.0')
