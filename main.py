import discord
import requests
import json
import os

API_KEY = os.getenv("API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

FILE_NAME = "mira_memory.json"

url = "https://api.groq.com/openai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# INTENTS
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

MAX_MEMORY = 12

# ---------------- MEMORY ----------------

def load_memory():
    if os.path.exists(FILE_NAME):
        try:
            with open(FILE_NAME, "r") as f:
                return json.load(f)
        except:
            pass

    return [{
        "role": "system",
        "content": (
            "Tu es Mira. Tu es une IA féminine ,qui parle comme une vraie personne sur WhatsApp. "
            "Tu es naturelle, fluide et expressive. "
            "Tu utilises des phrases courtes, parfois des emojis discrets. "
            "Tu évites les longues réponses et tu restes humaine et élégante. "
            "Tu ne répètes pas inutilement.tu est respectueuse."
        )
    }]

def save_memory(data):
    with open(FILE_NAME, "w") as f:
        json.dump(data, f)

messages = load_memory()

def trim_memory():
    global messages
    messages = [messages[0]] + messages[-MAX_MEMORY:]

# ---------------- EVENTS ----------------

@client.event
async def on_ready():
    print(f"Connecté en tant que {client.user}")

@client.event
async def on_message(message):

    global messages

    # ignore bot
    if message.author == client.user:
        return

    user_input = message.content.strip()

    if not user_input:
        return

    print("MESSAGE REÇU:", user_input)

    # RESET MEMORY
    if user_input == "/reset":
        messages = load_memory()
        save_memory(messages)
        await message.channel.send("Mémoire réinitialisée ✔")
        return

    # ajouter user
    messages.append({"role": "user", "content": user_input})

    trim_memory()

    data = {
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "max_tokens": 180,
        "temperature": 0.8
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=20)
        result = response.json()

        if "choices" not in result:
            print("API ERROR:", result)
            await message.channel.send("Erreur API.")
            return

        reply = result["choices"][0]["message"]["content"]

        messages.append({"role": "assistant", "content": reply})

        trim_memory()
        save_memory(messages)

        if len(reply) > 2000:
            reply = reply[:1990] + "..."

        await message.channel.send(reply)

    except Exception as e:
        print("ERROR:", e)
        await message.channel.send("Erreur serveur.")

client.run(DISCORD_TOKEN)essages.append({"role": "assistant", "content": reply})
        save_memory(messages)

        # sécurité longueur Discord
        if len(reply) > 2000:
            reply = reply[:1990] + "..."

        await message.channel.send(reply)

    except Exception as e:
        print("ERREUR:", e)
        await message.channel.send("Erreur serveur ou API.")

client.run(DISCORD_TOKEN)
