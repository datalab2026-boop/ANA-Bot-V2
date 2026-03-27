import discord
from discord import app_commands
from discord.ext import commands
import config
from utils import has_permission, get_user_id, get_user_current_role, update_roblox_rank, send_log

class Demote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="demote", description="Demote a user to the previous rank")
    async def demote(self, interaction: discord.Interaction, username: str):
        if not has_permission(interaction):
            return await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        
        await interaction.response.defer()
        user_id, err = get_user_id(username.strip())
        if err:
            return await interaction.followup.send(f"Error: {err}")

        current_role, _ = get_user_current_role(user_id)
        roles = config.VALID_ROLES
        prev_role = None
        
        if current_role in roles:
            idx = roles.index(current_role)
            prev_role = roles[idx - 1] if idx > 0 else "Guest"
        
        if not prev_role:
            return await interaction.followup.send("User is already at the lowest rank.")

        if update_roblox_rank(user_id, prev_role):
            await interaction.followup.send(f"✅ Successfully demoted **{username}** to **{prev_role}**")
            await send_log(self.bot, "Demotion", interaction.user, username, current_role, prev_role)
        else:
            await interaction.followup.send("❌ Failed to update rank on Roblox.")

async def setup(bot):
    await bot.add_cog(Demote(bot))
