import discord
from discord.ext import tasks, commands
import requests
from datetime import datetime, timezone
import config

class AgeCheck(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Храним ID последней записи лога, чтобы не проверять одних и тех же
        self.last_checked_log_id = None
        
        # Настройки из config.py
        self.GROUP_ID = config.GROUP_ID
        self.CLOUD_API = config.ROBLOX_API_KEY
        self.headers = {"x-api-key": self.CLOUD_API}
        
        # Каналы (ID из твоего примера)
        self.REPORT_CHANNEL_ID = 1480592830870192329
        self.ERROR_CHANNEL_ID = 1480592830870192329

        # ID стартовых вещей Roblox для детекта пустых аккаунтов
        self.STARTER_ASSET_IDS = [
            62724852, 144076436, 144076512, 10638267973, 10647852134, 
            382537569, 1772336109, 4047884939, 10638267973, 10647852134
        ]
        
        self.check_loop.start()

    def cog_unload(self):
        self.check_loop.cancel()

    @tasks.loop(seconds=60)
    async def check_loop(self):
        await self.bot.wait_until_ready()
        
        try:
            # Используем Audit Log для поиска новых участников
            # actionType=MemberJoined (тип 8)
            url = f"https://groups.roblox.com/v1/groups/{self.GROUP_ID}/audit-log?actionType=MemberJoined&limit=10&sortOrder=Desc"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                # Если ошибка 403 — проверь права API ключа (нужен View Audit Logs)
                if response.status_code == 403:
                    await self.log_error("Ошибка 403: У API ключа нет прав на просмотр Audit Log группы.")
                return
            
            data = response.json().get('data', [])
            if not data:
                return

            # Сортируем от старых к новым, чтобы корректно обновлять last_checked_log_id
            for entry in reversed(data):
                log_id = entry['id']
                
                # Если мы это уже видели — пропускаем
                if self.last_checked_log_id and log_id <= self.last_checked_log_id:
                    continue

                # В событии MemberJoined 'actor' — это тот, кто вступил
                user_data = entry.get('actor', {}).get('user', {})
                rbx_id = user_data.get('userId')
                username = user_data.get('username')
                group_join_time = entry.get('created', 'Unknown')

                if not rbx_id:
                    continue

                # Запускаем проверку рисков
                risk_data = self.perform_risk_check(rbx_id)
                
                if risk_data:
                    risk_data['group_join'] = group_join_time[:10]
                    await self.send_report(username, rbx_id, risk_data)
                
                # Обновляем маркер последней проверки
                self.last_checked_log_id = log_id

        except Exception as e:
            await self.log_error(f"Ошибка в цикле аудита: {str(e)}")

    def perform_risk_check(self, rbx_id):
        risk = 0
        reasons = []
        try:
            # Собираем данные из разных API Roblox
            u_info = requests.get(f"https://users.roblox.com/v1/users/{rbx_id}").json()
            f_info = requests.get(f"https://friends.roblox.com/v1/users/{rbx_id}/friends/count").json()
            b_info = requests.get(f"https://badges.roblox.com/v1/users/{rbx_id}/badges?limit=10").json()
            a_info = requests.get(f"https://avatar.roblox.com/v1/users/{rbx_id}/avatar").json()

            results = {}
            
            # 1. Проверка даты создания
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
                elif age_days < 90: 
                    risk += 10
                    reasons.append("Меньше 3 месяцев")
            
            # 2. Анализ аватара
            equipped = a_info.get('assets', [])
            # Игнорируем стандартные части тела
            ignored = ['Torso', 'LeftArm', 'RightArm', 'LeftLeg', 'RightLeg', 'Head']
            clothing = [str(a['id']) for a in equipped if a.get('assetType', {}).get('name') not in ignored]
            
            if clothing:
                matches = sum(1 for item_id in clothing if int(item_id) in self.STARTER_ASSET_IDS)
                match_percent = (matches / len(clothing)) * 100
                if match_percent >= 70: 
                    risk += 35
                    reasons.append(f"Стартовый аватар ({round(match_percent)}%)")
                results['clothing_list'] = ", ".join(clothing)
            else:
                risk += 30
                reasons.append("Пустой аватар")
                results['clothing_list'] = "Ничего не надето"

            # 3. Друзья
            friends = f_info.get('count', 0)
            results['friends'] = friends
            if friends < 5:
                risk += 40
                reasons.append("Почти нет друзей (<5)")
            elif friends < 15:
                risk += 15
                reasons.append("Мало друзей")

            # 4. Бейджи
            badges = b_info.get('data', [])
            if len(badges) < 3:
                risk += 20
                reasons.append("Мало игровых бейджей")

            results['reasons'] = ", ".join(reasons) if reasons else "Чистый аккаунт"
            results['total_risk'] = min(risk, 100)
            return results
        except Exception as e:
            print(f"Ошибка проверки игрока {rbx_id}: {e}")
            return None

    async def send_report(self, username, rbx_id, data):
        channel = self.bot.get_channel(self.REPORT_CHANNEL_ID)
        if not channel:
            return

        risk = data['total_risk']
        # Выбор цвета: Зеленый -> Оранжевый -> Красный
        color = discord.Color.green() if risk < 40 else discord.Color.gold() if risk < 75 else discord.Color.red()

        embed = discord.Embed(title=f"🛡️ Проверка: {username}", color=color, timestamp=datetime.now())
        embed.set_thumbnail(url=f"https://www.roblox.com/headshot-thumbnail/image?userId={rbx_id}&width=420&height=420&format=png")
        
        embed.add_field(name="Аккаунт:", value=f"[{username}](https://www.roblox.com/users/{rbx_id}/profile)", inline=True)
        embed.add_field(name="ID:", value=f"`{rbx_id}`", inline=True)
        embed.add_field(name="Риск:", value=f"**{risk}%**", inline=True)
        
        embed.add_field(name="Создан:", value=f"{data['join_date']} ({data['age_days']} дн.)", inline=True)
        embed.add_field(name="Вступил в группу:", value=data['group_join'], inline=True)
        embed.add_field(name="Друзей:", value=str(data.get('friends', 0)), inline=True)
        
        embed.add_field(name="Одетые вещи (IDs):", value=f"`{data.get('clothing_list', 'N/A')[:1000]}`", inline=False)
        embed.add_field(name="Причины подозрения:", value=f"```fix\n{data['reasons']}```", inline=False)

        await channel.send(embed=embed)

    async def log_error(self, error_msg):
        channel = self.bot.get_channel(self.ERROR_CHANNEL_ID)
        if channel:
            await channel.send(f"❌ **Системная ошибка**: {error_msg}")

async def setup(bot):
    await bot.add_cog(AgeCheck(bot))
            
