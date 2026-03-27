import os
import aiohttp
import discord
import datetime
import asyncio
from discord import app_commands
from discord.ext import commands, tasks
import config
from utils import has_permission

# Расписание строго по UTC
RESTART_TIMES = [
    datetime.time(hour=10, minute=0, second=0),
    datetime.time(hour=22, minute=0, second=0)
]

class Restart(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Берем токен напрямую из твоего config.py
        self.restart_url = config.RESTART_TOKEN
        self.scheduled_restart.start()

    def cog_unload(self):
        self.scheduled_restart.cancel()

    async def trigger_render_restart(self):
        """Отправка запроса на Render для перезапуска"""
        if not self.restart_url:
            print("❌ Restart failed: No Restarttoken found in config.")
            return False
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.restart_url) as resp:
                    return resp.status in [200, 201]
        except Exception as e:
            print(f"Error during restart request: {e}")
            return False

    # --- Автоматизация (10:00 и 22:00 UTC) ---
    @tasks.loop(time=RESTART_TIMES)
    async def scheduled_restart(self):
        channel = self.bot.get_channel(config.LOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="🔄 Scheduled Maintenance",
                description="Initiating automated daily restart (UTC schedule)...",
                color=discord.Color.orange(),
                timestamp=datetime.datetime.now()
            )
            embed.add_field(name="Schedule", value="`10:00 / 22:00 UTC`", inline=True)
            try:
                await channel.send(embed=embed)
            except: pass

        print("Executing scheduled UTC restart...")
        await self.trigger_render_restart()

    # --- Ручная команда ---
    @app_commands.command(name="restart", description="Full reboot of the Render instance")
    async def restart(self, interaction: discord.Interaction):
        # Проверка роли ALLOWED_ROLE_ID из твоего config.py через utils.py
        if not has_permission(interaction):
            return await interaction.response.send_message(
                "❌ Access Denied: You don't have the required role.", 
                ephemeral=True
            )

        if not self.restart_url:
            await interaction.response.send_message("❌ Error: Restart token is missing.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🚀 Manual Restart",
            description="Restart command received. Bot will reboot shortly.",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        await interaction.response.send_message(embed=embed)
        
        # Пауза, чтобы Discord успел подтвердить отправку сообщения
        await asyncio.sleep(2)
        await self.trigger_render_restart()

async def setup(bot):
    await bot.add_cog(Restart(bot))
        
