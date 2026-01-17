import discord
from discord.ext import commands
import aiosqlite
import datetime


class MemberEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------------------------------------------------
    # DB HELPERS
    # ---------------------------------------------------------
    async def get_member_log_channel(self, guild: discord.Guild):
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            async with db.execute(
                "SELECT member_logging_channel FROM logging_channels WHERE guild_id = ?",
                (guild.id,)
            ) as cursor:
                row = await cursor.fetchone()
        return guild.get_channel(row[0]) if row and row[0] else None

    async def get_join_leave_log_channel(self, guild: discord.Guild):
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            async with db.execute(
                "SELECT join_leave_logging_channel FROM logging_channels WHERE guild_id = ?",
                (guild.id,)
            ) as cursor:
                row = await cursor.fetchone()
        return guild.get_channel(row[0]) if row and row[0] else None

    # ---------------------------------------------------------
    # MEMBER JOIN
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        log_channel = await self.get_join_leave_log_channel(member.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="👋 Member Joined",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )

        embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
        embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)

        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)

        await log_channel.send(embed=embed)

    # ---------------------------------------------------------
    # MEMBER LEAVE
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        log_channel = await self.get_join_leave_log_channel(member.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            title="🚪 Member Left",
            color=discord.Color.red(),
            timestamp=datetime.datetime.utcnow()
        )

        embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)

        await log_channel.send(embed=embed)

    # ---------------------------------------------------------
    # MEMBER UPDATE (nickname, roles, avatar)
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        log_channel = await self.get_member_log_channel(after.guild)
        if not log_channel:
            return

        # Nickname change
        if before.nick != after.nick:
            embed = discord.Embed(
                title="📝 Nickname Changed",
                color=discord.Color.orange(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="User", value=f"{after} (`{after.id}`)", inline=False)
            embed.add_field(name="Before", value=before.nick or "None", inline=True)
            embed.add_field(name="After", value=after.nick or "None", inline=True)
            await log_channel.send(embed=embed)

        # Avatar change
        if before.avatar != after.avatar:
            embed = discord.Embed(
                title="🖼️ Avatar Changed",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="User", value=f"{after} (`{after.id}`)", inline=False)
            embed.set_thumbnail(url=after.avatar.url if after.avatar else after.default_avatar.url)
            await log_channel.send(embed=embed)

        # Role changes
        before_roles = set(before.roles)
        after_roles = set(after.roles)

        gained = after_roles - before_roles
        lost = before_roles - after_roles

        if gained or lost:
            embed = discord.Embed(
                title="🎭 Role Updated",
                color=discord.Color.purple(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="User", value=f"{after} (`{after.id}`)", inline=False)

            if gained:
                embed.add_field(
                    name="Roles Added",
                    value="\n".join([r.mention for r in gained]),
                    inline=False
                )

            if lost:
                embed.add_field(
                    name="Roles Removed",
                    value="\n".join([r.mention for r in lost]),
                    inline=False
                )

            await log_channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(MemberEvents(bot))