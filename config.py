import os

# Токены
DISCORD_TOKEN = os.environ.get("Bottoken")
ROBLOX_API_KEY = os.environ.get("Apitoken")
RESTART_TOKEN = os.environ.get("Restarttoken")

# Настройки каналов и ролей
GROUP_ID = 79507695
ALLOWED_ROLE_ID = 1467991343468118170  # ID роли в Discord
LOG_CHANNEL_ID = 1467475314086117459

# Словари рангов
ROLE_IDS = {
    "Guest": 553192051,
    "Member": 12884901889,
    "[C] Cadet": 593902054,
    "[AR] Airman Recruit": 595344014,
    "[JA] Junior Airman": 595748001,
    "[AMN] Airman": 594658030,
    "[SA] Senior Airman": 594682030,
    "[COR] Corporal": 594658029,
    "[SCO] Senior Corporal": 593596019,
    "[JFS] Junior Flight Sergeant": 594976023,
    "[FS] Flight Sergeant": 592992043,
    "[CFS] Chief Flight Sergeant": 592808034,
    "[TO] Trainee Officer": 595150017,
    "[LTJ] Lieutenant Junior": 595324015,
    "[FL] Flight Lieutenant": 593270049,
    "[WC] Wing Commander": 595324014,
    "[SWC] Senior Wing Commander": 592880031,
    "[AM] Air Marshal": 595566023,
    "[CAM] Chief Air Marshal": 592622025,
    "[DEV] Developer": 553100075,
    "[CR] Chief Recruiter": 594188044,
    "[CH] Chief Hoster": 593786039,
    "[BOT] Bot": 552360083,
    "[VSM] Vice Sky Major": 553496092,
    "[SM] Sky Major": 553922096,
    "[VSC] Vice Sky Chief": 553674100,
    "[SC] Sky Chief": 552360145,
    "[DAC] Deputy Aerial Commander": 553518076,
    "[AC] Aerial Commander": 553066065
}

VALID_ROLES = [
    "[C] Cadet", "[AR] Airman Recruit", "[JA] Junior Airman", 
    "[AMN] Airman", "[SA] Senior Airman", "[COR] Corporal", 
    "[SCO] Senior Corporal", "[JFS] Junior Flight Sergeant", 
    "[FS] Flight Sergeant", "[CFS] Chief Flight Sergeant", 
    "[TO] Trainee Officer", "[LTJ] Lieutenant Junior", 
    "[FL] Flight Lieutenant", "[WC] Wing Commander", 
    "[SWC] Senior Wing Commander", "[AM] Air Marshal", 
    "[CAM] Chief Air Marshal"
]
