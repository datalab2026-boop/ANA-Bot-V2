import discord
import os
import asyncio
import logging
from discord.ext import commands, tasks
from web_server import keep_alive
import config
from datetime import datetime

# Настройка логирования (Критически важно для отладки на Render)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord_bot')

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(
            command_prefix="!", 
            intents=intents,
            heartbeat_timeout=30.0,  # Если Discord не отвечает 30 сек — считаем соединение мертвым
            close_timeout=10.0
        )

    async def setup_hook(self):
        print("\n=== STARTING MODULE LOADING ===")
        path = './commands'
        if not os.path.exists(path):
            print(f"CRITICAL ERROR: Folder '{path}' not found!")
            return

        # Перед загрузкой очищаем старые расширения, если они были
        for extension in list(self.extensions):
            await self.unload_extension(extension)

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
            # Синхронизируем команды (глобально)
            synced = await self.tree.sync()
            print(f"✅ Successfully synced {len(synced)} slash commands.")
        except Exception as e:
            print(f"❌ Failed to sync slash commands: {e}")

    async def on_ready(self):
        print(f"✅ Bot is logged in as {self.user} (ID: {self.user.id})")
        
        if not self.connection_watchdog.is_running():
            self.connection_watchdog.start()

        channel = self.get_channel(config.LOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="🤖 System Restarted",
                description="The bot process has been initialized and is now active.",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Status", value="`ONLINE`", inline=True)
            embed.add_field(name="Latency", value=f"`{round(self.latency * 1000)}ms`", inline=True)
            try:
                await channel.send(embed=embed)
            except: pass

    @tasks.loop(minutes=2)
    async def connection_watchdog(self):
        """Проверка на зависание сокета"""
        if self.is_closed():
            return
            
        # Если лаг сети огромный или задержка не определяется
        if self.latency > 15.0 or self.latency is None:
            print(f"🚨 High latency detected ({self.latency}). Reconnecting...")
            await self.close()

async def run_bot():
    """Основной цикл запуска бота"""
    while True:
        bot = MyBot()
        try:
            print("📡 Connecting to Discord Gateway...")
            # reconnect=True позволяет библиотеке пытаться чинить связь без перезапуска процесса
            await bot.start(config.DISCORD_TOKEN, reconnect=True)
        except Exception as e:
            print(f"⚠️ Connection loop error: {e}")
        finally:
            if not bot.is_closed():
                await bot.close()
            
            # Важный момент: даем системе "продышаться" перед рестартом
            print("⏳ Process will restart in 20 seconds...")
            await asyncio.sleep(20)

if __name__ == "__main__":
    if config.DISCORD_TOKEN:
        # 1. Запуск Flask (keep_alive должен работать в Thread, проверь свой файл web_server)
        try:
            keep_alive()
        except Exception as e:
            print(f"Flask failed to start: {e}")

        # 2. Бесконечный цикл запуска asyncio
        while True:
            try:
                asyncio.run(run_bot())
            except KeyboardInterrupt:
                print("Bot stopped by user.")
                break
            except Exception as e:
                print(f"🔥 Critical Event Loop Failure: {e}")
                import time
                time.sleep(10) # Пауза перед полным перезапуском цикла
    else:
        print("CRITICAL ERROR: DISCORD_TOKEN not found.")
    
