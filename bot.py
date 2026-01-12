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
        #setup cogs
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')
                print(f'Loaded cog: {filename}')

    async def on_ready(self):
        print(f'Logged on as {self.user}')


# Create bot instance
bot = GrassBot()

#logging handler
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

# sync commands using prefix command
@bot.command(name="sync")
async def sync_commands(ctx, scope: str = None):
    """
    Sync slash commands using a prefix command.
    Usage:
      !sync            -> sync to this guild only
      !sync global     -> global sync
      !sync clear      -> clear & resync guild commands
    """
    try:
        if scope == "global":
            print("Starting global sync...")
            synced = await bot.tree.sync()
            print("Global sync completed.")
            await ctx.send(f"Globally synced {len(synced)} commands")

        elif scope == "clear":
            print("Clearing guild commands...")
            bot.tree.clear_commands(guild=ctx.guild)
            print("starting resync...")
            await bot.tree.sync(guild=ctx.guild)
            print("Resync completed.")
            await ctx.send(f"Cleared and resynced commands for **{ctx.guild.name}**")

        else:
            print("Starting guild sync...")
            synced = await bot.tree.sync(guild=ctx.guild)
            print("Guild sync completed.")
            await ctx.send(f"Synced {len(synced)} commands to **{ctx.guild.name}**")

    except Exception as e:
        await ctx.send(f"Error while syncing commands: `{e}`")

# Run the bot with token
bot.run(BotConfig.BOT_TOKEN, log_handler=handler)