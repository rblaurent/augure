---
name: creer-pnj
description: Créer une fiche PNJ complète dans memory/characters/
---

# Créer un PNJ

## Quand utiliser
- Un nouveau personnage apparaît dans l'histoire (spontanément ou planifié)
- Un joueur demande l'introduction d'un type de personnage
- Le MJ prépare un arc et a besoin de nouveaux PNJ

## Processus
1. Déterminer le rôle narratif (allié, obstacle, mystère, comic relief, etc.)
2. Créer la fiche dans /workspace/memory/characters/{nom_slug}.md
3. Remplir TOUTES les sections du format (voir ci-dessous)
4. Générer une image (si pertinent) via /generate et noter l'URL dans Avatar
5. Ajouter le PNJ à active_scene.md s'il est déjà dans la scène

## Format de la fiche PNJ

```markdown
# [Nom]

- **Rôle** : [rôle narratif]
- **Créé le** : [date]
- **Affiché comme** : [nom affiché dans Discord]
- **Avatar** : [URL de l'image ou "à générer"]

## Personnalité
[Description courte, traits dominants]

## Apparence (génération d'images)
[Tags visuels en anglais pour ComfyUI]

## Secrets (INVISIBLE pour les joueurs et les autres PNJ)
- [secret 1]
- [secret 2]

## Objectifs
1. [objectif principal]
2. [objectif secondaire]

## Ce que [Nom] sait
- [fait 1]
- [fait 2]

## Ce que [Nom] ne sait PAS
- [ignorance 1]
- [ignorance 2]

## Historique des interactions
- [date] : [description]

## Voix
[Style de dialogue, exemples de répliques]
```

## Principes
- Chaque PNJ a un DÉFAUT ou une particularité qui le rend mémorable
- Chaque PNJ a au moins UN secret (même mineur)
- Chaque PNJ a un objectif (même "survivre jusqu'à demain")
- La "Voix" doit être distinctive — pas deux PNJ qui parlent pareil
- Les tags d'apparence doivent être assez précis pour une bonne génération d'image

## PNJ spontanés
Quand le MJ invente un PNJ en pleine scène ("un mendiant vous interpelle") :
- Créer la fiche IMMÉDIATEMENT, même minimale
- Compléter les sections manquantes après la scène
- Ne JAMAIS laisser un PNJ sans fiche — même les figurants ont un fichier
