async def add_user(session, user_data):
    from yt_university.models.user import User

    user = User(**user_data)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user(session, user_data):
    from sqlalchemy.orm.exc import NoResultFound
    from sqlalchemy.sql import select

    from yt_university.models.user import User

    query = select(User).filter_by(id=user_data["id"])
    result = await session.execute(query)
    user = result.scalar()
    if user:
        for key, value in user_data.items():
            setattr(user, key, value)
        await session.commit()
        return user
    else:
        raise NoResultFound("User not found")


async def delete_user(session, user_data):
    from sqlalchemy.orm.exc import NoResultFound
    from sqlalchemy.sql import select

    from yt_university.models.user import User

    query = select(User).filter_by(id=user_data["id"])
    result = await session.execute(query)
    user = result.scalar()
    if user:
        await user.delete()
        await session.commit()
    else:
        raise NoResultFound("User not found")
