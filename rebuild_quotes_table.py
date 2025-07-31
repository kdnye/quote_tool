#rebuild_quotes_table.py
from db import Quote, engine

Quote.__table__.drop(engine)  # Drop just the quotes table
Quote.__table__.create(engine)  # Recreate with new schema
