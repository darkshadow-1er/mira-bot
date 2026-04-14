import discord
import requests
import json
import os
import time
from threading import Thread
from flask import Flask

# ---------------- WEB KEEP ALIVE ----------------

app = Flask(__name__)

@app.route('/')
def home():
    return "Mira Elite is alive"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_web).start()

# ---------------- CONFIG ----------------

API_KEY = os.getenv("API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

PREFIX = "mira"
MEMORY_FILE = "memory.json"
COOLDOWN = 2
MAX_MEMORY = 6

url = "https://api.groq.com/openai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

intents = discord.Intents.all()
client = discord.Client(intents=intents)

memory = {}
last_used = {}

# ---------------- MEMORY SMART ----------------

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_memory():
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f)

memory = load_memory()

def base_prompt():
    return {
        "role": "system",
        "content": (
            "Tu es Mira, une IA Discord féminine, calme et intelligente. "
            "Tu écris en français correct, sans faute. "
            "Tu ne répètes jamais. "
            "Tu réponds uniquement au message actuel. "
            "Tu ne ramènes jamais d’anciens sujets sans raison. "
            "Tu es naturelle, concise et humaine."
        )
    }

def get_memory(user_id):
    user_id = str(user_id)

    if user_id not in memory:
        memory[user_id] = {
            "messages": [base_prompt()],
            "last_topic": ""
        }

    return memory[user_id]

def clean_memory(user_id):
    user_id = str(user_id)
    data = memory[user_id]

    data["messages"] = [data["messages"][0]] + data["messages"][-MAX_MEMORY:]

# ---------------- FILTRE RAPIDE ----------------

def quick_reply(msg):
    msg = msg.lower().strip()

    if msg in ["salut", "cc", "yo", "hello"]:
        return "Salut 🙂"

    if msg in ["ça va", "cv"]:
        return "Oui ça va, et toi ?"

    return None

# ---------------- IA ----------------

def ask_ai(messages):
    data = {
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": 200
    }

    r = requests.post(url, headers=headers, json=data, timeout=20)
    res = r.json()

    if "choices" not in res:
        return "Petit bug 😅"

    return res["choices"][0]["message"]["content"].strip()

# ---------------- COMMANDES ----------------

async def handle_command(message, cmd, args):

    # 🔧 ADMIN CLEAR
    if cmd == "clear":
        if message.author.guild_permissions.manage_messages:
            await message.channel.purge(limit=int(args[0]) if args else 10)
            await message.channel.send("Nettoyage effectué ✔", delete_after=3)
        return True

    # 👢 KICK
    if cmd == "kick":
        if message.author.guild_permissions.kick_members:
            if message.mentions:
                await message.mentions[0].kick()
                await message.channel.send("Utilisateur expulsé ✔")
        return True

    # 🔨 BAN
    if cmd == "ban":
        if message.author.guild_permissions.ban_members:
            if message.mentions:
                await message.mentions[0].ban()
                await message.channel.send("Utilisateur banni ✔")
        return True

    # 🧠 RESET MEMOIRE
    if cmd == "reset":
        uid = str(message.author.id)
        memory[uid] = {
            "messages": [base_prompt()],
            "last_topic": ""
        }
        save_memory()
        await message.channel.send("Mémoire effacée ✔")
        return True

    # 🎭 MODE RP
    if cmd == "rp":
        uid = str(message.author.id)
        memory[uid]["messages"][0]["content"] += " Tu es immersive et expressive (mode RP activé)."
        await message.channel.send("Mode RP activé 🎭")
        return True

    # 📜 HELP
    if cmd == "help":
        await message.channel.send(
            "**Commandes Mira :**\n"
            "mira clear [nb]\n"
            "mira kick @user\n"
            "mira ban @user\n"
            "mira reset\n"
            "mira rp\n"
        )
        return True

    return False

# ---------------- BOT ----------------

@client.event
async def on_ready():
    print(f"🔥 Mira Elite prête : {client.user}")

@client.event
async def on_message(message):

    if message.author.bot:
        return

    content = message.content.strip()
    user_id = str(message.author.id)

    # PREFIX
    if not content.lower().startswith(PREFIX):
        return

    parts = content[len(PREFIX):].strip().split()
    if not parts:
        await message.channel.send("Oui ?")
        return

    cmd = parts[0].lower()
    args = parts[1:]

    # cooldown
    now = time.time()
    if user_id in last_used and now - last_used[user_id] < COOLDOWN:
        return
    last_used[user_id] = now

    # COMMANDES
    if await handle_command(message, cmd, args):
        return

    user_input = " ".join(parts)

    # réponse rapide
    quick = quick_reply(user_input)
    if quick:
        await message.channel.send(quick)
        return

    # mémoire intelligente
    data = get_memory(user_id)

    # 🔥 détection nouveau sujet simple
    if len(user_input.split()) < 4:
        data["messages"] = [data["messages"][0]]

    data["messages"].append({"role": "user", "content": user_input})
    clean_memory(user_id)

    reply = ask_ai(data["messages"])

    # anti répétition
    if data["messages"][-1]["content"] == reply:
        reply = "Je reformule : " + reply

    data["messages"].append({"role": "assistant", "content": reply})

    save_memory()

    if len(reply) > 2000:
        reply = reply[:1990] + "..."

    await message.channel.send(reply)

client.run(DISCORD_TOKEN)
