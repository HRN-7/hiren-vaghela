from app.db import Base, engine
Base.metadata.create_all(engine())
print('Database schema initialized. For subsequent schema changes, use reviewed SQL migrations.')
