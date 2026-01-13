from ast import mod
import discord
from discord.ext import commands
from discord import app_commands

import aiosqlite
import sqlite3

from BotConfig import GUILD_ID

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    #creating a group for moderation commands
    mods = app_commands.Group(name="moderation", description="Moderation commands", guild_ids=[GUILD_ID.id])

    # creating a group for grabbing info
    info = app_commands.Group(name="info", description="this command relates to gaining information about somthing", guild_ids=[GUILD_ID.id])

    # set roles group
    set_role = app_commands.Group(name="set_roles", description="This command sets roles for setting command perms", guild_ids=[GUILD_ID.id])

    # say command
    @mods.command(name="say", description="Send a message to a channel")
    async def say(self, interaction: discord.Interaction, message: str, channel: discord.TextChannel | None = None):
        target = channel or interaction.channel
        await target.send(message)
        await interaction.response.send_message(f"Message sent to {target.mention}", ephemeral=True)
        print(f"Sent message to {target.name}: {message}")

    # ping command
    @mods.command(name="ping", description="Check if the bot is alive by mentioning you")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"{interaction.user.mention}", ephemeral=True)
        print(f"Pinged user: {interaction.user.name}")

    # roles commands
    #role creation command
    @mods.command(name="createrole", description="Create a new role in the server")
    async def createrole(self, interaction: discord.Interaction, role_name: str, color: str = "default"):
        guild = interaction.guild
        try:
            if color.lower() == "default":
                new_role = await guild.create_role(name=role_name)
                print("Created role with default color")
            else:
                new_role = await guild.create_role(name=role_name, color=discord.Color(int(color.strip("#"), 16)))
            await interaction.response.send_message(f"Role '{new_role.name}' created successfully!")
            print(f"Created role: {new_role.name} with color {new_role.color}")
        except Exception as e:
            await interaction.response.send_message(f"Failed to create role: {e}", ephemeral=True)

    # role deletion command
    @mods.command(name="delete_role", description="Delete a role from the server")
    async def delete_role(self, interaction: discord.Interaction, role: discord.Role):
        try:
            await role.delete()
            await interaction.response.send_message(f"Role '{role.name}' deleted successfully!")
            print(f"Deleted role: {role.name}")
        except Exception as e:
            await interaction.response.send_message(f"Failed to delete role: {e}", ephemeral=True)

    #delete role command
    @mods.command(name="deleterole", description="Delete a role from the server")
    async def deleterole(self, interaction: discord.Interaction, role: discord.Role):
        try:
            await role.delete()
            await interaction.response.send_message(f"Role '{role.name}' deleted successfully!")
            print(f"Deleted role: {role.name}")
        except Exception as e:
            await interaction.response.send_message(f"Failed to delete role: {e}", ephemeral=True)

    # info command
    @info.command(name="userinfo", description="Get information about a user")
    async def userinfo(self, interaction: discord.Interaction, user: discord.Member):
        embed = discord.Embed(title="User Information", color=discord.Color.blue())
        embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
        embed.add_field(name="Username", value=f"{user.name}#{user.discriminator}", inline=True)
        embed.add_field(name="User ID", value=user.id, inline=True)
        embed.add_field(name="Account Created", value=user.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
        embed.add_field(name="Joined Server", value=user.joined_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
        roles = ', '.join([role.mention for role in user.roles if role.name != "@everyone"])
        embed.add_field(name="Roles", value=roles if roles else "None", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        print(f"Fetched info for user: {user.name}")

    # server info command
    @info.command(name="serverinfo", description="Get information about the server")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(title="Server Information", color=discord.Color.green())
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.add_field(name="Server Name", value=guild.name, inline=True)
        embed.add_field(name="Server ID", value=guild.id, inline=True)
        embed.add_field(name="Owner", value=f"{guild.owner}", inline=False)
        embed.add_field(name="Created On", value=guild.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
        embed.add_field(name="Member Count", value=guild.member_count, inline=True)
        embed.add_field(name="Roles Count", value=len(guild.roles), inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        print(f"Fetched info for server: {guild.name}")

    # set moderator role command
    @set_role.command(name="moderator", description="Set the moderator role for the server")
    async def set_moderator_role(self, interaction: discord.Interaction, role: discord.Role):
        import json
        guild_id = interaction.guild.id

        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            # Fetch existing roles
            cursor = await db.execute(
                "SELECT Moderator_Roles FROM Mod_Role_Management WHERE guild_id = ?",
                (guild_id,)
            )
            row = await cursor.fetchone()

            # Load existing array or create a new one
            if row is None:
                mod_roles = []
            else:
                mod_roles = json.loads(row[0]) if row[0] else []

            # Add role if not already in list
            if role.id not in mod_roles:
                mod_roles.append(role.id)

            # UPSERT updated array
            await db.execute(
                """
                INSERT INTO Mod_Role_Management (guild_id, Moderator_Roles)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET Moderator_Roles = excluded.Moderator_Roles;
                """,
                (guild_id, json.dumps(mod_roles))
            )

            await db.commit()

        await interaction.response.send_message(
            f"Added **{role.name}** to moderator roles.",
            ephemeral=True
        )

        print(f"[DB] Added mod role {role.name} ({role.id}) to guild {interaction.guild.name}")

    # set admin role command
    @set_role.command(name="admin", description="Set the admin role for the server")
    async def set_admin_role(self, interaction: discord.Interaction, role: discord.Role):
        import json
        guild_id = interaction.guild.id
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            # Fetch existing roles
            cursor = await db.execute(
                "SELECT Admin_Roles FROM Mod_Role_Management WHERE guild_id = ?",
                (guild_id,)
            )
            row = await cursor.fetchone()
            # Load existing array or create a new one
            if row is None:
                admin_roles = []
            else:
                admin_roles = json.loads(row[0]) if row[0] else []
            # Add role if not already in list
            if role.id not in admin_roles:
                admin_roles.append(role.id)
            # UPSERT updated array
            await db.execute(
                """
                INSERT INTO Mod_Role_Management (guild_id, Admin_Roles)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET Admin_Roles = excluded.Admin_Roles;
                """,
                (guild_id, json.dumps(admin_roles))
            )
            await db.commit()
        await interaction.response.send_message(
            f"Added **{role.name}** to admin roles.",
            ephemeral=True
        )
        print(f"[DB] Added admin role {role.name} ({role.id}) to guild {interaction.guild.name}")

    # set muted role command
    @set_role.command(name="muted", description="Set the muted role for the server")
    async def set_muted_role(self, interaction: discord.Interaction, role: discord.Role):
        guild_id = interaction.guild.id
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            # UPSERT muted role
            await db.execute(
                """
                INSERT INTO Mod_Role_Management (guild_id, Muted_Role)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET Muted_Role = excluded.Muted_Role;
                """,
                (guild_id, str(role.id))
            )
            await db.commit()
        await interaction.response.send_message(
            f"Set **{role.name}** as the muted role.",
            ephemeral=True
        )
        print(f"[DB] Set muted role {role.name} ({role.id}) for guild {interaction.guild.name}")

    #remove moderator role command
    @set_role.command(name="remove_moderator", description="Remove a moderator role from the server")
    async def remove_moderator_role(self, interaction: discord.Interaction, role: discord.Role):
        import json
        guild_id = interaction.guild.id
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            # Fetch existing roles
            cursor = await db.execute(
                "SELECT Moderator_Roles FROM Mod_Role_Management WHERE guild_id = ?",
                (guild_id,)
            )
            row = await cursor.fetchone()
            if row is None:
                await interaction.response.send_message(
                    "No moderator roles are set for this server.",
                    ephemeral=True
                )
                return
            mod_roles = json.loads(row[0]) if row[0] else []
            # Remove role if it exists in the list
            if role.id in mod_roles:
                mod_roles.remove(role.id)
            # UPSERT updated array
            await db.execute(
                """
                INSERT INTO Mod_Role_Management (guild_id, Moderator_Roles)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET Moderator_Roles = excluded.Moderator_Roles;
                """,
                (guild_id, json.dumps(mod_roles))
            )
            await db.commit()
        await interaction.response.send_message(
            f"Removed **{role.name}** from moderator roles.",
            ephemeral=True
        )
        print(f"[DB] Removed mod role {role.name} ({role.id}) from guild {interaction.guild.name}")

    #remove admin role command
    @set_role.command(name="remove_admin", description="Remove an admin role from the server")
    async def remove_admin_role(self, interaction: discord.Interaction, role: discord.Role):
        import json
        guild_id = interaction.guild.id
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            # Fetch existing roles
            cursor = await db.execute(
                "SELECT Admin_Roles FROM Mod_Role_Management WHERE guild_id = ?",
                (guild_id,)
            )
            row = await cursor.fetchone()
            if row is None:
                await interaction.response.send_message(
                    "No admin roles are set for this server.",
                    ephemeral=True
                )
                return
            admin_roles = json.loads(row[0]) if row[0] else []
            # Remove role if it exists in the list
            if role.id in admin_roles:
                admin_roles.remove(role.id)
            # UPSERT updated array
            await db.execute(
                """
                INSERT INTO Mod_Role_Management (guild_id, Admin_Roles)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET Admin_Roles = excluded.Admin_Roles;
                """,
                (guild_id, json.dumps(admin_roles))
            )
            await db.commit()
        await interaction.response.send_message(
            f"Removed **{role.name}** from admin roles.",
            ephemeral=True
        )
        print(f"[DB] Removed admin role {role.name} ({role.id}) from guild {interaction.guild.name}")

    # remove muted role command
    @set_role.command(name="remove_muted", description="Remove the muted role from the server")
    async def remove_muted_role(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            # UPSERT muted role to NULL
            await db.execute(
                """
                INSERT INTO Mod_Role_Management (guild_id, Muted_Role)
                VALUES (?, NULL)
                ON CONFLICT(guild_id) DO UPDATE SET Muted_Role = NULL;
                """,
                (guild_id,)
            )
            await db.commit()
        await interaction.response.send_message(
            "Removed the muted role.",
            ephemeral=True
        )
        print(f"[DB] Removed muted role for guild {interaction.guild.name}")

    # wipe roles command
    @set_role.command(name="wipe_roles", description="Wipe all role settings for the server")
    async def wipe_roles(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            await db.execute(
                "DELETE FROM Mod_Role_Management WHERE guild_id = ?",
                (guild_id,)
            )
            await db.commit()
        await interaction.response.send_message(
            "Wiped all role settings for this server.",
            ephemeral=True
        )
        print(f"[DB] Wiped all role settings for guild {interaction.guild.name}")

    # display all roles set command
    @set_role.command(name="display_roles", description="Display all role settings for the server")
    async def display_roles(self, interaction: discord.Interaction):
        import json
        guild_id = interaction.guild.id
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            cursor = await db.execute(
                "SELECT Moderator_Roles, Admin_Roles, Muted_Role FROM Mod_Role_Management WHERE guild_id = ?",
                (guild_id,)
            )
            row = await cursor.fetchone()
            if row is None:
                await interaction.response.send_message(
                    "No role settings are configured for this server.",
                    ephemeral=True
                )
                return
            mod_roles = json.loads(row[0]) if row[0] else []
            admin_roles = json.loads(row[1]) if row[1] else []
            muted_role = row[2]

        mod_roles_mentions = ', '.join([f"<@&{role_id}>" for role_id in mod_roles]) if mod_roles else "None"
        admin_roles_mentions = ', '.join([f"<@&{role_id}>" for role_id in admin_roles]) if admin_roles else "None"
        muted_role_mention = f"<@&{muted_role}>" if muted_role else "None"
        embed = discord.Embed(title="Role Settings", color=discord.Color.purple())
        embed.add_field(name="Moderator Roles", value=mod_roles_mentions, inline=False)
        embed.add_field(name="Admin Roles", value=admin_roles_mentions, inline=False)
        embed.add_field(name="Muted Role", value=muted_role_mention, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        print(f"[DB] Displayed role settings for guild {interaction.guild.name}")


async def setup(bot):
    await bot.add_cog(Moderation(bot))