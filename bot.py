import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import subprocess
import time
import paramiko
from dotenv import load_dotenv
import socket
from flask import Flask
import requests
import threading

# Cargar variables de entorno
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
PING_URL = os.getenv("PING_URL")
SSH_HOST = os.getenv("SSH_HOST")  # Dirección pública de tu PC
SSH_PORT = int(os.getenv("SSH_PORT", 22))  # Puerto SSH
SSH_USER = os.getenv("SSH_USER")  # Usuario SSH en tu PC
SSH_PASSWORD = os.getenv("SSH_PASSWORD")  # Contraseña SSH
SERVER_DIRECTORY = os.getenv("SERVER_DIRECTORY")  # Ruta del servidor en la PC remota
MINECRAFT_SERVER_IP = os.getenv("MINECRAFT_SERVER_IP", "127.0.0.1")  # IP del servidor
MINECRAFT_SERVER_PORT = int(os.getenv("MINECRAFT_SERVER_PORT", 25565))  # Puerto del servidor

# Configuración del bot
intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.message_content = True

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
    await tree.sync()
    print(f'Bot conectado como {bot.user}')
    print("✅ Slash commands sincronizados correctamente.")
    if not keep_awake.is_running():
        print(f'🚀 Iniciando loop para mantener el bot despierto')
        keep_awake.start()

@tree.command(name="hola", description="Responde con un saludo")
async def hola(interaction: discord.Interaction):
    await interaction.response.send_message("👋 ¡Hola! ¿En qué puedo ayudarte?")

@tree.command(name="comandos", description="Lista los comandos disponibles")
async def comandos(interaction: discord.Interaction):
    comandos_lista = (
        "📜 **Lista de comandos:**\n"
        "- `/hola` ➝ Saludo del bot\n"
        "- `/comandos` ➝ Muestra esta lista\n"
        "- `/servidor` ➝ Información del servidor de Discord\n"
        "- `/iniciar_servidor` ➝ Inicia el servidor de Minecraft\n"
        "- `/apaga_servidor` ➝ Apaga el servidor de Minecraft\n"
        "- `/estado_servidor` ➝ Verifica si el servidor de Minecraft está activo\n"
        "- `/alimentar_mono` ➝ Alimenta al argentino mono (@CT) 🐵"
    )
    await interaction.response.send_message(comandos_lista)

@tree.command(name="servidor", description="Muestra información del servidor de Discord")
async def servidor(interaction: discord.Interaction):
    server = interaction.guild
    mensaje = (
        f"🏰 **Información del Servidor**\n"
        f"Nombre: {server.name}\n"
        f"Miembros: {server.member_count}\n"
        f"Propietario: {server.owner}"
    )
    await interaction.response.send_message(mensaje)

@tree.command(name="iniciar_servidor", description="Inicia el servidor de Minecraft en la PC remota mediante SSH")
async def iniciar_servidor(interaction: discord.Interaction):
    await interaction.response.defer()  # Notificar a Discord que la respuesta tomará tiempo
    
    if not SERVER_DIRECTORY:
        await interaction.followup.send("⚠️ La ruta del directorio del servidor no está configurada.")
        return

    # Verificar si el servidor ya está activo antes de iniciar
    try:
        with socket.create_connection((MINECRAFT_SERVER_IP, MINECRAFT_SERVER_PORT), timeout=5):
            await interaction.followup.send("✅ El servidor de Minecraft ya está activo y no necesita ser iniciado nuevamente.")
            return
    except (socket.timeout, ConnectionRefusedError):
        pass  # El servidor no está activo, proceder con el inicio

    # Conexión SSH y ejecución del servidor
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SSH_HOST, port=SSH_PORT, username=SSH_USER, password=SSH_PASSWORD)

        command = f'cd "{SERVER_DIRECTORY}" && java -Xmx8G -Xms4G -jar server.jar nogui'
        ssh.exec_command(command)

        ssh.close()
        await interaction.followup.send("✅ Se ha enviado el comando para iniciar el servidor de Minecraft.")
    except Exception as e:
        await interaction.followup.send(f"❌ Error al conectar por SSH: {e}")


@tree.command(name="estado_servidor", description="Verifica si el servidor de Minecraft está activo")
async def estado_servidor(interaction: discord.Interaction):
    await interaction.response.defer()  # ⚡ Responder primero para evitar el error de "Unknown interaction"

    try:
        with socket.create_connection((MINECRAFT_SERVER_IP, MINECRAFT_SERVER_PORT), timeout=5):
            mensaje = "✅ El servidor de Minecraft está activo y aceptando conexiones."
    except (socket.timeout, ConnectionRefusedError):
        mensaje = "❌ El servidor de Minecraft no está activo o no responde."

    await interaction.followup.send(mensaje)  # 📌 Enviar la respuesta después de comprobar el estado


@tree.command(name="apaga_servidor", description="Apaga el servidor de Minecraft")
async def apaga_servidor(interaction: discord.Interaction):
    await interaction.response.defer()  # ⚡ Evita errores de "Unknown interaction"

    if not SERVER_DIRECTORY:
        await interaction.followup.send("⚠️ La ruta del directorio del servidor no está configurada.")
        return

    try:
        # Verificar si hay procesos Java en ejecución
        process = subprocess.Popen("tasklist", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, _ = process.communicate()

        if b"java.exe" in output or b"javaw.exe" in output:
            await interaction.followup.send("🛑 Intentando apagar el servidor de Minecraft...")

            # Primero, intentar apagarlo con el comando "stop"
            stop_command = 'powershell -Command "echo stop | Out-File -Encoding ASCII -Append server_input.txt"'
            subprocess.run(stop_command, shell=True, cwd=SERVER_DIRECTORY)

            time.sleep(5)  # Esperar un poco para ver si se apaga correctamente

            # Verificar si sigue en ejecución
            process = subprocess.Popen("tasklist", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, _ = process.communicate()

            if b"java.exe" in output or b"javaw.exe" in output:
                await interaction.followup.send("⚠️ El servidor sigue encendido. Intentando forzar el apagado...")

                # Forzar el cierre de procesos Java
                subprocess.run("taskkill /F /IM java.exe", shell=True)
                subprocess.run("taskkill /F /IM javaw.exe", shell=True)

                await interaction.followup.send("✅ Servidor de Minecraft apagado con éxito mediante 'taskkill'.")
            else:
                await interaction.followup.send("✅ Servidor de Minecraft apagado correctamente con el comando 'stop'.")
        else:
            await interaction.followup.send("❌ No se encontró un servidor de Minecraft en ejecución.")

    except Exception as e:
        await interaction.followup.send(f"❌ Error al intentar apagar el servidor: {e}")



@tree.command(name="alimentar_mono", description="Alimenta al argentino mono (@CT) y cuenta las veces")
async def alimentar_mono(interaction: discord.Interaction):
    global alimentaciones
    alimentaciones += 1
    await interaction.response.send_message(f"🍌🐵 Has alimentado al argentino mono (@CT) {alimentaciones} veces.")

bot.run(TOKEN)
