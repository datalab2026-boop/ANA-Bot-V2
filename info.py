import discord
from discord import app_commands
from discord.ext import commands
import config
from utils import get_group_info, get_roles_count
import time
import os

class GroupInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="info", description="Show public information about the Roblox group")
    async def info(self, interaction: discord.Interaction):
        start_perf = time.perf_counter()
        await interaction.response.defer()
        
        group_data = get_group_info()
        roles_count = get_roles_count()

        if not group_data:
            return await interaction.followup.send("[ERROR] Failed to sync with Roblox API.")

        latency = round((time.perf_counter() - start_perf) * 1000)

        # Используем нейтральный серый или темный цвет для строгого стиля
        embed = discord.Embed(
            title=f"GROUP_DIAGNOSTICS: {group_data['name'].upper()}",
            color=0x2f3136 
        )
        
        # Основные параметры
        embed.add_field(name="MEMBERS", value=f"`{group_data['member_count']}`", inline=True)
        embed.add_field(name="ROLES_TOTAL", value=f"`{roles_count}`", inline=True)
        embed.add_field(name="OWNER", value=f"`{group_data['owner_name']}`", inline=False)
        
        # Ссылки без лишнего оформления
        links_value = (
            f"ROBLOX: https://www.roblox.com/groups/{config.GROUP_ID}\n"
            f"DISCORD: https://discord.gg/XQjUNkmBr"
        )
        embed.add_field(name="RESOURCES", value=f"```\n{links_value}\n```", inline=False)
        
        # Описание в строгом блоке
        desc = group_data.get('description', 'NO_DATA')
        if len(desc) > 250:
            desc = desc[:247] + "..."
            
        embed.add_field(
            name="DESCRIPTION_DATA", 
            value=f"```text\n{desc.strip() if desc.strip() else 'NULL'}\n```", 
            inline=False
        )

        # Технический футер
        embed.set_footer(text=f"SYS_REF: {config.GROUP_ID} | PID: {os.getpid()} | LATENCY: {latency}ms")
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(GroupInfo(bot))
        
