import discord
from discord.ext import tasks, commands
import requests
from datetime import datetime, timezone
import config

class AgeCheck(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # В v2 API для пагинации часто используется pageToken, 
        # но мы будем использовать время, чтобы отсекать старые события.
        self.last_event_time = datetime.now(timezone.utc)
        
        self.GROUP_ID = config.GROUP_ID
        self.CLOUD_API = config.ROBLOX_API_KEY
        # В Open Cloud заголовок обычно x-api-key
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
            # Используем Open Cloud API v2 для Audit Log
            # Фильтр: только вступления (member-join)
            url = f"https://apis.roblox.com/cloud/v2/groups/{self.GROUP_ID}/audit-log"
            params = {
                "filter": "action_type == 'member-join'",
                "max_page_size": 10
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code != 200:
                await self.log_error(f"API Error {response.status_code}: {response.text}")
                return
            
            data = response.json().get('groupAuditLogEvents', [])
            if not data:
                return

            newest_event_time = self.last_event_time

            # Обрабатываем события
            for entry in data:
                # В v2 время в формате "2023-10-12T15:30:00.123456Z"
                event_time_str = entry.get('createTime').replace('Z', '+00:00')
                event_time = datetime.fromisoformat(event_time_str)

                # Проверяем, новое ли это событие
                if event_time <= self.last_event_time:
                    continue
                
                if event_time > newest_event_time:
                    newest_event_time = event_time

                # В v2 данные пользователя лежат в поле user
                # Формат ресурса пользователя: "users/123456"
                user_resource = entry.get('user', '')
                rbx_id = user_resource.split('/')[-1] if user_resource else None
                
                if not rbx_id:
                    continue

                # Получаем имя пользователя (v2 возвращает только ID, имя берем отдельно)
                user_info_req = requests.get(f"https://users.roblox.com/v1/users/{rbx_id}")
                username = user_info_req.json().get('name', 'Unknown')

                risk_data = self.perform_risk_check(rbx_id)
                
                if risk_data:
                    risk_data['group_join'] = event_time_str[:10]
                    await self.send_report(username, rbx_id, risk_data)
            
            self.last_event_time = newest_event_time

        except Exception as e:
            await self.log_error(f"Ошибка в цикле: {str(e)}")

    def perform_risk_check(self, rbx_id):
        # Метод остается без изменений, так как он использует публичные v1 API, 
        # которые не требуют ключей для базовой инфы
        risk = 0
        reasons = []
        try:
            u_info = requests.get(f"https://users.roblox.com/v1/users/{rbx_id}").json()
            f_info = requests.get(f"https://friends.roblox.com/v1/users/{rbx_id}/friends/count").json()
            b_info = requests.get(f"https://badges.roblox.com/v1/users/{rbx_id}/badges?limit=10").json()
            a_info = requests.get(f"https://avatar.roblox.com/v1/users/{rbx_id}/avatar").json()

            results = {}
            
            created_str = u_info.get('created')
            if created_str:
                created_dt = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                age_days = (datetime.now(timezone.utc) - created_dt).days
                results['age_days'] = age_days
                results['join_date'] = created_str[:10]
                
                if age_days < 14: 
                    risk += 60
                    reasons.append("Меньше 2 недель")
                elif age_days < 30: 
                    risk += 25
                    reasons.append("Меньше 1 месяца")
            
            equipped = a_info.get('assets', [])
            ignored = ['Torso', 'LeftArm', 'RightArm', 'LeftLeg', 'RightLeg', 'Head']
            clothing = [str(a['id']) for a in equipped if a.get('assetType', {}).get('name') not in ignored]
            
            if clothing:
                matches = sum(1 for item_id in clothing if int(item_id) in self.STARTER_ASSET_IDS)
                if matches >= 2: 
                    risk += 35
                    reasons.append("Стартовый аватар")
                results['clothing_list'] = ", ".join(clothing)
            else:
                risk += 30
                reasons.append("Пустой аватар")
                results['clothing_list'] = "Ничего не надето"

            friends = f_info.get('count', 0)
            results['friends'] = friends
            if friends < 5:
                risk += 40
                reasons.append("Почти нет друзей")

            badges = b_info.get('data', [])
            if len(badges) < 3:
                risk += 20
                reasons.append("Мало бейджей")

            results['reasons'] = ", ".join(reasons) if reasons else "Чистый аккаунт"
            results['total_risk'] = min(risk, 100)
            return results
        except Exception as e:
            print(f"Ошибка проверки {rbx_id}: {e}")
            return None

    async def send_report(self, username, rbx_id, data):
        channel = self.bot.get_channel(self.REPORT_CHANNEL_ID)
        if not channel: return

        risk = data['total_risk']
        color = discord.Color.green() if risk < 40 else discord.Color.gold() if risk < 75 else discord.Color.red()

        embed = discord.Embed(title=f"🛡️ Проверка: {username}", color=color, timestamp=datetime.now())
        embed.set_thumbnail(url=f"https://www.roblox.com/headshot-thumbnail/image?userId={rbx_id}&width=420&height=420&format=png")
        
        embed.add_field(name="Аккаунт:", value=f"[{username}](https://www.roblox.com/users/{rbx_id}/profile)", inline=True)
        embed.add_field(name="ID:", value=f"`{rbx_id}`", inline=True)
        embed.add_field(name="Риск:", value=f"**{risk}%**", inline=True)
        embed.add_field(name="Создан:", value=f"{data['join_date']} ({data['age_days']} дн.)", inline=True)
        embed.add_field(name="Причины:", value=f"```fix\n{data['reasons']}```", inline=False)

        await channel.send(embed=embed)

    async def log_error(self, error_msg):
        channel = self.bot.get_channel(self.ERROR_CHANNEL_ID)
        if channel:
            await channel.send(f"❌ **Системная ошибка**: {error_msg}")

async def setup(bot):
    await bot.add_cog(AgeCheck(bot))
    
