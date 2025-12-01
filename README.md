Bot Discord – Projet B2
    Description

Ce projet consiste en la création d’un bot Discord avec plusieurs fonctionnalités :

Historique des commandes par utilisateur et global

Système de discussion interactif basé sur un arbre de conversation

Sauvegarde persistante des données dans un fichier JSON unique

Trois fonctionnalités supplémentaires : statistiques personnelles, mini-jeu “Devine le nombre” et citation aléatoire

Le bot est entièrement développé en Python avec la librairie discord.py.

    Prérequis

Python 3.9 ou supérieur

Bibliothèques Python :

pip install discord.py python-dotenv


Un token Discord pour le bot (à placer dans un fichier .env)

Exemple .env :
DISCORD_TOKEN=TON_TOKEN_ICI

Commandes

Commandes principales

Commande	Description

!bonjour	Dire bonjour au bot

!last	Affiche la dernière commande entrée par n’importe quel utilisateur
!myhistory	Affiche toutes vos commandes depuis votre première connexion
!clearhistory	Vide votre historique personnel
!clearglobal	Vide l’historique global (administrateur)

Arbre de discussion

Commande	Description

!start	    Commence une conversation avec le bot
!reset	    Recommence la discussion depuis la racine
!speak_about <sujet>	Vérifie si un sujet existe dans l’arbre (répond Oui/Non)


Fonctionnalités supplémentaires

Commande	    Description

!stats	        Affiche vos statistiques personnelles de commandes
!guessnumber	Démarre un mini-jeu “Devine le nombre”
!guess          <nombre>	Devine le nombre choisi par le bot
!quote	        Affiche une citation aléatoire inspirante


Sauvegarde des données

Toutes les commandes et conversations sont sauvegardées automatiquement dans un fichier JSON unique :

histories.json


Ce fichier contient :

Historique global des commandes

Historique individuel des utilisateurs

Les données sont chargées automatiquement au démarrage du bot et sauvegardées à chaque nouvelle commande.

    Arbre de conversation

Le bot peut converser sur différents sujets :

Tech : programmation ou IA

Loisirs : sport ou jeux vidéo

À la fin de la conversation, le bot donne une conclusion personnalisée selon le chemin choisi.

    Lancer le bot

Cloner le dépôt ou copier le fichier bot.py et le .env

Installer les dépendances

Lancer le bot :

python bot.py

Notes

L’administrateur peut utiliser !clearglobal pour vider toutes les commandes

L’arbre de conversation peut être étendu facilement en modifiant la variable conversation_root

Les nouvelles commandes sont automatiquement ajoutées à l’historique et sauvegardées dans histories.json