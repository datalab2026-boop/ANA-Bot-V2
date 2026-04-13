import discord
from discord import app_commands
from discord.ext import commands
import time
import datetime
import aiohttp
import psutil
import os

class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Фиксация времени запуска для точного Uptime
        self.start_time = datetime.datetime.now(datetime.timezone.utc)

    @app_commands.command(name="ping", description="Check bot speed and server health")
    async def ping(self, interaction: discord.Interaction):
        # Точка отсчета для замера общей скорости ответа
        start_perf = time.perf_counter()
        
        # Предварительный ответ
        await interaction.response.send_message("Analyzing system status...", ephemeral=False)

        # 1. Время работы (Uptime)
        now = datetime.datetime.now(datetime.timezone.utc)
        delta = now - self.start_time
        uptime_str = f"{delta.days}d {delta.seconds // 3600}h {(delta.seconds // 60) % 60}m {delta.seconds % 60}s"

        # 2. Сетевые задержки (Network)
        # Пульс Discord (WebSocket)
        discord_ping = round(self.bot.latency * 1000)
        
        # Пинг к Roblox API
        roblox_ping = "Error"
        api_start = time.perf_counter()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://groups.roblox.com/v1/groups/841435331", timeout=5) as resp:
                    if resp.status == 200:
                        roblox_ping = f"{round((time.perf_counter() - api_start) * 1000)}ms"
                    else:
                        roblox_ping = f"HTTP {resp.status}"
        except:
            roblox_ping = "Timeout"

        # 3. Нагрузка на сервер (Hardware - актуально для Render)
        cpu_usage = psutil.cpu_percent()
        process = psutil.Process(os.getpid())
        ram_usage = round(process.memory_info().rss / 1024 / 1024, 1) # В MB

        # 4. Полная скорость выполнения (Response Time)
        total_speed = round((time.perf_counter() - start_perf) * 1000)

        # Создание Embed
        embed = discord.Embed(
            title="System Diagnostics", 
            color=discord.Color.blue(),
            timestamp=now
        )
        
        embed.add_field(
            name="Connection", 
            value=f"Discord: `{discord_ping}ms`\nRoblox: `{roblox_ping}`", 
            inline=True
        )
        
        embed.add_field(
            name="Server Load", 
            value=f"CPU: `{cpu_usage}%`\nRAM: `{ram_usage}MB`", 
            inline=True
        )
        
        embed.add_field(
            name="Performance", 
            value=f"Response: `{total_speed}ms`", 
            inline=True
        )
        
        embed.add_field(
            name="Online For", 
            value=f"`{uptime_str}`", 
            inline=False
        )
        
        embed.set_footer(text=f"Render Instance | PID: {os.getpid()}")

        # Редактируем сообщение, добавляя Embed
        await interaction.edit_original_response(content=None, embed=embed)

async def setup(bot):
    # Ваш "Гарант": Двойная регистрация кога для стабильной выгрузки в API
    await bot.add_cog(Ping(bot))
    try:
        await bot.add_cog(Ping(bot))
    except discord.errors.ClientException:
        # Игнорируем ошибку, если ког уже успешно добавлен первым вызовом
        pass
        
