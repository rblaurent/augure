---
name: creer-pnj
description: Créer ou mettre à jour la fiche d'un PNJ dans memory/characters/
---

# Créer ou mettre à jour un PNJ

## Quand utiliser
- Un nouveau personnage apparaît dans l'histoire (spontanément ou planifié)
- Un joueur demande l'introduction d'un type de personnage
- Le MJ prépare un arc et a besoin de nouveaux PNJ
- Une fiche existante doit être enrichie ou corrigée

## Processus
1. Construire le slug : minuscules, sans accents, underscores pour les espaces
2. Vérifier si une fiche existe : Glob(`/workspace/memory/characters/{slug}.md`)
   - Si oui → lire la fiche, identifier ce qui manque ou doit être mis à jour
   - Si non → créer à partir du template ci-dessous
3. Remplir toutes les sections du format
4. Générer une image (si pertinent) via POST /generate et noter l'URL dans Avatar
5. Ajouter le PNJ à active_scene.md s'il est déjà dans la scène

## Format de la fiche PNJ

```markdown
# [Nom]

- **Rôle** : [rôle narratif]
- **Créé le** : [date]
- **Affiché comme** : [nom affiché dans Discord]
- **Avatar** : [URL de l'image ou "à générer"]

## Webhook RP
- **Nom** : [nom affiché dans Discord — doit correspondre exactement]
- **Avatar** : [URL du portrait de référence]
- **Couleur** : [code hex] ([nom couleur — choisie selon le personnage : trait dominant, élément, ambiance])

## Portrait de référence

![Nom](URL)

Style : [description du style artistique]

## Personnalité
[Description courte, traits dominants]

## Apparence (génération d'images)
[Tags visuels en anglais pour ComfyUI]

### Tenues connues
- **[contexte]** : [description tenue]

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

## Relations
### [Nom du personnage lié]
- [nature de la relation, faits importants]

## Historique des interactions
- [date] : [description]

## Voix
[Style de dialogue, exemples de répliques]

## Notes narratives
- [observations, arcs en cours, informations MJ]
```

## Règle redirection

Si un personnage change de nom, l'ancien fichier devient une redirection :
```
⚠️ Ce personnage a été renommé **X**. → Fiche complète : [x.md](x.md)
```

## Principes
- Chaque PNJ a un DÉFAUT ou une particularité qui le rend mémorable
- Chaque PNJ a au moins UN secret (même mineur)
- Chaque PNJ a un objectif (même "survivre jusqu'à demain")
- La "Voix" doit être distinctive — pas deux PNJ qui parlent pareil
- Les tags d'apparence doivent être assez précis pour une bonne génération d'image
- Les fiches sont vivantes : mettre à jour au fil du RP, pas seulement à la création

## PNJ spontanés
Quand le MJ invente un PNJ en pleine scène ("un mendiant vous interpelle") :
- Créer la fiche IMMÉDIATEMENT, même minimale
- Compléter les sections manquantes après la scène
- Ne JAMAIS laisser un PNJ sans fiche — même les figurants ont un fichier

---

## Prompts image — style Arcane/Fortiche (style validé)

**Prompt positif** (adapter les détails physiques) :
```
CINEMATIC CLOSE-UP PORTRAIT, stylized digital painting, Arcane Fortiche animation art style, cel-shaded with visible brushstrokes, matte painting texture, bold graphic shadows. [DESCRIPTION PHYSIQUE DU PERSONNAGE]. [TENUE]. [POSTURE ET EXPRESSION]. Warm dramatic side lighting, golden hour glow, cinematic depth of field, bokeh background.
```

**Prompt négatif** (base commune) :
```
ugly, deformed, bad anatomy, bad hands, extra fingers, blurry, lowres, photorealistic, photograph, hyperrealistic, smooth digital art, airbrushed, 3D render, plastic skin, anime eyes, cartoon, chibi, Disney, oil painting, watercolor
```

**Workflow** : `z_turbo`

**Règles de prompt** :
- Jamais de "NOT" dans le prompt positif (le modèle l'interprète mal)
- Cheveux ondulés : spécifier "SOFT WAVY", éviter "curly"
- Col fermé voulu : insister sur "high closed neckline" ; mettre "low neckline, revealing cleavage" dans le négatif
