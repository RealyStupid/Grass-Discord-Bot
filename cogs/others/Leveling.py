import discord
import sqlite3
import aiosqlite
from discord import interactions
from discord.ext import commands
from discord import app_commands

from BotConfig import GUILD_IDS, admin_only, staff_only 

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        async with aiosqlite.connect("Data/Levels.db") as db:
            cursor = await db.execute(
                "SELECT exp, level, multiplier FROM Levels WHERE User_Id = ?",
                (message.author.id,)
            )
            row = await cursor.fetchone()

            # New user
            if row is None:
                await db.execute(
                    "INSERT INTO Levels (User_Id, level, exp, multiplier) VALUES (?, ?, ?, ?)",
                    (message.author.id, 0, 0, 1)
                )
                await db.commit()
                return

            exp, level, multiplier = row
            exp += 10 * multiplier
            level_needed = level * 10

            # Level up
            if exp >= level_needed:
                level += 1
                exp = 0
                await db.execute(
                    "UPDATE Levels SET exp = ?, level = ? WHERE User_Id = ?", (exp, level, message.author.id))
                await db.commit()

                await message.channel.send(f"Congratulations {message.author.mention}, you've leveled up to level {level}!")
                return

            # Normal exp update
            await db.execute("UPDATE Levels SET exp = ?, level = ? WHERE User_Id = ?", (exp, level, message.author.id))
            await db.commit()

    Level = app_commands.Group(
        name="level",
        description="Commands related to your levels",
        guild_ids=GUILD_IDS
    )

    # show levels command
    @Level.command(name="show_levels", description="Display your levels and exp")
    async def showLevels(self, interaction: discord.Interaction, user: discord.Member | None = None):
        target_user = user or interaction.user

        async with aiosqlite.connect("Data/Levels.db") as db:
            cursor = await db.execute("SELECT exp, level, multiplier FROM Levels WHERE User_Id = ?", (target_user.id,))
            row = await cursor.fetchone()

        if row is None:
            await interaction.response.send_message(f"{target_user.mention} has no level data.")
            return

        exp, level, multiplier = row

        embed = discord.Embed(
            title=f"{target_user.name}'s Level Info",
            color=discord.Color.green()
        )
        embed.add_field(name="Level", value=str(level), inline=True)
        embed.add_field(name="Experience", value=str(exp), inline=True)
        embed.add_field(name="Multiplier", value=str(multiplier), inline=True)

        await interaction.response.send_message(embed=embed)

    # reset levels
    @Level.command(name="reset_levels", description="Reset the exp data from a user")
    @staff_only()
    async def resetExp(self, interaction: discord.Interaction, user: discord.Member | None = None):
        target_user = user or interaction.user

        async with aiosqlite.connect("Data/Levels.db") as db:
            await db.execute(
                "UPDATE Levels SET exp = 0, level = 0 WHERE User_Id = ?",
                (target_user.id,)
            )
            await db.commit()

        await interaction.response.send_message(f"{target_user.mention}'s experience has been reset.")

    # set the multiplier
    @Level.command(name="set_multiplier", description="Set your exp multiplier")
    @staff_only()
    async def setMultiplier(self, interaction: discord.Interaction, multiplier: int, user: discord.Member | None = None):
        target_user = user or interaction.user

        if multiplier < 1:
            await interaction.response.send_message("Multiplier must be at least 1.")
            return

        async with aiosqlite.connect("Data/Levels.db") as db:
            await db.execute(
                "UPDATE Levels SET multiplier = ? WHERE User_Id = ?",
                (multiplier, target_user.id)
            )
            await db.commit()

        await interaction.response.send_message(f"{target_user.mention}'s experience multiplier has been set to {multiplier}.")
    
    # leaderboard command
    @Level.command(name="leaderboard", description="Shows a leaderboard with the top 10 most highest levels")
    async def leaderboard(self, Interaction: discord.Interaction):
        
        async with aiosqlite.connect("Data/levels.db") as db:
            # fetch top 10
            async with db.execute("SELECT User_Id, level, exp FROM Levels ORDER BY level DESC, EXP Limit 10") as cursor:
                top_rows = await cursor.fetchall()

            # fetch all users rank for calculations
            async with db.execute("SELECT User_Id FROM Levels ORDER BY level DESC, exp DESC") as cursor:
                all_users = [row[0] for row in await cursor.fetchall()]

        # determain user rank
        if Interaction.user.id in all_users:
            user_rank = all_users.index(Interaction.user.id) + 1
        else:
            user_rank = "UNMARKED"

        # build leaderboard

        description = ""
        position = 1

        for user_id, level, exp in top_rows:
            member = Interaction.guild.get_member(user_id)
            username = member.mention if member else f"<@{user_id}>"

            description += (
                f"**#{position}** - {username} | "
                f"Level **{level}** | EXP **{exp}**\n"
            )
            position += 1;

            embed = discord.Embed(
                title="Level Leaderboard",
                description=description,
                color=discord.Color.gold()
            )

        embed.set_footer(text=f"{Interaction.user}'s Rank: {user_rank}")

        await Interaction.response.send_message(embed=embed, ephemeral=True)

    # wipe all data related to the levels
    @Level.command(name=("wipe"), description="Wipes all EXP data from everyone")
    @admin_only()
    async def wipeData(self, interaction= discord.Interaction):
        async with aiosqlite.connect("Data/levels.db") as db:
            await db.execute("DELETE FROM levels")
            await db.commit()
        
        await interaction.response.send_message("All EXP data has been wiped.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Leveling(bot))