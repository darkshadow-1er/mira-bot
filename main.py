import discord
import requests
import json
import os
import time
from threading import Thread
from flask import Flask

# ---------------- ANTI-SLEEP (RENDER) ----------------

app = Flask(__name__)

@app.route('/')
def home():
    return "Mira is alive"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

def auto_ping():
    url = os.getenv("RENDER_EXTERNAL_URL")
    while True:
        try:
            if url:
                requests.get(url)
        except:
            pass
        time.sleep(300)  # 5 minutes

keep_alive()
Thread(target=auto_ping).start()

# ---------------- CONFIG ----------------

API_KEY = os.getenv("API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

MEMORY_FILE = "memory.json"
PREFIX = "mira"
COOLDOWN = 2

url = "https://api.groq.com/openai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

MAX_MEMORY = 10
last_used = {}

# ---------------- MEMORY ----------------

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_memory(data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f)

memory = load_memory()

def get_user_memory(user_id):
    user_id = str(user_id)

    if user_id not in memory:
        memory[user_id] = [{
            "role": "system",
            "content": (
                "Tu es Mira, une IA Discord féminine naturelle. "
                "Tu parles comme une vraie personne (style WhatsApp). "
                "Réponses courtes, humaines, fluides. "
                "Tu es expressive, légère et intelligente."
            )
        }]

    return memory[user_id]

def trim_memory(user_id):
    user_id = str(user_id)
    memory[user_id] = [memory[user_id][0]] + memory[user_id][-MAX_MEMORY:]

# ---------------- BOT ----------------

@client.event
async def on_ready():
    print(f"🔥 Mira active : {client.user}")

@client.event
async def on_message(message):

    if message.author == client.user:
        return

    user_id = str(message.author.id)
    content = message.content.strip()

    # DM = toujours actif
    if isinstance(message.channel, discord.DMChannel):
        user_input = content

    # serveur = seulement avec "mira"
    else:
        if not content.lower().startswith(PREFIX):
            return
        user_input = content[len(PREFIX):].strip()

    # cooldown anti spam
    now = time.time()
    if user_id in last_used and now - last_used[user_id] < COOLDOWN:
        return
    last_used[user_id] = now

    if not user_input:
        await message.channel.send("Oui ? 😊")
        return

    # reset mémoire
    if user_input.lower() == "/reset":
        memory[user_id] = memory[user_id][:1]
        save_memory(memory)
        await message.channel.send("Mémoire reset ✔")
        return

    user_memory = get_user_memory(user_id)

    user_memory.append({"role": "user", "content": user_input})
    trim_memory(user_id)

    data = {
        "model": "llama-3.1-8b-instant",
        "messages": user_memory,
        "max_tokens": 120,
        "temperature": 0.9
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)
        result = response.json()

        if "choices" not in result:
            await message.channel.send("Hmm... bug 😅")
            return

        reply = result["choices"][0]["message"]["content"]

        if len(reply) > 300:
            reply = reply[:300] + "..."

        user_memory.append({"role": "assistant", "content": reply})
        trim_memory(user_id)
        save_memory(memory)

        await message.channel.send(reply)

    except Exception as e:
        print("ERROR:", e)
        await message.channel.send("Petit bug... 😅")

client.run(DISCORD_TOKEN)
