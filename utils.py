import discord
import requests
from datetime import datetime
import config 
import time

# Headers for Roblox Open Cloud API
HEADERS = {
    "x-api-key": config.ROBLOX_API_KEY, 
    "Content-Type": "application/json"
}

def has_permission(interaction: discord.Interaction):
    return any(role.id == config.ALLOWED_ROLE_ID for role in interaction.user.roles)

async def send_log(bot, action_type, moderator, target_user, old_rank, new_rank):
    channel = bot.get_channel(config.LOG_CHANNEL_ID)
    if not channel: return
    
    color = discord.Color.red() if action_type == "Demotion" else discord.Color.green()
    if action_type == "Promotion": color = discord.Color.green()

    embed = discord.Embed(title=f"Log: {action_type}", color=color, timestamp=datetime.now())
    embed.add_field(name="Moderator", value=moderator.mention, inline=True)
    embed.add_field(name="Target User", value=target_user, inline=True)
    embed.add_field(name="Old Rank", value=f"`{old_rank}`", inline=False)
    embed.add_field(name="New Rank", value=f"`{new_rank}`", inline=False)
    
    await channel.send(embed=embed)

def get_user_id(username):
    url = "https://users.roblox.com/v1/usernames/users"
    data = {"usernames": [username], "excludeBannedUsers": True}
    try:
        r = requests.post(url, json=data)
        if r.status_code != 200: return None, f"API Error: {r.status_code}"
        result = r.json().get("data", [])
        return (result[0]["id"], None) if result else (None, "User not found")
    except Exception as e: return None, str(e)

def get_user_current_role(user_id):
    """Используем V1 эндпоинт, он стабильнее для проверки конкретной группы."""
    # Добавляем метку времени, чтобы Roblox не отдавал старый (закешированный) результат
    url = f"https://groups.roblox.com/v1/users/{user_id}/groups/roles"
    try:
        r = requests.get(url, params={"_": time.time()})
        if r.status_code != 200:
            return "Guest", 0
        
        data = r.json().get("data", [])
        for entry in data:
            # Сравниваем ID групп как числа (int) для исключения ошибок типа данных
            if int(entry["group"]["id"]) == int(config.GROUP_ID):
                return entry["role"]["name"], entry["role"]["rank"]
        
        return "Guest", 0
    except:
        return "Guest", 0

def update_roblox_rank(user_id, role_name):
    # Берем ID роли из конфига
    role_id = config.ROLE_IDS.get(role_name)
    if not role_id:
        return False
        
    url = f"https://apis.roblox.com/cloud/v2/groups/{config.GROUP_ID}/memberships/{user_id}"
    payload = {"role": f"groups/{config.GROUP_ID}/roles/{role_id}"}
    
    try:
        r = requests.patch(url, headers=HEADERS, json=payload)
        return r.status_code == 200
    except:
        return False

# --- Вспомогательные функции ---

def get_group_info():
    url = f"https://groups.roblox.com/v1/groups/{config.GROUP_ID}"
    try:
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            return {
                "member_count": data.get("memberCount", 0),
                "owner_name": data.get("owner", {}).get("username", "No Owner"),
                "description": data.get("description", ""),
                "name": data.get("name", "Group")
            }
        return None
    except: return None

def get_roles_count():
    url = f"https://groups.roblox.com/v1/groups/{config.GROUP_ID}/roles"
    try:
        r = requests.get(url)
        if r.status_code == 200:
            return len(r.json().get("roles", []))
        return 0
    except: return 0
        
