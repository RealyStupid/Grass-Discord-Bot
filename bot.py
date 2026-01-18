"""
to commit changes:
git add .
git commit -m "discription"
git push
"""

# import libraries
import discord
import logging
import os

from discord.ext import commands
from discord import app_commands

import BotConfig

# Define the bot class
class GrassBot(commands.Bot):
    def __init__(self):
        # Initialize the bot with command prefix and intents
        super().__init__(command_prefix='!', intents=BotConfig.INTENTS, application_id=BotConfig.APPLICATION_ID)

    async def setup_hook(self):
        for root, dirs, files in os.walk('./cogs'):
            for file in files:
                if file.endswith('.py'):
                    path = os.path.join(root, file)
                    ext = path.replace('./', '').replace('/', '.').replace('\\', '.').replace('.py', '')
                    await self.load_extension(ext)
                    print(f"Loaded cog: {ext}")


    async def on_ready(self):
        print(f'Logged on as {self.user}')


# Create bot instance
bot = GrassBot()

#logging handler
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

# sync commands using prefix command
@bot.command(name="sync")
@BotConfig.bot_owner_only()
async def sync_commands(ctx, scope: str = None):
    try:
        if scope == "global":
            synced = await bot.tree.sync()
            await ctx.send(f"Globally synced {len(synced)} commands")

        elif scope == "all":
            total = 0
            for gid in BotConfig.GUILD_IDS:
                synced = await bot.tree.sync(guild=discord.Object(id=gid))
                total += len(synced)
            await ctx.send(f"Synced commands to all dev guilds ({len(BotConfig.GUILD_IDS)} guilds).")

        else:
            synced = await bot.tree.sync(guild=ctx.guild)
            await ctx.send(f"Synced {len(synced)} commands to **{ctx.guild.name}**")

    except Exception as e:
        await ctx.send(f"Error while syncing commands: `{e}`")

# Run the bot with token
bot.run(BotConfig.BOT_TOKEN, log_handler=handler)