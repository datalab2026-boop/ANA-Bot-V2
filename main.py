import discord
import os
import asyncio
import logging
import time
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
            heartbeat_timeout=60.0,  # Увеличили до 60 сек для стабильности на плохом канале
            close_timeout=20.0
        )

    async def setup_hook(self):
        print("\n=== STARTING MODULE LOADING ===")
        path = './commands'
        if not os.path.exists(path):
            print(f"CRITICAL ERROR: Folder '{path}' not found!")
            return

        # Очистка старых расширений при жестком рестарте внутри процесса
        for extension in list(self.extensions):
            try:
                await self.unload_extension(extension)
            except: pass

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
        
        # Запуск вочдога, если он еще не запущен
        if not self.connection_watchdog.is_running():
            self.connection_watchdog.start()

        # Лог активации в канал
        channel = self.get_channel(config.LOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="🤖 System Active",
                description="The bot has reconnected and re-synced modules.",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Status", value="`ONLINE` (Resumed)", inline=True)
            embed.add_field(name="Latency", value=f"`{round(self.latency * 1000)}ms`", inline=True)
            try:
                await channel.send(embed=embed)
            except: pass

    @tasks.loop(minutes=3)
    async def connection_watchdog(self):
        """Проверка на 'зависание' сессии (эффект призрака)"""
        if self.is_closed():
            return
            
        # 1. Проверка пинга WebSocket
        if self.latency is None or self.latency > 20.0:
            print(f"🚨 Пинг критический или отсутствует ({self.latency}). Рестарт сессии...")
            await self.close()
            return

        # 2. Проверка реального ответа API (самый надежный способ)
        try:
            # Делаем легкий запрос к API Discord, чтобы проверить реальную связь
            await self.fetch_user(self.user.id)
        except Exception as e:
            print(f"🚨 API не отвечает (Heartbeat failed): {e}. Перезагрузка...")
            await self.close()

async def run_bot():
    """Бесконечный цикл управления объектом бота"""
    while True:
        bot = MyBot()
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 📡 Connecting to Discord Gateway...")
            # Используем start() вместо run() для лучшего контроля в async среде
            await bot.start(config.DISCORD_TOKEN, reconnect=True)
        except discord.errors.HTTPException as e:
            if e.status == 429:
                print("🚨 Rate Limit (429) обнаружен! Ждем 2 минуты...")
                await asyncio.sleep(120)
            else:
                print(f"⚠️ HTTP Error: {e}")
        except Exception as e:
            print(f"⚠️ Session Loop Error: {e}")
        finally:
            # Гарантированное закрытие перед рестартом
            if not bot.is_closed():
                await bot.close()
            
            # Удаляем объект из памяти для чистого перезапуска
            del bot
            print("⏳ Restarting bot process in 30 seconds...")
            await asyncio.sleep(30)

if __name__ == "__main__":
    if config.DISCORD_TOKEN:
        # Запуск Flask сервера ( keep_alive() )
        try:
            keep_alive()
        except Exception as e:
            print(f"Flask failed: {e}")

        # Глобальный цикл для защиты от падения самого asyncio
        while True:
            try:
                asyncio.run(run_bot())
            except KeyboardInterrupt:
                print("Stopped by user.")
                break
            except Exception as e:
                print(f"🔥 Critical Global Failure: {e}")
                time.sleep(20)
    else:
        print("CRITICAL ERROR: No DISCORD_TOKEN found!")
    
