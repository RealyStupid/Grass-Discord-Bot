import discord
from discord.ext import commands
import aiosqlite
import datetime


class MessageEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------------------------------------------------
    # Helper: Fetch message logging channel from DB
    # ---------------------------------------------------------
    async def get_message_log_channel(self, guild: discord.Guild):
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            async with db.execute(
                "SELECT message_logging_channel FROM logging_channels WHERE guild_id = ?",
                (guild.id,)
            ) as cursor:
                row = await cursor.fetchone()

        if row and row[0]:
            return guild.get_channel(row[0])
        return None

    # ---------------------------------------------------------
    # MESSAGE DELETE
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild:
            return

        log_channel = await self.get_message_log_channel(message.guild)
        if not log_channel:
            return

        # Ignore bot messages
        if message.author.bot:
            return

        embed = discord.Embed(
            title="🗑️ Message Deleted",
            color=discord.Color.red(),
            timestamp=datetime.datetime.utcnow()
        )

        embed.add_field(name="Author", value=f"{message.author} (`{message.author.id}`)", inline=False)
        embed.add_field(name="Channel", value=message.channel.mention, inline=False)

        if message.content:
            embed.add_field(name="Content", value=message.content[:1024], inline=False)
        else:
            embed.add_field(name="Content", value="*(No text content)*", inline=False)

        if message.attachments:
            attachment_urls = "\n".join(a.url for a in message.attachments)
            embed.add_field(name="Attachments", value=attachment_urls, inline=False)

        await log_channel.send(embed=embed)

    # ---------------------------------------------------------
    # MESSAGE EDIT
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not after.guild:
            return

        if before.content == after.content:
            return

        log_channel = await self.get_message_log_channel(after.guild)
        if not log_channel:
            return

        if before.author.bot:
            return

        embed = discord.Embed(
            title="✏️ Message Edited",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )

        embed.add_field(name="Author", value=f"{before.author} (`{before.author.id}`)", inline=False)
        embed.add_field(name="Channel", value=before.channel.mention, inline=False)

        embed.add_field(name="Before", value=before.content[:1024] if before.content else "*(No content)*", inline=False)
        embed.add_field(name="After", value=after.content[:1024] if after.content else "*(No content)*", inline=False)

        await log_channel.send(embed=embed)

    # ---------------------------------------------------------
    # ANTI-TAMPER: Prevent users from sending messages in log channels
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return

        if message.author.bot:
            return

        log_channel = await self.get_message_log_channel(message.guild)
        if not log_channel:
            return

        # If user tries to send a message in the log channel → delete it
        if message.channel.id == log_channel.id:
            try:
                await message.delete()
            except:
                pass


async def setup(bot):
    await bot.add_cog(MessageEvents(bot))