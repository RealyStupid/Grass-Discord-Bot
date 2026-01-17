import discord
from discord.ext import commands
import aiosqlite
import datetime


class ServerEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------------------------------------------------
    # DB HELPER
    # ---------------------------------------------------------
    async def get_server_log_channel(self, guild: discord.Guild):
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            async with db.execute(
                "SELECT server_logging_channel FROM logging_channels WHERE guild_id = ?",
                (guild.id,)
            ) as cursor:
                row = await cursor.fetchone()
        return guild.get_channel(row[0]) if row and row[0] else None

    # ---------------------------------------------------------
    # CHANNEL CREATED
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        log_channel = await self.get_server_log_channel(channel.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="📁 Channel Created",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )

        embed.add_field(name="Channel", value=channel.mention, inline=False)
        embed.add_field(name="Type", value=str(channel.type).title(), inline=False)

        await log_channel.send(embed=embed)

    # ---------------------------------------------------------
    # CHANNEL DELETED
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        log_channel = await self.get_server_log_channel(channel.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="🗑️ Channel Deleted",
            color=discord.Color.red(),
            timestamp=datetime.datetime.utcnow()
        )

        embed.add_field(name="Name", value=channel.name, inline=False)
        embed.add_field(name="Type", value=str(channel.type).title(), inline=False)

        await log_channel.send(embed=embed)

    # ---------------------------------------------------------
    # CHANNEL UPDATED
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        log_channel = await self.get_server_log_channel(after.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="✏️ Channel Updated",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )

        changes = []

        if before.name != after.name:
            changes.append(f"**Name:** `{before.name}` → `{after.name}`")

        if hasattr(before, "topic") and before.topic != after.topic:
            changes.append(f"**Topic:** `{before.topic}` → `{after.topic}`")

        if before.category != after.category:
            before_cat = before.category.name if before.category else "None"
            after_cat = after.category.name if after.category else "None"
            changes.append(f"**Category:** `{before_cat}` → `{after_cat}`")

        if hasattr(before, "nsfw") and before.nsfw != after.nsfw:
            changes.append(f"**NSFW:** `{before.nsfw}` → `{after.nsfw}`")

        if hasattr(before, "slowmode_delay") and before.slowmode_delay != after.slowmode_delay:
            changes.append(f"**Slowmode:** `{before.slowmode_delay}` → `{after.slowmode_delay}`")

        if not changes:
            return

        embed.add_field(name="Channel", value=after.mention, inline=False)
        embed.add_field(name="Changes", value="\n".join(changes), inline=False)

        await log_channel.send(embed=embed)

    # ---------------------------------------------------------
    # ROLE CREATED
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        log_channel = await self.get_server_log_channel(role.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="🎨 Role Created",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )

        embed.add_field(name="Role", value=role.mention, inline=False)
        embed.add_field(name="Color", value=str(role.color), inline=False)

        await log_channel.send(embed=embed)

    # ---------------------------------------------------------
    # ROLE DELETED
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        log_channel = await self.get_server_log_channel(role.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="🗑️ Role Deleted",
            color=discord.Color.red(),
            timestamp=datetime.datetime.utcnow()
        )

        embed.add_field(name="Name", value=role.name, inline=False)
        embed.add_field(name="Color", value=str(role.color), inline=False)

        await log_channel.send(embed=embed)

    # ---------------------------------------------------------
    # ROLE UPDATED
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        log_channel = await self.get_server_log_channel(after.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="✏️ Role Updated",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )

        changes = []

        if before.name != after.name:
            changes.append(f"**Name:** `{before.name}` → `{after.name}`")

        if before.color != after.color:
            changes.append(f"**Color:** `{before.color}` → `{after.color}`")

        if before.permissions != after.permissions:
            changes.append("**Permissions changed**")

        if before.position != after.position:
            changes.append(f"**Position:** `{before.position}` → `{after.position}`")

        if not changes:
            return

        embed.add_field(name="Role", value=after.mention, inline=False)
        embed.add_field(name="Changes", value="\n".join(changes), inline=False)

        await log_channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ServerEvents(bot))