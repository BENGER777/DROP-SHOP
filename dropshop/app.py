# DROP SHOP — Полный финальный app.py (истории с группировкой и просмотрами, эфиры, голосовые, всё)
from flask import Flask, render_template, request, redirect, session, send_from_directory, jsonify
import sqlite3
import hashlib
from datetime import datetime, timedelta
import threading
import time
import os
import json
import random
import string
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'dropshop_secret_key_2024'

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS_IMG = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_EXTENSIONS_VID = {'mp4', 'webm', 'mov'}
ALLOWED_EXTENSIONS_AUDIO = {'mp3', 'ogg', 'wav', 'webm'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file_img(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_IMG

def allowed_file_vid(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_VID

def allowed_file_audio(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_AUDIO

@app.context_processor
def inject_notification_count():
    if 'user_id' in session:
        conn = get_db()
        count = conn.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0",
                             (session['user_id'],)).fetchone()[0]
        conn.close()
        return {'unread_notifications': count}
    return {'unread_notifications': 0}

@app.context_processor
def inject_cart_count():
    if 'user_id' in session:
        conn = get_db()
        count = conn.execute("SELECT COUNT(*) FROM cart_items WHERE user_id=?", 
                             (session['user_id'],)).fetchone()[0]
        conn.close()
        return {'cart_count': count}
    return {'cart_count': 0}

@app.context_processor
def inject_wishlist_count():
    if 'user_id' in session:
        conn = get_db()
        count = conn.execute("SELECT COUNT(*) FROM wishlist WHERE user_id=?", 
                             (session['user_id'],)).fetchone()[0]
        conn.close()
        return {'wishlist_count': count}
    return {'wishlist_count': 0}

@app.context_processor
def inject_bookmarks_count():
    if 'user_id' in session:
        conn = get_db()
        count = conn.execute("SELECT COUNT(*) FROM post_bookmarks WHERE user_id=?", 
                             (session['user_id'],)).fetchone()[0]
        conn.close()
        return {'bookmarks_count': count}
    return {'bookmarks_count': 0}

def get_db():
    conn = sqlite3.connect('dropshop.db')
    conn.row_factory = sqlite3.Row
    for col, tbl in [('avatar_url', 'users'), ('address', 'orders'), ('contact', 'orders'), ('comment', 'orders'),
                     ('name', 'conversations'), ('avatar_url', 'conversations'), ('admin_id', 'conversations'),
                     ('is_read', 'conversation_messages'), ('is_read', 'messages'), ('referral_code', 'users'),
                     ('referred_by', 'users'), ('video_url', 'products'), ('active', 'promotions'),
                     ('created_at', 'promotions'), ('sizes', 'products'), ('msg_type', 'messages')]:
        try:
            conn.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} TEXT")
        except:
            pass
    try:
        conn.execute("ALTER TABLE cart_items ADD COLUMN size TEXT")
    except:
        pass
    try:
        conn.execute("ALTER TABLE messages ADD COLUMN quoted_msg_id INTEGER")
    except:
        pass
    try:
        conn.execute("ALTER TABLE conversation_messages ADD COLUMN quoted_msg_id INTEGER")
    except:
        pass
    return conn

def add_notification(user_id, content, link='/'):
    conn = get_db()
    conn.execute("INSERT INTO notifications (user_id, content, link) VALUES (?, ?, ?)",
                 (user_id, content, link))
    conn.commit()
    conn.close()

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            avatar_url TEXT,
            points INTEGER DEFAULT 0,
            role TEXT DEFAULT 'user',
            referral_code TEXT UNIQUE,
            referred_by INTEGER,
            last_seen TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER DEFAULT 0,
            description TEXT,
            image_url TEXT,
            video_url TEXT,
            sizes TEXT
        );
        CREATE TABLE IF NOT EXISTS friendships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            friend_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            avatar_url TEXT,
            admin_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS conversation_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS conversation_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            quoted_msg_id INTEGER,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS cart_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            size TEXT
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            group_purchase_id INTEGER,
            final_price REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            address TEXT,
            contact TEXT,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS group_purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            creator_id INTEGER NOT NULL,
            discount REAL DEFAULT 0,
            status TEXT DEFAULT 'active',
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS group_purchase_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            finished INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS group_purchase_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            image_url TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            msg_type TEXT DEFAULT 'text',
            quoted_msg_id INTEGER,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS message_reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            reaction TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(message_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS bonus_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, post_id)
        );
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            link TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS promos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            discount_type TEXT NOT NULL,
            value REAL NOT NULL,
            max_uses INTEGER DEFAULT 0,
            used_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, product_id)
        );
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_id INTEGER NOT NULL,
            bonus_paid INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            endpoint TEXT NOT NULL,
            p256dh TEXT NOT NULL,
            auth TEXT NOT NULL,
            UNIQUE(user_id, endpoint)
        );
        CREATE TABLE IF NOT EXISTS post_bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, post_id)
        );
        CREATE TABLE IF NOT EXISTS typing_status (
            user_id INTEGER NOT NULL,
            peer_id INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, peer_id)
        );
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            blocker_id INTEGER NOT NULL,
            blocked_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(blocker_id, blocked_id)
        );
        CREATE TABLE IF NOT EXISTS promotions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            discount_percent REAL NOT NULL,
            product_id INTEGER,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS pinned_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            pinned_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS stories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            image_url TEXT,
            video_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP DEFAULT (datetime('now', '+1 day'))
        );
        CREATE TABLE IF NOT EXISTS story_views (
            story_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            PRIMARY KEY (story_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS streams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            video_url TEXT,
            is_live INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        products = [
            ('Nike Air Force 1 Original', 'original', 12990, 5, 'Культовые кроссовки Nike. 100% оригинал.', '["39","40","41","42","43"]'),
            ('Nike Air Force 1 Replica AAA', 'replica', 4990, 20, 'Точная копия премиум качества.', '["39","40","41","42","43","44"]'),
            ('Balenciaga Hoodie Original', 'original', 89990, 2, 'Худи Balenciaga из новой коллекции.', '["XS","S","M","L","XL"]'),
            ('Balenciaga Hoodie Replica 1:1', 'replica', 8990, 15, 'Реальное качество 1:1.', '["XS","S","M","L","XL","XXL"]'),
            ('Jordan 4 Retro Original', 'original', 24990, 3, 'Air Jordan 4 Retro. Оригинал из США.', '["40","41","42","43"]'),
            ('Jordan 4 Retro Replica Box', 'replica', 7490, 25, 'Реа-а-ально крутое качество.', '["39","40","41","42","43","44"]'),
            ('Essentials Hoodie Original', 'original', 15990, 4, 'Fear of God Essentials. Оригинал с тегами.', '["S","M","L","XL"]'),
            ('Essentials Hoodie Replica Premium', 'replica', 3990, 30, 'Неотличим от оригинала.', '["XS","S","M","L","XL","XXL"]')
        ]
        for p in products:
            c.execute("INSERT INTO products (name, type, price, stock, description, sizes) VALUES (?, ?, ?, ?, ?, ?)", p)
    admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (username, password_hash, role, points) VALUES (?, ?, 'admin', 1000)",
              ('admin', admin_hash))
    conn.commit()
    conn.close()

init_db()

def get_discount(participants):
    discounts = {1: 0, 2: 2, 3: 4, 4: 6, 5: 8, 6: 10}
    return discounts.get(participants, 10)

def check_expired_groups():
    while True:
        time.sleep(60)
        conn = get_db()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        expired = conn.execute("SELECT * FROM group_purchases WHERE status='active' AND expires_at <= ?", (now,)).fetchall()
        for gp in expired:
            conn.execute("UPDATE group_purchases SET status='cancelled' WHERE id=?", (gp['id'],))
        conn.commit()
        conn.close()

threading.Thread(target=check_expired_groups, daemon=True).start()

# ==================== МАРШРУТЫ ====================
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/')
def index():
    conn = get_db()
    blocked_ids = []
    if 'user_id' in session:
        blocked_ids = [row['blocked_id'] for row in conn.execute("SELECT blocked_id FROM blocks WHERE blocker_id=?", (session['user_id'],)).fetchall()]
    if 'user_id' in session:
        last_orders = conn.execute("""
            SELECT products.type FROM orders 
            JOIN products ON orders.product_id = products.id 
            WHERE orders.user_id=? AND orders.status='completed' 
            ORDER BY orders.created_at DESC LIMIT 5
        """, (session['user_id'],)).fetchall()
        fav_type = None
        if last_orders:
            types = [row['type'] for row in last_orders]
            fav_type = max(set(types), key=types.count)
        if fav_type:
            products = conn.execute("SELECT * FROM products WHERE type=? ORDER BY RANDOM() LIMIT 4", (fav_type,)).fetchall()
        else:
            products = conn.execute("SELECT * FROM products ORDER BY RANDOM() LIMIT 4").fetchall()
    else:
        products = conn.execute("SELECT * FROM products ORDER BY RANDOM() LIMIT 4").fetchall()
    query = """
        SELECT posts.*, users.username,
               (SELECT COUNT(*) FROM likes WHERE post_id=posts.id) as likes_count,
               (SELECT COUNT(*) FROM comments WHERE post_id=posts.id) as comments_count
        FROM posts JOIN users ON posts.user_id = users.id 
        WHERE 1=1
    """
    params = []
    if blocked_ids:
        query += " AND posts.user_id NOT IN ({})".format(','.join('?'*len(blocked_ids)))
        params.extend(blocked_ids)
    query += " ORDER BY posts.created_at DESC LIMIT 20"
    posts = conn.execute(query, params).fetchall()
    group_buys = conn.execute("SELECT * FROM group_purchases WHERE status='active' LIMIT 5").fetchall()
    promotion = conn.execute("SELECT * FROM promotions WHERE active=1 AND datetime('now') BETWEEN start_date AND end_date ORDER BY discount_percent DESC LIMIT 1").fetchone()
    stories = []
    if 'user_id' in session:
        stories_raw = conn.execute("""
            SELECT DISTINCT stories.user_id, users.username, users.avatar_url,
                   (SELECT COUNT(*) FROM story_views WHERE story_views.story_id IN (SELECT id FROM stories WHERE user_id=users.id) AND story_views.user_id=?) as viewed_count,
                   (SELECT COUNT(*) FROM stories WHERE user_id=users.id AND expires_at > datetime('now')) as total_count
            FROM stories
            JOIN users ON stories.user_id = users.id
            WHERE stories.expires_at > datetime('now')
            ORDER BY stories.created_at DESC
        """, (session['user_id'],)).fetchall()
        for row in stories_raw:
            d = dict(row)
            d['viewed'] = (d['viewed_count'] == d['total_count'])
            stories.append(d)
    else:
        stories_raw = conn.execute("""
            SELECT DISTINCT stories.user_id, users.username, users.avatar_url
            FROM stories JOIN users ON stories.user_id = users.id
            WHERE stories.expires_at > datetime('now')
            ORDER BY stories.created_at DESC
        """).fetchall()
        for row in stories_raw:
            d = dict(row)
            d['viewed'] = False
            stories.append(d)
    conn.close()
    return render_template('index.html', posts=posts, products=products, group_buys=group_buys, promotion=promotion, stories=stories)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        ref_code = request.form.get('ref', '').strip()
        conn = get_db()
        def generate_code():
            return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        code = generate_code()
        while conn.execute("SELECT id FROM users WHERE referral_code=?", (code,)).fetchone():
            code = generate_code()
        try:
            referred_by = None
            if ref_code:
                referrer = conn.execute("SELECT id FROM users WHERE referral_code=?", (ref_code,)).fetchone()
                if referrer:
                    referred_by = referrer['id']
            conn.execute("INSERT INTO users (username, password_hash, referral_code, referred_by) VALUES (?, ?, ?, ?)",
                         (username, password_hash, code, referred_by))
            conn.commit()
            if referred_by:
                new_user_id = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()['id']
                conn.execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referred_by, new_user_id))
                conn.commit()
            conn.close()
            return redirect('/login')
        except:
            conn.close()
            return "Пользователь уже существует"
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password_hash=?",
                           (username, password_hash)).fetchone()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            conn.execute("UPDATE users SET last_seen=CURRENT_TIMESTAMP WHERE id=?", (user['id'],))
            conn.commit()
            conn.close()
            return redirect('/')
        conn.close()
        return "Неверный логин или пароль"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/ping')
def ping():
    if 'user_id' in session:
        conn = get_db()
        conn.execute("UPDATE users SET last_seen=CURRENT_TIMESTAMP WHERE id=?", (session['user_id'],))
        conn.commit()
        conn.close()
        return '', 204
    return '', 401

# ========== МАГАЗИН ==========
@app.route('/shop')
def shop():
    filter_type = request.args.get('type', 'all')
    search_query = request.args.get('q', '').strip()
    price_min = request.args.get('price_min', type=int, default=0)
    price_max = request.args.get('price_max', type=int, default=9999999)
    conn = get_db()
    query = """
        SELECT p.*, 
               ROUND(AVG(r.rating), 1) as avg_rating, 
               COUNT(r.id) as review_count
        FROM products p
        LEFT JOIN reviews r ON p.id = r.product_id
        WHERE 1=1
    """
    params = []
    if filter_type != 'all':
        query += " AND p.type=?"
        params.append(filter_type)
    if search_query:
        query += " AND (p.name LIKE ? OR p.description LIKE ?)"
        params.extend([f'%{search_query}%', f'%{search_query}%'])
    query += " AND p.price >= ? AND p.price <= ?"
    params.extend([price_min, price_max])
    query += " GROUP BY p.id"
    products = conn.execute(query, params).fetchall()
    promos_active = {}
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    promos = conn.execute("SELECT * FROM promotions WHERE active=1 AND start_date<=? AND end_date>=?", (now, now)).fetchall()
    for promo in promos:
        if promo['product_id']:
            promos_active[promo['product_id']] = promo
    conn.close()
    return render_template('shop.html', products=products, current_filter=filter_type, search_query=search_query,
                         price_min=price_min, price_max=price_max, promos_active=promos_active)

@app.route('/product/<int:id>')
def product(id):
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id=?", (id,)).fetchone()
    active_gb = conn.execute("SELECT * FROM group_purchases WHERE status='active'").fetchall()
    reviews = conn.execute("""
        SELECT reviews.*, users.username, users.avatar_url
        FROM reviews JOIN users ON reviews.user_id = users.id 
        WHERE product_id=? ORDER BY reviews.created_at DESC
    """, (id,)).fetchall()
    avg_rating = conn.execute("SELECT ROUND(AVG(rating), 1) FROM reviews WHERE product_id=?", (id,)).fetchone()[0] or 0
    review_count = conn.execute("SELECT COUNT(*) FROM reviews WHERE product_id=?", (id,)).fetchone()[0]
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    promo = conn.execute("SELECT * FROM promotions WHERE active=1 AND product_id=? AND start_date<=? AND end_date>=?", (id, now, now)).fetchone()
    conn.close()
    return render_template('product.html', product=product, active_gb=active_gb,
                         reviews=reviews, avg_rating=avg_rating, review_count=review_count, promo=promo)

@app.route('/add_to_cart/<int:product_id>', methods=['GET', 'POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if not product:
        conn.close()
        return "Товар не найден", 404
    if request.method == 'POST':
        size = request.form.get('size', '')
        quantity = request.form.get('quantity', 1, type=int)
        existing = conn.execute("SELECT * FROM cart_items WHERE user_id=? AND product_id=? AND size=?",
                                (session['user_id'], product_id, size)).fetchone()
        if existing:
            conn.execute("UPDATE cart_items SET quantity=quantity+? WHERE id=?", (quantity, existing['id']))
        else:
            conn.execute("INSERT INTO cart_items (user_id, product_id, quantity, size) VALUES (?, ?, ?, ?)",
                         (session['user_id'], product_id, quantity, size))
        conn.commit()
        conn.close()
        return redirect('/cart')
    sizes = []
    if product['sizes']:
        try:
            sizes = json.loads(product['sizes'])
        except:
            pass
    conn.close()
    return render_template('add_to_cart.html', product=product, sizes=sizes)

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    items = conn.execute("""
        SELECT cart_items.*, products.name, products.price, products.image_url, products.video_url
        FROM cart_items JOIN products ON cart_items.product_id = products.id 
        WHERE cart_items.user_id=?
    """, (session['user_id'],)).fetchall()
    total = sum(item['price'] * item['quantity'] for item in items)
    conn.close()
    return render_template('cart.html', items=items, total=total)

@app.route('/remove_from_cart/<int:item_id>')
def remove_from_cart(item_id):
    conn = get_db()
    conn.execute("DELETE FROM cart_items WHERE id=? AND user_id=?", (item_id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect('/cart')

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    items = conn.execute("""
        SELECT cart_items.*, products.name, products.price, products.image_url 
        FROM cart_items JOIN products ON cart_items.product_id = products.id 
        WHERE cart_items.user_id=?
    """, (session['user_id'],)).fetchall()
    if not items:
        conn.close()
        return redirect('/cart')
    if request.method == 'POST':
        address = request.form.get('address', '').strip()
        contact = request.form.get('contact', '').strip()
        comment = request.form.get('comment', '').strip()
        for item in items:
            product = conn.execute("SELECT * FROM products WHERE id=?", (item['product_id'],)).fetchone()
            if product and product['stock'] >= item['quantity']:
                final_price = product['price'] * item['quantity']
                conn.execute("INSERT INTO orders (user_id, product_id, final_price, status, address, contact, comment) VALUES (?, ?, ?, 'processing', ?, ?, ?)",
                             (session['user_id'], item['product_id'], final_price, address, contact, comment))
                conn.execute("UPDATE products SET stock=stock-? WHERE id=?", (item['quantity'], item['product_id']))
                bonus = int(final_price * 0.01)
                conn.execute("UPDATE users SET points = points + ? WHERE id = ?", (bonus, session['user_id']))
                conn.execute("INSERT INTO bonus_transactions (user_id, amount, description) VALUES (?, ?, 'Покупка')",
                             (session['user_id'], bonus))
            else:
                conn.close()
                return "Товар недоступен", 400
        user = conn.execute("SELECT referred_by FROM users WHERE id=?", (session['user_id'],)).fetchone()
        if user and user['referred_by']:
            already_paid = conn.execute("SELECT bonus_paid FROM referrals WHERE referrer_id=? AND referred_id=?", 
                                        (user['referred_by'], session['user_id'])).fetchone()
            if already_paid and already_paid['bonus_paid'] == 0:
                conn.execute("UPDATE users SET points = points + 500 WHERE id=?", (user['referred_by'],))
                conn.execute("INSERT INTO bonus_transactions (user_id, amount, description) VALUES (?, 500, 'Реферальный бонус')",
                             (user['referred_by'],))
                conn.execute("UPDATE referrals SET bonus_paid=1 WHERE referrer_id=? AND referred_id=?", 
                             (user['referred_by'], session['user_id']))
                add_notification(user['referred_by'], f"@{session['username']} совершил первую покупку! Вы получили 500 бонусов.")
        conn.execute("DELETE FROM cart_items WHERE user_id=?", (session['user_id'],))
        conn.commit()
        conn.close()
        return redirect('/orders')
    total = sum(item['price'] * item['quantity'] for item in items)
    conn.close()
    return render_template('checkout.html', items=items, total=total)

@app.route('/orders')
def orders():
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    orders = conn.execute("""
        SELECT orders.*, products.name 
        FROM orders JOIN products ON orders.product_id = products.id 
        WHERE orders.user_id=? AND orders.group_purchase_id IS NULL
        ORDER BY orders.created_at DESC
    """, (session['user_id'],)).fetchall()
    conn.close()
    return render_template('orders.html', orders=orders)

# ========== ГРУППОВЫЕ ПОКУПКИ ==========
@app.route('/group/start/<int:product_id>')
def start_group_from_product(product_id):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    expires_at = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')
    c = conn.cursor()
    c.execute("INSERT INTO group_purchases (creator_id, expires_at) VALUES (?, ?)", (session['user_id'], expires_at))
    group_id = c.lastrowid
    c.execute("INSERT INTO group_purchase_participants (group_id, user_id) VALUES (?, ?)", (group_id, session['user_id']))
    c.execute("INSERT INTO group_purchase_items (group_id, user_id, product_id, quantity) VALUES (?, ?, ?, 1)",
              (group_id, session['user_id'], product_id))
    conn.commit()
    conn.close()
    return redirect(f'/group/{group_id}')

@app.route('/group/create', methods=['GET', 'POST'])
def create_group():
    if 'user_id' not in session:
        return redirect('/login')
    if request.method == 'POST':
        conn = get_db()
        expires_at = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')
        c = conn.cursor()
        c.execute("INSERT INTO group_purchases (creator_id, expires_at) VALUES (?, ?)", (session['user_id'], expires_at))
        group_id = c.lastrowid
        c.execute("INSERT INTO group_purchase_participants (group_id, user_id) VALUES (?, ?)", (group_id, session['user_id']))
        friends = request.form.getlist('friends')
        for fid in friends:
            c.execute("INSERT INTO group_purchase_participants (group_id, user_id) VALUES (?, ?)", (group_id, int(fid)))
        conn.commit()
        conn.close()
        return redirect(f'/group/{group_id}')
    conn = get_db()
    friends = conn.execute("""
        SELECT users.id, users.username FROM friendships 
        JOIN users ON (friendships.friend_id = users.id OR friendships.user_id = users.id) 
        WHERE (friendships.user_id=? OR friendships.friend_id=?) AND friendships.status='accepted' AND users.id != ?
    """, (session['user_id'], session['user_id'], session['user_id'])).fetchall()
    conn.close()
    return render_template('create_group.html', friends=friends)

@app.route('/group/<int:group_id>')
def view_group(group_id):
    conn = get_db()
    group = conn.execute("SELECT * FROM group_purchases WHERE id=?", (group_id,)).fetchone()
    if not group:
        conn.close()
        return "Группа не найдена", 404
    participants = conn.execute("""
        SELECT group_purchase_participants.*, users.username, users.avatar_url 
        FROM group_purchase_participants JOIN users ON group_purchase_participants.user_id = users.id 
        WHERE group_id=?
    """, (group_id,)).fetchall()
    items = conn.execute("""
        SELECT group_purchase_items.*, products.name, products.price 
        FROM group_purchase_items JOIN products ON group_purchase_items.product_id = products.id 
        WHERE group_id=?
    """, (group_id,)).fetchall()
    discount = get_discount(len(participants))
    finished = False
    if 'user_id' in session:
        part = conn.execute("SELECT finished FROM group_purchase_participants WHERE group_id=? AND user_id=?",
                            (group_id, session['user_id'])).fetchone()
        finished = part is not None and part['finished'] == 1
    conn.close()
    return render_template('group.html', group=group, participants=participants, items=items, discount=discount, finished=finished)

@app.route('/group/<int:group_id>/add_item', methods=['POST'])
def add_item_to_group(group_id):
    if 'user_id' not in session:
        return redirect('/login')
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', 1, type=int)
    conn = get_db()
    conn.execute("INSERT INTO group_purchase_items (group_id, user_id, product_id, quantity) VALUES (?, ?, ?, ?)",
                 (group_id, session['user_id'], product_id, quantity))
    conn.commit()
    conn.close()
    return redirect(f'/group/{group_id}')

@app.route('/group/<int:group_id>/finish')
def finish_group(group_id):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    part = conn.execute("SELECT * FROM group_purchase_participants WHERE group_id=? AND user_id=? AND finished=0",
                        (group_id, session['user_id'])).fetchone()
    if part:
        conn.execute("UPDATE group_purchase_participants SET finished=1 WHERE id=?", (part['id'],))
        conn.commit()
    all_finished = conn.execute("SELECT COUNT(*) FROM group_purchase_participants WHERE group_id=? AND finished=0",
                                (group_id,)).fetchone()[0] == 0
    if all_finished:
        group = conn.execute("SELECT * FROM group_purchases WHERE id=?", (group_id,)).fetchone()
        participants_count = conn.execute("SELECT COUNT(*) FROM group_purchase_participants WHERE group_id=?",
                                          (group_id,)).fetchone()[0]
        discount = get_discount(participants_count)
        items = conn.execute("SELECT * FROM group_purchase_items WHERE group_id=?", (group_id,)).fetchall()
        for item in items:
            product = conn.execute("SELECT * FROM products WHERE id=?", (item['product_id'],)).fetchone()
            if product and product['stock'] >= item['quantity']:
                final_price = round(product['price'] * item['quantity'] * (1 - discount/100))
                conn.execute("INSERT INTO orders (user_id, product_id, group_purchase_id, final_price, status) VALUES (?, ?, ?, ?, 'completed')",
                             (item['user_id'], item['product_id'], group_id, final_price))
                conn.execute("UPDATE products SET stock=stock-? WHERE id=?", (item['quantity'], item['product_id']))
                bonus = int(final_price * 0.01)
                conn.execute("UPDATE users SET points = points + ? WHERE id = ?", (bonus, item['user_id']))
                conn.execute("INSERT INTO bonus_transactions (user_id, amount, description) VALUES (?, ?, 'Групповая покупка')",
                             (item['user_id'], bonus))
        conn.execute("UPDATE group_purchases SET discount=?, status='completed' WHERE id=?", (discount, group_id))
    conn.commit()
    conn.close()
    return redirect(f'/group/{group_id}')

# ========== ДРУЗЬЯ ==========
@app.route('/friends')
def friends():
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    friends = conn.execute("""
        SELECT users.id, users.username, users.avatar_url FROM friendships 
        JOIN users ON (friendships.friend_id = users.id OR friendships.user_id = users.id) 
        WHERE (friendships.user_id=? OR friendships.friend_id=?) AND friendships.status='accepted' AND users.id != ?
    """, (session['user_id'], session['user_id'], session['user_id'])).fetchall()
    incoming = conn.execute("""
        SELECT friendships.id as req_id, users.id, users.username, users.avatar_url FROM friendships 
        JOIN users ON friendships.user_id = users.id 
        WHERE friendships.friend_id=? AND friendships.status='pending'
    """, (session['user_id'],)).fetchall()
    conn.close()
    return render_template('friends.html', friends=friends, incoming=incoming)

@app.route('/search_friends', methods=['GET'])
def search_friends():
    query = request.args.get('q', '').strip()
    if not query:
        return redirect('/friends')
    conn = get_db()
    results = conn.execute("SELECT * FROM users WHERE username LIKE ? AND id != ?", (f'%{query}%', session['user_id'])).fetchall()
    conn.close()
    return render_template('search_friends.html', results=results)

@app.route('/add_friend/<int:friend_id>')
def add_friend(friend_id):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    conn.execute("INSERT INTO friendships (user_id, friend_id) VALUES (?, ?)", (session['user_id'], friend_id))
    conn.commit()
    conn.close()
    return redirect('/friends')

@app.route('/accept_friend/<int:request_id>')
def accept_friend(request_id):
    conn = get_db()
    conn.execute("UPDATE friendships SET status='accepted' WHERE id=?", (request_id,))
    conn.commit()
    conn.close()
    return redirect('/friends')

@app.route('/remove_friend/<int:user_id>')
def remove_friend(user_id):
    conn = get_db()
    conn.execute("DELETE FROM friendships WHERE (user_id=? AND friend_id=?) OR (user_id=? AND friend_id=?)",
                 (session['user_id'], user_id, user_id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect('/friends')

# ========== СООБЩЕНИЯ ==========
@app.route('/messages')
def messages():
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    friends = conn.execute("""
        SELECT DISTINCT u.id, u.username, u.avatar_url, u.last_seen,
            (SELECT content FROM messages WHERE (sender_id=u.id AND receiver_id=?) OR (sender_id=? AND receiver_id=u.id) ORDER BY created_at DESC LIMIT 1) as last_msg,
            (SELECT COUNT(*) FROM messages WHERE sender_id=u.id AND receiver_id=? AND is_read=0) as unread
        FROM friendships f
        JOIN users u ON (f.friend_id = u.id OR f.user_id = u.id)
        WHERE (f.user_id=? OR f.friend_id=?) AND f.status='accepted' AND u.id != ?
    """, (session['user_id'], session['user_id'], session['user_id'], session['user_id'], session['user_id'], session['user_id'])).fetchall()
    conversations = conn.execute("""
        SELECT c.*, 
            (SELECT content FROM conversation_messages WHERE conversation_id=c.id ORDER BY created_at DESC LIMIT 1) as last_msg
        FROM conversations c
        JOIN conversation_participants cp ON c.id = cp.conversation_id
        WHERE cp.user_id = ?
    """, (session['user_id'],)).fetchall()
    conn.close()
    now = datetime.now()
    friends_enhanced = []
    for f in friends:
        d = dict(f)
        d['is_online'] = False
        if f['last_seen']:
            try:
                last_seen_dt = datetime.strptime(f['last_seen'], '%Y-%m-%d %H:%M:%S')
                d['is_online'] = (now - last_seen_dt).seconds < 120
            except:
                pass
        friends_enhanced.append(d)
    return render_template('messages.html', friends=friends_enhanced, conversations=conversations)

@app.route('/chat/<int:user_id>', methods=['GET', 'POST'])
def chat(user_id):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    if request.method == 'POST':
        if 'content' in request.form:
            content = request.form['content']
            quoted_id = request.form.get('quoted_msg_id', type=int)
            conn.execute("INSERT INTO messages (sender_id, receiver_id, content, quoted_msg_id) VALUES (?, ?, ?, ?)",
                        (session['user_id'], user_id, content, quoted_id))
            conn.commit()
            add_notification(user_id, f"Новое сообщение от @{session['username']}", f"/chat/{session['user_id']}")
        elif 'audio' in request.files:
            file = request.files['audio']
            if file and file.filename != '':
                filename = secure_filename(f"voice_{session['user_id']}_{int(time.time())}.mp3")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                audio_url = f"/uploads/{filename}"
                conn.execute("INSERT INTO messages (sender_id, receiver_id, content, msg_type) VALUES (?, ?, ?, 'voice')",
                            (session['user_id'], user_id, audio_url))
                conn.commit()
                add_notification(user_id, f"🎤 Голосовое сообщение от @{session['username']}", f"/chat/{session['user_id']}")
    conn.execute("UPDATE messages SET is_read=1 WHERE sender_id=? AND receiver_id=?", (user_id, session['user_id']))
    conn.commit()
    messages = conn.execute("""
        SELECT m.*, 
               (SELECT GROUP_CONCAT(reaction || ' ' || cnt, ', ') FROM (SELECT reaction, COUNT(*) as cnt FROM message_reactions WHERE message_id=m.id GROUP BY reaction)) as reactions
        FROM messages m
        WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?) 
        ORDER BY created_at
    """, (session['user_id'], user_id, user_id, session['user_id'])).fetchall()
    receiver = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    quoted_ids = [m['quoted_msg_id'] for m in messages if m['quoted_msg_id']]
    quoted_msgs = {}
    if quoted_ids:
        quoted_msgs_raw = conn.execute("SELECT * FROM messages WHERE id IN ({})".format(','.join('?'*len(quoted_ids))), quoted_ids).fetchall()
        quoted_msgs = {m['id']: m for m in quoted_msgs_raw}
    conn.close()
    return render_template('chat.html', messages=messages, receiver=receiver, quoted_msgs=quoted_msgs)

@app.route('/messages/delete/<int:msg_id>')
def delete_message(msg_id):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    conn.execute("DELETE FROM messages WHERE id=? AND sender_id=?", (msg_id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(request.referrer or '/messages')

@app.route('/conversation/<int:conv_id>', methods=['GET', 'POST'])
def conversation(conv_id):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    if request.method == 'POST':
        content = request.form['content']
        quoted_id = request.form.get('quoted_msg_id', type=int)
        conn.execute("INSERT INTO conversation_messages (conversation_id, user_id, content, quoted_msg_id) VALUES (?, ?, ?, ?)",
                     (conv_id, session['user_id'], content, quoted_id))
        conn.commit()
    conv = conn.execute("SELECT * FROM conversations WHERE id=?", (conv_id,)).fetchone()
    if not conv:
        conn.close()
        return "Беседа не найдена", 404
    participants = conn.execute("""
        SELECT u.* FROM conversation_participants cp
        JOIN users u ON cp.user_id = u.id
        WHERE cp.conversation_id=?
    """, (conv_id,)).fetchall()
    msgs = conn.execute("""
        SELECT cm.*, u.username, u.avatar_url,
               (SELECT GROUP_CONCAT(reaction || ' ' || cnt, ', ') FROM (SELECT reaction, COUNT(*) as cnt FROM message_reactions WHERE message_id=cm.id GROUP BY reaction)) as reactions
        FROM conversation_messages cm
        JOIN users u ON cm.user_id = u.id
        WHERE cm.conversation_id=?
        ORDER BY cm.created_at
    """, (conv_id,)).fetchall()
    quoted_ids = [m['quoted_msg_id'] for m in msgs if m['quoted_msg_id']]
    quoted_msgs = {}
    if quoted_ids:
        quoted_msgs_raw = conn.execute("SELECT * FROM conversation_messages WHERE id IN ({})".format(','.join('?'*len(quoted_ids))), quoted_ids).fetchall()
        quoted_msgs = {m['id']: m for m in quoted_msgs_raw}
    pinned = conn.execute("""
        SELECT pm.*, cm.content, u.username
        FROM pinned_messages pm
        JOIN conversation_messages cm ON pm.message_id = cm.id
        JOIN users u ON cm.user_id = u.id
        WHERE pm.conversation_id=?
    """, (conv_id,)).fetchall()
    conn.close()
    return render_template('conversation.html', conv=conv, participants=participants, msgs=msgs, quoted_msgs=quoted_msgs, pinned=pinned)

@app.route('/conversation/create', methods=['POST'])
def create_conversation():
    if 'user_id' not in session:
        return redirect('/login')
    name = request.form.get('name', '').strip()
    friends = request.form.getlist('participants')
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO conversations (name, admin_id) VALUES (?, ?)", (name, session['user_id']))
    conv_id = c.lastrowid
    c.execute("INSERT INTO conversation_participants (conversation_id, user_id) VALUES (?, ?)", (conv_id, session['user_id']))
    for fid in friends:
        if fid.isdigit():
            c.execute("INSERT INTO conversation_participants (conversation_id, user_id) VALUES (?, ?)", (conv_id, int(fid)))
    conn.commit()
    conn.close()
    return redirect(f'/conversation/{conv_id}')

@app.route('/conversation/<int:conv_id>/edit', methods=['POST'])
def edit_conversation(conv_id):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    conv = conn.execute("SELECT * FROM conversations WHERE id=? AND admin_id=?", (conv_id, session['user_id'])).fetchone()
    if not conv:
        conn.close()
        return "Только админ может редактировать", 403
    name = request.form.get('name', '').strip()
    conn.execute("UPDATE conversations SET name=? WHERE id=?", (name, conv_id))
    if 'avatar' in request.files and request.files['avatar'].filename != '':
        file = request.files['avatar']
        if file and allowed_file_img(file.filename):
            filename = secure_filename(f"conv_{conv_id}_{int(time.time())}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            conn.execute("UPDATE conversations SET avatar_url=? WHERE id=?", (f"/uploads/{filename}", conv_id))
    conn.commit()
    conn.close()
    return redirect(f'/conversation/{conv_id}')

@app.route('/conversation/<int:conv_id>/add_user', methods=['POST'])
def add_user_to_conversation(conv_id):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    conv = conn.execute("SELECT * FROM conversations WHERE id=? AND admin_id=?", (conv_id, session['user_id'])).fetchone()
    if not conv:
        conn.close()
        return "Только админ может добавлять", 403
    user_id = request.form.get('user_id', type=int)
    if user_id:
        try:
            conn.execute("INSERT INTO conversation_participants (conversation_id, user_id) VALUES (?, ?)", (conv_id, user_id))
            conn.commit()
        except:
            pass
    conn.close()
    return redirect(f'/conversation/{conv_id}')

@app.route('/conversation/<int:conv_id>/remove_user/<int:user_id>')
def remove_user_from_conversation(conv_id, user_id):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    conv = conn.execute("SELECT * FROM conversations WHERE id=? AND admin_id=?", (conv_id, session['user_id'])).fetchone()
    if not conv:
        conn.close()
        return "Только админ может удалять", 403
    conn.execute("DELETE FROM conversation_participants WHERE conversation_id=? AND user_id=?", (conv_id, user_id))
    conn.commit()
    conn.close()
    return redirect(f'/conversation/{conv_id}')

@app.route('/conversation/<int:conv_id>/leave')
def leave_conversation(conv_id):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    conn.execute("DELETE FROM conversation_participants WHERE conversation_id=? AND user_id=?", (conv_id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect('/messages')

@app.route('/conversation/<int:conv_id>/delete/<int:msg_id>')
def delete_conv_message(conv_id, msg_id):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    conn.execute("DELETE FROM conversation_messages WHERE id=? AND user_id=?", (msg_id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(f'/conversation/{conv_id}')

@app.route('/conversations')
def old_conversations_redirect():
    return redirect('/messages')

# ========== ПРОФИЛЬ ==========
@app.route('/profile/<int:user_id>')
def profile(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    posts = conn.execute("SELECT * FROM posts WHERE user_id=? ORDER BY created_at DESC", (user_id,)).fetchall()
    orders = conn.execute("SELECT orders.*, products.name FROM orders JOIN products ON orders.product_id = products.id WHERE orders.user_id=?", (user_id,)).fetchall()
    friends = conn.execute("""
        SELECT users.id, users.username, users.avatar_url FROM friendships 
        JOIN users ON (friendships.friend_id = users.id OR friendships.user_id = users.id) 
        WHERE (friendships.user_id=? OR friendships.friend_id=?) AND friendships.status='accepted' AND users.id != ?
    """, (user_id, user_id, user_id)).fetchall()
    is_friend = False
    if 'user_id' in session and session['user_id'] != user_id:
        existing = conn.execute("SELECT * FROM friendships WHERE (user_id=? AND friend_id=?) OR (user_id=? AND friend_id=?)",
                                (session['user_id'], user_id, user_id, session['user_id'])).fetchone()
        is_friend = existing is not None and existing['status'] == 'accepted'
    conn.close()
    return render_template('profile.html', user=user, posts=posts, orders=orders, friends=friends, is_friend=is_friend)

# ========== ПОСТЫ ==========
@app.route('/create_post', methods=['GET', 'POST'])
def create_post():
    if 'user_id' not in session:
        return redirect('/login')
    if request.method == 'POST':
        description = request.form['description']
        image_url = None
        if 'photo' in request.files and request.files['photo'].filename != '':
            file = request.files['photo']
            if file and allowed_file_img(file.filename):
                filename = secure_filename(f"{session['user_id']}_{int(time.time())}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_url = f"/uploads/{filename}"
        if not image_url:
            image_url = request.form.get('image_url', '')
        conn = get_db()
        conn.execute("INSERT INTO posts (user_id, image_url, description) VALUES (?, ?, ?)",
                    (session['user_id'], image_url, description))
        conn.commit()
        conn.close()
        return redirect('/')
    return render_template('create_post.html')

@app.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    post = conn.execute("SELECT * FROM posts WHERE id=? AND user_id=?", (post_id, session['user_id'])).fetchone()
    if not post:
        conn.close()
        return "Не ваш пост", 403
    if request.method == 'POST':
        description = request.form['description']
        conn.execute("UPDATE posts SET description=? WHERE id=?", (description, post_id))
        conn.commit()
        conn.close()
        return redirect(f'/post/{post_id}')
    conn.close()
    return render_template('edit_post.html', post=post)

@app.route('/delete_post/<int:post_id>')
def delete_post(post_id):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    conn.execute("DELETE FROM posts WHERE id=? AND user_id=?", (post_id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect('/profile/' + str(session['user_id']))

@app.route('/like/<int:post_id>', methods=['POST'])
def like_post(post_id):
    if 'user_id' not in session:
        return "Войдите", 401
    conn = get_db()
    post = conn.execute("SELECT user_id FROM posts WHERE id=?", (post_id,)).fetchone()
    try:
        conn.execute("INSERT INTO likes (user_id, post_id) VALUES (?, ?)", (session['user_id'], post_id))
        conn.commit()
    except:
        conn.execute("DELETE FROM likes WHERE user_id=? AND post_id=?", (session['user_id'], post_id))
        conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM likes WHERE post_id=?", (post_id,)).fetchone()[0]
    liked = conn.execute("SELECT * FROM likes WHERE user_id=? AND post_id=?", (session['user_id'], post_id)).fetchone() is not None
    if post and post['user_id'] != session['user_id'] and liked:
        add_notification(post['user_id'], f"@{session['username']} лайкнул ваш лук", f"/post/{post_id}")
    conn.close()
    heart = '❤️' if liked else '🤍'
    return f'<span class="cursor-pointer" hx-post="/like/{post_id}" hx-target="this" hx-swap="outerHTML">{heart} {count}</span>'

@app.route('/post/<int:post_id>')
def view_post(post_id):
    conn = get_db()
    post = conn.execute("""
        SELECT posts.*, users.username,
               (SELECT COUNT(*) FROM likes WHERE post_id=posts.id) as likes_count
        FROM posts JOIN users ON posts.user_id = users.id 
        WHERE posts.id=?
    """, (post_id,)).fetchone()
    if not post:
        conn.close()
        return "Пост не найден", 404
    comments = conn.execute("""
        SELECT comments.*, users.username, users.avatar_url
        FROM comments JOIN users ON comments.user_id = users.id 
        WHERE post_id=? ORDER BY comments.created_at ASC
    """, (post_id,)).fetchall()
    conn.close()
    return render_template('post.html', post=post, comments=comments, likes_count=post['likes_count'])

@app.route('/add_comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    if 'user_id' not in session:
        return redirect('/login')
    content = request.form.get('content', '').strip()
    if content:
        conn = get_db()
        conn.execute("INSERT INTO comments (user_id, post_id, content) VALUES (?, ?, ?)", (session['user_id'], post_id, content))
        conn.commit()
        post = conn.execute("SELECT user_id FROM posts WHERE id=?", (post_id,)).fetchone()
        if post and post['user_id'] != session['user_id']:
            add_notification(post['user_id'], f"@{session['username']} прокомментировал ваш лук", f"/post/{post_id}")
        conn.close()
    return redirect(f'/post/{post_id}')

@app.route('/load_more_posts')
def load_more_posts():
    offset = request.args.get('offset', 0, type=int)
    conn = get_db()
    posts = conn.execute("""
        SELECT posts.*, users.username,
               (SELECT COUNT(*) FROM likes WHERE post_id=posts.id) as likes_count,
               (SELECT COUNT(*) FROM comments WHERE post_id=posts.id) as comments_count
        FROM posts JOIN users ON posts.user_id = users.id 
        ORDER BY posts.created_at DESC LIMIT 20 OFFSET ?
    """, (offset,)).fetchall()
    conn.close()
    if not posts:
        return ""
    return render_template('_posts.html', posts=posts, offset=offset)

# ========== ОТЗЫВЫ ==========
@app.route('/add_review/<int:product_id>', methods=['POST'])
def add_review(product_id):
    if 'user_id' not in session:
        return redirect('/login')
    rating = request.form.get('rating', type=int)
    content = request.form.get('content', '').strip()
    if rating and 1 <= rating <= 5:
        conn = get_db()
        conn.execute("INSERT INTO reviews (user_id, product_id, rating, content) VALUES (?, ?, ?, ?)",
                    (session['user_id'], product_id, rating, content))
        conn.commit()
        conn.close()
    return redirect(f'/product/{product_id}')

# ========== НАСТРОЙКИ ==========
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    if request.method == 'POST':
        if 'avatar' in request.files and request.files['avatar'].filename != '':
            file = request.files['avatar']
            if file and allowed_file_img(file.filename):
                filename = secure_filename(f"avatar_{session['user_id']}_{int(time.time())}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                avatar_url = f"/uploads/{filename}"
                conn.execute("UPDATE users SET avatar_url=? WHERE id=?", (avatar_url, session['user_id']))
                conn.commit()
        return redirect('/settings')
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    conn.close()
    return render_template('settings.html', user=user)

# ========== УВЕДОМЛЕНИЯ ==========
@app.route('/notifications')
def notifications():
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    notifs = conn.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
                          (session['user_id'],)).fetchall()
    conn.close()
    return render_template('notifications.html', notifications=notifs)

@app.route('/notifications/count')
def notification_count():
    if 'user_id' not in session:
        return jsonify({'count': 0})
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0",
                         (session['user_id'],)).fetchone()[0]
    conn.close()
    return jsonify({'count': count})

@app.route('/notifications/read/<int:notif_id>')
def read_notification(notif_id):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    conn.execute("UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?", (notif_id, session['user_id']))
    conn.commit()
    notif = conn.execute("SELECT * FROM notifications WHERE id=?", (notif_id,)).fetchone()
    conn.close()
    if notif and notif['link']:
        return redirect(notif['link'])
    return redirect('/notifications')

# ========== АДМИНКА ==========
@app.route('/admin')
def admin():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    conn = get_db()
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    total_orders = conn.execute("SELECT COUNT(*) FROM orders WHERE status='completed'").fetchone()[0]
    total_revenue = conn.execute("SELECT SUM(final_price) FROM orders WHERE status='completed'").fetchone()[0] or 0
    active_gb = conn.execute("SELECT COUNT(*) FROM group_purchases WHERE status='active'").fetchone()[0]
    recent_orders = conn.execute("""
        SELECT orders.*, users.username, products.name 
        FROM orders JOIN users ON orders.user_id = users.id 
        JOIN products ON orders.product_id = products.id 
        ORDER BY orders.created_at DESC LIMIT 10
    """).fetchall()
    conn.close()
    return render_template('admin.html', total_users=total_users, total_products=total_products,
                         total_orders=total_orders, total_revenue=total_revenue,
                         active_gb=active_gb, recent_orders=recent_orders)

@app.route('/admin/products')
def admin_products():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    conn = get_db()
    products = conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('admin_products.html', products=products)

@app.route('/admin/products/add', methods=['GET', 'POST'])
def admin_add_product():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    if request.method == 'POST':
        name = request.form['name']
        ptype = request.form['type']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        description = request.form['description']
        sizes = request.form.get('sizes', '[]')
        image_url = ''
        video_url = ''
        if 'photo' in request.files and request.files['photo'].filename != '':
            file = request.files['photo']
            if file and allowed_file_img(file.filename):
                filename = secure_filename(f"product_{int(time.time())}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_url = f"/uploads/{filename}"
        if 'video' in request.files and request.files['video'].filename != '':
            file = request.files['video']
            if file and allowed_file_vid(file.filename):
                filename = secure_filename(f"product_vid_{int(time.time())}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                video_url = f"/uploads/{filename}"
        conn = get_db()
        conn.execute("INSERT INTO products (name, type, price, stock, description, image_url, video_url, sizes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     (name, ptype, price, stock, description, image_url, video_url, sizes))
        conn.commit()
        conn.close()
        return redirect('/admin/products')
    return render_template('admin_product_form.html', product=None)

@app.route('/admin/products/edit/<int:id>', methods=['GET', 'POST'])
def admin_edit_product(id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id=?", (id,)).fetchone()
    if not product:
        conn.close()
        return "Товар не найден"
    if request.method == 'POST':
        name = request.form['name']
        ptype = request.form['type']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        description = request.form['description']
        sizes = request.form.get('sizes', product['sizes'])
        image_url = product['image_url']
        video_url = product['video_url']
        if 'photo' in request.files and request.files['photo'].filename != '':
            file = request.files['photo']
            if file and allowed_file_img(file.filename):
                filename = secure_filename(f"product_{int(time.time())}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_url = f"/uploads/{filename}"
        if 'video' in request.files and request.files['video'].filename != '':
            file = request.files['video']
            if file and allowed_file_vid(file.filename):
                filename = secure_filename(f"product_vid_{int(time.time())}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                video_url = f"/uploads/{filename}"
        conn.execute("UPDATE products SET name=?, type=?, price=?, stock=?, description=?, image_url=?, video_url=?, sizes=? WHERE id=?",
                     (name, ptype, price, stock, description, image_url, video_url, sizes, id))
        conn.commit()
        conn.close()
        return redirect('/admin/products')
    conn.close()
    return render_template('admin_product_form.html', product=product)

@app.route('/admin/products/delete/<int:id>')
def admin_delete_product(id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect('/admin/products')

@app.route('/admin/orders')
def admin_orders():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    conn = get_db()
    orders = conn.execute("""
        SELECT orders.*, users.username, products.name 
        FROM orders 
        JOIN users ON orders.user_id = users.id 
        JOIN products ON orders.product_id = products.id 
        ORDER BY orders.created_at DESC
    """).fetchall()
    conn.close()
    return render_template('admin_orders.html', orders=orders)

@app.route('/admin/orders/status/<int:order_id>', methods=['POST'])
def change_order_status(order_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    new_status = request.form.get('status')
    if new_status not in ('processing', 'shipped', 'delivered', 'completed'):
        return "Недопустимый статус", 400
    conn = get_db()
    conn.execute("UPDATE orders SET status=? WHERE id=?", (new_status, order_id))
    conn.commit()
    conn.close()
    return redirect('/admin/orders')

@app.route('/admin/stats')
def admin_stats():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    conn = get_db()
    sales_data = conn.execute("""
        SELECT DATE(created_at) as day, SUM(final_price) as total
        FROM orders
        WHERE status IN ('completed', 'delivered') AND created_at >= DATE('now', '-7 days')
        GROUP BY day
        ORDER BY day
    """).fetchall()
    top_products = conn.execute("""
        SELECT products.name, SUM(orders.final_price) as total
        FROM orders
        JOIN products ON orders.product_id = products.id
        WHERE orders.status IN ('completed', 'delivered')
        GROUP BY products.id
        ORDER BY total DESC
        LIMIT 5
    """).fetchall()
    conn.close()
    return render_template('admin_stats.html', sales_data=sales_data, top_products=top_products)

@app.route('/admin/promos')
def admin_promos():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    conn = get_db()
    promos = conn.execute("SELECT * FROM promos ORDER BY created_at DESC").fetchall()
    conn.close()
    return render_template('admin_promos.html', promos=promos)

@app.route('/admin/promos/add', methods=['POST'])
def admin_add_promo():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    code = request.form.get('code', '').strip().upper()
    discount_type = request.form.get('type')
    value = float(request.form.get('value', 0))
    max_uses = int(request.form.get('max_uses', 0))
    if not code or value <= 0:
        return "Неверные данные", 400
    conn = get_db()
    try:
        conn.execute("INSERT INTO promos (code, discount_type, value, max_uses) VALUES (?, ?, ?, ?)",
                     (code, discount_type, value, max_uses))
        conn.commit()
    except:
        conn.close()
        return "Такой код уже существует", 400
    conn.close()
    return redirect('/admin/promos')

@app.route('/admin/promos/delete/<int:promo_id>')
def admin_delete_promo(promo_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    conn = get_db()
    conn.execute("DELETE FROM promos WHERE id=?", (promo_id,))
    conn.commit()
    conn.close()
    return redirect('/admin/promos')

@app.route('/admin/users')
def admin_users():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    conn = get_db()
    users = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    conn.close()
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/role/<int:user_id>', methods=['POST'])
def change_user_role(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    new_role = request.form.get('role')
    if new_role not in ('user', 'admin'):
        return "Недопустимая роль", 400
    conn = get_db()
    conn.execute("UPDATE users SET role=? WHERE id=?", (new_role, user_id))
    conn.commit()
    conn.close()
    return redirect('/admin/users')

@app.route('/admin/users/bonus/<int:user_id>', methods=['POST'])
def give_bonus(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    amount = request.form.get('amount', type=int, default=0)
    if amount <= 0:
        return "Сумма должна быть положительной", 400
    conn = get_db()
    conn.execute("UPDATE users SET points = points + ? WHERE id = ?", (amount, user_id))
    conn.execute("INSERT INTO bonus_transactions (user_id, amount, description) VALUES (?, ?, 'Начислено администратором')",
                 (user_id, amount))
    conn.commit()
    conn.close()
    return redirect('/admin/users')

# ========== ЗАКЛАДКИ ==========
@app.route('/bookmark/<int:post_id>', methods=['POST'])
def bookmark_post(post_id):
    if 'user_id' not in session:
        return 'login', 401
    conn = get_db()
    try:
        conn.execute("INSERT INTO post_bookmarks (user_id, post_id) VALUES (?, ?)", (session['user_id'], post_id))
        conn.commit()
    except:
        conn.execute("DELETE FROM post_bookmarks WHERE user_id=? AND post_id=?", (session['user_id'], post_id))
        conn.commit()
    is_bookmarked = conn.execute("SELECT * FROM post_bookmarks WHERE user_id=? AND post_id=?", (session['user_id'], post_id)).fetchone() is not None
    count = conn.execute("SELECT COUNT(*) FROM post_bookmarks WHERE post_id=?", (post_id,)).fetchone()[0]
    conn.close()
    icon = '🔖' if is_bookmarked else '📑'
    return f'<span class="cursor-pointer" hx-post="/bookmark/{post_id}" hx-target="this" hx-swap="outerHTML">{icon} {count}</span>'

@app.route('/bookmarks')
def bookmarks():
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    posts = conn.execute("""
        SELECT posts.*, users.username, 
               (SELECT COUNT(*) FROM likes WHERE post_id=posts.id) as likes_count,
               (SELECT COUNT(*) FROM comments WHERE post_id=posts.id) as comments_count
        FROM post_bookmarks
        JOIN posts ON post_bookmarks.post_id = posts.id
        JOIN users ON posts.user_id = users.id
        WHERE post_bookmarks.user_id=?
        ORDER BY post_bookmarks.created_at DESC
    """, (session['user_id'],)).fetchall()
    conn.close()
    return render_template('bookmarks.html', posts=posts)

# ========== ИНДИКАТОР ПЕЧАТИ ==========
@app.route('/typing/<int:peer_id>', methods=['POST'])
def set_typing(peer_id):
    if 'user_id' not in session:
        return '', 401
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO typing_status (user_id, peer_id, timestamp) VALUES (?, ?, CURRENT_TIMESTAMP)",
                 (session['user_id'], peer_id))
    conn.commit()
    conn.close()
    return '', 204

@app.route('/typing/<int:peer_id>', methods=['GET'])
def get_typing(peer_id):
    if 'user_id' not in session:
        return jsonify({'typing': False})
    conn = get_db()
    row = conn.execute("SELECT timestamp FROM typing_status WHERE user_id=? AND peer_id=?", (peer_id, session['user_id'])).fetchone()
    conn.close()
    if row:
        try:
            ts = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
            delta = (datetime.now() - ts).seconds
            return jsonify({'typing': delta < 5})
        except:
            pass
    return jsonify({'typing': False})

# ========== ЖАЛОБЫ ==========
@app.route('/report/<int:post_id>', methods=['GET', 'POST'])
def report_post(post_id):
    if 'user_id' not in session:
        return redirect('/login')
    if request.method == 'POST':
        reason = request.form.get('reason', '').strip()
        conn = get_db()
        conn.execute("INSERT INTO reports (reporter_id, post_id, reason) VALUES (?, ?, ?)",
                     (session['user_id'], post_id, reason))
        conn.commit()
        conn.close()
        return redirect('/')
    return render_template('report.html', post_id=post_id)

@app.route('/admin/reports')
def admin_reports():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    conn = get_db()
    reports = conn.execute("""
        SELECT reports.*, users.username as reporter_name, posts.description as post_desc
        FROM reports JOIN users ON reports.reporter_id = users.id
        JOIN posts ON reports.post_id = posts.id
        ORDER BY reports.created_at DESC
    """).fetchall()
    conn.close()
    return render_template('admin_reports.html', reports=reports)

@app.route('/admin/reports/<int:report_id>/action', methods=['POST'])
def handle_report(report_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    action = request.form.get('action')
    conn = get_db()
    report = conn.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
    if report:
        if action == 'delete':
            conn.execute("DELETE FROM posts WHERE id=?", (report['post_id'],))
            conn.execute("UPDATE reports SET status='reviewed' WHERE id=?", (report_id,))
        elif action == 'dismiss':
            conn.execute("UPDATE reports SET status='dismissed' WHERE id=?", (report_id,))
    conn.commit()
    conn.close()
    return redirect('/admin/reports')

# ========== БЛОКИРОВКИ ==========
@app.route('/block/<int:user_id>')
def block_user(user_id):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO blocks (blocker_id, blocked_id) VALUES (?, ?)", (session['user_id'], user_id))
    conn.commit()
    conn.close()
    return redirect(request.referrer or '/')

@app.route('/unblock/<int:user_id>')
def unblock_user(user_id):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    conn.execute("DELETE FROM blocks WHERE blocker_id=? AND blocked_id=?", (session['user_id'], user_id))
    conn.commit()
    conn.close()
    return redirect(request.referrer or '/')

@app.route('/blocks')
def blocks():
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    blocked = conn.execute("""
        SELECT users.id, users.username, users.avatar_url FROM blocks
        JOIN users ON blocks.blocked_id = users.id
        WHERE blocks.blocker_id=?
    """, (session['user_id'],)).fetchall()
    conn.close()
    return render_template('blocks.html', blocked=blocked)

# ========== АКЦИИ ==========
@app.route('/admin/promotions')
def admin_promotions():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    conn = get_db()
    promotions = conn.execute("SELECT * FROM promotions ORDER BY created_at DESC").fetchall()
    conn.close()
    return render_template('admin_promotions.html', promotions=promotions)

@app.route('/admin/promotions/add', methods=['GET', 'POST'])
def admin_add_promotion():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        discount = float(request.form['discount'])
        product_id = request.form.get('product_id', type=int) or None
        start = request.form['start_date']
        end = request.form['end_date']
        conn = get_db()
        conn.execute("INSERT INTO promotions (title, description, discount_percent, product_id, start_date, end_date) VALUES (?, ?, ?, ?, ?, ?)",
                     (title, description, discount, product_id, start, end))
        conn.commit()
        conn.close()
        return redirect('/admin/promotions')
    conn = get_db()
    products = conn.execute("SELECT id, name FROM products").fetchall()
    conn.close()
    return render_template('admin_promotion_form.html', products=products, promo=None)

@app.route('/admin/promotions/edit/<int:id>', methods=['GET', 'POST'])
def admin_edit_promotion(id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    conn = get_db()
    promo = conn.execute("SELECT * FROM promotions WHERE id=?", (id,)).fetchone()
    if not promo:
        conn.close()
        return "Акция не найдена"
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        discount = float(request.form['discount'])
        product_id = request.form.get('product_id', type=int) or None
        start = request.form['start_date']
        end = request.form['end_date']
        active = request.form.get('active', '1')
        conn.execute("UPDATE promotions SET title=?, description=?, discount_percent=?, product_id=?, start_date=?, end_date=?, active=? WHERE id=?",
                     (title, description, discount, product_id, start, end, active, id))
        conn.commit()
        conn.close()
        return redirect('/admin/promotions')
    products = conn.execute("SELECT id, name FROM products").fetchall()
    conn.close()
    return render_template('admin_promotion_form.html', products=products, promo=promo)

@app.route('/admin/promotions/delete/<int:id>')
def admin_delete_promotion(id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect('/login')
    conn = get_db()
    conn.execute("DELETE FROM promotions WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect('/admin/promotions')

# ========== РЕАКЦИИ ==========
@app.route('/message/<int:msg_id>/react', methods=['POST'])
def react_to_message(msg_id):
    if 'user_id' not in session:
        return 'login', 401
    reaction = request.form.get('reaction', '👍')
    conn = get_db()
    try:
        conn.execute("INSERT INTO message_reactions (message_id, user_id, reaction) VALUES (?, ?, ?)",
                     (msg_id, session['user_id'], reaction))
        conn.commit()
    except:
        conn.execute("DELETE FROM message_reactions WHERE message_id=? AND user_id=?", (msg_id, session['user_id']))
        conn.commit()
    reactions = conn.execute("SELECT reaction, COUNT(*) as cnt FROM message_reactions WHERE message_id=? GROUP BY reaction", (msg_id,)).fetchall()
    html = ''
    for r in reactions:
        html += f'<span class="mr-2 cursor-pointer" onclick="reactToMsg({msg_id}, \'{r["reaction"]}\')">{r["reaction"]} {r["cnt"]}</span>'
    conn.close()
    return html

# ========== ПОИСК ПО СООБЩЕНИЯМ ==========
@app.route('/messages/search')
def search_messages():
    if 'user_id' not in session:
        return redirect('/login')
    query = request.args.get('q', '').strip()
    if not query:
        return redirect('/messages')
    conn = get_db()
    results = conn.execute("""
        SELECT messages.*, sender.username as sender_name, receiver.username as receiver_name
        FROM messages
        JOIN users AS sender ON messages.sender_id = sender.id
        JOIN users AS receiver ON messages.receiver_id = receiver.id
        WHERE (sender_id=? OR receiver_id=?) AND content LIKE ?
        ORDER BY messages.created_at DESC
        LIMIT 50
    """, (session['user_id'], session['user_id'], f'%{query}%')).fetchall()
    conn.close()
    return render_template('search_messages.html', results=results, query=query)

# ========== ЗАКРЕПЛЕНИЕ СООБЩЕНИЙ ==========
@app.route('/conversation/<int:conv_id>/pin/<int:msg_id>')
def pin_message(conv_id, msg_id):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    is_admin = conn.execute("SELECT * FROM conversations WHERE id=? AND admin_id=?", (conv_id, session['user_id'])).fetchone()
    if is_admin:
        conn.execute("INSERT OR IGNORE INTO pinned_messages (conversation_id, message_id, pinned_by) VALUES (?, ?, ?)",
                     (conv_id, msg_id, session['user_id']))
        conn.commit()
    conn.close()
    return redirect(f'/conversation/{conv_id}')

@app.route('/conversation/<int:conv_id>/unpin/<int:msg_id>')
def unpin_message(conv_id, msg_id):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    conn.execute("DELETE FROM pinned_messages WHERE conversation_id=? AND message_id=?", (conv_id, msg_id))
    conn.commit()
    conn.close()
    return redirect(f'/conversation/{conv_id}')

# ========== ИСТОРИИ ==========
@app.route('/stories/create', methods=['GET', 'POST'])
def create_story():
    if 'user_id' not in session:
        return redirect('/login')
    if request.method == 'POST':
        image_url = None
        video_url = None
        if 'photo' in request.files and request.files['photo'].filename != '':
            file = request.files['photo']
            if file and allowed_file_img(file.filename):
                filename = secure_filename(f"story_{session['user_id']}_{int(time.time())}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_url = f"/uploads/{filename}"
        if 'video' in request.files and request.files['video'].filename != '':
            file = request.files['video']
            if file and allowed_file_vid(file.filename):
                filename = secure_filename(f"story_vid_{session['user_id']}_{int(time.time())}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                video_url = f"/uploads/{filename}"
        if image_url or video_url:
            conn = get_db()
            conn.execute("INSERT INTO stories (user_id, image_url, video_url) VALUES (?, ?, ?)",
                         (session['user_id'], image_url, video_url))
            conn.commit()
            conn.close()
        return redirect('/')
    return render_template('create_story.html')

@app.route('/stories')
def stories():
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    users_with_stories = conn.execute("""
        SELECT DISTINCT stories.user_id, users.username, users.avatar_url,
               (SELECT COUNT(*) FROM stories WHERE user_id=users.id AND expires_at > datetime('now')) as story_count,
               (SELECT id FROM stories WHERE user_id=users.id AND expires_at > datetime('now') ORDER BY created_at DESC LIMIT 1) as latest_story_id
        FROM stories
        JOIN users ON stories.user_id = users.id
        WHERE stories.expires_at > datetime('now')
        ORDER BY stories.created_at DESC
    """).fetchall()
    conn.close()
    return render_template('stories.html', users_with_stories=users_with_stories)

@app.route('/story/<int:user_id>')
def view_user_stories(user_id):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    stories = conn.execute("""
        SELECT * FROM stories
        WHERE user_id=? AND expires_at > datetime('now')
        ORDER BY created_at ASC
    """, (user_id,)).fetchall()
    if not stories:
        conn.close()
        return "Истории не найдены", 404
    for story in stories:
        try:
            conn.execute("INSERT OR IGNORE INTO story_views (story_id, user_id) VALUES (?, ?)",
                         (story['id'], session['user_id']))
            conn.commit()
        except:
            pass
    conn.close()
    return render_template('story_viewer.html', user=user, stories=stories)

# ========== ПРЯМЫЕ ЭФИРЫ ==========
@app.route('/streams')
def streams():
    conn = get_db()
    streams = conn.execute("""
        SELECT streams.*, users.username, users.avatar_url
        FROM streams JOIN users ON streams.user_id = users.id
        ORDER BY streams.created_at DESC
    """).fetchall()
    conn.close()
    return render_template('streams.html', streams=streams)

@app.route('/stream/create', methods=['GET', 'POST'])
def create_stream():
    if 'user_id' not in session:
        return redirect('/login')
    if request.method == 'POST':
        title = request.form['title']
        video_url = ''
        if 'video' in request.files and request.files['video'].filename != '':
            file = request.files['video']
            if file and allowed_file_vid(file.filename):
                filename = secure_filename(f"stream_{session['user_id']}_{int(time.time())}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                video_url = f"/uploads/{filename}"
        conn = get_db()
        conn.execute("INSERT INTO streams (user_id, title, video_url, is_live) VALUES (?, ?, ?, 1)",
                     (session['user_id'], title, video_url))
        conn.commit()
        conn.close()
        return redirect('/streams')
    return render_template('create_stream.html')

@app.route('/stream/<int:stream_id>')
def view_stream(stream_id):
    conn = get_db()
    stream = conn.execute("""
        SELECT streams.*, users.username, users.avatar_url
        FROM streams JOIN users ON streams.user_id = users.id
        WHERE streams.id=?
    """, (stream_id,)).fetchone()
    if not stream:
        conn.close()
        return "Эфир не найден", 404
    conn.close()
    return render_template('stream.html', stream=stream)

# ========== ВИШЛИСТ ==========
@app.route('/wishlist')
def wishlist():
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    items = conn.execute("""
        SELECT wishlist.*, products.name, products.price, products.image_url, products.video_url, products.type
        FROM wishlist JOIN products ON wishlist.product_id = products.id
        WHERE wishlist.user_id=?
        ORDER BY wishlist.created_at DESC
    """, (session['user_id'],)).fetchall()
    conn.close()
    return render_template('wishlist.html', items=items)

@app.route('/wishlist/add/<int:product_id>')
def add_to_wishlist(product_id):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    try:
        conn.execute("INSERT INTO wishlist (user_id, product_id) VALUES (?, ?)", (session['user_id'], product_id))
        conn.commit()
    except:
        pass
    conn.close()
    return redirect(request.referrer or '/shop')

@app.route('/wishlist/remove/<int:product_id>')
def remove_from_wishlist(product_id):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    conn.execute("DELETE FROM wishlist WHERE user_id=? AND product_id=?", (session['user_id'], product_id))
    conn.commit()
    conn.close()
    return redirect(request.referrer or '/wishlist')

# ========== ДАШБОРД ==========
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    user_id = session['user_id']
    total_likes = conn.execute("""
        SELECT COUNT(*) FROM likes WHERE post_id IN (SELECT id FROM posts WHERE user_id=?)
    """, (user_id,)).fetchone()[0]
    total_posts = conn.execute("SELECT COUNT(*) FROM posts WHERE user_id=?", (user_id,)).fetchone()[0]
    top_posts = conn.execute("""
        SELECT posts.id, posts.image_url, posts.description,
               (SELECT COUNT(*) FROM likes WHERE post_id=posts.id) as likes_count
        FROM posts
        WHERE posts.user_id=?
        ORDER BY likes_count DESC
        LIMIT 3
    """, (user_id,)).fetchall()
    activity_data = conn.execute("""
        SELECT DATE(created_at) as day, COUNT(*) as count
        FROM posts
        WHERE user_id=? AND created_at >= DATE('now', '-7 days')
        GROUP BY day
        ORDER BY day
    """, (user_id,)).fetchall()
    fav_category = conn.execute("""
        SELECT products.type, COUNT(*) as cnt
        FROM orders
        JOIN products ON orders.product_id = products.id
        WHERE orders.user_id=? AND orders.status IN ('completed', 'delivered')
        GROUP BY products.type
        ORDER BY cnt DESC
        LIMIT 1
    """, (user_id,)).fetchone()
    conn.close()
    days = []
    counts = []
    for row in activity_data:
        days.append(row['day'][-5:])
        counts.append(row['count'])
    return render_template('dashboard.html',
                         total_likes=total_likes,
                         total_posts=total_posts,
                         top_posts=top_posts,
                         activity_days=json.dumps(days),
                         activity_counts=json.dumps(counts),
                         fav_category=fav_category['type'] if fav_category else 'Нет данных')

# ========== РЕФЕРАЛЫ ==========
@app.route('/referrals')
def referrals():
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    invited = conn.execute("""
        SELECT u.id, u.username, u.created_at, r.bonus_paid
        FROM referrals r
        JOIN users u ON r.referred_id = u.id
        WHERE r.referrer_id=?
        ORDER BY r.created_at DESC
    """, (session['user_id'],)).fetchall()
    total_bonus = conn.execute("""
        SELECT SUM(amount) FROM bonus_transactions 
        WHERE user_id=? AND description LIKE '%Реферальный бонус%'
    """, (session['user_id'],)).fetchone()[0] or 0
    conn.close()
    return render_template('referrals.html', user=user, invited=invited, total_bonus=total_bonus)

# ========== ИИ-КОНСУЛЬТАНТ ==========
@app.route('/api/chat/ai', methods=['POST'])
def ai_chat():
    if 'user_id' not in session:
        return jsonify({'error': 'Войдите'}), 401
    user_message = request.form.get('message', '').strip().lower()
    if not user_message:
        return jsonify({'error': 'Пустое сообщение'}), 400
    if 'кроссовк' in user_message or 'nike' in user_message:
        answer = "У нас есть Nike Air Force 1 (оригинал за 12 990 ₽ и реплика AAA за 4 990 ₽). Могу помочь с выбором!"
    elif 'худи' in user_message or 'balenciaga' in user_message:
        answer = "Худи Balenciaga: оригинал 89 990 ₽, реплика 1:1 за 8 990 ₽. Качество 🔥"
    elif 'скидк' in user_message or 'группов' in user_message:
        answer = "Групповая покупка даёт скидку до 10% (до 6 человек). Чем больше участников, тем выгоднее!"
    elif 'доставк' in user_message:
        answer = "Доставка по всей России. После оформления заказа мы отправим его в течение 24 часов."
    elif 'привет' in user_message or 'здравствуй' in user_message:
        answer = "Привет! Я стилист DROP SHOP. Спрашивай о товарах, скидках, доставке."
    else:
        answer = "Пока я учусь отвечать на такие вопросы. Попробуй спросить о кроссовках, худи или скидках!"
    return jsonify({'answer': answer})

# ========== PWA PUSH-ПОДПИСКА ==========
@app.route('/push/subscribe', methods=['POST'])
def push_subscribe():
    if 'user_id' not in session:
        return jsonify({'error': 'Войдите'}), 401
    data = request.get_json()
    subscription = data.get('subscription')
    if not subscription:
        return jsonify({'error': 'Нет подписки'}), 400
    conn = get_db()
    conn.execute("""INSERT OR REPLACE INTO push_subscriptions 
                    (user_id, endpoint, p256dh, auth) VALUES (?, ?, ?, ?)""",
                 (session['user_id'], subscription['endpoint'],
                  subscription['keys']['p256dh'], subscription['keys']['auth']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)