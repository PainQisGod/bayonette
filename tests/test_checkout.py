"""Integration tests for Bayonette's checkout and order lifecycle.

Run with: python -m unittest discover -s tests -v
"""
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from werkzeug.security import generate_password_hash

import app as shop


class ShopFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test-shop.db")

        def test_db():
            connection = sqlite3.connect(self.db_path)
            connection.row_factory = sqlite3.Row
            return connection

        self.db_patch = patch.object(shop, "db", side_effect=test_db)
        self.db_patch.start()
        shop.setup()

        conn = shop.db()
        conn.execute(
            "INSERT INTO users (email, password, is_admin) VALUES (?, ?, 0)",
            ("customer@example.com", generate_password_hash("test-password"),),
        )
        conn.execute(
            "INSERT INTO users (email, password, is_admin) VALUES (?, ?, 1)",
            ("admin@example.com", generate_password_hash("test-admin-password"),),
        )
        self.user_id = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("customer@example.com",)
        ).fetchone()["id"]
        self.admin_id = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("admin@example.com",)
        ).fetchone()["id"]
        self.product = conn.execute(
            "SELECT id, price, stock FROM products ORDER BY id LIMIT 1"
        ).fetchone()
        conn.execute(
            "INSERT INTO coupons (code, percent, active) VALUES ('TEST10', 10, 1)"
        )
        conn.commit()
        conn.close()

        shop.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = shop.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = self.user_id
            session["_csrf_token"] = "test-csrf-token"
            session["cart"] = {str(self.product["id"]): 2}

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def post_checkout(self, **extra):
        data = {
            "csrf_token": "test-csrf-token",
            "name": "Test Customer",
            "phone": "012345678",
            "address": "Test address",
            "payment": "Cash on delivery",
        }
        data.update(extra)
        return self.client.post("/checkout", data=data)

    def test_checkout_creates_order_and_deducts_stock(self):
        response = self.post_checkout()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].startswith("/order/"))

        conn = shop.db()
        order = conn.execute("SELECT * FROM orders").fetchone()
        item = conn.execute("SELECT * FROM order_items").fetchone()
        stock = conn.execute(
            "SELECT stock FROM products WHERE id = ?", (self.product["id"],)
        ).fetchone()["stock"]
        conn.close()

        subtotal = self.product["price"] * 2
        shipping = 0 if subtotal >= shop.FREE_SHIPPING_OVER else shop.SHIPPING_FEE
        expected_total = subtotal + shipping + (subtotal * shop.TAX_PERCENT // 100)
        self.assertEqual(order["total"], expected_total)
        self.assertEqual(item["quantity"], 2)
        self.assertEqual(stock, self.product["stock"] - 2)

        with self.client.session_transaction() as session:
            self.assertEqual(session.get("cart"), {})
            self.assertNotIn("coupon", session)

    def test_checkout_rejects_insufficient_stock_without_creating_order(self):
        conn = shop.db()
        conn.execute(
            "UPDATE products SET stock = 1 WHERE id = ?", (self.product["id"],)
        )
        conn.commit()
        conn.close()

        response = self.post_checkout()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/cart")

        conn = shop.db()
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0], 0)
        self.assertEqual(
            conn.execute(
                "SELECT stock FROM products WHERE id = ?", (self.product["id"],)
            ).fetchone()["stock"],
            1,
        )
        conn.close()

    def test_coupon_is_applied_and_removed_from_session_after_checkout(self):
        with self.client.session_transaction() as session:
            session["coupon"] = "TEST10"

        response = self.post_checkout()
        self.assertEqual(response.status_code, 302)

        conn = shop.db()
        order = conn.execute("SELECT * FROM orders").fetchone()
        conn.close()

        subtotal = self.product["price"] * 2
        discount = subtotal * 10 // 100
        after_discount = subtotal - discount
        shipping = 0 if after_discount >= shop.FREE_SHIPPING_OVER else shop.SHIPPING_FEE
        tax = after_discount * shop.TAX_PERCENT // 100
        self.assertEqual(order["coupon"], "TEST10")
        self.assertEqual(order["discount"], discount)
        self.assertEqual(order["shipping"], shipping)
        self.assertEqual(order["tax"], tax)
        self.assertEqual(order["total"], after_discount + shipping + tax)

        with self.client.session_transaction() as session:
            self.assertNotIn("coupon", session)

    def test_cancelled_order_restores_stock_only_once(self):
        response = self.post_checkout()
        order_id = int(response.headers["Location"].rsplit("/", 1)[1])

        with self.client.session_transaction() as session:
            session["_csrf_token"] = "test-csrf-token"

        first = self.client.post(
            f"/order/{order_id}/cancel", data={"csrf_token": "test-csrf-token"}
        )
        second = self.client.post(
            f"/order/{order_id}/cancel", data={"csrf_token": "test-csrf-token"}
        )
        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)

        conn = shop.db()
        stock = conn.execute(
            "SELECT stock FROM products WHERE id = ?", (self.product["id"],)
        ).fetchone()["stock"]
        status = conn.execute(
            "SELECT status FROM orders WHERE id = ?", (order_id,)
        ).fetchone()["status"]
        conn.close()

        self.assertEqual(stock, self.product["stock"])
        self.assertEqual(status, "cancelled")

    def test_customer_cannot_view_another_customers_order(self):
        response = self.post_checkout()
        order_id = int(response.headers["Location"].rsplit("/", 1)[1])

        conn = shop.db()
        other_id = conn.execute(
            "INSERT INTO users (email, password, is_admin) VALUES (?, ?, 0)",
            ("other@example.com", generate_password_hash("other-password")),
        ).lastrowid
        conn.commit()
        conn.close()

        with self.client.session_transaction() as session:
            session["user_id"] = other_id

        response = self.client.get(f"/order/{order_id}")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/orders")

    def test_shipped_order_cannot_be_cancelled(self):
        response = self.post_checkout()
        order_id = int(response.headers["Location"].rsplit("/", 1)[1])

        conn = shop.db()
        conn.execute("UPDATE orders SET status = 'shipped' WHERE id = ?", (order_id,))
        conn.commit()
        conn.close()

        response = self.client.post(
            f"/order/{order_id}/cancel", data={"csrf_token": "test-csrf-token"}
        )
        self.assertEqual(response.status_code, 302)

        conn = shop.db()
        stock = conn.execute(
            "SELECT stock FROM products WHERE id = ?", (self.product["id"],)
        ).fetchone()["stock"]
        status = conn.execute(
            "SELECT status FROM orders WHERE id = ?", (order_id,)
        ).fetchone()["status"]
        conn.close()

        self.assertEqual(stock, self.product["stock"] - 2)
        self.assertEqual(status, "shipped")


if __name__ == "__main__":
    unittest.main()
