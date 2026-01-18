import discord
from discord import app_commands
from discord.ext import commands
from BotConfig import GUILD_IDS, admin_only, staff_only
import asyncio
import aiosqlite
import json

# ============================================================
# CONFIRM / CANCEL BUTTON VIEW
# ============================================================

class RoleConfirmView(discord.ui.View):
    def __init__(self, user_id: int, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.value: bool | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()
        #await interaction.response.send_message("Confirmed. Saving...", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        await interaction.response.send_message("Cancelled. No changes saved.", ephemeral=True)


# ============================================================
# MAIN COG (ONLY MODERATOR ROLE COMMAND SHOWN)
# ============================================================

class RoleSetter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    set_role = app_commands.Group(
        name="set-role",
        description="Configure moderation roles",
        guild_ids=GUILD_IDS
    )

    # Ensure DB table exists
    async def ensure_table(self):
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            await db.execute(
                """CREATE TABLE IF NOT EXISTS Mod_Role_Management (
                    guild_id INTEGER PRIMARY KEY,
                    Moderator_Roles TEXT,
                    Admin_Roles TEXT,
                    Muted_Role TEXT
                )"""
            )
            await db.commit()

    # SET MODERATOR ROLES
    @set_role.command(name="moderator", description="Interactively set moderator roles")
    @admin_only()
    async def set_moderator_role(self, interaction: discord.Interaction):
        await self.ensure_table()
        guild_id = interaction.guild.id

        # Fetch existing moderator roles
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            cursor = await db.execute(
                "SELECT Moderator_Roles FROM Mod_Role_Management WHERE guild_id = ?",
                (guild_id,)
            )
            row = await cursor.fetchone()
            current_roles = json.loads(row[0]) if (row and row[0]) else []

        await interaction.response.send_message(
            "**Moderator Role Setup**\n"
            "Mention roles one at a time.\n"
            "Type **done** when finished or **cancel** to stop.",
            ephemeral=False
        )

        collected_new = []

        def check(msg: discord.Message):
            return msg.author.id == interaction.user.id and msg.channel.id == interaction.channel.id

        try:
            while True:
                msg = await self.bot.wait_for("message", check=check, timeout=120)
                content = msg.content.lower().strip()

                if content == "cancel":
                    await interaction.followup.send("❌ Moderator role setup cancelled.")
                    return

                if content == "done":
                    break

                if not msg.role_mentions:
                    await interaction.followup.send("Please mention a **role**.")
                    continue

                role = msg.role_mentions[0]

                if role.id in current_roles or role.id in collected_new:
                    await interaction.followup.send(f"{role.mention} is already included.")
                    continue

                collected_new.append(role.id)
                await interaction.followup.send(f"Added {role.mention}")

        except asyncio.TimeoutError:
            timeout_embed = discord.Embed(
                title="Timeout",
                description="You took too long. Run the command again.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=timeout_embed)
            return

        final_roles = list({*current_roles, *collected_new})

        if not final_roles:
            await interaction.followup.send("No roles to save.")
            return

        # Preview embed
        preview = discord.Embed(
            title="Moderator Roles Preview",
            description="These roles will be saved:",
            color=discord.Color.blurple()
        )
        for r in final_roles:
            preview.add_field(name="Role", value=f"<@&{r}>", inline=False)

        view = RoleConfirmView(interaction.user.id)
        await interaction.followup.send(embed=preview, view=view)

        await view.wait()

        if view.value is None:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="Timeout",
                    description="You didn't confirm in time.",
                    color=discord.Color.red()
                )
            )
            return

        if view.value is False:
            await interaction.followup.send("Cancelled.")
            return

        # Save to DB
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            await db.execute(
                """
                INSERT INTO Mod_Role_Management (guild_id, Moderator_Roles)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET Moderator_Roles = excluded.Moderator_Roles;
                """,
                (guild_id, json.dumps(final_roles))
            )
            await db.commit()

        await interaction.followup.send("Moderator roles saved.")

    # SET ADMIN ROLES
    @set_role.command(name="admin", description="Interactively set admin roles")
    @admin_only()
    async def set_admin_role(self, interaction: discord.Interaction):
        await self.ensure_table()
        guild_id = interaction.guild.id

        # Fetch existing admin roles
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            cursor = await db.execute(
                "SELECT Admin_Roles FROM Mod_Role_Management WHERE guild_id = ?",
                (guild_id,)
            )
            row = await cursor.fetchone()
            current_roles = json.loads(row[0]) if (row and row[0]) else []

        await interaction.response.send_message(
            "Admin Role Setup\n"
            "Mention roles one at a time.\n"
            "Type 'done' when finished or 'cancel' to stop.",
            ephemeral=False
        )

        collected_new = []

        def check(msg: discord.Message):
            return msg.author.id == interaction.user.id and msg.channel.id == interaction.channel.id

        try:
            while True:
                msg = await self.bot.wait_for("message", check=check, timeout=120)
                content = msg.content.lower().strip()

                if content == "cancel":
                    await interaction.followup.send("Admin role setup cancelled.")
                    return

                if content == "done":
                    break

                if not msg.role_mentions:
                    await interaction.followup.send("Please mention a role.")
                    continue

                role = msg.role_mentions[0]

                if role.id in current_roles or role.id in collected_new:
                    await interaction.followup.send(f"{role.mention} is already included.")
                    continue

                collected_new.append(role.id)
                await interaction.followup.send(f"Added {role.mention}")

        except asyncio.TimeoutError:
            timeout_embed = discord.Embed(
                title="Timeout",
                description="You took too long. Run the command again.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=timeout_embed)
            return

        final_roles = list({*current_roles, *collected_new})

        if not final_roles:
            await interaction.followup.send("No roles to save.")
            return

        # Preview embed
        preview = discord.Embed(
            title="Admin Roles Preview",
            description="These roles will be saved:",
            color=discord.Color.orange()
        )
        for r in final_roles:
            preview.add_field(name="Role", value=f"<@&{r}>", inline=False)

        view = RoleConfirmView(interaction.user.id)
        await interaction.followup.send(embed=preview, view=view)

        await view.wait()

        if view.value is None:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="Timeout",
                    description="You did not confirm in time.",
                    color=discord.Color.red()
                )
            )
            return

        if view.value is False:
            await interaction.followup.send("Cancelled. No changes were saved.")
            return

        # Save to DB
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            await db.execute(
                """
                INSERT INTO Mod_Role_Management (guild_id, Admin_Roles)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET Admin_Roles = excluded.Admin_Roles;
                """,
                (guild_id, json.dumps(final_roles))
            )
            await db.commit()

        await interaction.followup.send("Admin roles saved.")

    # SET MUTED ROLE (simple one-shot command)
    @set_role.command(name="muted", description="Set the muted role for the server")
    @admin_only()
    async def set_muted_role(self, interaction: discord.Interaction, role: discord.Role):
        await self.ensure_table()
        guild_id = interaction.guild.id

        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
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
            f"Muted role set to {role.mention}.",
            ephemeral=True
        )

    # REMOVE MODERATOR ROLE
    @set_role.command(name="remove_moderator", description="Remove a moderator role from the server")
    @admin_only()
    async def remove_moderator_role(self, interaction: discord.Interaction):
        await self.ensure_table()
        guild_id = interaction.guild.id

        # Fetch roles
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            cursor = await db.execute(
                "SELECT Moderator_Roles FROM Mod_Role_Management WHERE guild_id = ?",
                (guild_id,)
            )
            row = await cursor.fetchone()

        if not row or not row[0]:
            await interaction.response.send_message("No moderator roles are set for this server.", ephemeral=True)
            return

        roles = json.loads(row[0])

        # Show list
        embed = discord.Embed(
            title="Moderator Roles",
            description="These roles are currently set as moderator roles.\n"
                        "Mention the role you want to remove, or type 'cancel' to stop.",
            color=discord.Color.blurple()
        )

        for r in roles:
            embed.add_field(name="Role", value=f"<@&{r}>", inline=False)

        await interaction.response.send_message(embed=embed)

        # Wait for user message
        def check(msg: discord.Message):
            return msg.author.id == interaction.user.id and msg.channel.id == interaction.channel.id

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            await interaction.followup.send("Timed out. Run the command again.", ephemeral=True)
            return

        if msg.content.lower().strip() == "cancel":
            await interaction.followup.send("Operation cancelled.", ephemeral=True)
            return

        if not msg.role_mentions:
            await interaction.followup.send("You must mention a role.", ephemeral=True)
            return

        role = msg.role_mentions[0]

        if role.id not in roles:
            await interaction.followup.send("That role is not in the moderator list.", ephemeral=True)
            return

        roles.remove(role.id)

        # Save
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            await db.execute(
                """
                INSERT INTO Mod_Role_Management (guild_id, Moderator_Roles)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET Moderator_Roles = excluded.Moderator_Roles;
                """,
                (guild_id, json.dumps(roles))
            )
            await db.commit()

        await interaction.followup.send(f"Removed {role.mention} from moderator roles.", ephemeral=True)

    # REMOVE ADMIN ROLE
    @set_role.command(name="remove_admin", description="Remove an admin role from the server")
    @admin_only()
    async def remove_admin_role(self, interaction: discord.Interaction):
        await self.ensure_table()
        guild_id = interaction.guild.id

        # Fetch roles
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            cursor = await db.execute(
                "SELECT Admin_Roles FROM Mod_Role_Management WHERE guild_id = ?",
                (guild_id,)
            )
            row = await cursor.fetchone()

        if not row or not row[0]:
            await interaction.response.send_message("No admin roles are set for this server.", ephemeral=True)
            return

        roles = json.loads(row[0])

        # Show list
        embed = discord.Embed(
            title="Admin Roles",
            description="These roles are currently set as admin roles.\n"
                        "Mention the role you want to remove, or type 'cancel' to stop.",
            color=discord.Color.orange()
        )

        for r in roles:
            embed.add_field(name="Role", value=f"<@&{r}>", inline=False)

        await interaction.response.send_message(embed=embed)

        # Wait for user message
        def check(msg: discord.Message):
            return msg.author.id == interaction.user.id and msg.channel.id == interaction.channel.id

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            await interaction.followup.send("Timed out. Run the command again.", ephemeral=True)
            return

        if msg.content.lower().strip() == "cancel":
            await interaction.followup.send("Operation cancelled.", ephemeral=True)
            return

        if not msg.role_mentions:
            await interaction.followup.send("You must mention a role.", ephemeral=True)
            return

        role = msg.role_mentions[0]

        if role.id not in roles:
            await interaction.followup.send("That role is not in the admin list.", ephemeral=True)
            return

        roles.remove(role.id)

        # Save
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            await db.execute(
                """
                INSERT INTO Mod_Role_Management (guild_id, Admin_Roles)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET Admin_Roles = excluded.Admin_Roles;
                """,
                (guild_id, json.dumps(roles))
            )
            await db.commit()

        await interaction.followup.send(f"Removed {role.mention} from admin roles.", ephemeral=True)

    # REMOVE MUTED ROLE
    @set_role.command(name="remove_muted", description="Remove the muted role from the server")
    @admin_only()
    async def remove_muted_role(self, interaction: discord.Interaction):
        await self.ensure_table()
        guild_id = interaction.guild.id

        # Fetch muted role
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            cursor = await db.execute(
                "SELECT Muted_Role FROM Mod_Role_Management WHERE guild_id = ?",
                (guild_id,)
            )
            row = await cursor.fetchone()

        if not row or not row[0]:
            await interaction.response.send_message("No muted role is set for this server.", ephemeral=True)
            return

        muted_role = row[0]

        embed = discord.Embed(
            title="Muted Role",
            description=f"Current muted role: <@&{muted_role}>\n"
                        "Type 'cancel' to stop, or type 'remove' to confirm removal.",
            color=discord.Color.red()
        )

        await interaction.response.send_message(embed=embed)

        # Wait for user message
        def check(msg: discord.Message):
            return msg.author.id == interaction.user.id and msg.channel.id == interaction.channel.id

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            await interaction.followup.send("Timed out. Run the command again.", ephemeral=True)
            return

        content = msg.content.lower().strip()

        if content == "cancel":
            await interaction.followup.send("Operation cancelled.", ephemeral=True)
            return

        if content != "remove":
            await interaction.followup.send("Invalid response. Type 'remove' or 'cancel'.", ephemeral=True)
            return

        # Remove muted role
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            await db.execute(
                """
                INSERT INTO Mod_Role_Management (guild_id, Muted_Role)
                VALUES (?, NULL)
                ON CONFLICT(guild_id) DO UPDATE SET Muted_Role = NULL;
                """,
                (guild_id,)
            )
            await db.commit()

        await interaction.followup.send("Muted role removed.", ephemeral=True)

    # WIPE ALL ROLES
    @set_role.command(name="wipe_roles", description="Wipe all role settings for the server")
    @admin_only()
    async def wipe_roles(self, interaction: discord.Interaction):
        await self.ensure_table()
        guild_id = interaction.guild.id

        embed = discord.Embed(
            title="Wipe All Role Settings",
            description=(
                "This will remove all moderator roles, admin roles, and the muted role.\n"
                "Type 'confirm' to proceed or 'cancel' to stop."
            ),
            color=discord.Color.red()
        )

        await interaction.response.send_message(embed=embed)

        # Wait for user message
        def check(msg: discord.Message):
            return msg.author.id == interaction.user.id and msg.channel.id == interaction.channel.id

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            await interaction.followup.send("Timed out. Run the command again.", ephemeral=True)
            return

        content = msg.content.lower().strip()

        if content == "cancel":
            await interaction.followup.send("Operation cancelled.", ephemeral=True)
            return

        if content != "confirm":
            await interaction.followup.send("Invalid response. Type 'confirm' or 'cancel'.", ephemeral=True)
            return

        # Perform wipe
        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            await db.execute("DELETE FROM Mod_Role_Management WHERE guild_id = ?", (guild_id,))
            await db.commit()

        await interaction.followup.send("All role settings have been wiped.", ephemeral=True)

    # DISPLAY ROLES
    @set_role.command(name="display_roles", description="Display all role settings for the server")
    @staff_only()
    async def display_roles(self, interaction: discord.Interaction):
        await self.ensure_table()
        guild_id = interaction.guild.id

        async with aiosqlite.connect("Data/Moderation_settings.db") as db:
            cursor = await db.execute(
                "SELECT Moderator_Roles, Admin_Roles, Muted_Role FROM Mod_Role_Management WHERE guild_id = ?",
                (guild_id,)
            )
            row = await cursor.fetchone()

        if not row:
            await interaction.response.send_message(
                "No role settings are configured for this server."
            )
            return

        mod_roles = json.loads(row[0]) if row[0] else []
        admin_roles = json.loads(row[1]) if row[1] else []
        muted_role = row[2]

        embed = discord.Embed(
            title="Role Settings",
            color=discord.Color.purple()
        )

        embed.add_field(
            name="Moderator Roles",
            value=", ".join(f"<@&{r}>" for r in mod_roles) if mod_roles else "None",
            inline=False
        )

        embed.add_field(
            name="Admin Roles",
            value=", ".join(f"<@&{r}>" for r in admin_roles) if admin_roles else "None",
            inline=False
        )

        embed.add_field(
            name="Muted Role",
            value=f"<@&{muted_role}>" if muted_role else "None",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(RoleSetter(bot))

