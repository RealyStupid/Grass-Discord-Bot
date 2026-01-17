import discord
from discord.ext import commands
import aiosqlite
import datetime


class VoiceEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------------------------------------------------
    # DB HELPER
    # ---------------------------------------------------------
    async def get_voice_log_channel(self, guild: discord.Guild):
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            async with db.execute(
                "SELECT voice_logging_channel FROM logging_channels WHERE guild_id = ?",
                (guild.id,)
            ) as cursor:
                row = await cursor.fetchone()
        return guild.get_channel(row[0]) if row and row[0] else None

    # ---------------------------------------------------------
    # VOICE STATE UPDATE
    # ---------------------------------------------------------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        log_channel = await self.get_voice_log_channel(member.guild)
        if not log_channel:
            return

        embed = discord.Embed(
            color=discord.Color.blue(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_author(
            name=f"{member} ({member.id})",
            icon_url=member.avatar.url if member.avatar else member.default_avatar.url
        )

        # -----------------------------------------------------
        # JOINED A VOICE CHANNEL
        # -----------------------------------------------------
        if before.channel is None and after.channel is not None:
            embed.title = "Joined Voice Channel"
            embed.add_field(name="Channel", value=after.channel.mention, inline=False)
            return await log_channel.send(embed=embed)

        # -----------------------------------------------------
        # LEFT A VOICE CHANNEL
        # -----------------------------------------------------
        if before.channel is not None and after.channel is None:
            embed.title = "Left Voice Channel"
            embed.add_field(name="Channel", value=before.channel.mention, inline=False)
            return await log_channel.send(embed=embed)

        # -----------------------------------------------------
        # SWITCHED CHANNELS
        # -----------------------------------------------------
        if before.channel != after.channel:
            embed.title = "Switched Voice Channels"
            embed.add_field(name="Before", value=before.channel.mention if before.channel else "None", inline=False)
            embed.add_field(name="After", value=after.channel.mention if after.channel else "None", inline=False)
            return await log_channel.send(embed=embed)

        # -----------------------------------------------------
        # MUTE / UNMUTE
        # -----------------------------------------------------
        if before.self_mute != after.self_mute:
            embed.title = "Mute Status Changed"
            embed.add_field(name="Muted", value=str(after.self_mute), inline=False)
            return await log_channel.send(embed=embed)

        # -----------------------------------------------------
        # DEAFEN / UNDEAFEN
        # -----------------------------------------------------
        if before.self_deaf != after.self_deaf:
            embed.title = "Deafen Status Changed"
            embed.add_field(name="Deafened", value=str(after.self_deaf), inline=False)
            return await log_channel.send(embed=embed)

        # -----------------------------------------------------
        # STREAMING
        # -----------------------------------------------------
        if before.self_stream != after.self_stream:
            embed.title = "Streaming Status Changed"
            embed.add_field(name="Streaming", value=str(after.self_stream), inline=False)
            return await log_channel.send(embed=embed)

        # -----------------------------------------------------
        # SCREEN SHARE (Go Live)
        # -----------------------------------------------------
        if before.self_video != after.self_video:
            embed.title = "Screen Share Status Changed"
            embed.add_field(name="Screen Sharing", value=str(after.self_video), inline=False)
            return await log_channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(VoiceEvents(bot))