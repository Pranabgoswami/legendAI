import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from dotenv import load_dotenv

# ================= LOAD ENV =================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))

# ================= OWNER LOCK =================
OWNER_ID = 1406313503278764174  # ONLY this ID can use /redban

# ================= FILE =================
REDLIST_FILE = "redlist.json"

# ================= INTENTS =================
intents = discord.Intents.default()
intents.members = True

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
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"🔥 RedBan Bot logged in as {bot.user}")

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

# ================= RUN BOT =================
bot.run(TOKEN)
