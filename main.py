import discord
import os
import asyncio
from discord.ext import commands
from web_server import keep_alive
import config
from datetime import datetime

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        # Using a simple prefix, but focus is on Slash Commands
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        print("\n=== STARTING MODULE LOADING ===")
        path = './commands'
        if not os.path.exists(path):
            print(f"CRITICAL ERROR: Folder '{path}' not found!")
            return

        loaded_count = 0
        for filename in os.listdir(path):
            if filename.endswith('.py') and filename != '__init__.py':
                try:
                    # Logic to handle reloads if the bot restarts internally
                    if f'commands.{filename[:-3]}' in self.extensions:
                        await self.reload_extension(f'commands.{filename[:-3]}')
                    else:
                        await self.load_extension(f'commands.{filename[:-3]}')
                    print(f"✅ Loaded extension: {filename}")
                    loaded_count += 1
                except Exception as e:
                    print(f"❌ Failed to load {filename}: {e}")
        
        print(f"Total modules loaded: {loaded_count}")
        
        print("=== SYNCING SLASH COMMANDS ===")
        try:
            synced = await self.tree.sync()
            print(f"Successfully synced {len(synced)} slash commands.")
        except Exception as e:
            print(f"Failed to sync commands: {e}")
        print("=== SETUP HOOK COMPLETE ===\n")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        
        # Send Activation Log Embed
        channel = self.get_channel(config.LOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="🚀 Bot System Activated",
                description="The bot has successfully connected to Discord Gateway.",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Status", value="`ONLINE`", inline=True)
            embed.add_field(name="Instance", value="`Render.com`", inline=True)
            embed.set_footer(text=f"Session started | ID: {self.user.id}")
            try:
                await channel.send(embed=embed)
            except Exception as e:
                print(f"Could not send log embed: {e}")

async def run_bot():
    """Main loop with 1-minute wait logic to prevent 429 errors."""
    while True:
        bot = MyBot()
        try:
            print("📡 Sending request to Discord Token...")
            # We use .start() instead of .run() for better control in async
            await bot.start(config.DISCORD_TOKEN)
        except Exception as e:
            print(f"⚠️ Session Error: {e}")
        finally:
            # Cleanup before waiting
            if not bot.is_closed():
                await bot.close()
            
            print("⏳ Bot disconnected. Waiting 60 seconds (1m) before retry...")
            await asyncio.sleep(60) 
            print("🔄 Attempting to reconnect...")

if __name__ == "__main__":
    if config.DISCORD_TOKEN:
        # Start the Flask web server for Render (runs in a separate Thread)
        keep_alive()
        
        # Run the async bot manager
        try:
            asyncio.run(run_bot())
        except KeyboardInterrupt:
            print("Bot stopped manually.")
    else:
        print("CRITICAL ERROR: DISCORD_TOKEN not found in config!")
                    
