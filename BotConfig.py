import discord
import sqlite3
import aiosqlite
import json
from discord import app_commands
from discord.ext import commands

# bot constants
GUILD_ID = discord.Object(id=1460487931461636240)

BOT_TOKEN = 'MTQ1ODk0MzU2ODE1MTQ0OTY3Mw.GHT4i4.4-X7l39NQCbY0IbqWH59CMPLDS5VINhmktgBRk'

INTENTS = discord.Intents.default()
INTENTS.message_content = True

APPLICATION_ID = 1458943568151449673

# ============================================================
# DATABASE HELPERS
# ============================================================

async def get_role_data(guild_id: int):
    async with aiosqlite.connect("Data/Moderation_settings.db") as db:
        cursor = await db.execute(
            "SELECT Moderator_Roles, Admin_Roles, Muted_Role FROM Mod_Role_Management WHERE guild_id = ?",
            (guild_id,)
        )
        row = await cursor.fetchone()

    if not row:
        return [], [], None

    mod_roles = json.loads(row[0]) if row[0] else []
    admin_roles = json.loads(row[1]) if row[1] else []
    muted_role = row[2]

    return mod_roles, admin_roles, muted_role

# ============================================================
# PERMISSION CHECKS WITH FALLBACK
# ============================================================

async def user_has_mod(interaction: discord.Interaction) -> bool:
    guild_id = interaction.guild.id
    user_roles = [r.id for r in interaction.user.roles]

    mod_roles, admin_roles, _ = await get_role_data(guild_id)

    # Fallback: if no mod roles set, allow admins
    if not mod_roles:
        return any(r.id in admin_roles for r in interaction.user.roles)

    return any(r in user_roles for r in mod_roles)


async def user_has_admin(interaction: discord.Interaction) -> bool:
    guild_id = interaction.guild.id
    user_roles = [r.id for r in interaction.user.roles]

    _, admin_roles, _ = await get_role_data(guild_id)

    # Fallback: if no admin roles set, allow server owner
    if not admin_roles:
        return interaction.user == interaction.guild.owner

    return any(r in user_roles for r in admin_roles)


async def user_has_staff(interaction: discord.Interaction) -> bool:
    return (
        await user_has_admin(interaction)
        or await user_has_mod(interaction)
        or interaction.user.id == interaction.client.owner_id
    )


# ============================================================
# DECORATORS
# ============================================================

def mod_only():
    def decorator(func):
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            if not await user_has_mod(interaction):
                await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
                return
            return await func(self, interaction, *args, **kwargs)
        return wrapper
    return decorator


def admin_only():
    def decorator(func):
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            if not await user_has_admin(interaction):
                await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
                return
            return await func(self, interaction, *args, **kwargs)
        return wrapper
    return decorator

def staff_only():
    def decorator(func):
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            if not await user_has_staff(interaction):
                await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
                return
            return await func(self, interaction, *args, **kwargs)
        return wrapper
    return decorator
