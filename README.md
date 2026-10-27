# Bayonette

A small Flask shop with accounts, a cart, orders and an admin area. Data is stored in SQLite.

## Features

**Shop**
- Product list with search, category filter and price sorting
- Product pages, stock counts and "Sold out" labels
- Cart, checkout and order history with statuses (pending, shipped, delivered)
- Register and log in

**Admin** (the first account you register becomes the admin)
- Add, edit and delete products
- Update order statuses
- Dashboard with total sales, best sellers and low stock

## Run it

    pip install -r requirements.txt
    python app.py

Then open http://127.0.0.1:5000

## Files

- `app.py` - routes and database code
- `templates/` - the pages
- `static/style.css` - the styling
- `shop.db` - created on first run (delete it to reset everything)

## Edit it

Change the `PRODUCTS` and `CATEGORIES` lists at the top of `app.py`, then delete `shop.db` and run again. Or just use the admin page.
