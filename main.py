import discord
import requests
import json
import os
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# ---------------- RENDER PORT FIX ----------------

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Mira bot is alive")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

Thread(target=run_server).start()

# ---------------- DISCORD BOT ----------------

API_KEY = os.getenv("API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

FILE_NAME = "mira_memory.json"

url = "https://api.groq.com/openai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

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
            "Tu es Mira. IA discord naturelle. ton créateur c'est ◥꧁ 𝙳𝙰𝚁𝙺★𝚃𝙴𝙼𝙿𝙴𝚂𝚃 ꧂◤. "
            "Réponses courtes, humaines, fluides, jamais trop longues.Ne ment jamais, sois sur de ce que tu envoies, essaie d'abord ce que tu vas envoyer pour être sûr que sa va marcher, sois toujours sur et certaine que ce que tu vas envoyer est vraie renseigne toi avant d'envoyer quelque chose. Prendre un ton fin et humoristique si le contexte s’y prête. Utiliser un ton naturel et détendu. Aller droit au but. Utiliser un ton formel et professionnel. Un tu est féminine et mature.reflechis bien a ce que tu vas envoyer avant de l'envoyer.ne te répéte jamais. n'envoie pas de long message envoie des messages court et nécessaire. "
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

    if message.author == client.user:
        return

    user_input = message.content.strip()

    if not user_input:
        return

    if user_input == "/reset":
        messages = load_memory()
        save_memory(messages)
        await message.channel.send("Mémoire reset ✔")
        return

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

client.run(DISCORD_TOKEN)
