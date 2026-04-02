import discord
import os
import asyncio
import logging
import sys
from discord.ext import commands, tasks
from web_server import keep_alive
import config
from datetime import datetime

# Настройка логирования для Render
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord_bot')

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(
            command_prefix="!", 
            intents=intents,
            heartbeat_timeout=60.0,
            close_timeout=20.0
        )

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
                    await self.load_extension(f'commands.{filename[:-3]}')
                    print(f"✅ Loaded extension: {filename}")
                    loaded_count += 1
                except Exception as e:
                    print(f"❌ Failed to load {filename}: {e}")
        
        print(f"Total modules loaded: {loaded_count}")
        
        print("=== SYNCING SLASH COMMANDS ===")
        try:
            synced = await self.tree.sync()
            print(f"✅ Successfully synced {len(synced)} slash commands.")
        except Exception as e:
            print(f"❌ Failed to sync slash commands: {e}")

    async def on_ready(self):
        print(f"✅ Bot is logged in as {self.user} (ID: {self.user.id})")
        
        if not self.connection_watchdog.is_running():
            self.connection_watchdog.start()

        # Лог активации в канал
        channel = self.get_channel(config.LOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="🤖 System Active",
                description="The bot has been started by the Anti-Crash system.",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Status", value="`ONLINE`", inline=True)
            embed.add_field(name="Latency", value=f"`{round(self.latency * 1000)}ms`", inline=True)
            try:
                await channel.send(embed=embed)
            except: pass

    @tasks.loop(minutes=3)
    async def connection_watchdog(self):
        """Проверка на 'зависание' сессии"""
        if self.is_closed():
            return
            
        # Если пинг пропал или он слишком огромный
        if self.latency is None or self.latency > 20.0:
            print(f"🚨 Пинг критический ({self.latency}). Жесткий перезапуск...")
            os._exit(1) # Убиваем процесс для внешней перезагрузки

        try:
            # Реальный запрос к API для проверки связи
            await self.fetch_user(self.user.id)
        except Exception as e:
            print(f"🚨 API не отвечает: {e}. Жесткий перезапуск...")
            os._exit(1)

async def run_bot():
    # Запуск Flask сервера
    try:
        keep_alive()
    except Exception as e:
        print(f"Flask failed: {e}")

    bot = MyBot()
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📡 Connecting to Discord Gateway...")
        await bot.start(config.DISCORD_TOKEN)
    except Exception as e:
        print(f"⚠️ Fatal Error: {e}")
        os._exit(1) # Выход при любой фатальной ошибке

if __name__ == "__main__":
    if config.DISCORD_TOKEN:
        try:
            asyncio.run(run_bot())
        except KeyboardInterrupt:
            print("Stopped by user.")
            sys.exit(0)
        except Exception as e:
            print(f"🔥 Critical Failure: {e}")
            os._exit(1)
    else:
        print("CRITICAL ERROR: No DISCORD_TOKEN found!")
                        
