import discord
from discord.ext import tasks, commands
import requests
from datetime import datetime, timezone
import config

class AltDetector(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_top_user_id = None # ID самого верхнего юзера из прошлой проверки
        self.is_initialized = False
        
        self.GROUP_ID = config.GROUP_ID
        self.CLOUD_API = config.ROBLOX_API_KEY
        self.headers = {"x-api-key": self.CLOUD_API}
        
        self.REPORT_CHANNEL_ID = 1480592830870192329
        self.ERROR_CHANNEL_ID = 1480592830870192329

        self.STARTER_ASSET_IDS = [
            62724852, 144076436, 144076512, 10638267973, 10647852134, 
            382537569, 1772336109, 4047884939
        ]
        
        self.check_loop.start()

    def cog_unload(self):
        self.check_loop.cancel()

    @tasks.loop(seconds=60)
    async def check_loop(self):
        await self.bot.wait_until_ready()
        
        try:
            # Получаем список. Новые всегда в начале (data[0])
            url = f"https://groups.roblox.com/v1/groups/{self.GROUP_ID}/users?sortOrder=Desc&limit=50"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                return
            
            data = response.json().get('data', [])
            if not data:
                return

            current_members_to_check = []

            if not self.is_initialized:
                # ПЕРВЫЙ ЗАПУСК: берем 5 самых верхних
                # Идем с конца (с 5-го к 1-му), чтобы лог был хронологическим
                current_members_to_check = list(reversed(data[:5]))
                self.is_initialized = True
            else:
                # ПОСЛЕДУЮЩИЕ ПРОВЕРКИ:
                # Ищем, где в новом списке находится наш старый "якорь"
                found_anchor_index = -1
                for i, member in enumerate(data):
                    if member['user']['userId'] == self.last_top_user_id:
                        found_anchor_index = i
                        break
                
                if found_anchor_index == -1:
                    # Если старый якорь не найден (ушел слишком далеко вниз или список сильно обновился)
                    # Чтобы не спамить, просто берем только самого первого (нового)
                    current_members_to_check = [data[0]]
                else:
                    # Все, кто имеет индекс меньше найденного якоря — это новые люди
                    # (т.е. они стоят выше него в списке)
                    new_people = data[0:found_anchor_index]
                    current_members_to_check = list(reversed(new_people))

            # Проверяем отобранных кандидатов
            for member in current_members_to_check:
                rbx_id = member['user']['userId']
                username = member['user']['username']
                
                risk_data = self.perform_risk_check(rbx_id)
                if risk_data:
                    group_join = member.get('created', 'Unknown')
                    risk_data['group_join'] = group_join[:10] if group_join != 'Unknown' else 'N/A'
                    await self.send_report(username, rbx_id, risk_data)

            # В конце каждой итерации обновляем "якорь" на самого верхнего из списка
            self.last_top_user_id = data[0]['user']['userId']

        except Exception as e:
            await self.log_error(f"Loop error: {str(e)}")

    def perform_risk_check(self, rbx_id):
        # ... (Логика проверки риска остается прежней) ...
        risk = 0
        reasons = []
        try:
            u_info = requests.get(f"https://users.roblox.com/v1/users/{rbx_id}").json()
            f_info = requests.get(f"https://friends.roblox.com/v1/users/{rbx_id}/friends/count").json()
            a_info = requests.get(f"https://avatar.roblox.com/v1/users/{rbx_id}/avatar").json()

            results = {}
            
            created_str = u_info.get('created')
            if created_str:
                created_dt = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                age_days = (datetime.now(timezone.utc) - created_dt).days
                results['age_days'] = age_days
                results['join_date'] = created_str[:10]
                if age_days < 30: 
                    risk += 50
                    reasons.append(f"New account ({age_days}d)")
            
            friends = f_info.get('count', 0)
            if friends < 5:
                risk += 30
                reasons.append("Few friends")

            results['reasons'] = ", ".join(reasons) if reasons else "Clean"
            results['total_risk'] = min(risk, 100)
            return results
        except:
            return None

    async def send_report(self, username, rbx_id, data):
        channel = self.bot.get_channel(self.REPORT_CHANNEL_ID)
        if not channel: return
        
        embed = discord.Embed(
            title=f"🔎 AltDetector: {username}", 
            description=f"Risk Score: **{data['total_risk']}%**",
            color=discord.Color.orange()
        )
        embed.add_field(name="Profile", value=f"[Link](https://www.roblox.com/users/{rbx_id}/profile)")
        embed.add_field(name="Reasons", value=data['reasons'])
        await channel.send(embed=embed)

    async def log_error(self, error_msg):
        channel = self.bot.get_channel(self.ERROR_CHANNEL_ID)
        if channel:
            await channel.send(f"⚠️ **AltDetector Error**: {error_msg}")

async def setup(bot):
    await bot.add_cog(AltDetector(bot))
      
