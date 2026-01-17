import discord
from discord.ext import commands
from discord import app_commands

import aiosqlite
import sqlite3

from BotConfig import GUILD_ID, staff_only

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    #creating a group for moderation commands
    mods = app_commands.Group(name="moderation", description="Moderation commands", guild_ids=[GUILD_ID.id])

    # creating a group for grabbing info
    info = app_commands.Group(name="info", description="this command relates to gaining information about somthing", guild_ids=[GUILD_ID.id])

    # say command
    @mods.command(name="say", description="Send a message to a channel")
    @staff_only()
    async def say(self, interaction: discord.Interaction, message: str, channel: discord.TextChannel | None = None):
        target = channel or interaction.channel
        await target.send(message)
        await interaction.response.send_message(f"Message sent to {target.mention}", ephemeral=True)
        print(f"Sent message to {target.name}: {message}")

    # ping command
    @mods.command(name="ping", description="Check if the bot is alive by mentioning you")
    @staff_only()
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"{interaction.user.mention}", ephemeral=True)
        print(f"Pinged user: {interaction.user.name}")

    # purge command
    @mods.command(
        name="purge",
        description="Delete messages with optional filters (user, search length)."
    )
    @app_commands.describe(
        user="Only delete messages from this user",
        search="How many recent messages to search through"
    )
    @staff_only()
    async def purge(
        self,
        interaction: discord.Interaction,
        user: discord.User | None = None,
        search: int | None = None
    ):
        await interaction.response.defer(ephemeral=True)

        # Default search depth if none provided
        search_depth = search if search is not None else 10

        # Safety check
        if search_depth < 1:
            return await interaction.followup.send("Search length must be at least 1.")

        # CASE 1: User filter only
        if user and not search:
            deleted = await interaction.channel.purge(
                limit=None,  # default search depth for user-only purge
                check=lambda m: m.author.id == user.id
            )
            return await interaction.followup.send(
                f"Deleted {len(deleted)} messages from **{user}**."
            )

        # CASE 2: Search length only
        if search and not user:
            deleted = await interaction.channel.purge(limit=search_depth)
            return await interaction.followup.send(
                f"Deleted {len(deleted)} messages."
            )

        # CASE 3: Both user + search length
        if user and search:
            deleted = await interaction.channel.purge(
                limit=search_depth,
                check=lambda m: m.author.id == user.id
            )
            return await interaction.followup.send(
                f"Deleted {len(deleted)} messages from **{user}** "
                f"within the last {search_depth} messages."
            )

        # CASE 4: Neither provided → default purge 10
        deleted = await interaction.channel.purge(limit=None)
        await interaction.followup.send(f"Deleted {len(deleted)} messages.")

async def setup(bot):
    await bot.add_cog(Moderation(bot))