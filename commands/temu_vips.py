import discord
from discord import app_commands
from discord.ext import commands
import datetime
import os

class TemuVipCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Твой ID роли из конфига
        self.ROLE_ID = 1480292974893076491
        # ID разрешенных пользователей (из JS кода)
        self.ALLOWED_USERS = [1344271236620091453, 1189492690522476586]

    @app_commands.command(name="temuvip", description="Manage Temu VIPs")
    @app_commands.choices(subcommand=[
        app_commands.Choice(name="list", value="list"),
        app_commands.Choice(name="add", value="add"),
        app_commands.Choice(name="remove", value="remove")
    ])
    @app_commands.describe(user="User to add or remove")
    async def temuvip(self, interaction: discord.Interaction, subcommand: str, user: discord.Member = None):
        # 1. Проверка прав (как в JS)
        if interaction.user.id not in self.ALLOWED_USERS:
            await interaction.response.send_message("You do not have permission to use this command!", ephemeral=True)
            return

        role = interaction.guild.get_role(self.ROLE_ID)

        if not role:
            await interaction.response.send_message(f"Temu VIP role not found. Admin will fix it.", ephemeral=True)
            return

        # 2. Логика подкоманд
        if subcommand == "list":
            # ВАЖНО: Принудительно загружаем участников, чтобы role.members не был пустым
            # Это аналог того, почему у JS кода может работать, а у Python - нет
            await interaction.guild.chunk() 
            
            members = role.members
            if not members:
                await interaction.response.send_message("There are no Temu VIP's!", ephemeral=False)
                return

            description = "**Temu VIPs:**\n" + "\n".join([m.mention for m in members[:40]])
            if len(members) > 40:
                description += f"\n\n*...and {len(members) - 40} more.*"

            embed = discord.Embed(title="👑 Temu VIP List", description=description, color=discord.Color.red())
            await interaction.response.send_message(embed=embed)

        elif subcommand == "add":
            if not user:
                await interaction.response.send_message("Please specify a user!", ephemeral=True)
                return
            
            if role in user.roles:
                await interaction.response.send_message(f"{user.mention} is already a Temu VIP.", ephemeral=False)
            else:
                await user.add_roles(role)
                await interaction.response.send_message(f"✅ {user.mention} is now a Temu VIP.", ephemeral=False)

        elif subcommand == "remove":
            if not user:
                await interaction.response.send_message("Please specify a user!", ephemeral=True)
                return

            if role not in user.roles:
                await interaction.response.send_message(f"{user.mention} is not a Temu VIP.", ephemeral=False)
            else:
                await user.remove_roles(role)
                await interaction.response.send_message(f"❌ {user.mention} is now no longer a Temu VIP.", ephemeral=False)

async def setup(bot):
    await bot.add_cog(TemuVipCommand(bot))
    
