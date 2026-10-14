# Bayonette

A small Flask shop: product list, search, cart, accounts and orders. Data is stored in SQLite.

## Run it

    pip install -r requirements.txt
    python app.py

Then open http://127.0.0.1:5000

## Files

- `app.py` - all the routes and the database code
- `templates/` - the pages
- `static/style.css` - the styling
- `shop.db` - created on first run (delete it to reset everything)

## Edit it

Change the `PRODUCTS` list at the top of `app.py`, then delete `shop.db` and run again.
