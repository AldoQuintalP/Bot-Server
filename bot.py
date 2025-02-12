import discord
from discord.ext import commands
from discord import app_commands
import os
import subprocess
import time
from dotenv import load_dotenv
import socket
from flask  import Flask
import requests
import threading


# Cargar variables de entorno
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
PING_URL = os.getenv("PING_URL")
print(f"Token: {TOKEN}")
SERVER_DIRECTORY = os.getenv("SERVER_DIRECTORY")  # Ruta del directorio del servidor
MINECRAFT_SERVER_IP = os.getenv("MINECRAFT_SERVER_IP", "127.0.0.1")  # IP del servidor
MINECRAFT_SERVER_PORT = int(os.getenv("MINECRAFT_SERVER_PORT", 25565))  # Puerto del servidor

# Configuración del bot
intents = discord.Intents.default()
intents.presences = True  # Para ver estados de usuarios
intents.members = True  # Para ver miembros del servidor
intents.message_content = True  # Permitir leer mensajes

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree  # Slash commands

# Contador de veces alimentado
alimentaciones = 0

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot activo"

def run_web_server():
    app.run(host="0.0.0.0", port=8080)


threading.Thread(target=run_web_server, daemon=True).start()

@tasks.loop(minutes=5)
async def keep_awake():
    if PING_URL:
        try:
            requests.get(PING_URL)
            print("✅ Ping enviado para mantener el bot despierto")
        except Exception as e:
            print(f"⚠️ Error al enviar ping: {e}")
        


@bot.event
async def on_ready():
    await tree.sync()  # Sincronizar slash commands
    print(f'Bot conectado como {bot.user}')
    print("✅ Slash commands sincronizados correctamente.")

@tree.command(name="hola", description="Responde con un saludo")
async def hola(interaction: discord.Interaction):
    await interaction.response.send_message("👋 ¡Hola! ¿En qué puedo ayudarte?")

@tree.command(name="comandos", description="Lista los comandos disponibles")
async def comandos(interaction: discord.Interaction):
    comandos_lista = "📜 **Lista de comandos:**\n"
    comandos_lista += "- `/hola` ➝ Saludo del bot\n"
    comandos_lista += "- `/comandos` ➝ Muestra esta lista\n"
    comandos_lista += "- `/servidor` ➝ Información del servidor\n"
    comandos_lista += "- `/iniciar_servidor` ➝ Inicia el servidor de Minecraft\n"
    comandos_lista += "- `/estado_servidor` ➝ Verifica si el servidor de Minecraft está activo\n"
    comandos_lista += "- `/alimentar_mono` ➝ Alimenta al argentino mono (@CT) 🐵"
    await interaction.response.send_message(comandos_lista)

@tree.command(name="servidor", description="Muestra información del servidor de Discord")
async def servidor(interaction: discord.Interaction):
    server = interaction.guild
    mensaje = f"🏰 **Información del Servidor**\n"
    mensaje += f"Nombre: {server.name}\n"
    mensaje += f"Miembros: {server.member_count}\n"
    mensaje += f"Propietario: {server.owner}"
    await interaction.response.send_message(mensaje)

@tree.command(name="iniciar_servidor", description="Inicia el servidor de Minecraft directamente con el comando de Java")
async def iniciar_servidor(interaction: discord.Interaction):
    if not SERVER_DIRECTORY:
        await interaction.response.send_message("⚠️ La ruta del directorio del servidor no está configurada.")
        return
    
    # Verificar si el servidor ya está activo antes de iniciar
    try:
        with socket.create_connection((MINECRAFT_SERVER_IP, MINECRAFT_SERVER_PORT), timeout=5):
            await interaction.response.send_message("✅ El servidor de Minecraft ya está activo y no necesita ser iniciado nuevamente.")
            return
    except (socket.timeout, ConnectionRefusedError):
        pass  # El servidor no está activo, proceder con el inicio

    try:
        process = subprocess.Popen(
            'java -Xmx8G -Xms4G -jar server.jar nogui',
            cwd=SERVER_DIRECTORY,
            shell=True
        )
        time.sleep(10)  # Esperar un poco para verificar si el servidor se inicia correctamente

        # Verificar si el servidor está activo después de intentar iniciarlo
        try:
            with socket.create_connection((MINECRAFT_SERVER_IP, MINECRAFT_SERVER_PORT), timeout=5):
                await interaction.response.send_message("✅ El servidor de Minecraft se ha iniciado correctamente.")
        except (socket.timeout, ConnectionRefusedError):
            await interaction.response.send_message("❌ El servidor no se pudo iniciar correctamente. Verifica la configuración o revisa los logs de errores.")

    except Exception as e:
        await interaction.response.send_message(f"❌ Error al intentar iniciar el servidor: {e}")

@tree.command(name="estado_servidor", description="Verifica si el servidor de Minecraft está activo")
async def estado_servidor(interaction: discord.Interaction):
    try:
        with socket.create_connection((MINECRAFT_SERVER_IP, MINECRAFT_SERVER_PORT), timeout=5):
            await interaction.response.send_message("✅ El servidor de Minecraft está activo y aceptando conexiones.")
    except (socket.timeout, ConnectionRefusedError):
        await interaction.response.send_message("❌ El servidor de Minecraft no está activo o no responde.")

@tree.command(name="alimentar_mono", description="Alimenta al argentino mono (@CT) y cuenta las veces")
async def alimentar_mono(interaction: discord.Interaction):
    global alimentaciones
    alimentaciones += 1
    await interaction.response.send_message(f"🍌🐵 Has alimentado al argentino mono (@CT) {alimentaciones} veces.")

bot.run(TOKEN)
