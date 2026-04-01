"""Service for managing custom user lists."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from cinematch.models.movie import Movie
from cinematch.models.user import User
from cinematch.models.user_list import UserList
from cinematch.models.user_list_item import UserListItem


class UserListService:
    """CRUD operations for user-created movie lists."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _ensure_user(self, user_id: int, db: AsyncSession) -> None:
        result = await db.execute(select(User).where(User.id == user_id))
        if result.scalar_one_or_none() is None:
            db.add(User(id=user_id, movielens_id=user_id))
            await db.flush()

    async def _get_list_owned(
        self, user_id: int, list_id: int, db: AsyncSession
    ) -> UserList | None:
        result = await db.execute(
            select(UserList).where(UserList.id == list_id, UserList.user_id == user_id)
        )
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # List CRUD
    # ------------------------------------------------------------------

    async def create_list(
        self,
        user_id: int,
        name: str,
        description: str | None,
        is_public: bool,
        db: AsyncSession,
    ) -> UserList:
        await self._ensure_user(user_id, db)
        now = datetime.now(UTC)
        ul = UserList(
            user_id=user_id,
            name=name,
            description=description,
            is_public=is_public,
            created_at=now,
            updated_at=now,
        )
        db.add(ul)
        await db.commit()
        await db.refresh(ul)
        return ul

    async def update_list(
        self,
        user_id: int,
        list_id: int,
        db: AsyncSession,
        name: str | None = None,
        description: str | None = None,
        is_public: bool | None = None,
    ) -> UserList | None:
        ul = await self._get_list_owned(user_id, list_id, db)
        if ul is None:
            return None
        if name is not None:
            ul.name = name
        if description is not None:
            ul.description = description
        if is_public is not None:
            ul.is_public = is_public
        ul.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(ul)
        return ul

    async def delete_list(self, user_id: int, list_id: int, db: AsyncSession) -> bool:
        stmt = delete(UserList).where(UserList.id == list_id, UserList.user_id == user_id)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0

    # ------------------------------------------------------------------
    # Retrieve lists
    # ------------------------------------------------------------------

    async def get_list(
        self,
        list_id: int,
        db: AsyncSession,
        offset: int = 0,
        limit: int = 20,
    ) -> (
        tuple[
            UserList,
            list[tuple[UserListItem, str | None, str | None, list | None, float, str | None]],
            int,
        ]
        | None
    ):
        """Return list metadata + paginated items with movie details, or None."""
        result = await db.execute(select(UserList).where(UserList.id == list_id))
        ul = result.scalar_one_or_none()
        if ul is None:
            return None

        count_result = await db.execute(
            select(func.count()).select_from(UserListItem).where(UserListItem.list_id == list_id)
        )
        total = count_result.scalar_one()

        items_stmt = (
            select(
                UserListItem,
                Movie.title,
                Movie.poster_path,
                Movie.genres,
                Movie.vote_average,
                Movie.release_date,
            )
            .outerjoin(Movie, UserListItem.movie_id == Movie.id)
            .where(UserListItem.list_id == list_id)
            .order_by(UserListItem.position)
            .offset(offset)
            .limit(limit)
        )
        items_result = await db.execute(items_stmt)
        rows = list(items_result.all())
        return ul, rows, total

    async def get_user_lists(
        self, user_id: int, db: AsyncSession
    ) -> list[tuple[UserList, int, list[str]]]:
        """Return all lists for a user with movie_count and preview posters."""
        lists_result = await db.execute(
            select(UserList).where(UserList.user_id == user_id).order_by(UserList.updated_at.desc())
        )
        lists_ = list(lists_result.scalars().all())

        out: list[tuple[UserList, int, list[str]]] = []
        for ul in lists_:
            count_result = await db.execute(
                select(func.count()).select_from(UserListItem).where(UserListItem.list_id == ul.id)
            )
            movie_count = count_result.scalar_one()

            poster_result = await db.execute(
                select(Movie.poster_path)
                .join(UserListItem, UserListItem.movie_id == Movie.id)
                .where(UserListItem.list_id == ul.id, Movie.poster_path.isnot(None))
                .order_by(UserListItem.position)
                .limit(4)
            )
            posters = [row[0] for row in poster_result.all()]
            out.append((ul, movie_count, posters))
        return out

    async def get_popular_lists(
        self, db: AsyncSession, offset: int = 0, limit: int = 20
    ) -> tuple[list[tuple[UserList, int, list[str]]], int]:
        """Return public lists ordered by item count, with total."""
        count_result = await db.execute(
            select(func.count()).select_from(UserList).where(UserList.is_public.is_(True))
        )
        total = count_result.scalar_one()

        item_count = (
            select(func.count())
            .where(UserListItem.list_id == UserList.id)
            .correlate(UserList)
            .scalar_subquery()
            .label("item_count")
        )

        lists_result = await db.execute(
            select(UserList, item_count)
            .where(UserList.is_public.is_(True))
            .order_by(item_count.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = list(lists_result.all())

        out: list[tuple[UserList, int, list[str]]] = []
        for ul, mc in rows:
            poster_result = await db.execute(
                select(Movie.poster_path)
                .join(UserListItem, UserListItem.movie_id == Movie.id)
                .where(UserListItem.list_id == ul.id, Movie.poster_path.isnot(None))
                .order_by(UserListItem.position)
                .limit(4)
            )
            posters = [row[0] for row in poster_result.all()]
            out.append((ul, mc, posters))
        return out, total

    # ------------------------------------------------------------------
    # Item operations
    # ------------------------------------------------------------------

    async def add_item(
        self, user_id: int, list_id: int, movie_id: int, db: AsyncSession
    ) -> UserListItem | None:
        """Add a movie to a list. Returns None if list not owned by user."""
        ul = await self._get_list_owned(user_id, list_id, db)
        if ul is None:
            return None

        max_result = await db.execute(
            select(func.coalesce(func.max(UserListItem.position), -1)).where(
                UserListItem.list_id == list_id
            )
        )
        next_pos = max_result.scalar_one() + 1
        now = datetime.now(UTC)

        stmt = (
            insert(UserListItem)
            .values(list_id=list_id, movie_id=movie_id, position=next_pos, added_at=now)
            .on_conflict_do_nothing(constraint="uq_list_item_list_movie")
        )
        await db.execute(stmt)

        ul.updated_at = datetime.now(UTC)
        await db.commit()

        result = await db.execute(
            select(UserListItem).where(
                UserListItem.list_id == list_id, UserListItem.movie_id == movie_id
            )
        )
        return result.scalar_one()

    async def remove_item(
        self, user_id: int, list_id: int, movie_id: int, db: AsyncSession
    ) -> bool:
        """Remove a movie from a list. Returns False if list not owned or item missing."""
        ul = await self._get_list_owned(user_id, list_id, db)
        if ul is None:
            return False

        stmt = delete(UserListItem).where(
            UserListItem.list_id == list_id, UserListItem.movie_id == movie_id
        )
        result = await db.execute(stmt)
        if result.rowcount == 0:
            return False

        # Recompact positions
        remaining = await db.execute(
            select(UserListItem)
            .where(UserListItem.list_id == list_id)
            .order_by(UserListItem.position)
        )
        for idx, item in enumerate(remaining.scalars().all()):
            if item.position != idx:
                await db.execute(
                    update(UserListItem).where(UserListItem.id == item.id).values(position=idx)
                )

        ul.updated_at = datetime.now(UTC)
        await db.commit()
        return True

    async def reorder_items(
        self, user_id: int, list_id: int, movie_ids: list[int], db: AsyncSession
    ) -> bool:
        """Reorder items by setting position = index in movie_ids list."""
        ul = await self._get_list_owned(user_id, list_id, db)
        if ul is None:
            return False

        for idx, mid in enumerate(movie_ids):
            await db.execute(
                update(UserListItem)
                .where(UserListItem.list_id == list_id, UserListItem.movie_id == mid)
                .values(position=idx)
            )

        ul.updated_at = datetime.now(UTC)
        await db.commit()
        return True
