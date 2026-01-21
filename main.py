import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from dotenv import load_dotenv
import time

# ================= LOAD ENV =================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))

# ================= OWNER LOCK =================
OWNER_ID = 1406313503278764174  # ONLY this ID can use /redban and /redlist

# ================= FILE =================
REDLIST_FILE = "redlist.json"

# ================= INTENTS =================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= UTIL FUNCTIONS =================
def load_redlist():
    if not os.path.exists(REDLIST_FILE):
        return []
    with open(REDLIST_FILE, "r") as f:
        return json.load(f)

def save_redlist(data):
    with open(REDLIST_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ================= READY =================
@bot.event
async def on_ready():
    try:
        await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"🔥 RedBan Bot logged in as {bot.user}. Commands synced.")
    except discord.errors.Forbidden as e:
        print(f"❌ Command sync failed: {e}. Check bot invite scopes (applications.commands required).")

# ================= /REDBAN COMMAND =================
@bot.tree.command(
    name="redban",
    description="Owner-only: Red list & auto-ban by user ID",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(userid="Discord User ID to red-list")
async def redban(interaction: discord.Interaction, userid: str):

    # 🔒 OWNER CHECK
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message(
            "❌ You are not authorized to use this command.",
            ephemeral=True
        )
        return

    # Validate ID
    if not userid.isdigit() or not (17 <= len(userid) <= 20):
        await interaction.response.send_message(
            "❌ Invalid Discord User ID.",
            ephemeral=True
        )
        return

    redlist = load_redlist()

    if userid in redlist:
        await interaction.response.send_message(
            "⚠️ User already exists in red list.",
            ephemeral=True
        )
        return

    redlist.append(userid)
    save_redlist(redlist)

    # Try banning immediately if in server
    try:
        await interaction.guild.ban(
            discord.Object(id=int(userid)),
            reason="Red List"
        )
    except:
        pass  # user not in server yet

    await interaction.response.send_message(
        f"🚫 User **{userid}** added to red list.\nAuto-ban enabled."
    )

# ================= /REDLIST COMMAND =================
@bot.tree.command(
    name="redlist",
    description="Owner-only: Show the IDs in the red list",
    guild=discord.Object(id=GUILD_ID)
)
async def redlist_command(interaction: discord.Interaction):
    # 🔒 OWNER CHECK
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message(
            "❌ You are not authorized to use this command.",
            ephemeral=True
        )
        return

    redlist = load_redlist()

    if not redlist:
        await interaction.response.send_message(
            "📋 The red list is currently empty.",
            ephemeral=True
        )
        return

    # Format the list nicely
    formatted_list = "\n".join([f"- {user_id}" for user_id in redlist])
    message = f"📋 Red List IDs:\n{formatted_list}"

    # Split message if too long (Discord limit ~2000 chars)
    if len(message) > 1900:
        await interaction.response.send_message(
            "📋 The red list is too long to display in one message. Check the file directly.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            message,
            ephemeral=True
        )

# ================= AUTO BAN ON JOIN =================
@bot.event
async def on_member_join(member):
    redlist = load_redlist()
    if str(member.id) in redlist:
        try:
            await member.ban(reason="Red List")
            print(f"🚫 Auto-banned {member.id}")
        except Exception as e:
            print("❌ Auto-ban failed:", e)

# =============== AUTO PING (ABSOLUTE SINGLE-PING FIX) ==================

TARGET_CHANNEL_ID = 1458400694682783775
CRYSTAL_ROLE_ID = 1458400797133115474
IGNORED_BOT_ID = 1460114117783195841  # bot to ignore

ping_allowed = True  # global state lock

@bot.event
async def on_message(message):
    global ping_allowed

    # ❌ ignore all bots
    if message.author.bot:
        return

    # ❌ ignore specific bot ID
    if message.author.id == IGNORED_BOT_ID:
        return

    # ❌ ignore webhooks
    if message.webhook_id is not None:
        return

    # ❌ only target channel
    if message.channel.id != TARGET_CHANNEL_ID:
        return

    role = message.guild.get_role(CRYSTAL_ROLE_ID)
    if not role:
        return

    # 🔁 RESET only when crystal speaks
    if role in message.author.roles:
        ping_allowed = True
        return

    # 🔒 HARD LOCK — already pinged
    if ping_allowed is False:
        return

    # ✅ FIRST VALID USER MESSAGE → PING ONCE
    ping_allowed = False  # lock BEFORE sending (IMPORTANT)

    await message.channel.send(
        f"{role.mention} in discord, share todo list",
        allowed_mentions=discord.AllowedMentions(roles=[role])
    )

    return  # 🛑 HARD STOP — prevents second ping



# ================= RUN BOT =================
bot.run(TOKEN)