import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import async_session_maker
from app.db_depends import get_async_db
from app.auth import hash_password
from app.config import settings
from app.models.users import User

async def create_first_admin():

    async with async_session_maker() as session:

        query_admin = await session.scalars(select(User).where(User.role == "admin"))    

        first_admin = query_admin.first()

        if first_admin is not None:
            return f"Admin already exists"
        
        admin = User(email = settings.EMAIL_ADMIN, hashed_password = hash_password(settings.PASSWORD_ADMIN), role = "admin")
        session.add(admin)
        await session.commit()
        print("First admin was created successful")


if __name__ == "__main__":
    asyncio.run(create_first_admin())







