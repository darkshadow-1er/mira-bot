import discord
import requests
import json
import os
import time
import asyncio
from threading import Thread
from flask import Flask
from collections import deque

# ---------------- WEB ----------------

app = Flask(__name__)

@app.route('/')
def home():
    return "Mira Ultimate is alive"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_web).start()

# ---------------- CONFIG ----------------

API_KEY = os.getenv("API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

PREFIX = "mira"
MEMORY_FILE = "memory.json"
XP_FILE = "xp.json"

MAX_MEMORY = 5
API_DELAY = 2.5
GLOBAL_DELAY = 2.5
USER_DELAY = 5
XP_DELAY = 20

url = "https://api.groq.com/openai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

intents = discord.Intents.all()
client = discord.Client(intents=intents)

memory = {}
xp_data = {}

last_global = 0
user_last = {}
last_message = {}
xp_cooldown = {}

queue = deque()
processing = False

# ---------------- LOAD ----------------

def load_json(file):
    if os.path.exists(file):
        try:
            with open(file, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

memory = load_json(MEMORY_FILE)
xp_data = load_json(XP_FILE)

# ---------------- IA ----------------

def base_prompt():
    return {
        "role": "system",
        "content": (
            "Tu es Mira, une IA Discord calme, intelligente et naturelle. "
            "Tu écris en français parfait, sans faute. "
            "Tu ne répètes jamais. "
            "Tu réponds uniquement au message actuel. "
            "Tu es concise et humaine."
        )
    }

def get_memory(user_id):
    if user_id not in memory:
        memory[user_id] = {"messages": [base_prompt()]}
    return memory[user_id]

def clean_memory(user_id):
    data = memory[user_id]
    data["messages"] = [data["messages"][0]] + data["messages"][-MAX_MEMORY:]

def ask_ai(messages):
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": 120
    }

    r = requests.post(url, headers=headers, json=payload, timeout=20)

    if r.status_code == 429:
        return None

    res = r.json()
    if "choices" not in res:
        return "Petit bug 😅"

    return res["choices"][0]["message"]["content"].strip()

# ---------------- XP ----------------

def add_xp(user_id):
    if user_id not in xp_data:
        xp_data[user_id] = {"xp": 0, "level": 1}

    xp_data[user_id]["xp"] += 10
    need = xp_data[user_id]["level"] * 100

    if xp_data[user_id]["xp"] >= need:
        xp_data[user_id]["xp"] = 0
        xp_data[user_id]["level"] += 1
        return True

    return False

# ---------------- QUEUE ----------------

async def process_queue():
    global processing, last_global

    if processing:
        return

    processing = True

    while queue:
        message, user_id, user_input = queue.popleft()

        try:
            now = time.time()

            if now - last_global < GLOBAL_DELAY:
                await asyncio.sleep(GLOBAL_DELAY)

            last_global = time.time()

            data = get_memory(user_id)

            if len(user_input.split()) < 4:
                data["messages"] = [data["messages"][0]]

            data["messages"].append({"role": "user", "content": user_input})
            clean_memory(user_id)

            reply = ask_ai(data["messages"])

            if reply is None:
                await message.channel.send("Je vais trop vite 😅")
                await asyncio.sleep(3)
                continue

            data["messages"].append({"role": "assistant", "content": reply})
            save_json(MEMORY_FILE, memory)

            async with message.channel.typing():
                await asyncio.sleep(1.5)
                await message.channel.send(reply)

            await asyncio.sleep(API_DELAY)

        except Exception as e:
            print("ERROR:", e)

    processing = False

# ---------------- COMMANDES ----------------

async def handle_command(message, cmd, args):
    uid = str(message.author.id)

    # LEVEL
    if cmd == "level":
        if uid not in xp_data:
            xp_data[uid] = {"xp": 0, "level": 1}
        await message.channel.send(f"Niveau {xp_data[uid]['level']} | XP {xp_data[uid]['xp']}")
        return True

    # TOP
    if cmd == "top":
        top = sorted(xp_data.items(), key=lambda x: x[1]["level"], reverse=True)[:5]
        msg = "🏆 Classement :\n"
        for i, (u, d) in enumerate(top, 1):
            msg += f"{i}. <@{u}> - Niveau {d['level']}\n"
        await message.channel.send(msg)
        return True

    # CLEAR
    if cmd == "clear" and message.author.guild_permissions.manage_messages:
        await message.channel.purge(limit=int(args[0]) if args else 10)
        return True

    # KICK
    if cmd == "kick" and message.author.guild_permissions.kick_members:
        if message.mentions:
            await message.mentions[0].kick()
            await message.channel.send("Utilisateur expulsé ✔")
        return True

    # BAN
    if cmd == "ban" and message.author.guild_permissions.ban_members:
        if message.mentions:
            await message.mentions[0].ban()
            await message.channel.send("Utilisateur banni ✔")
        return True

    # HELP
    if cmd == "help":
        await message.channel.send(
            "Commandes :\n"
            "mira level\nmira top\nmira clear\nmira kick\nmira ban\n"
        )
        return True

    return False

# ---------------- BOT ----------------

@client.event
async def on_ready():
    print(f"Mira Ultimate prête : {client.user}")

@client.event
async def on_message(message):

    if message.author.bot:
        return

    content = message.content.strip()
    user_id = str(message.author.id)

    if len(content) < 3:
        return

    if not content.lower().startswith(PREFIX):
        return

    user_input = content[len(PREFIX):].strip()

    if not user_input:
        return

    now = time.time()

    if user_id in user_last and now - user_last[user_id] < USER_DELAY:
        return
    user_last[user_id] = now

    if user_id in last_message and last_message[user_id] == user_input:
        return
    last_message[user_id] = user_input

    # XP
    if user_id not in xp_cooldown or now - xp_cooldown[user_id] > XP_DELAY:
        if add_xp(user_id):
            await message.channel.send(f"🎉 {message.author.mention} niveau {xp_data[user_id]['level']} !")
        xp_cooldown[user_id] = now
        save_json(XP_FILE, xp_data)

    parts = user_input.split()
    cmd = parts[0].lower()
    args = parts[1:]

    if await handle_command(message, cmd, args):
        return

    queue.append((message, user_id, user_input))
    await process_queue()

client.run(DISCORD_TOKEN)
