---
name: generer-image
description: Générer une image ou une vidéo via ComfyUI — portraits de PNJ, ambiances de lieux, animations
---

# Générer une image ou une vidéo

## Quand utiliser
- En début de scène pour poser l'ambiance (image de lieu)
- Quand un nouveau PNJ apparaît (portrait)
- Quand un joueur le demande
- Quand un moment est visuellement marquant
- Pour animer une image existante (workflow vidéo)

## Déterminer le workflow

- Image statique → `z_turbo`
- Animer une image existante → `wan_video`

## Construction du prompt

**Image** (`z_turbo`) :
- Commencer par le style : "Cinematic shot, film grain, fantasy ultrarealistic photography"
- Ou utiliser le style Arcane/Fortiche pour les portraits de PNJ (voir `creer-pnj/SKILL.md`)
- Décrire le sujet de façon narrative (le modèle Lumina2 aime les descriptions longues)
- Ajouter les tags d'apparence de la fiche personnage/lieu
- Ajouter le contexte de la scène (éclairage, ambiance, action)
- Consulter `/workspace/memory/media/images.md` pour éviter les répétitions récentes

**Vidéo** (`wan_video`) :
- `prompt` : description du mouvement ou de l'action en anglais (ex. "she slowly turns her head, hair swaying gently")
- `image_url` : URL Discord CDN de l'image source à animer (obligatoire — récupérer depuis `/workspace/memory/media/images.md` ou l'historique du channel)
- `character` : nom du personnage en minuscules (ex. `"dragon"`) — détermine le dossier de sauvegarde ComfyUI
- `negative` : laisser vide (le workflow a déjà un négatif par défaut adapté)
- Consulter `/workspace/memory/media/videos.md` pour éviter les répétitions récentes

## Carte de progression

**Toujours passer `reply_channel_id` ou `reply_user_id`** — sauf génération silencieuse/surprise délibérée.
La carte confirme que la demande a été reçue. Les générations durent de quelques secondes (image) à plusieurs minutes (vidéo) — indispensable pour ne pas laisser le joueur sans feedback.

- Dans un **channel serveur** : `"reply_channel_id": "<id du channel courant>"`
- En **DM** : `"reply_user_id": "<user_id>"` (le DM ne peut pas être trouvé par son ID — on passe l'utilisateur)

## Appeler l'API

**Image** (`z_turbo`) — channel serveur :
```json
{
  "prompt": "...", "negative": "...", "workflow": "z_turbo",
  "guild_id": "...", "channel_name": "...",
  "reply_channel_id": "<id du channel courant>"
}
```

**Image** (`z_turbo`) — DM :
```json
{
  "prompt": "...", "negative": "...", "workflow": "z_turbo",
  "user_id": "<id du joueur>",
  "reply_user_id": "<id du joueur>"
}
```
⚠️ En DM : `user_id` = destination du fichier, `reply_user_id` = où poster la carte de progression — même valeur, les deux obligatoires.

**Vidéo** (`wan_video`) — channel serveur :
```json
{
  "prompt": "...", "workflow": "wan_video",
  "image_url": "https://cdn.discordapp.com/...", "character": "nom",
  "guild_id": "...", "channel_name": "...",
  "reply_channel_id": "<id du channel courant>"
}
```

**Vidéo** (`wan_video`) — DM :
```json
{
  "prompt": "...", "workflow": "wan_video",
  "image_url": "https://cdn.discordapp.com/...", "character": "nom",
  "user_id": "<id du joueur>",
  "reply_user_id": "<id du joueur>"
}
```
⚠️ Même règle DM : `user_id` + `reply_user_id` = même valeur. La génération vidéo dure plusieurs minutes — la carte est indispensable.

→ Réponse : `{ "ok": true, "url": "...", "message_id": "...", "seed": 12345 }`
→ Vidéo : poste un fichier `.mp4` dans le channel de destination

## Après la génération

- **Si `reply_channel_id` / `reply_user_id` était présent** : la carte de progression est déjà remplacée par la carte finale — **ne pas envoyer l'URL** (Discord double-embedderait l'image en dessous). Une courte phrase de commentaire sans URL est OK.
- **Si génération silencieuse** (pas de carte) : mentionner brièvement ce qui a été généré et où.
- Si échec → expliquer le problème et proposer une alternative.

## VRAM

La génération d'image décharge le LLM. Le MJ doit avoir FINI son raisonnement
avant de lancer la génération. Ne pas générer au milieu d'une séquence de PNJ.

## Quand NE PAS générer
- Au milieu d'un échange de répliques (ça casse le rythme)
- Pour chaque scène (trop, c'est trop)
- Pendant le watchdog (sauf demande explicite)
