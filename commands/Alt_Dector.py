import discord
from discord.ext import tasks, commands
import requests
import asyncio
from datetime import datetime, timezone
import config

class AltDetector(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_top_user_id = None  # Наш "якорь" для отслеживания позиции
        self.is_initialized = False  # Флаг первого запуска
        
        # Данные из твоего конфига
        self.GROUP_ID = config.GROUP_ID
        self.CLOUD_API = config.ROBLOX_API_KEY
        self.headers = {"x-api-key": self.CLOUD_API}
        
        # Настройки каналов и роли
        self.ROLE_ID = 593902054  # Твоя роль для проверки
        self.REPORT_CHANNEL_ID = 1480592830870192329
        self.ERROR_CHANNEL_ID = 1480592830870192329
        self.CHECK_INTERVAL = 30  # Интервал проверки в секундах

        self.STARTER_ASSET_IDS = [
            62724852, 144076436, 144076512, 10638267973, 10647852134, 
            382537569, 1772336109, 4047884939
        ]
        
        self.check_loop.start()

    def cog_unload(self):
        self.check_loop.cancel()

    @tasks.loop(seconds=30)
    async def check_loop(self):
        await self.bot.wait_until_ready()
        
        try:
            # Запрос списка участников конкретной роли (новые сверху)
            url = f"https://groups.roblox.com/v1/groups/{self.GROUP_ID}/roles/{self.ROLE_ID}/users?limit=50&sortOrder=Desc"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                return
            
            data = response.json().get('data', [])
            if not data:
                return

            members_to_check = []

            if not self.is_initialized:
                # ПЕРВЫЙ ЗАПУСК: Берем 5 самых верхних и запоминаем самого нового
                members_to_check = list(reversed(data[:5]))
                self.is_initialized = True
            else:
                # ПОСЛЕДУЮЩИЕ ПРОВЕРКИ: Ищем индекс прошлого "якоря"
                anchor_index = -1
                for i, member in enumerate(data):
                    if member['user']['userId'] == self.last_top_user_id:
                        anchor_index = i
                        break
                
                if anchor_index == -1:
                    # Если якорь не найден (ушел за пределы 50 записей), проверяем только топ-1
                    members_to_check = [data[0]]
                elif anchor_index > 0:
                    # Берем всех, кто выше якоря (от 0 до индекса якоря)
                    new_entries = data[0:anchor_index]
                    members_to_check = list(reversed(new_entries))

            # Проходим по списку новых людей
            for member in members_to_check:
                rbx_id = member['user']['userId']
                username = member['user']['username']
                
                risk_data = self.perform_risk_check(rbx_id)
                if risk_data:
                    # Дата вступления в группу
                    group_join_raw = member.get('created', 'Unknown')
                    risk_data['group_join'] = group_join_raw[:10] if group_join_raw != 'Unknown' else 'N/A'
                    await self.send_report(username, rbx_id, risk_data)

            # Обновляем ID самого верхнего юзера для следующей проверки
            self.last_top_user_id = data[0]['user']['userId']

        except Exception as e:
            await self.log_error(f"Loop error: {str(e)}")

    def perform_risk_check(self, rbx_id):
        risk = 0
        reasons = []
        try:
            # Запросы к API Roblox для анализа
            u_info = requests.get(f"https://users.roblox.com/v1/users/{rbx_id}").json()
            f_info = requests.get(f"https://friends.roblox.com/v1/users/{rbx_id}/friends/count").json()
            b_info = requests.get(f"https://badges.roblox.com/v1/users/{rbx_id}/badges?limit=10").json()
            a_info = requests.get(f"https://avatar.roblox.com/v1/users/{rbx_id}/avatar").json()

            results = {}
            
            # 1. Возраст аккаунта
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
            
            # 2. Проверка Аватара
            equipped = a_info.get('assets', [])
            ignored_types = ['Torso', 'LeftArm', 'RightArm', 'LeftLeg', 'RightLeg', 'Head']
            clothing_ids = [str(a.get('id')) for a in equipped if a.get('assetType', {}).get('name') not in ignored_types]
            
            if clothing_ids:
                matches = sum(1 for item_id in clothing_ids if int(item_id) in self.STARTER_ASSET_IDS)
                match_percent = (matches / len(clothing_ids)) * 100
                if match_percent >= 75: 
                    risk += 35
                    reasons.append(f"Starter items match ({round(match_percent)}%)")
            else:
                risk += 30
                reasons.append("Empty avatar (No assets)")

            # 3. Друзья
            friends = f_info.get('count', 0)
            if friends < 5:
                risk += 40
                reasons.append("Extremely low friends (<5)")
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
        channel = self.bot.get_channel(self.REPORT_CHANNEL_ID)
        if not channel:
            return

        risk = data['total_risk']
        color = discord.Color.green() if risk < 40 else discord.Color.gold() if risk < 75 else discord.Color.red()

        # Твое форматирование меню
        embed = discord.Embed(title=f"🛡️ AltDetector Checkup", color=color)
        embed.add_field(name="Username:", value=f"**{username}**", inline=True)
        embed.add_field(name="User ID:", value=f"`{rbx_id}`", inline=True)
        embed.add_field(name="Roblox join:", value=f"{data['join_date']} ({data['age_days']} days)", inline=False)
        embed.add_field(name="Risk:", value=f"**{risk}%**", inline=True)
        embed.add_field(name="Reason:", value=data['reasons'], inline=False)

        await channel.send(embed=embed)

    async def log_error(self, error_msg):
        channel = self.bot.get_channel(self.ERROR_CHANNEL_ID)
        if channel:
            await channel.send(f"❌ **System Error (AltDetector)**: {error_msg}")

async def setup(bot):
    await bot.add_cog(AltDetector(bot))
                
