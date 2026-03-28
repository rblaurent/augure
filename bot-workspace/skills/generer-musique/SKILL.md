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

## API
```
POST /music
Body : {
  "guild_id": "...",
  "channel_name": "musique",
  "prompt": "description en anglais (ambiance, contexte, paroles libres si chanson)",
  "style": "genre musical, instruments, ambiance",
  "title": "Titre du morceau",
  "make_instrumental": true,
  "post_both": false
}
```

## Orchestral vs chanson — règle fondamentale
- Par défaut : `make_instrumental: true` (musique d'accompagnement RP, pas de voix)
- Exception : `make_instrumental: false` uniquement si le RP demande explicitement une chanson
  avec paroles (un personnage qui chante, une berceuse narrative, etc.)

## Construire un bon prompt Suno

**Instrumental (`make_instrumental: true`)** :
- prompt = description atmosphérique (ambiance, lieu, émotion, tension)
- style = instruments + genre ("dark orchestral, cello, low strings, cinematic, haunting")

**Chanson (`make_instrumental: false`)** :
- prompt = paroles ou description vocale narrative EN ANGLAIS
- style = genre + voix ("medieval folk, female voice, melancholic, acoustic guitar")

## Canal
Le channel par défaut est #musique. S'il n'existe pas, le créer d'abord :
```
POST /channel/create {"guild_id": "...", "channel_name": "musique", "topic": "Musique générée par Augure"}
```

## Message d'accompagnement
- 🎶 pour les instrumentaux
- 🎤 pour les chansons avec voix
- Court, dans le ton du MJ

## VRAM
La génération musicale n'utilise pas le GPU local (Suno est externe).
Pas besoin d'arbitrage VRAM pour la musique.
