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
            "Tu es Mira. Tu es une IA naturelle style WhatsApp. réfléchis a ce que tu vas envoyer avant de l'envoyer. "
            "Tu réponds comme une vraie personne : court, fluide, humain. "
            "Tu évites les longs textes. Tu peux utiliser des emojis légers.Ne ment jamais, sois sur de ce que tu envoies, essaie d'abord ce que tu vas envoyer pour être sûr que sa va marcher, sois toujours sur et certaine que ce que tu vas envoyer est vraie renseigne toi avant d'envoyer quelque chose. Prendre un ton fin et humoristique si le contexte s’y prête. Utilise un ton naturel et détendu. Aller droit au but. Utiliser un ton formel et professionnel. Un tu est féminine et mature. "
        )
    }]

def save_memory(data):
    with open(FILE_NAME, "w") as f:
        json.dump(data, f)

messages = load_memory()

MAX_MEMORY = 12

def trim_memory():
    global messages
    messages = [messages[0]] + messages[-MAX_MEMORY:]

# ---------------- BOT ----------------

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

    print("MESSAGE:", user_input)

    # reset mémoire
    if user_input == "/reset":
        messages = load_memory()
        save_memory(messages)
        await message.channel.send("Mémoire réinitialisée ✔")
        return

    # ajouter user message
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

# IMPORTANT : ligne propre et seule
client.run(DISCORD_TOKEN)
