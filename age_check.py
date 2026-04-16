import discord
from discord.ext import tasks, commands
import requests
import asyncio
from datetime import datetime, timezone
import config

# --- КОНФИГУРАЦИЯ ---
"BOT_TOKEN" = config.DISCORD_TOKEN
"GROUP_ID" = config.GROUP_ID
"CLOUD_API" = config.ROBLOX_API_KEY
REPORT_CHANNEL_ID = 1480592830870192329
ERROR_CHANNEL_ID = 1480592830870192329
CHECK_INTERVAL = 60

class AntiRaidBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.last_checked_id = None
        self.headers = {"x-api-key": CLOUD_API}
        
        self.STARTER_ASSET_IDS = [
            62724852, 144076436, 144076512, 10638267973, 10647852134, 382537569, 1772336109, 4047884939, 10638267973, 10647852134
        ]

    async def on_ready(self):
        print(f"✅ Бот активен: {self.user}")
        self.report_channel = self.get_channel(REPORT_CHANNEL_ID)
        self.error_channel = self.get_channel(ERROR_CHANNEL_ID)
        if not self.check_loop.is_running():
            self.check_loop.start()

    @tasks.loop(seconds=CHECK_INTERVAL)
    async def check_loop(self):
        try:
            url = f"https://groups.roblox.com/v1/groups/{GROUP_ID}/users?sortOrder=Desc&limit=10"
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200: return
            
            members = response.json().get('data', [])
            for member in reversed(members):
                rbx_id = member['user']['userId']
                username = member['user']['username']
                group_join = member.get('joined', 'Unknown')

                if self.last_checked_id and rbx_id <= self.last_checked_id:
                    continue

                risk_data = self.perform_risk_check(rbx_id)
                if risk_data:
                    risk_data['group_join'] = group_join[:10] if group_join != 'Unknown' else 'N/A'
                    await self.send_report(username, rbx_id, risk_data)
                    self.last_checked_id = rbx_id
        except Exception as e:
            await self.log_error(f"Loop error: {str(e)}")

    def perform_risk_check(self, rbx_id):
        risk = 0
        reasons = []
        try:
            u_info = requests.get(f"https://users.roblox.com/v1/users/{rbx_id}", headers=self.headers).json()
            f_info = requests.get(f"https://friends.roblox.com/v1/users/{rbx_id}/friends/count", headers=self.headers).json()
            b_info = requests.get(f"https://badges.roblox.com/v1/users/{rbx_id}/badges?limit=10", headers=self.headers).json()
            a_info = requests.get(f"https://avatar.roblox.com/v1/users/{rbx_id}/avatar", headers=self.headers).json()

            results = {}
            
            # 1. Возраст профиля
            created_str = u_info.get('created')
            if created_str:
                created_dt = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                age_days = (datetime.now(timezone.utc) - created_dt).days
                results['age_days'] = age_days
                results['join_date'] = created_str[:10]
                
                if age_days < 14: 
                    risk += 60
                    reasons.append("Account age < 2 weeks")
                elif age_days < 30: 
                    risk += 25
                    reasons.append("Account age < 1 month")
                elif age_days < 90: 
                    risk += 10
                    reasons.append("Account age < 3 months")
            
            # 2. Проверка аватара (Замена названий на ID)
            equipped = a_info.get('assets', [])
            ignored_types = ['Torso', 'LeftArm', 'RightArm', 'LeftLeg', 'RightLeg', 'Head']
            # Сохраняем список ID вместо названий типов
            clothing_ids = [str(a.get('id')) for a in equipped if a.get('assetType', {}).get('name') not in ignored_types]
            
            if clothing_ids:
                matches = sum(1 for item_id in clothing_ids if int(item_id) in self.STARTER_ASSET_IDS)
                match_percent = (matches / len(clothing_ids)) * 100
                if match_percent >= 75: 
                    risk += 35
                    reasons.append(f"Starter items match ({round(match_percent)}%)")
                results['clothing_list'] = ", ".join(clothing_ids)
            else:
                risk += 30
                reasons.append("Empty avatar (No assets)")
                results['clothing_list'] = "None"

            # 3. Друзья (Твои новые условия: <5 +40%, <10 +30%, <20 +10%, >20 +0%)
            friends = f_info.get('count', 0)
            results['friends'] = friends
            if friends < 5:
                risk += 40
                reasons.append("Extremely low friends (<5)")
            elif friends < 10:
                risk += 30
                reasons.append("Very low friends (<10)")
            elif friends < 20:
                risk += 10
                reasons.append("Low friends (<20)")

            # 4. Бейджи
            badges = b_info.get('data', [])
            if not b_info.get('nextPageCursor') and len(badges) < 5:
                risk += 15
                reasons.append("Lack of badges")

            results['reasons'] = ", ".join(reasons) if reasons else "None"
            results['total_risk'] = min(risk, 100)
            return results
        except:
            return None

    async def send_report(self, username, rbx_id, data):
        risk = data['total_risk']
        color = discord.Color.green() if risk < 40 else discord.Color.gold() if risk < 75 else discord.Color.red()

        embed = discord.Embed(title=f"🛡️ {username} checkup", color=color)
        embed.add_field(name="Username:", value=f"**{username}**", inline=True)
        embed.add_field(name="Roblox ID:", value=f"`{rbx_id}`", inline=True)
        embed.add_field(name="Roblox join date:", value=f"{data['join_date']} ({data['age_days']} days)", inline=False)
        embed.add_field(name="Group join date:", value=data['group_join'], inline=False)
        embed.add_field(name="Risk level:", value=f"**{risk}%**", inline=True)
        embed.add_field(name="Equipped Assets (IDs):", value=data.get('clothing_list', 'N/A'), inline=False)
        embed.add_field(name="Reason of increasing risk:", value=data['reasons'], inline=False)

        await self.report_channel.send(embed=embed)

    async def log_error(self, error_msg):
        if self.error_channel:
            await self.error_channel.send(f"❌ **System Error**: {error_msg}")

if __name__ == "__main__":
    bot = AntiRaidBot()
    bot.run(BOT_TOKEN)
          
