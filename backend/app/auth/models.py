from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID

from app.core.database import Base


class User(SQLAlchemyBaseUserTableUUID, Base):
    pass
