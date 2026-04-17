import discord
from discord.ext import tasks, commands
import requests
import asyncio
from datetime import datetime, timezone
import config

class AltDetector(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_top_user_id = None  # ID самого верхнего пользователя
        self.is_initialized = False
        
        self.GROUP_ID = config.GROUP_ID
        self.CLOUD_API = config.ROBLOX_API_KEY
        self.headers = {"x-api-key": self.CLOUD_API}
        
        self.ROLE_ID = 593902054
        self.REPORT_CHANNEL_ID = 1494677345263681668
        self.ERROR_CHANNEL_ID = 1494676707955835011

        self.STARTER_ASSET_IDS = [
            62724852, 144076436, 144076512, 10638267973, 10647852134, 
            382537569, 1772336109, 4047884939, 63690008,86500008,86500036,86500054,86500064,86500078,144076358,144076760,10638267973,10647852134
        ]
        
        self.check_loop.start()

    def cog_unload(self):
        self.check_loop.cancel()

    @tasks.loop(seconds=60)
    async def check_loop(self):
        await self.bot.wait_until_ready()
        
        try:
            # Запрос к эндпоинту роли (плоская структура JSON)
            url = f"https://groups.roblox.com/v1/groups/{self.GROUP_ID}/roles/{self.ROLE_ID}/users?limit=50&sortOrder=Desc"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                return
            
            data = response.json().get('data', [])
            if not data:
                return

            members_to_check = []

            # Логика определения новых участников
            if not self.is_initialized:
                # ПРИ СТАРТЕ: Берем 5 самых свежих
                members_to_check = list(reversed(data[:5]))
                self.is_initialized = True
            else:
                # ПОСЛЕ СТАРТА: Ищем индекс предыдущего первого юзера
                found_anchor_index = -1
                for i, member in enumerate(data):
                    # ИСПРАВЛЕНО: Читаем userId напрямую (без ['user'])
                    if member.get('userId') == self.last_top_user_id:
                        found_anchor_index = i
                        break
                
                if found_anchor_index == -1:
                    # Если старый топ не найден, проверяем только самого нового
                    members_to_check = [data[0]]
                else:
                    # Берем всех, кто выше него в списке
                    new_entries = data[0:found_anchor_index]
                    members_to_check = list(reversed(new_entries))

            for member in members_to_check:
                # ИСПРАВЛЕНО: Читаем напрямую из объекта member
                rbx_id = member.get('userId')
                username = member.get('username')
                
                if not rbx_id: continue

                risk_data = self.perform_risk_check(rbx_id)
                if risk_data:
                    risk_data['group_join'] = "N/A" 
                    await self.send_report(username, rbx_id, risk_data)

            # ИСПРАВЛЕНО: Обновляем "якорь" без обращения к ['user']
            if data and len(data) > 0:
                self.last_top_user_id = data[0].get('userId')

        except Exception as e:
            await self.log_error(f"Loop error: {str(e)}")

    def perform_risk_check(self, rbx_id):
        risk = 0
        reasons = []
        try:
            u_info = requests.get(f"https://users.roblox.com/v1/users/{rbx_id}").json()
            f_info = requests.get(f"https://friends.roblox.com/v1/users/{rbx_id}/friends/count").json()
            b_info = requests.get(f"https://badges.roblox.com/v1/users/{rbx_id}/badges?limit=10").json()
            a_info = requests.get(f"https://avatar.roblox.com/v1/users/{rbx_id}/avatar").json()

            results = {}
            
            # Возраст профиля
            created_str = u_info.get('created')
            if created_str:
                created_dt = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                age_days = (datetime.now(timezone.utc) - created_dt).days
                results['age_days'] = age_days
                results['join_date'] = created_str[:10]
                
                if age_days < 14: risk += 60; reasons.append("Account age < 2 weeks")
                elif age_days < 30: risk += 25; reasons.append("Account age < 1 month")
                elif age_days < 90: risk += 10; reasons.append("Account age < 3 months")
            
            # Аватар
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
                risk += 30; reasons.append("Empty avatar (No assets)")

            # Друзья
            friends = f_info.get('count', 0)
            if friends < 5: risk += 40; reasons.append("Extremely low friends (<5)")
            elif friends < 20: risk += 10; reasons.append("Low friends (<20)")

            # Бейджи
            badges = b_info.get('data', [])
            if not b_info.get('nextPageCursor') and len(badges) < 5:
                risk += 15; reasons.append("Lack of badges")

            results['reasons'] = ", ".join(reasons) if reasons else "None"
            results['total_risk'] = min(risk, 100)
            return results
        except:
            return None

    async def send_report(self, username, rbx_id, data):
        channel = self.bot.get_channel(self.REPORT_CHANNEL_ID)
        if not channel: return

        risk = data['total_risk']
        color = discord.Color.green() if risk < 40 else discord.Color.gold() if risk < 75 else discord.Color.red()

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
        
