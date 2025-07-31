from db import Base, engine, Quote

# Drop the quotes table only
Quote.__table__.drop(engine)
print("✅ 'quotes' table dropped.")
