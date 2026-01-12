import discord
from discord import app_commands
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

client_openai = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# 🛡️ SAFETY LIST: Removed all "Llama" models to prevent 404 errors.
# We only use the two most stable models now.
AI_MODELS = [
    "google/gemini-2.0-flash-exp:free",      # Priority 1: Smartest for NEET
    "mistralai/mistral-7b-instruct:free",    # Priority 2: Never fails
    "microsoft/phi-3-mini-128k-instruct:free"# Priority 3: Backup
]

class LegendAI(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Slash commands synced")

client = LegendAI()

@client.event
async def on_ready():
    print(f"🔥 legendAI online as {client.user}")

@client.tree.command(name="ai", description="Ask legendAI (Stable Version)")
@app_commands.describe(prompt="Your question")
async def ai(interaction: discord.Interaction, prompt: str):
    
    # 1. Prevent "Unknown Interaction" Crash
    try:
        await interaction.response.defer()
    except:
        return 

    # 2. Try only the working models
    success = False
    for model_id in AI_MODELS:
        try:
            response = await client_openai.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                timeout=15.0
            )

            reply = response.choices[0].message.content
            if len(reply) > 1900: reply = reply[:1900] + "..."
            
            await interaction.followup.send(f"{reply}\n\n*⚡ Answered by:legendAI*")
            success = True
            break 

        except Exception:
            continue 

    if not success:
        await interaction.followup.send("⚠️ All AIs are busy. Please wait 2 minutes.")

client.run(DISCORD_TOKEN)