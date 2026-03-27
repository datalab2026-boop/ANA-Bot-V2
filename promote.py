import discord
from discord import app_commands
from discord.ext import commands
import config
from utils import has_permission, get_user_id, get_user_current_role, update_roblox_rank, send_log

class Promote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="promote", description="Promote a user to the next rank")
    async def promote(self, interaction: discord.Interaction, username: str):
        if not has_permission(interaction):
            return await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        
        await interaction.response.defer()
        user_id, err = get_user_id(username.strip())
        if err:
            return await interaction.followup.send(f"Error: {err}")

        current_role, _ = get_user_current_role(user_id)
        roles = config.VALID_ROLES
        next_role = None
        
        if current_role == "Guest":
            next_role = roles[0]
        elif current_role in roles:
            idx = roles.index(current_role)
            if idx + 1 < len(roles):
                next_role = roles[idx + 1]

        if not next_role:
            return await interaction.followup.send("User has already reached the maximum rank.")

        if update_roblox_rank(user_id, next_role):
            await interaction.followup.send(f"✅ Successfully promoted **{username}** to **{next_role}**")
            await send_log(self.bot, "Promotion", interaction.user, username, current_role, next_role)
        else:
            await interaction.followup.send("❌ Failed to update rank on Roblox.")

async def setup(bot):
    await bot.add_cog(Promote(bot))
