from sqlalchemy import create_engine, inspect, text
from config import Config

engine = create_engine(Config.DATABASE_URL)
inspector = inspect(engine)

existing_columns = [col["name"] for col in inspector.get_columns("quotes")]

required_columns = {
    "actual_weight": "FLOAT",
    "dim_weight": "FLOAT",
    "pieces": "INTEGER",
    "length": "FLOAT",
    "width": "FLOAT",
    "height": "FLOAT",
}

with engine.begin() as conn:
    for column, col_type in required_columns.items():
        if column not in existing_columns:
            print(f"🔧 Adding missing column: {column}")
            conn.execute(text(f"ALTER TABLE quotes ADD COLUMN {column} {col_type}"))
        else:
            print(f"✅ Column already exists: {column}")
