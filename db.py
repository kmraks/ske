import sqlite3

def get_connection(db_path="recharge.db"):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    c = conn.cursor()

    # --- Create tables if not exist ---
    c.execute('''CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT UNIQUE,
        group_name TEXT,
        operator TEXT,
        plan_amount REAL,
        recharge_day INTEGER,
        premium BOOLEAN DEFAULT 0,
        notes TEXT,
        lucky_draw_wins INTEGER DEFAULT 0,
        referred BOOLEAN DEFAULT 0,
        referred_by_name TEXT,
        referred_by_phone TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS recharge_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        data TEXT,
        voice TEXT,
        sms TEXT,
        validity INTEGER,
        operator TEXT,
        price REAL,
        description TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        category TEXT,
        subcategory TEXT,
        price REAL,
        stock INTEGER,
        image_paths TEXT,
        description TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        amount REAL,
        discount REAL,
        commission REAL,
        status TEXT,
        created_at TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS product_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        amount REAL,
        status TEXT,
        created_at TEXT
    )''')

    conn.commit()
    return conn, c