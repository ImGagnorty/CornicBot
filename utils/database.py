"""
CornicBot — Couche base de données (aiosqlite).
Gère les tickets, commandes personnalisées et la configuration des guilds.
"""

from __future__ import annotations

import aiosqlite
from typing import Optional

DB_PATH = "cornicbot.db"


class Database:

    def __init__(self) -> None:
        self._db: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        self._db = await aiosqlite.connect(DB_PATH)
        self._db.row_factory = aiosqlite.Row
        await self._create_tables()
        await self._migrate()

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    # ──────────────────────────────────────────────
    #  Création des tables
    # ──────────────────────────────────────────────

    async def _migrate(self) -> None:
        """Ajoute les colonnes manquantes sur une base existante."""
        try:
            await self._db.execute("ALTER TABLE custom_commands ADD COLUMN title TEXT")
            await self._db.commit()
        except Exception:
            pass  # Colonne déjà présente

    async def _create_tables(self) -> None:
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id         INTEGER PRIMARY KEY,
                category_id      INTEGER,
                log_channel_id   INTEGER,
                support_role_id  INTEGER,
                ticket_counter   INTEGER DEFAULT 0,
                panel_message_id INTEGER,
                panel_channel_id INTEGER
            );

            CREATE TABLE IF NOT EXISTS tickets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id   TEXT    NOT NULL,
                guild_id    INTEGER NOT NULL,
                channel_id  INTEGER NOT NULL UNIQUE,
                user_id     INTEGER NOT NULL,
                staff_id    INTEGER,
                status      TEXT    NOT NULL DEFAULT 'open',
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                closed_at   DATETIME,
                close_reason TEXT
            );

            CREATE TABLE IF NOT EXISTS custom_commands (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id    INTEGER NOT NULL,
                name        TEXT    NOT NULL,
                title       TEXT,
                content     TEXT    NOT NULL,
                created_by  INTEGER NOT NULL,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, name)
            );
        """)
        await self._db.commit()

    # ──────────────────────────────────────────────
    #  Guild Config
    # ──────────────────────────────────────────────

    async def upsert_guild_config(
        self,
        guild_id: int,
        category_id: int,
        log_channel_id: int,
        support_role_id: int,
    ) -> None:
        await self._db.execute(
            """
            INSERT INTO guild_config (guild_id, category_id, log_channel_id, support_role_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                category_id     = excluded.category_id,
                log_channel_id  = excluded.log_channel_id,
                support_role_id = excluded.support_role_id
            """,
            (guild_id, category_id, log_channel_id, support_role_id),
        )
        await self._db.commit()

    async def get_guild_config(self, guild_id: int) -> Optional[aiosqlite.Row]:
        async with self._db.execute(
            "SELECT * FROM guild_config WHERE guild_id = ?", (guild_id,)
        ) as cursor:
            return await cursor.fetchone()

    async def set_panel_info(
        self, guild_id: int, channel_id: int, message_id: int
    ) -> None:
        await self._db.execute(
            """
            UPDATE guild_config
            SET panel_channel_id = ?, panel_message_id = ?
            WHERE guild_id = ?
            """,
            (channel_id, message_id, guild_id),
        )
        await self._db.commit()

    async def increment_ticket_counter(self, guild_id: int) -> int:
        """Incrémente et retourne le nouveau compteur de tickets."""
        await self._db.execute(
            "INSERT INTO guild_config (guild_id, ticket_counter) VALUES (?, 1) "
            "ON CONFLICT(guild_id) DO UPDATE SET ticket_counter = ticket_counter + 1",
            (guild_id,),
        )
        await self._db.commit()
        async with self._db.execute(
            "SELECT ticket_counter FROM guild_config WHERE guild_id = ?", (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row["ticket_counter"]

    # ──────────────────────────────────────────────
    #  Tickets
    # ──────────────────────────────────────────────

    async def create_ticket(
        self,
        ticket_id: str,
        guild_id: int,
        channel_id: int,
        user_id: int,
    ) -> None:
        await self._db.execute(
            """
            INSERT INTO tickets (ticket_id, guild_id, channel_id, user_id)
            VALUES (?, ?, ?, ?)
            """,
            (ticket_id, guild_id, channel_id, user_id),
        )
        await self._db.commit()

    async def get_ticket_by_channel(self, channel_id: int) -> Optional[aiosqlite.Row]:
        async with self._db.execute(
            "SELECT * FROM tickets WHERE channel_id = ?", (channel_id,)
        ) as cursor:
            return await cursor.fetchone()

    async def get_open_ticket_by_user(
        self, guild_id: int, user_id: int
    ) -> Optional[aiosqlite.Row]:
        async with self._db.execute(
            "SELECT * FROM tickets WHERE guild_id = ? AND user_id = ? AND status = 'open'",
            (guild_id, user_id),
        ) as cursor:
            return await cursor.fetchone()

    async def claim_ticket(self, channel_id: int, staff_id: int) -> None:
        await self._db.execute(
            "UPDATE tickets SET staff_id = ?, status = 'claimed' WHERE channel_id = ?",
            (staff_id, channel_id),
        )
        await self._db.commit()

    async def close_ticket(
        self, channel_id: int, reason: str = "Aucune raison fournie"
    ) -> None:
        await self._db.execute(
            """
            UPDATE tickets
            SET status = 'closed', closed_at = CURRENT_TIMESTAMP, close_reason = ?
            WHERE channel_id = ?
            """,
            (reason, channel_id),
        )
        await self._db.commit()

    async def archive_ticket(self, channel_id: int) -> None:
        await self._db.execute(
            "UPDATE tickets SET status = 'archived', closed_at = CURRENT_TIMESTAMP WHERE channel_id = ?",
            (channel_id,),
        )
        await self._db.commit()

    # ──────────────────────────────────────────────
    #  Commandes personnalisées
    # ──────────────────────────────────────────────

    async def create_command(
        self, guild_id: int, name: str, content: str, created_by: int,
        title: Optional[str] = None,
    ) -> None:
        await self._db.execute(
            """
            INSERT INTO custom_commands (guild_id, name, title, content, created_by)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, name) DO UPDATE SET
                title   = excluded.title,
                content = excluded.content
            """,
            (guild_id, name.lower(), title or None, content, created_by),
        )
        await self._db.commit()

    async def get_command(
        self, guild_id: int, name: str
    ) -> Optional[aiosqlite.Row]:
        async with self._db.execute(
            "SELECT * FROM custom_commands WHERE guild_id = ? AND name = ?",
            (guild_id, name.lower()),
        ) as cursor:
            return await cursor.fetchone()

    async def delete_command(self, guild_id: int, name: str) -> bool:
        cursor = await self._db.execute(
            "DELETE FROM custom_commands WHERE guild_id = ? AND name = ?",
            (guild_id, name.lower()),
        )
        await self._db.commit()
        return cursor.rowcount > 0

    async def list_commands(self, guild_id: int) -> list:
        async with self._db.execute(
            "SELECT name, content FROM custom_commands WHERE guild_id = ? ORDER BY name",
            (guild_id,),
        ) as cursor:
            return await cursor.fetchall()
