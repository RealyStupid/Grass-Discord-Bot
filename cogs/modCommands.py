import discord
from discord.ext import commands
from discord import app_commands

from BotConfig import GUILD_ID

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    #creating a group for moderation commands
    mods = app_commands.Group(name="moderation", description="Moderation commands", guild_ids=[GUILD_ID.id])

    # creating a group for grabbing info
    info = app_commands.Group(name="info", description="this command relates to gaining information about somthing", guild_ids=[GUILD_ID.id])

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