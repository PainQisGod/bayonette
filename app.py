import sqlite3
from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "change-this-to-anything"

STATUSES = ["pending", "shipped", "delivered"]

PRODUCTS = [
    ("Ridge Wool Throw", "Hearth & Co", 78, 12, "Heavy merino blanket woven in small batches."),
    ("Halcyon Desk Lamp", "Lumen", 64, 38, "Dimmable brass lamp with a warm, low glow."),
    ("Ember Mug Set", "Kiln", 42, 20, "Four stoneware mugs, speckled glaze."),
    ("Fathom Backpack", "Atlas", 112, 200, "Waxed canvas, 24L, roll-top."),
    ("Drift Speaker", "Pulse", 95, 260, "Portable wireless speaker with 20h battery."),
    ("Field Jacket", "Atlas", 148, 90, "Water-resistant cotton, four pockets."),
    ("Pour-Over Kit", "Kiln", 56, 30, "Dripper, server and filters in one box."),
    ("Nomad Wallet", "Hearth & Co", 48, 25, "Vegetable-tanned leather, slim fold."),
    ("Pulse Keyboard", "Pulse", 129, 300, "75% mechanical board, hot-swap switches."),
    ("Linen Overshirt", "Lumen", 72, 150, "Breathable garment-dyed linen."),
    ("Orbit Bottle", "Atlas", 29, 175, "Insulated steel, keeps cold for 24h."),
    ("Cobalt Sneaker", "Lumen", 99, 225, "Low-top court shoe in recycled canvas."),
]


def db():
    conn = sqlite3.connect("shop.db")
    conn.row_factory = sqlite3.Row
    return conn


def setup():
    conn = db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT UNIQUE, password TEXT, is_admin INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT, brand TEXT, price INTEGER, hue INTEGER, description TEXT, stock INTEGER DEFAULT 10);
        CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, user_id INTEGER, total INTEGER, created TEXT DEFAULT CURRENT_TIMESTAMP, status TEXT DEFAULT 'pending');
        CREATE TABLE IF NOT EXISTS order_items (order_id INTEGER, product_id INTEGER, quantity INTEGER);
    """)
    try:
        conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # column already exists
    try:
        conn.execute("ALTER TABLE products ADD COLUMN stock INTEGER DEFAULT 10")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE orders ADD COLUMN status TEXT DEFAULT 'pending'")
    except sqlite3.OperationalError:
        pass
    if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        conn.executemany("INSERT INTO products (name, brand, price, hue, description) VALUES (?,?,?,?,?)", PRODUCTS)
    conn.commit()
    conn.close()


@app.context_processor
def cart_count():
    return {"cart_count": sum(session.get("cart", {}).values())}


@app.route("/")
def shop():
    q = request.args.get("q", "")
    conn = db()
    products = conn.execute("SELECT * FROM products WHERE name LIKE ? OR brand LIKE ?", (f"%{q}%", f"%{q}%")).fetchall()
    conn.close()
    return render_template("shop.html", products=products, q=q)


@app.route("/product/<int:id>")
def product(id):
    conn = db()
    p = conn.execute("SELECT * FROM products WHERE id = ?", (id,)).fetchone()
    if p is None:
        conn.close()
        return redirect("/")
    more = conn.execute("SELECT * FROM products WHERE brand = ? AND id != ? LIMIT 4", (p["brand"], id)).fetchall()
    conn.close()
    return render_template("product.html", p=p, more=more)


@app.route("/add/<int:id>", methods=["POST"])
def add(id):
    cart = session.get("cart", {})
    conn = db()
    p = conn.execute("SELECT stock FROM products WHERE id = ?", (id,)).fetchone()
    conn.close()
    if p is None:
        return redirect("/")
    if cart.get(str(id), 0) >= p["stock"]:
        flash("Sorry, no more of that item in stock.")
    else:
        cart[str(id)] = cart.get(str(id), 0) + 1
        session["cart"] = cart
    return redirect(request.referrer or "/")


@app.route("/change/<int:id>/<int:amount>", methods=["POST"])
def change(id, amount):
    cart = session.get("cart", {})
    conn = db()
    p = conn.execute("SELECT stock FROM products WHERE id = ?", (id,)).fetchone()
    conn.close()
    new = cart.get(str(id), 0) + amount
    if p is not None and new > p["stock"]:
        flash("Only " + str(p["stock"]) + " in stock.")
    elif new <= 0:
        cart.pop(str(id), None)
    else:
        cart[str(id)] = new
    session["cart"] = cart
    return redirect("/cart")


def cart_items():
    conn = db()
    items = []
    total = 0
    for id, quantity in session.get("cart", {}).items():
        product = conn.execute("SELECT * FROM products WHERE id = ?", (id,)).fetchone()
        if product is None:
            continue
        items.append({"product": product, "quantity": quantity})
        total += product["price"] * quantity
    conn.close()
    return items, total


@app.route("/cart")
def cart():
    items, total = cart_items()
    return render_template("cart.html", items=items, total=total)


@app.route("/checkout", methods=["POST"])
def checkout():
    if "user_id" not in session:
        flash("Please log in to check out.")
        return redirect("/login")
    items, total = cart_items()
    if not items:
        return redirect("/cart")
    for item in items:
        if item["quantity"] > item["product"]["stock"]:
            flash("Not enough stock for " + item["product"]["name"] + ".")
            return redirect("/cart")
    conn = db()
    order_id = conn.execute("INSERT INTO orders (user_id, total) VALUES (?, ?)", (session["user_id"], total)).lastrowid
    for item in items:
        conn.execute("INSERT INTO order_items VALUES (?, ?, ?)", (order_id, item["product"]["id"], item["quantity"]))
        conn.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (item["quantity"], item["product"]["id"]))
    conn.commit()
    conn.close()
    session["cart"] = {}
    flash("Order placed. Thank you!")
    return redirect("/orders")


@app.route("/orders")
def orders():
    if "user_id" not in session:
        return redirect("/login")
    conn = db()
    rows = conn.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (session["user_id"],)).fetchall()
    orders = []
    for row in rows:
        names = conn.execute("""SELECT COALESCE(p.name, '(removed item)') AS name, i.quantity FROM order_items i
                                LEFT JOIN products p ON p.id = i.product_id WHERE i.order_id = ?""", (row["id"],)).fetchall()
        orders.append({"order": row, "items": names})
    conn.close()
    return render_template("orders.html", orders=orders)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].lower()
        password = generate_password_hash(request.form["password"])
        conn = db()
        is_admin = 1 if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0 else 0
        try:
            user_id = conn.execute("INSERT INTO users (email, password, is_admin) VALUES (?, ?, ?)", (email, password, is_admin)).lastrowid
            conn.commit()
        except sqlite3.IntegrityError:
            flash("That email is already registered.")
            return redirect("/register")
        finally:
            conn.close()
        session["user_id"] = user_id
        session["email"] = email
        session["is_admin"] = is_admin
        return redirect("/")
    return render_template("login.html", title="Register")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        conn = db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (request.form["email"].lower(),)).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], request.form["password"]):
            session["user_id"] = user["id"]
            session["email"] = user["email"]
            session["is_admin"] = user["is_admin"]
            return redirect("/")
        flash("Wrong email or password.")
        return redirect("/login")
    return render_template("login.html", title="Log in")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("email", None)
    session.pop("is_admin", None)
    return redirect("/")


def is_admin():
    return session.get("is_admin") == 1


@app.route("/admin")
def admin():
    if not is_admin():
        return redirect("/")
    conn = db()
    products = conn.execute("SELECT * FROM products ORDER BY id").fetchall()
    conn.close()
    return render_template("admin.html", products=products)


@app.route("/admin/new", methods=["GET", "POST"])
@app.route("/admin/edit/<int:id>", methods=["GET", "POST"])
def product_form(id=None):
    if not is_admin():
        return redirect("/")
    conn = db()
    product = None
    if id:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (id,)).fetchone()
    if request.method == "POST":
        data = (request.form["name"], request.form["brand"], int(request.form["price"]),
                int(request.form["hue"]), request.form["description"], int(request.form["stock"]))
        if id:
            conn.execute("UPDATE products SET name=?, brand=?, price=?, hue=?, description=?, stock=? WHERE id=?", data + (id,))
        else:
            conn.execute("INSERT INTO products (name, brand, price, hue, description, stock) VALUES (?,?,?,?,?,?)", data)
        conn.commit()
        conn.close()
        flash("Saved.")
        return redirect("/admin")
    conn.close()
    return render_template("admin_form.html", product=product)


@app.route("/admin/orders")
def admin_orders():
    if not is_admin():
        return redirect("/")
    conn = db()
    rows = conn.execute("SELECT o.*, u.email FROM orders o JOIN users u ON u.id = o.user_id ORDER BY o.id DESC").fetchall()
    orders = []
    for row in rows:
        items = conn.execute("""SELECT COALESCE(p.name, '(removed item)') AS name, i.quantity FROM order_items i
                                LEFT JOIN products p ON p.id = i.product_id WHERE i.order_id = ?""", (row["id"],)).fetchall()
        orders.append({"order": row, "items": items})
    conn.close()
    return render_template("admin_orders.html", orders=orders, statuses=STATUSES)


@app.route("/admin/orders/<int:id>", methods=["POST"])
def set_status(id):
    if not is_admin():
        return redirect("/")
    status = request.form["status"]
    if status in STATUSES:
        conn = db()
        conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, id))
        conn.commit()
        conn.close()
        flash("Order #" + str(id) + " is now " + status + ".")
    return redirect("/admin/orders")


@app.route("/admin/delete/<int:id>", methods=["POST"])
def delete_product(id):
    if not is_admin():
        return redirect("/")
    conn = db()
    conn.execute("DELETE FROM products WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("Product deleted.")
    return redirect("/admin")


setup()

if __name__ == "__main__":
    app.run(debug=True)
