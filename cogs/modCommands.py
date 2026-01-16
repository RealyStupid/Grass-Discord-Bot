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

    # roles commands
    #role creation command
    @mods.command(name="createrole", description="Create a new role in the server")
    @staff_only()
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
    @staff_only()
    async def delete_role(self, interaction: discord.Interaction, role: discord.Role):
        try:
            await role.delete()
            await interaction.response.send_message(f"Role '{role.name}' deleted successfully!")
            print(f"Deleted role: {role.name}")
        except Exception as e:
            await interaction.response.send_message(f"Failed to delete role: {e}", ephemeral=True)

    # info command
    @info.command(name="userinfo", description="Get information about a user")
    @staff_only()
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

async def setup(bot):
    await bot.add_cog(Moderation(bot))