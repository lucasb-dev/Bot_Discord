import discord
import os
import json
import random
from dotenv import load_dotenv
from discord.ext import commands
from datetime import datetime
from collections import Counter

load_dotenv()

print("Lancement du bot...")

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# ==================== STRUCTURES DE DONNÉES ====================

class CommandNode:
    """Noeud pour la liste chaînée"""
    def __init__(self, username, command, timestamp):
        self.username = username
        self.command = command
        self.timestamp = timestamp
        self.next = None

class CommandHistory:
    """Liste chaînée pour l'historique global"""
    def __init__(self):
        self.head = None
        self.size = 0
    
    def add_command(self, username, command):
        """Ajoute une commande au début de la liste"""
        new_node = CommandNode(username, command, datetime.now())
        new_node.next = self.head
        self.head = new_node
        self.size += 1
    
    def get_last_command(self):
        if self.head is None:
            return None
        return {
            'username': self.head.username,
            'command': self.head.command,
            'timestamp': self.head.timestamp
        }

    def get_user_commands(self, username):
        commands = []
        current = self.head
        while current:
            if current.username == username:
                commands.append({
                    'command': current.command,
                    'timestamp': current.timestamp
                })
            current = current.next
        return commands

    def clear(self):
        self.head = None
        self.size = 0

class UserCommandStack:
    def __init__(self):
        self.stack = []
    
    def push(self, command):
        self.stack.append({
            'command': command,
            'timestamp': datetime.now()
        })
    
    def get_all(self):
        return list(reversed(self.stack))
    
    def size(self):
        return len(self.stack)
    
    def clear(self):
        self.stack.clear()

# ==================== SAUVEGARDE ET CHARGEMENT ====================

HISTORY_FILE = "histories.json"

def save_histories():
    data = {
        "global_history": [],
        "user_histories": {}
    }

    # Historique global
    current = global_history.head
    while current:
        data["global_history"].append({
            "username": current.username,
            "command": current.command,
            "timestamp": current.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        })
        current = current.next

    # Historique par utilisateur
    for username, stack in user_histories.items():
        data["user_histories"][username] = [
            {
                "command": cmd["command"],
                "timestamp": cmd["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            }
            for cmd in stack.stack
        ]

    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=4)
    print("Sauvegarde terminée")

def load_histories():
    try:
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)

            # Historique global
            for cmd in reversed(data.get("global_history", [])):
                global_history.add_command(cmd["username"], cmd["command"])
                global_history.head.timestamp = datetime.strptime(cmd["timestamp"], "%Y-%m-%d %H:%M:%S")

            # Historique par utilisateur
            for username, commands in data.get("user_histories", {}).items():
                stack = get_user_stack(username)
                for cmd in commands:
                    stack.stack.append({
                        "command": cmd["command"],
                        "timestamp": datetime.strptime(cmd["timestamp"], "%Y-%m-%d %H:%M:%S")
                    })
        print("Chargement terminé")
    except FileNotFoundError:
        print("Aucun fichier d'historique trouvé, démarrage propre.")

# INITIALISATION
global_history = CommandHistory()
user_histories = {}

def get_user_stack(username):
    if username not in user_histories:
        user_histories[username] = UserCommandStack()
    return user_histories[username]

def format_timestamp(dt):
    return dt.strftime("%d/%m/%Y %H:%M:%S")

# Charger l'historique après avoir tout défini
load_histories()

# ==================== ÉVÉNEMENTS ====================

@bot.event
async def on_ready():
    print(f"Bot connecté : {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    username = f"{message.author.name}#{message.author.discriminator}"

    if message.author.id in user_conversations:
        current_node = user_conversations[message.author.id]

        if current_node.conclusion is None:
            user_answer = message.content.lower().strip()
            if user_answer in current_node.children:
                next_node = current_node.children[user_answer]
                user_conversations[message.author.id] = next_node
                if next_node.conclusion:
                    await message.channel.send(next_node.conclusion)
                    del user_conversations[message.author.id]
                else:
                    await message.channel.send(next_node.question)
                return
            else:
                await message.channel.send("Réponse invalide. Réessayez.")
                return

    content = message.content.strip()

    # IGNORER les commandes purement numériques
    if content.startswith("!") and content[1:].isdigit():
        return

    if content.startswith("!"):
        global_history.add_command(username, content)
        get_user_stack(username).push(content)
        save_histories()

    if message.content.lower() == "bonjour":
        await message.channel.send("Comment tu vas ?")

    await bot.process_commands(message)

# ==================== COMMANDES PREFIX ====================

@bot.command(name="bonjour", help="Dire bonjour au bot")
async def bonjour_cmd(ctx):
    await ctx.send(f'Bonjour {ctx.author.mention} ! Comment tu vas ?')

@bot.command(name="last", description="Affiche la commande utilisée juste avant la dernière")
async def last_cmd(ctx):
    if global_history.head is None or global_history.head.next is None:
        await ctx.send("Pas assez de commandes dans l'historique pour afficher l'avant-dernière.")
        return
    
    second_node = global_history.head.next
    embed = discord.Embed(title="Avant-dernière commande", color=discord.Color.blue())
    embed.add_field(name="Utilisateur", value=second_node.username, inline=False)
    embed.add_field(name="Commande", value=f"`{second_node.command}`", inline=False)
    embed.add_field(name="Date", value=format_timestamp(second_node.timestamp), inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name="myhistory", help="Affiche votre historique personnel")
async def myhistory_cmd(ctx):
    username = f"{ctx.author.name}#{ctx.author.discriminator}"
    stack = get_user_stack(username).get_all()
    if not stack:
        return await ctx.send("Vous n'avez utilisé aucune commande.")
    
    text = "\n".join([f"{i+1}. {cmd['command']} ({format_timestamp(cmd['timestamp'])})"
                      for i, cmd in enumerate(stack[:15])])
    await ctx.send(f"**Votre historique :**\n{text}")

@bot.command(name="clearhistory", help="Efface votre historique personnel")
async def clearhistory_cmd(ctx):
    username = f"{ctx.author.name}#{ctx.author.discriminator}"
    count = get_user_stack(username).size()
    get_user_stack(username).clear()
    save_histories()
    await ctx.send(f"Historique supprimé ({count} commandes).")

@bot.command(name="clearglobal", help="Efface l'historique global (admin)")
@commands.has_permissions(administrator=True)
async def clearglobal_cmd(ctx):
    global_history.clear()
    save_histories()
    await ctx.send("Historique global effacé.")

# ==================== LISTE DES COMMANDES ====================

@bot.command(name="commands", aliases=["helpme"])
async def commands_cmd(ctx):
    embed = discord.Embed(
        title="Liste des commandes du bot",
        description="Voici toutes les commandes disponibles, organisées par catégories :",
        color=discord.Color.purple()
    )

    interaction = ["`!bonjour` → Le bot vous dit bonjour"]
    embed.add_field(name="Interaction", value="\n".join(interaction), inline=False)

    history = [
        "`!last` → Affiche la dernière commande utilisée",
        "`!myhistory` → Affiche votre propre historique",
        "`!clearhistory` → Vide votre historique personnel",
        "`!clearglobal` → Vide l'historique global (Admin uniquement)"
    ]
    embed.add_field(name="Historique", value="\n".join(history), inline=False)

    discussion = [
        "`!start` → Démarre une discussion",
        "`!reset` → Réinitialise la discussion",
        "`!speak_about <mot>` → Vérifie si un sujet existe dans l’arbre"
    ]
    embed.add_field(name="Discussion", value="\n".join(discussion), inline=False)

    games = [
        "`!guessnumber` → Lance une partie 'Devine le nombre'",
        "`!guess <nombre>` → Devine le nombre choisi par le bot"
    ]
    embed.add_field(name="Mini-jeux", value="\n".join(games), inline=False)

    quotes_list = ["`!quote` → Envoie une citation aléatoire"]
    embed.add_field(name="Citations", value="\n".join(quotes_list), inline=False)

    stats = ["`!stats` → Montre vos statistiques personnelles"]
    embed.add_field(name="Statistiques", value="\n".join(stats), inline=False)

    await ctx.send(embed=embed)

# ==================== ARBRE DE DISCUSSION ====================

class TreeNode:
    def __init__(self, question, children=None, conclusion=None):
        self.question = question
        self.children = children or {}
        self.conclusion = conclusion

conversation_root = TreeNode(
    "Bienvenue ! Quel sujet voulez-vous explorer ? (tech / loisirs)",
    children={
        "tech": TreeNode(
            "Voulez-vous parler de programmation ou cyber ?",
            children={
                "programmation": TreeNode(None, conclusion="Super parlons de ça !"),
                "cyber": TreeNode(None, conclusion="Pourquoi aimes-tu ce sujet !")
            }
        ),
        "loisirs": TreeNode(
            "Préférez-vous sport ou jeux video ?",
            children={
                "sport": TreeNode(None, conclusion="Go faire du sport !"),
                "jeux video": TreeNode(None, conclusion="Jouons à un petit jeu !")
            }
        )
    }
)

user_conversations = {}

def traverse_tree(user_id, answer):
    current = user_conversations.get(user_id, conversation_root)
    if answer.lower() in current.children:
        next_node = current.children[answer.lower()]
        user_conversations[user_id] = next_node
        return next_node.conclusion if next_node.conclusion else next_node.question
    return "Réponse invalide. Réessayez."

@bot.command(name="start", help="Commence une discussion")
async def start_cmd(ctx):
    user_conversations[ctx.author.id] = conversation_root
    await ctx.send(conversation_root.question)

@bot.command(name="reset", help="Recommence la discussion")
async def reset_cmd(ctx):
    if ctx.author.id in user_conversations:
        del user_conversations[ctx.author.id]

    user_conversations[ctx.author.id] = conversation_root
    await ctx.send("Conversation réinitialisée !")
    await ctx.send(conversation_root.question)

@bot.command(name="speak_about", help="Vérifie si un sujet existe dans l'arbre")
async def speak_about_cmd(ctx, *, topic):
    def search(node, topic):
        if node.question and topic.lower() in node.question.lower():
            return True
        return any(search(child, topic) for child in node.children.values())
    exists = search(conversation_root, topic)
    await ctx.send("Oui !" if exists else "Non !")

# ==================== FONCTIONNALITÉS SUPPLÉMENTAIRES ====================

@bot.command(name="stats", help="Affiche vos statistiques de commandes")
async def stats_cmd(ctx):
    username = f"{ctx.author.name}#{ctx.author.discriminator}"
    stack = get_user_stack(username).stack
    if not stack:
        return await ctx.send("Aucune commande enregistrée.")
    most_common = Counter([c["command"] for c in stack]).most_common(1)[0][0]
    await ctx.send(f"Total commandes : {len(stack)}\nCommande la plus utilisée : `{most_common}`")

active_games = {}

@bot.command(name="guessnumber", help="Lance un jeu de devinette")
async def guessnumber_cmd(ctx):
    number = random.randint(1, 20)
    active_games[ctx.author.id] = number
    await ctx.send("J'ai choisi un nombre entre 1 et 20 ! Devinez-le avec `!guess <nombre>`")

@bot.command(name="guess", help="Devine le nombre")
async def guess_cmd(ctx, guess: int):
    if ctx.author.id not in active_games:
        return await ctx.send("Aucune partie en cours. Tapez `!guessnumber`.")
    number = active_games[ctx.author.id]
    if guess < number:
        await ctx.send("Trop petit !")
    elif guess > number:
        await ctx.send("Trop grand !")
    else:
        await ctx.send(f"Bravo ! Le nombre était {number} !")
        del active_games[ctx.author.id]

quotes = [
    "Crois en toi !",
    "Chaque jour est une nouvelle chance.",
    "Le succès vient avec la persévérance.",
    "Le savoir est une arme.",
]

@bot.command(name="quote", help="Envoie une citation aléatoire")
async def quote_cmd(ctx):
    await ctx.send(random.choice(quotes))

# ==================== LANCEMENT ====================

bot.run(os.getenv("DISCORD_TOKEN"))