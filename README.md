# Bayonette

A small Flask shop with customer accounts, a cart, checkout, order management and an admin area. Data is stored in SQLite.

## Features

**Shop**
- Product list with search, category filter and price sorting
- Product pages, stock counts and sold-out labels
- Star ratings and written reviews (admins can delete reviews)
- Cart, checkout and order history with order statuses
- Customer registration and login
- Wishlist

**Admin**
- Add, edit and delete products
- Update order statuses
- Dashboard with sales, best sellers and low-stock information
- Manage coupons and customer messages

## Requirements

- Python 3.10+
- Dependencies in `requirements.txt`

## Local development

Create and activate a virtual environment, then install dependencies:

    python -m venv .venv
    # Windows:
    .venv\\Scripts\\activate
    # macOS / Linux:
    source .venv/bin/activate

    pip install -r requirements.txt

Run the development server:

    python app.py

Open http://127.0.0.1:5000.

For local development, Bayonette uses a generated secret key if `SECRET_KEY` is not set and stores its database in `shop.db` in the project directory.

## Configuration

Configure these environment variables before deploying:

| Variable | Required in production | Description |
|---|---:|---|
| `APP_ENV` | Yes | Set to `production` to enable production safeguards. |
| `SECRET_KEY` | Yes | Long, random secret used to sign sessions. Keep it private and stable across restarts and all app workers. |
| `ADMIN_EMAIL` | Recommended | Email reserved for the store administrator. Defaults to `admin@bayonette.com`. |
| `DATABASE_PATH` | Recommended | Absolute path to the SQLite database on persistent storage. Relative paths are resolved from the project directory. Defaults to `shop.db`. |
| `SESSION_COOKIE_SECURE` | No | Defaults to secure cookies in production and non-secure cookies in local development. Set to `true` only when serving over HTTPS. |

A starter template is available in `.env.example`. The application does not automatically load `.env` files; configure variables in your shell or hosting provider's environment settings.

Generate a secret key with:

    python -c "import secrets; print(secrets.token_hex(32))"

Do not commit real secrets or production environment files.

## Production deployment

Install the dependencies and start the app with Gunicorn:

    gunicorn --bind 0.0.0.0:$PORT app:app

Configure the hosting provider to:
1. Install dependencies with `pip install -r requirements.txt`.
2. Set `APP_ENV=production`.
3. Set a generated `SECRET_KEY`.
4. Set `SESSION_COOKIE_SECURE=true` when HTTPS is enabled (the production default).
5. Set `DATABASE_PATH` to a location on a persistent disk or volume.
6. Use the Gunicorn command above as the start command.

**SQLite storage matters:** the database file must live on persistent storage. Do not put it on an ephemeral filesystem or a temporary deployment directory. Back up the database regularly. SQLite is appropriate for a small, single-instance shop; if you later need multiple app instances or heavier concurrent writes, plan a migration to a managed database such as PostgreSQL.

Create the administrator after the database volume is mounted and the production environment variables are configured:

    flask --app app create-admin

The command securely prompts for a password of at least 12 characters and creates or resets the configured administrator account. Run it against the same database path used by the web process.

Do not run the Flask development server or enable debug mode in production.

## Tests

Run the automated test suite with:

    python -m unittest discover -s tests -v

GitHub Actions runs the tests on pushes and pull requests.

## Project structure

- `app.py` - Flask routes, configuration and SQLite database setup
- `templates/` - page templates
- `static/css/` - site styling
- `static/js/main.js` - theme, cart and wishlist interactions
- `static/img/` - logo and favicon
- `tests/` - automated application tests
- `shop.db` - local development database (created on first run; do not commit)
