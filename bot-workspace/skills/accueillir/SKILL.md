---
name: accueillir
description: Accueillir un nouveau joueur — créer sa fiche et l'intégrer dans la scène
---

# Accueillir un nouveau joueur

## Quand utiliser
Un nouveau joueur rejoint le serveur ou demande à jouer.

## Processus
1. Le saluer chaleureusement dans #général
2. Lui demander :
   - Le nom de son personnage
   - Une description courte (apparence, personnalité, background)
   - Ce qu'il aime dans le RP (combat, intrigue, exploration, romance...)
3. Créer sa fiche joueur dans players/player_{id}.md
4. Créer la fiche de son personnage dans characters/{nom}.md
5. Proposer de générer un avatar (image)
6. L'intégrer dans la scène en cours de façon naturelle :
   - Le MJ invente une raison narrative pour son arrivée
   - Ou propose au joueur comment il veut entrer dans l'histoire
7. Mettre à jour active_scene.md

## Format fiche joueur

```markdown
# Joueur : [pseudo Discord]

- **Discord ID** : [id]
- **Rejoint le** : [date]

## Personnage actif
- **Nom** : [nom du personnage]
- **Description** : [ce que le joueur a fourni]
- **Apparence** : [tags pour génération d'images]
- **Avatar** : [URL]

## Préférences de style
- Ton préféré : [dark, léger, épique...]
- Ce qu'il aime : [combat, intrigue, romance, exploration...]
- Ce qu'il n'aime pas : [...]

## Notes du MJ
[Observations privées sur le joueur — son style, ce qui marche avec lui]
```

## Ton
Chaleureux, inclusif, sans pression. Le joueur doit se sentir bienvenu.
Le MJ peut poser les questions en DM si le joueur préfère.
