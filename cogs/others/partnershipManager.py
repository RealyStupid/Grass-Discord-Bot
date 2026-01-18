from BotConfig import GUILD_IDS, bot_owner_only
import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import os
import io

DB_PATH = 'Data/Partherships.db'


class MessageBridge(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._ensure_db()
        self.bot.bridges = self._load_bridges()

        # Cache for webhooks so we don't fetch/create every message
        self.webhook_cache: dict[int, discord.Webhook] = {}

    # ----------------------------------------------------
    # DATABASE SETUP
    # ----------------------------------------------------
    def _ensure_db(self):
        os.makedirs("Data", exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS bridges (
                channel_a INTEGER NOT NULL,
                channel_b INTEGER NOT NULL,
                PRIMARY KEY (channel_a, channel_b)
            );
        """)
        conn.commit()
        conn.close()

    def _load_bridges(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT channel_a, channel_b FROM bridges")
        rows = cursor.fetchall()
        conn.close()
        return {frozenset((a, b)) for a, b in rows}

    # ----------------------------------------------------
    # WEBHOOK HELPER
    # ----------------------------------------------------
    async def get_webhook(self, channel: discord.TextChannel) -> discord.Webhook:
        """Fetch or create a webhook for a channel, with caching."""
        if channel.id in self.webhook_cache:
            return self.webhook_cache[channel.id]

        webhooks = await channel.webhooks()
        for wh in webhooks:
            if wh.name == "BridgeWebhook":
                self.webhook_cache[channel.id] = wh
                return wh

        # Create a new webhook if none exist
        wh = await channel.create_webhook(name="BridgeWebhook")
        self.webhook_cache[channel.id] = wh
        return wh

    # ----------------------------------------------------
    # MESSAGE RELAY LISTENER (WEBHOOK VERSION)
    # ----------------------------------------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        for pair in self.bot.bridges:
            if message.channel.id in pair:
                other_channel_id = next(ch for ch in pair if ch != message.channel.id)
                other_channel = self.bot.get_channel(other_channel_id)

                if not other_channel or not isinstance(other_channel, discord.TextChannel):
                    continue

                webhook = await self.get_webhook(other_channel)

                # Forward attachments
                files = []
                for attachment in message.attachments:
                    data = await attachment.read()
                    files.append(discord.File(io.BytesIO(data), filename=attachment.filename))

                # Prevent blank webhook messages
                safe_content = message.content.strip() if message.content else ""
                if not safe_content and not files:
                    safe_content = " "  # ensures webhook message is visible

                print("Attempting webhook send to:", other_channel.id)
                print("DEBUG FILES:", files, type(files))

                try:
                    await webhook.send(
                        content=safe_content,
                        username=message.author.display_name,
                        avatar_url=message.author.display_avatar.url,
                        files=files
                    )
                    print("Webhook sent successfully.")

                except Exception as e:
                    print("WEBHOOK SEND ERROR:", repr(e))
                    # If webhook is bad, drop it from cache so it can be recreated next time
                    if other_channel.id in self.webhook_cache:
                        del self.webhook_cache[other_channel.id]

                return

    # ----------------------------------------------------
    # SLASH COMMAND GROUP
    # ----------------------------------------------------
    partnership = app_commands.Group(
        name="partnership",
        description="Manage cross-server message bridges.",
        guild_ids=GUILD_IDS
    )

    # ----------------------------------------------------
    # /partnership addbridge
    # ----------------------------------------------------
    @partnership.command(
        name="addbridge",
        description="Create a two-way message bridge between two channel IDs."
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def add_bridge(
        self,
        interaction: discord.Interaction,
        channel_a_id: str,
        channel_b_id: str
    ):
        await self._add_bridge_logic(interaction, channel_a_id, channel_b_id)

    # ----------------------------------------------------
    # /partnership removebridge
    # ----------------------------------------------------
    @partnership.command(
        name="removebridge",
        description="Remove a two-way message bridge using channel IDs."
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def remove_bridge(
        self,
        interaction: discord.Interaction,
        channel_a_id: str,
        channel_b_id: str
    ):
        await self._remove_bridge_logic(interaction, channel_a_id, channel_b_id)

    # ----------------------------------------------------
    # /partnership listbridges
    # ----------------------------------------------------
    @partnership.command(
        name="listbridges",
        description="List all active message bridges."
    )
    async def list_bridges(self, interaction: discord.Interaction):
        await self._list_bridges_logic(interaction)

    # ----------------------------------------------------
    # SHARED LOGIC
    # ----------------------------------------------------
    async def _add_bridge_logic(self, interaction, channel_a_id, channel_b_id):
        try:
            a = int(channel_a_id)
            b = int(channel_b_id)
        except ValueError:
            await interaction.response.send_message("Channel IDs must be numbers.")
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO bridges (channel_a, channel_b) VALUES (?, ?)", (a, b))
            conn.commit()
            msg = f"Bridge created between `{a}` and `{b}`."
        except sqlite3.IntegrityError:
            msg = "That bridge already exists."
        finally:
            conn.close()

        self.bot.bridges = self._load_bridges()
        await interaction.response.send_message(msg)

    async def _remove_bridge_logic(self, interaction, channel_a_id, channel_b_id):
        try:
            a = int(channel_a_id)
            b = int(channel_b_id)
        except ValueError:
            await interaction.response.send_message("Channel IDs must be numbers.")
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM bridges
            WHERE (channel_a = ? AND channel_b = ?)
               OR (channel_a = ? AND channel_b = ?)
            """,
            (a, b, b, a)
        )
        conn.commit()
        conn.close()

        self.bot.bridges = self._load_bridges()
        await interaction.response.send_message(f"Bridge removed between `{a}` and `{b}`.")

    async def _list_bridges_logic(self, interaction):
        if not self.bot.bridges:
            msg = "No bridges are currently set."
        else:
            lines = []
            for pair in self.bot.bridges:
                a, b = tuple(pair)
                lines.append(f"`{a}` ↔ `{b}`")
            msg = "Active bridges:\n" + "\n".join(lines)

        await interaction.response.send_message(msg)


async def setup(bot: commands.Bot):
    await bot.add_cog(MessageBridge(bot))