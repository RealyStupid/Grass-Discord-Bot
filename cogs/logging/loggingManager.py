import discord
from discord.ext import commands
from discord import app_commands

import asyncio
import aiosqlite
import json

from BotConfig import GUILD_IDS, staff_only


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


async def get_staff_roles(guild: discord.Guild):
    mod_roles_ids, admin_roles_ids, _ = await get_role_data(guild.id)
    staff_roles = []

    for role in guild.roles:
        if role.id in mod_roles_ids or role.id in admin_roles_ids:
            staff_roles.append(role)

    return staff_roles


class ConfirmCancelView(discord.ui.View):
    def __init__(self, user: discord.User | discord.Member):
        super().__init__(timeout=60)
        self.user = user
        self.value: bool | None = None

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.user.id

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        await interaction.response.defer()


class LoggingSettings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    logChannelSetup = app_commands.Group(
        name="loging-setup",
        description="Commands to setup logging channels",
        guild_ids=GUILD_IDS
    )

    # ---------------------------------------------------------
    # MAIN WIZARD ENTRY
    # ---------------------------------------------------------
    @logChannelSetup.command(name="logging-wizard", description="Start setting up logging channels for you")
    @staff_only()
    async def logging_wizard(self, interaction: discord.Interaction):

        await interaction.response.send_message(
            embed=discord.Embed(
                title="Logging Channel Setup Wizard",
                description=(
                    "This wizard will guide you through setting up logging channels.\n\n"
                    "Auto setup logging channels or manual setup?\n"
                    "Type: auto or manual"
                ),
                color=discord.Color.blue()
            )
        )

        def check(msg: discord.Message):
            return msg.author.id == interaction.user.id and msg.channel == interaction.channel

        try:
            mode_msg = await self.bot.wait_for("message", timeout=60, check=check)
        except asyncio.TimeoutError:
            return await interaction.followup.send("Wizard timed out.")

        mode = mode_msg.content.lower().strip()

        if mode == "auto":
            await self.run_auto_setup(interaction)
        elif mode == "manual":
            await self.run_manual_setup(interaction)
        else:
            await interaction.followup.send("Invalid option. Wizard stopped.")

    # ---------------------------------------------------------
    # AUTO SETUP BRANCH
    # ---------------------------------------------------------
    async def run_auto_setup(self, interaction: discord.Interaction):
        await interaction.followup.send(
            "You selected auto setup. Please provide a name for the logging category."
        )

        def check(msg: discord.Message):
            return msg.author.id == interaction.user.id and msg.channel == interaction.channel

        try:
            name_msg = await self.bot.wait_for("message", timeout=60, check=check)
        except asyncio.TimeoutError:
            return await interaction.followup.send("Wizard timed out.")

        category_name = name_msg.content.strip()
        guild = interaction.guild

        logs_category = await guild.create_category(name=category_name)

        channel_specs = [
            ("main-logs", "main_logging_channel"),
            ("member-logs", "member_logging_channel"),
            ("server-logs", "server_logging_channel"),
            ("voice-logs", "voice_logging_channel"),
            ("message-logs", "message_logging_channel"),
            ("join-leave-logs", "join_leave_logging_channel")
        ]

        overwrites = {}

        overwrites[guild.default_role] = discord.PermissionOverwrite(
            view_channel=False,
            send_messages=False,
            manage_messages=False,
            manage_channels=False
        )

        overwrites[guild.me] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_messages=True,
            manage_channels=True
        )

        staff_roles = await get_staff_roles(guild)
        for role in staff_roles:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=False,
                manage_messages=False,
                manage_channels=False
            )

        created_channels: dict[str, int] = {}
        for channel_name, db_column in channel_specs:
            ch = await guild.create_text_channel(
                name=channel_name,
                category=logs_category,
                overwrites=overwrites
            )
            created_channels[db_column] = ch.id

        preview_embed = discord.Embed(
            title="Auto Logging Channel Setup Preview",
            description="Review the created category and channels before confirming.",
            color=discord.Color.gold()
        )

        preview_embed.add_field(
            name="Category",
            value=logs_category.name,
            inline=False
        )

        for channel_name, db_column in channel_specs:
            cid = created_channels[db_column]
            preview_embed.add_field(
                name=db_column,
                value=f"{channel_name} → <#{cid}>",
                inline=False
            )

        view = ConfirmCancelView(interaction.user)
        await interaction.followup.send(embed=preview_embed, view=view)

        timeout = await view.wait()
        if timeout or view.value is None:
            return await interaction.followup.send("Wizard timed out.")

        if view.value is False:
            return await interaction.followup.send(
                "Wizard cancelled. Channels remain created but not saved to DB."
            )

        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            await db.execute("""
                INSERT INTO logging_channels (
                    guild_id, main_logging_channel, member_logging_channel,
                    server_logging_channel, voice_logging_channel,
                    message_logging_channel, join_leave_logging_channel
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    main_logging_channel = excluded.main_logging_channel,
                    member_logging_channel = excluded.member_logging_channel,
                    server_logging_channel = excluded.server_logging_channel,
                    voice_logging_channel = excluded.voice_logging_channel,
                    message_logging_channel = excluded.message_logging_channel,
                    join_leave_logging_channel = excluded.join_leave_logging_channel
            """, (
                interaction.guild.id,
                created_channels.get("main_logging_channel"),
                created_channels.get("member_logging_channel"),
                created_channels.get("server_logging_channel"),
                created_channels.get("voice_logging_channel"),
                created_channels.get("message_logging_channel"),
                created_channels.get("join_leave_logging_channel")
            ))
            await db.commit()

        await interaction.followup.send(
            "Auto logging channels have been set and saved."
        )

    # ---------------------------------------------------------
    # MANUAL SETUP BRANCH
    # ---------------------------------------------------------
    async def run_manual_setup(self, interaction: discord.Interaction):
        await interaction.followup.send(
            "You selected manual setup. We will now configure each logging channel."
        )

        steps = [
            ("main_logging_channel", "Main Logging Channel"),
            ("member_logging_channel", "Member Logging Channel"),
            ("server_logging_channel", "Server Logging Channel"),
            ("voice_logging_channel", "Voice Logging Channel"),
            ("message_logging_channel", "Message Logging Channel"),
            ("join_leave_logging_channel", "Join/Leave Logging Channel")
        ]

        results: dict[str, int | None] = {}

        def check(msg: discord.Message):
            return msg.author.id == interaction.user.id and msg.channel == interaction.channel

        for db_column, label in steps:
            await interaction.followup.send(
                f"Please mention the {label}, or type 'skip' to leave it unset."
            )

            try:
                msg = await self.bot.wait_for("message", timeout=60, check=check)
            except asyncio.TimeoutError:
                return await interaction.followup.send("Wizard timed out.")

            content = msg.content.lower().strip()

            if content == "cancel":
                return await interaction.followup.send("Wizard cancelled.")

            if content == "skip":
                results[db_column] = None
                continue

            channel = None
            if msg.channel_mentions:
                channel = msg.channel_mentions[0]
            else:
                try:
                    channel = interaction.guild.get_channel(int(msg.content))
                except:
                    channel = None

            if channel is None:
                return await interaction.followup.send("Invalid channel. Wizard stopped.")

            results[db_column] = channel.id

        preview_embed = discord.Embed(
            title="Manual Logging Channel Setup Preview",
            description="Review your selections before confirming.",
            color=discord.Color.gold()
        )

        for col, label in steps:
            cid = results.get(col)
            preview_embed.add_field(
                name=label,
                value=f"<#{cid}>" if cid else "Not set",
                inline=False
            )

        view = ConfirmCancelView(interaction.user)
        await interaction.followup.send(embed=preview_embed, view=view)

        timeout = await view.wait()
        if timeout or view.value is None:
            return await interaction.followup.send("Wizard timed out.")

        if view.value is False:
            return await interaction.followup.send("Wizard cancelled.")

        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            await db.execute("""
                INSERT INTO logging_channels (
                    guild_id, main_logging_channel, member_logging_channel,
                    server_logging_channel, voice_logging_channel,
                    message_logging_channel, join_leave_logging_channel
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    main_logging_channel = excluded.main_logging_channel,
                    member_logging_channel = excluded.member_logging_channel,
                    server_logging_channel = excluded.server_logging_channel,
                    voice_logging_channel = excluded.voice_logging_channel,
                    message_logging_channel = excluded.message_logging_channel,
                    join_leave_logging_channel = excluded.join_leave_logging_channel
            """, (
                interaction.guild.id,
                results.get("main_logging_channel"),
                results.get("member_logging_channel"),
                results.get("server_logging_channel"),
                results.get("voice_logging_channel"),
                results.get("message_logging_channel"),
                results.get("join_leave_logging_channel")
            ))
            await db.commit()

        await interaction.followup.send(
            "Logging channels updated successfully."
        )

    # SHOW COMMAND
    @logChannelSetup.command(name="show", description="Show current logging channel settings")
    @staff_only()
    async def show_logging(self, interaction: discord.Interaction):
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            async with db.execute("SELECT * FROM logging_channels WHERE guild_id = ?", (interaction.guild.id,)) as cursor:
                row = await cursor.fetchone()

        if row is None:
            return await interaction.response.send_message("No logging settings found.")

        (_, main, member, server, voice, message, join_leave) = row

        embed = discord.Embed(
            title="Logging Channel Settings",
            color=discord.Color.blue()
        )

        embed.add_field(name="Main Logging", value=f"<#{main}>" if main else "Not set", inline=False)
        embed.add_field(name="Member Logging", value=f"<#{member}>" if member else "Not set", inline=False)
        embed.add_field(name="Server Logging", value=f"<#{server}>" if server else "Not set", inline=False)
        embed.add_field(name="Voice Logging", value=f"<#{voice}>" if voice else "Not set", inline=False)
        embed.add_field(name="Message Logging", value=f"<#{message}>" if message else "Not set", inline=False)
        embed.add_field(name="Join/Leave Logging", value=f"<#{join_leave}>" if join_leave else "Not set", inline=False)

        await interaction.response.send_message(embed=embed)

    # RESET COMMAND
    @logChannelSetup.command(name="reset", description="Reset all logging channel settings")
    @staff_only()
    async def reset_logging(self, interaction: discord.Interaction):
        guild = interaction.guild

        # Fetch all channel IDs from DB
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            async with db.execute(
                "SELECT main_logging_channel, member_logging_channel, server_logging_channel, voice_logging_channel, message_logging_channel, join_leave_logging_channel FROM logging_channels WHERE guild_id = ?",
                (guild.id,)
            ) as cursor:
                row = await cursor.fetchone()

        if row:
            channel_ids = list(row)

            # Delete channels
            for cid in channel_ids:
                if cid:
                    channel = guild.get_channel(cid)
                    if channel:
                        try:
                            await channel.delete(reason="Logging wipeed")
                        except:
                            pass

        # Clear DB row
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            await db.execute("DELETE FROM logging_channels WHERE guild_id = ?", (guild.id,))
            await db.commit()

        await interaction.response.send_message(
            "Logging setup has been fully wiped. All logging channels and database entries have been removed."
        )

async def setup(bot):
    await bot.add_cog(LoggingSettings(bot))