import discord
from discord import app_commands
from discord.ext import commands
import config
from utils import has_permission, get_user_id, get_user_current_role, update_roblox_rank, send_log

class SetRank(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setrank", description="Set a user to a specific rank")
    @app_commands.choices(rank=[app_commands.Choice(name=r, value=r) for r in config.VALID_ROLES])
    async def setrank(self, interaction: discord.Interaction, username: str, rank: app_commands.Choice[str]):
        if not has_permission(interaction):
            return await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        
        await interaction.response.defer()
        user_id, err = get_user_id(username.strip())
        if err:
            return await interaction.followup.send(f"Error: {err}")

        current_role, _ = get_user_current_role(user_id)
        
        if update_roblox_rank(user_id, rank.value):
            await interaction.followup.send(f"✅ Successfully set **{username}** to **{rank.value}**")
            await send_log(self.bot, "SetRank", interaction.user, username, current_role, rank.value)
        else:
            await interaction.followup.send("❌ Failed to set rank on Roblox.")

async def setup(bot):
    await bot.add_cog(SetRank(bot))
