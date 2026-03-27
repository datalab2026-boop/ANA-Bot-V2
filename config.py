import os

# Токены
DISCORD_TOKEN = os.environ.get("Bottoken")
ROBLOX_API_KEY = os.environ.get("Apitoken")
RESTART_TOKEN = os.environ.get("Restarttoken")

# Настройки каналов и ролей
GROUP_ID = 841435331
ALLOWED_ROLE_ID = 1479884336051388604  # ID роли в Discord, которой можно юзать команды
LOG_CHANNEL_ID = 1481718190961590392

# Словари рангов
ROLE_IDS = {
    "Guest": 601712008,
    "『SR』Seaman Recruit": 627311089,
    "『SA』Seaman Apprentice": 626371120,
    "『SM』Seaman": 625449142,
    "『SS』Senior Seaman": 626739123,
    "『PO』Petty Officer": 625591116,
    "『CPO』Chief Petty Officer": 625249228,
    "『SC』Senior Chief": 626151118,
    "『MC』Master Chief": 621855265,
    "『DEV』Developer": 601712009,
    "『OOT』Officer On Trial": 625687178,
    "『ENS』Ensign": 626819052,
    "『LT』Lieutenant": 626001157,
    "『COM』Commodore": 625657188,
    "『CAPT』Captain": 625233175,
    "『FCDR』Fleet Commande": 601712006,
    "Admiral": 601712007
}

VALID_ROLES = [
    "『SR』Seaman Recruit", "『SA』Seaman Apprentice", "『SM』Seaman", 
    "『SS』Senior Seaman", "『PO』Petty Officer", "『CPO』Chief Petty Officer",
    "『SC』Senior Chief", "『MC』Master Chief", "『DEV』Developer",
    "『OOT』Officer On Trial", "『ENS』Ensign", "『LT』Lieutenant",
    "『COM』Commodore", "『CAPT』Captain", "『FCDR』Fleet Commande"
]
