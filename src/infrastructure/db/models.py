from sqlalchemy import Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# ================= USERS =================

class User(Base):
    __tablename__ = "users"

    tg_user_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    vk_access_token: Mapped[str | None] = mapped_column(String, nullable=True)
    vk_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    filter_city_name: Mapped[str | None] = mapped_column(String, nullable=True)
    filter_city_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    filter_gender: Mapped[int | None] = mapped_column(Integer, nullable=True)
    filter_age_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    filter_age_to: Mapped[int | None] = mapped_column(Integer, nullable=True)

    history_cursor: Mapped[int] = mapped_column(Integer, default=0)


# ================= QUEUE =================

class QueueItem(Base):
    __tablename__ = "queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.tg_user_id")
    )
    vk_profile_id: Mapped[int] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer)


# ================= FAVORITES =================

class FavoriteProfile(Base):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_user_id: Mapped[int] = mapped_column(Integer)
    vk_profile_id: Mapped[int] = mapped_column(Integer)

    __table_args__ = (
        UniqueConstraint("tg_user_id", "vk_profile_id"),
    )


# ================= BLACKLIST =================

class Blacklist(Base):
    __tablename__ = "blacklist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_user_id: Mapped[int] = mapped_column(Integer)
    vk_profile_id: Mapped[int] = mapped_column(Integer)


# ================= PROFILES =================

class Profile(Base):
    __tablename__ = "profiles"

    vk_user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    domain: Mapped[str] = mapped_column(String)


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vk_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("profiles.vk_user_id")
    )

    photo_id: Mapped[int] = mapped_column(Integer)
    owner_id: Mapped[int] = mapped_column(Integer)
    url: Mapped[str] = mapped_column(String)
    likes_count: Mapped[int] = mapped_column(Integer)

    local_path: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str | None] = mapped_column(String, nullable=True)