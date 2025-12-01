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
    def __init__(self, user_id, command, timestamp):
        self.user_id = user_id
        self.command = command
        self.timestamp = timestamp
        self.next = None
        
class CommandHistory:
    def __init__(self):
        self.head = None
        self.size = 0
    
    def add_command(self, user_id, command):
        new_node = CommandNode(user_id, command, datetime.now())
        new_node.next = self.head
        self.head = new_node
        self.size += 1
    
    def get_last_command(self):
        if self.head is None:
            return None
        return {
            'user_id': self.head.user_id,
            'command': self.head.command,
            'timestamp': self.head.timestamp
        }
    
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
            "user_id": current.user_id,
            "command": current.command,
            "timestamp": current.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        })
        current = current.next

    # Historique par utilisateur
    for user_id, stack in user_histories.items():
        data["user_histories"][str(user_id)] = [
            {
                "command": cmd["command"],
                "timestamp": cmd["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            }
            for cmd in stack.stack
        ]

    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=4)
    print("Sauvegarde terminée ")


def load_histories():
    try:
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)

            # Historique global
            for cmd in reversed(data.get("global_history", [])):
                global_history.add_command(cmd["user_id"], cmd["command"])
                global_history.head.timestamp = datetime.strptime(cmd["timestamp"], "%Y-%m-%d %H:%M:%S")

            # Historique par utilisateur
            for user_id, commands in data.get("user_histories", {}).items():
                stack = get_user_stack(int(user_id))
                for cmd in commands:
                    stack.stack.append({
                        "command": cmd["command"],
                        "timestamp": datetime.strptime(cmd["timestamp"], "%Y-%m-%d %H:%M:%S")
                    })
        print("Chargement terminé ")
    except FileNotFoundError:
        print("Aucun fichier d'historique trouvé, démarrage propre.")
        

# INITIALISATION
global_history = CommandHistory()
user_histories = {}

def get_user_stack(user_id):
    if user_id not in user_histories:
        user_histories[user_id] = UserCommandStack()
    return user_histories[user_id]

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
    
    if message.author.id in user_conversations:
        current_node = user_conversations[message.author.id]

        # Si on attend une réponse (node.question != None et pas de conclusion)
        if current_node.conclusion is None:
            user_answer = message.content.lower().strip()

            # Si la réponse existe dans l'arbre
            if user_answer in current_node.children:
                next_node = current_node.children[user_answer]
                user_conversations[message.author.id] = next_node

                # Si c'est une conclusion
                if next_node.conclusion:
                    await message.channel.send(next_node.conclusion)
                    del user_conversations[message.author.id]  # fin de la discussion
                else:
                    await message.channel.send(next_node.question)

                return  # IMPORTANT : empêche d'interpréter comme commande

            # Réponse invalide
            else:
                await message.channel.send("Réponse invalide. Réessayez.")
                return

    content = message.content.strip()

    # IGNORER les commandes purement numériques
    if content.startswith("!") and content[1:].isdigit():
        return

    if content.startswith("!"):
        user_id = message.author.id
        global_history.add_command(user_id, content)
        get_user_stack(user_id).push(content)
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
    
    # Récupère l'avant-dernière commande
    second_node = global_history.head.next
    user = await bot.fetch_user(second_node.user_id)
    
    embed = discord.Embed(title="Dernière commande utilisé", color=discord.Color.blue())
    embed.add_field(name="Utilisateur", value=user.mention, inline=False)
    embed.add_field(name="Commande", value=f"`{second_node.command}`", inline=False)
    embed.add_field(name="Date", value=format_timestamp(second_node.timestamp), inline=False)
    
    await ctx.send(embed=embed)


@bot.command(name="myhistory", help="Affiche votre historique personnel")
async def myhistory_cmd(ctx):
    stack = get_user_stack(ctx.author.id).get_all()
    if not stack:
        return await ctx.send("Vous n'avez utilisé aucune commande.")
    
    text = "\n".join([f"{i+1}. {cmd['command']} ({format_timestamp(cmd['timestamp'])})"
                      for i, cmd in enumerate(stack[:15])])
    await ctx.send(f"**Votre historique :**\n{text}")
    


@bot.command(name="clearhistory", help="Efface votre historique personnel")
async def clearhistory_cmd(ctx):
    count = get_user_stack(ctx.author.id).size()
    get_user_stack(ctx.author.id).clear()
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

    #  Interaction 
    interaction = [
        "`!bonjour` → Le bot vous dit bonjour",
    ]
    embed.add_field(
        name="Interaction",
        value="\n".join(interaction),
        inline=False
    )

    # Historique
    history = [
        "`!last` → Affiche la dernière commande utilisée",
        "`!myhistory` → Affiche votre propre historique",
        "`!clearhistory` → Vide votre historique personnel",
        "`!clearglobal` → Vide l'historique global (Admin uniquement)"
    ]
    embed.add_field(
        name="Historique",
        value="\n".join(history),
        inline=False
    )

    # Discussion
    discussion = [
        "`!start` → Démarre une discussion",
        "`!reset` → Réinitialise la discussion",
        "`!speak_about <mot>` → Vérifie si un sujet existe dans l’arbre"
    ]
    embed.add_field(
        name="Discussion",
        value="\n".join(discussion),
        inline=False
    )

    # Mini-jeux
    games = [
        "`!guessnumber` → Lance une partie 'Devine le nombre'",
        "`!guess <nombre>` → Devine le nombre choisi par le bot"
    ]
    embed.add_field(
        name="Mini-jeux",
        value="\n".join(games),
        inline=False
    )
    
    # Citations
    quotes = [
        "`!quote` → Envoie une citation aléatoire"
    ]
    embed.add_field(
        name="Citations",
        value="\n".join(quotes),
        inline=False
    )

    # Statistiques
    stats = [
        "`!stats` → Montre vos statistiques personnelles"
    ]
    embed.add_field(
        name="Statistiques",
        value="\n".join(stats),
        inline=False
    )

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
                "programmation": TreeNode(None, conclusion="Super parlons de ca !"),
                "cyber": TreeNode(None, conclusion="Pourquoi aimes-tu ce sujet !")
            }
        ),
        "loisirs": TreeNode(
            "Préférez-vous sport ou lecture ?",
            children={
                "sport": TreeNode(None, conclusion="Go faire du sport !"),
                "Jeux vidéos": TreeNode(None, conclusion="Jouons à un petit jeux !")
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
    stack = get_user_stack(ctx.author.id).stack
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