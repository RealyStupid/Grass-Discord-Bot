import discord
from discord.ext import commands
from discord import app_commands

from BotConfig import GUILD_ID, staff_only

import aiosqlite
import sqlite3

class LoggingSettings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    logChannelSetup = app_commands.Group(name="logchannelsetup", description="Commands to setup logging channels", guild_ids=[GUILD_ID.id])

    @logChannelSetup.command(name="logging-wizard", description="Start setting up logging channels for you")
    @staff_only()
    async def logging_wizard(self, interaction: discord.Interaction):
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            async with db.execute("SELECT * FROM logging_channels WHERE guild_id = ?", (interaction.guild.id,)) as cursor:
                row = cursor.fetchone()

            if row is None:
                print(f"No logging settings found for guild {interaction.guild.id}, initializing defaults.")
            else:
                print(f"Found existing logging settings for guild {interaction.guild.id}: {row}")

        embed = discord.Embed(
            title="Logging Channel Setup Wizard",
            description=(
                "This wizard will guide you through setting up logging channels for various events.\n\n"
                "Please follow the prompts to select channels for each logging category."
            ),
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(LoggingSettings(bot))