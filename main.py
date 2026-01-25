import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from dotenv import load_dotenv
import time
import asyncio
from discord.ext import tasks

# ================= LOAD ENV =================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))

# ================= OWNER LOCK =================
OWNER_ID = 1406313503278764174  # ONLY this ID can use /redban and /redlist

# ================= FILE =================
REDLIST_FILE = "redlist.json"
TODO_CHANNEL_ID = 1458400694682783775   # channel where ping happens
TODO_FILE = "todo_status.json"
MEMBERS_FILE = "members.json"

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

def load_todo():
    if not os.path.exists(TODO_FILE):
        return {}
    with open(TODO_FILE, "r") as f:
        return json.load(f)

def save_todo(data):
    with open(TODO_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_active_members():
    if not os.path.exists(MEMBERS_FILE):
        return []
    with open(MEMBERS_FILE, "r") as f:
        return json.load(f)

# ================= READY =================
@bot.event
async def on_ready():
    try:
        await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"🔥 RedBan Bot logged in as {bot.user}. Commands synced.")
    except discord.errors.Forbidden as e:
        print(f"❌ Command sync failed: {e}. Check bot invite scopes (applications.commands required).")
    if not todo_ping_check.is_running():
        todo_ping_check.start()

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
    except discord.NotFound:
        pass  # user not in server yet
    except discord.Forbidden as e:
        print(f"❌ Ban failed (permissions): {e}")
    except Exception as e:
        print(f"❌ Unexpected ban error: {e}")

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

class TodoModal(discord.ui.Modal, title="📝 Daily Todo Form"):
    name = discord.ui.TextInput(label="Your Name", required=True)
    date = discord.ui.TextInput(label="Date (DD/MM/YYYY)", required=True)
    must_do = discord.ui.TextInput(label="Must Do", style=discord.TextStyle.paragraph)
    can_do = discord.ui.TextInput(label="Can Do", style=discord.TextStyle.paragraph)
    dont_do = discord.ui.TextInput(label="Don't Do", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        data = load_todo()
        data[str(interaction.user.id)] = int(time.time())
        save_todo(data)

        await interaction.response.send_message(
            "✅ Todo submitted successfully.\n⏳ Ping timer reset.",
            ephemeral=True
        )

@bot.tree.command(
    name="todo",
    description="Submit your daily todo",
    guild=discord.Object(id=GUILD_ID)
)
async def todo(interaction: discord.Interaction):
    if interaction.user.bot:
        return
    await interaction.response.send_modal(TodoModal())

@tasks.loop(hours=1)
async def todo_ping_check():
    if not bot.is_ready():
        return
    channel = bot.get_channel(TODO_CHANNEL_ID)
    if not channel:
        return

    data = load_todo()
    active_members = load_active_members()
    now = int(time.time())

    for user_id in active_members:
        member = channel.guild.get_member(int(user_id))

        # User left server or is bot
        if not member or member.bot:
            continue

        last_time = data.get(str(member.id), 0)

        if now - last_time >= 86400:  # 24 hours
            await channel.send(
                f"{member.mention} ⏰ Please submit your `/todo`",
                allowed_mentions=discord.AllowedMentions(users=[member])
            )

# ================= RUN BOT =================
bot.run(TOKEN)