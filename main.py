import discord
import os
import asyncio
import logging
import sys
import traceback
from discord.ext import commands, tasks
from web_server import keep_alive
import config
from datetime import datetime

# Настройка логирования (Render будет подхватывать эти логи)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s % (levelname)s:%(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('discord_bot')

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        intents.members = True # Убедись, что это включено в Discord Developer Portal
        
        super().__init__(
            command_prefix="!", 
            intents=intents,
            heartbeat_timeout=60.0,
            close_timeout=20.0
        )

    async def setup_hook(self):
        print("\n=== [1] LOADING MODULES ===")
        path = './commands'
        if not os.path.exists(path):
            print(f"❌ CRITICAL: Folder '{path}' not found! Creating it...")
            os.makedirs(path, exist_ok=True)

        loaded_count = 0
        for filename in os.listdir(path):
            if filename.endswith('.py') and filename != '__init__.py':
                try:
                    await self.load_extension(f'commands.{filename[:-3]}')
                    print(f"✅ Loaded: {filename}")
                    loaded_count += 1
                except Exception as e:
                    print(f"❌ Failed {filename}: {e}")
                    traceback.print_exc()
        
        print(f"Total: {loaded_count} modules.")
        
        print("\n=== [2] SYNCING SLASH COMMANDS ===")
        try:
            synced = await self.tree.sync()
            print(f"✅ Synced {len(synced)} commands.")
        except Exception as e:
            print(f"❌ Sync failed: {e}")

    async def on_ready(self):
        print(f"\n🚀 LOGGED IN AS: {self.user} (ID: {self.user.id})")
        print(f"Status: ONLINE | Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if not self.connection_watchdog.is_running():
            self.connection_watchdog.start()

        # Отправка лога в канал (если ID верный)
        try:
            channel = self.get_channel(int(config.LOG_CHANNEL_ID))
            if channel:
                embed = discord.Embed(
                    title="🤖 System Status: ONLINE",
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="Latency", value=f"`{round(self.latency * 1000)}ms`")
                await channel.send(embed=embed)
        except Exception as e:
            print(f"⚠️ Could not send log to Discord channel: {e}")

    @tasks.loop(minutes=5)
    async def connection_watchdog(self):
        """Проверка на зависание. Смягчена, чтобы не было ложных срабатываний."""
        if self.is_closed():
            return
            
        # Даем боту фору. Если латентность None — он еще просыпается.
        if self.latency is not None:
            # Если пинг более 30 секунд (бот явно висит)
            if self.latency > 30.0:
                print(f"🚨 CRITICAL LATENCY: {self.latency}s. Rebooting...")
                os._exit(1)
            
            try:
                # Быстрая проверка связи с API
                await self.fetch_user(self.user.id)
            except Exception as e:
                print(f"🚨 API Unreachable: {e}. Rebooting...")
                os._exit(1)

async def run_bot():
    # 1. Запуск Flask (веб-сервера для Render)
    print("🌐 Starting Flask keep-alive server...")
    try:
        keep_alive()
    except Exception as e:
        print(f"❌ Flask failed to start: {e}")

    # 2. Инициализация и запуск бота
    bot = MyBot()
    
    token = getattr(config, 'DISCORD_TOKEN', None) or os.environ.get('DISCORD_TOKEN')
    
    if not token:
        print("❌ ERROR: No DISCORD_TOKEN found in config.py or Environment Variables!")
        return

    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📡 Connecting to Discord...")
        await bot.start(token)
    except discord.LoginFailure:
        print("❌ FATAL: Invalid Discord Token! Check your config/env.")
    except Exception as e:
        print(f"⚠️ Fatal Connection Error: {e}")
        traceback.print_exc()
    finally:
        os._exit(1) # Всегда выходим со статусом 1 при падении, чтобы Render перезапустил бота

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("🛑 Shutdown requested by user.")
        sys.exit(0)
    except Exception as e:
        print(f"🔥 UNCAUGHT FATAL ERROR: {e}")
        traceback.print_exc()
        os._exit(1)
        
