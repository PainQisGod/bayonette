import sqlite3
from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "change-this-to-anything"

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
        CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT UNIQUE, password TEXT);
        CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT, brand TEXT, price INTEGER, hue INTEGER, description TEXT);
        CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, user_id INTEGER, total INTEGER, created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS order_items (order_id INTEGER, product_id INTEGER, quantity INTEGER);
    """)
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


@app.route("/add/<int:id>", methods=["POST"])
def add(id):
    cart = session.get("cart", {})
    cart[str(id)] = cart.get(str(id), 0) + 1
    session["cart"] = cart
    return redirect(request.referrer or "/")


@app.route("/change/<int:id>/<int:amount>", methods=["POST"])
def change(id, amount):
    cart = session.get("cart", {})
    cart[str(id)] = cart.get(str(id), 0) + amount
    if cart[str(id)] <= 0:
        del cart[str(id)]
    session["cart"] = cart
    return redirect("/cart")


def cart_items():
    conn = db()
    items = []
    total = 0
    for id, quantity in session.get("cart", {}).items():
        product = conn.execute("SELECT * FROM products WHERE id = ?", (id,)).fetchone()
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
    conn = db()
    order_id = conn.execute("INSERT INTO orders (user_id, total) VALUES (?, ?)", (session["user_id"], total)).lastrowid
    for item in items:
        conn.execute("INSERT INTO order_items VALUES (?, ?, ?)", (order_id, item["product"]["id"], item["quantity"]))
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
        names = conn.execute("""SELECT p.name, i.quantity FROM order_items i
                                JOIN products p ON p.id = i.product_id WHERE i.order_id = ?""", (row["id"],)).fetchall()
        orders.append({"order": row, "items": names})
    conn.close()
    return render_template("orders.html", orders=orders)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].lower()
        password = generate_password_hash(request.form["password"])
        conn = db()
        try:
            user_id = conn.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password)).lastrowid
            conn.commit()
        except sqlite3.IntegrityError:
            flash("That email is already registered.")
            return redirect("/register")
        finally:
            conn.close()
        session["user_id"] = user_id
        session["email"] = email
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
            return redirect("/")
        flash("Wrong email or password.")
        return redirect("/login")
    return render_template("login.html", title="Log in")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("email", None)
    return redirect("/")


setup()

if __name__ == "__main__":
    app.run(debug=True)
