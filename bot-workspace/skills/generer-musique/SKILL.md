---
name: generer-musique
description: Générer de la musique via Suno — ambiances RP, thèmes de PNJ, chansons narratives
---

# Générer de la musique

## Quand utiliser
- Pour poser l'ambiance d'une scène importante
- Quand un joueur demande de la musique
- Pour les thèmes de PNJ ou de lieux récurrents
- Quand un moment narratif mérite une couleur sonore

## Orchestral vs chanson — règle fondamentale
- Par défaut : `make_instrumental: true` (musique d'accompagnement RP, pas de voix)
- Exception : `make_instrumental: false` uniquement si le RP demande explicitement une chanson
  avec paroles (un personnage qui chante, une berceuse narrative, etc.)

## Construire un bon prompt Suno

**Instrumental (`make_instrumental: true`)** :
- `prompt` = description atmosphérique (ambiance, lieu, émotion, tension)
- `style` = instruments + genre ("dark orchestral, cello, low strings, cinematic, haunting")

**Chanson (`make_instrumental: false`)** :
- `prompt` = paroles ou description vocale narrative EN ANGLAIS
- `style` = genre + voix ("medieval folk, female voice, melancholic, acoustic guitar")

Consulter `/workspace/memory/meta/music_library.md` pour éviter les répétitions récentes.

## Carte de progression

**Toujours passer `reply_channel_id` ou `reply_user_id`** — sauf génération silencieuse/surprise.
La génération Suno peut durer plusieurs minutes — la carte confirme que la demande a été reçue.

- Dans un **channel serveur** : `"reply_channel_id": "<id du channel courant>"`
- En **DM** : `"reply_user_id": "<user_id>"` (le DM ne peut pas être trouvé par son ID)

## Appeler l'API

**Channel serveur :**
```json
{
  "guild_id": "...",
  "channel_name": "musique",
  "prompt": "...",
  "style": "...",
  "title": "...",
  "make_instrumental": true,
  "post_both": false,
  "reply_channel_id": "<id du channel courant>"
}
```

**DM :**
```json
{
  "guild_id": "...",
  "channel_name": "musique",
  "prompt": "...",
  "style": "...",
  "title": "...",
  "make_instrumental": true,
  "post_both": false,
  "reply_user_id": "<id du joueur>"
}
```

→ Réponse : `{ "ok": true, "songs": [ { "clip_id": "...", "title": "...", ... } ] }`

## Canal

Le channel par défaut est #musique. S'il n'existe pas, le créer d'abord :
```json
POST /channel/create
{ "guild_id": "...", "channel_name": "musique", "topic": "Musique générée par Augure" }
```

## Après la génération

- **Si `reply_channel_id` / `reply_user_id` était présent** : la carte de progression est déjà remplacée par la carte finale — **ne pas envoyer l'URL** (évite le double-embed). Une courte phrase de commentaire est OK.
- **Si génération silencieuse** : mentionner brièvement ce qui a été généré et où.
- Si échec → expliquer et proposer une alternative.

## VRAM

La génération musicale n'utilise pas le GPU local (Suno est externe).
Pas besoin d'arbitrage VRAM pour la musique.
