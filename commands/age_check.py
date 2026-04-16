import discord
from discord.ext import tasks, commands
import requests
import asyncio
from datetime import datetime, timezone
import config

class AgeCheck(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_checked_id = None
        # Берем данные из конфига
        self.group_id = config.GROUP_ID
        self.cloud_api = config.ROBLOX_API_KEY
        self.headers = {"x-api-key": self.cloud_api}
        
        self.report_channel_id = 1480592830870192329
        self.error_channel_id = 1480592830870192329
        self.check_interval = 60

        self.STARTER_ASSET_IDS = [
            62724852, 144076436, 144076512, 10638267973, 10647852134, 
            382537569, 1772336109, 4047884939, 10638267973, 10647852134
        ]
        
        # Запуск цикла
        self.check_loop.start()

    def cog_unload(self):
        self.check_loop.cancel()

    @tasks.loop(seconds=60)
    async def check_loop(self):
        # Ждем, пока бот полностью загрузится
        await self.bot.wait_until_ready()
        
        try:
            url = f"https://groups.roblox.com/v1/groups/{self.group_id}/users?sortOrder=Desc&limit=10"
            # Используем asyncio для запросов в идеале, но пока оставим requests для простоты
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200: return
            
            members = response.json().get('data', [])
            if not members: return

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
            print(f"Loop error: {e}")

    def perform_risk_check(self, rbx_id):
        risk = 0
        reasons = []
        try:
            u_info = requests.get(f"https://users.roblox.com/v1/users/{rbx_id}", headers=self.headers).json()
            f_info = requests.get(f"https://friends.roblox.com/v1/users/{rbx_id}/friends/count", headers=self.headers).json()
            b_info = requests.get(f"https://badges.roblox.com/v1/users/{rbx_id}/badges?limit=10", headers=self.headers).json()
            a_info = requests.get(f"https://avatar.roblox.com/v1/users/{rbx_id}/avatar", headers=self.headers).json()

            results = {}
            
            # 1. Возраст
            created_str = u_info.get('created')
            if created_str:
                created_dt = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                age_days = (datetime.now(timezone.utc) - created_dt).days
                results['age_days'] = age_days
                results['join_date'] = created_str[:10]
                
                if age_days < 14: risk += 60; reasons.append("Age < 2w")
                elif age_days < 30: risk += 25; reasons.append("Age < 1m")
            
            # 2. Аватар
            equipped = a_info.get('assets', [])
            clothing_ids = [str(a.get('id')) for a in equipped]
            results['clothing_list'] = ", ".join(clothing_ids[:10]) if clothing_ids else "None"
            
            if not clothing_ids:
                risk += 30
                reasons.append("Empty avatar")

            # 3. Друзья
            friends = f_info.get('count', 0)
            results['friends'] = friends
            if friends < 5: risk += 40
            elif friends < 10: risk += 30

            results['reasons'] = ", ".join(reasons) if reasons else "Clean"
            results['total_risk'] = min(risk, 100)
            return results
        except Exception as e:
            print(f"Risk check error: {e}")
            return None

    async def send_report(self, username, rbx_id, data):
        channel = self.bot.get_channel(self.report_channel_id)
        if not channel: return

        risk = data['total_risk']
        color = discord.Color.red() if risk > 70 else discord.Color.gold() if risk > 40 else discord.Color.green()

        embed = discord.Embed(title=f"🛡️ Security Check: {username}", color=color)
        embed.add_field(name="Account Age", value=f"{data['age_days']} days", inline=True)
        embed.add_field(name="Risk", value=f"{risk}%", inline=True)
        embed.add_field(name="Reasons", value=data['reasons'], inline=False)
        
        await channel.send(embed=embed)

# Функция для загрузки кога в основной main.py
async def setup(bot):
    await bot.add_cog(AgeCheck(bot))
              
