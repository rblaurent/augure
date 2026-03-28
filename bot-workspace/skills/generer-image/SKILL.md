---
name: generer-image
description: Générer une image via ComfyUI — portraits de PNJ, ambiances de lieux, moments marquants
---

# Générer une image

## Quand utiliser
- En début de scène pour poser l'ambiance (image de lieu)
- Quand un nouveau PNJ apparaît (portrait)
- Quand un joueur le demande
- Quand un moment est visuellement marquant

## Processus
1. Lire les tags d'apparence du PNJ ou du lieu concerné
2. Construire le prompt EN ANGLAIS
3. Appeler POST /generate via l'API interne
4. L'image est postée dans le canal demandé

## Construction du prompt
- Commencer par le style : "Cinematic shot, film grain, fantasy ultrarealistic photography"
- Décrire le sujet de façon narrative (le modèle Lumina2 aime les descriptions longues)
- Ajouter les tags de la fiche personnage/lieu
- Ajouter le contexte de la scène (éclairage, ambiance, action)

## API
```
POST /generate
Body : {
  "prompt": "...",
  "negative": "",
  "workflow": "z_turbo",
  "guild_id": "...",
  "channel_name": "rp"
}
```

## VRAM
La génération d'image décharge le LLM. Le MJ doit avoir FINI son raisonnement
avant de lancer la génération. Ne pas générer d'image au milieu d'une séquence de PNJ.

## Quand NE PAS générer
- Au milieu d'un échange de répliques (ça casse le rythme)
- Pour chaque scène (trop, c'est trop)
- Pendant le watchdog (sauf demande explicite)
