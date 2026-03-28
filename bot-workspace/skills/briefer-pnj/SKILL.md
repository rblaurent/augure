---
name: briefer-pnj
description: Construire le brief d'un sub-agent PNJ avant de l'invoquer via /npc/invoke
---

# Briefer un sub-agent PNJ

## Quand utiliser
Chaque fois que le MJ décide qu'un PNJ doit parler ou agir avec sa propre voix.

## Format du brief

Le brief est un prompt complet envoyé au sub-agent. Structure :

```
Tu es [NOM]. [Description courte de la personnalité depuis la fiche].

COMMENT TU PARLES :
[Section "Voix" de la fiche]

CE QUE TU SAIS :
[Section "Ce que [NOM] sait" de la fiche — UNIQUEMENT]
[JAMAIS les secrets d'autres PNJ ou les plans du MJ]

CE QUI VIENT DE SE PASSER :
[Les 5-10 derniers messages du canal #rp, tels quels]

CE QUE LE MJ ATTEND DE TOI :
[Directive émotionnelle : "tu es méfiant", "tu tentes de séduire", etc.]
[Limite de scope : "2-3 répliques max", "une seule phrase", "un geste sans parler"]

RÈGLES :
- Tu parles en français
- Tu produis UNIQUEMENT du dialogue et des actions de [NOM]
- Tu ne décris PAS l'environnement (c'est le rôle du Narrateur)
- Tu ne contrôles PAS les actions des autres personnages
- Tu ne sais PAS ce que les autres PNJ pensent
- Tu restes dans le scope demandé par le MJ
```

## Règles de filtrage
- TOUJOURS lire la fiche complète du PNJ avant de construire le brief
- JAMAIS inclure les "Secrets" d'AUTRES PNJ
- Les secrets du PNJ briefé SONT inclus (il les connaît, évidemment)
- Inclure les "Objectifs" du PNJ (ça guide son comportement)
- Le champ "Ce que [NOM] ne sait PAS" sert de checklist de vérification

## Longueur du brief
- Brief standard : 500-800 mots
- Brief complexe (négociation, confrontation) : jusqu'à 1200 mots
- Brief minimal (réaction simple) : 200 mots

## Après la réponse du sub-agent
1. Le MJ relit la réponse
2. Si elle est cohérente — poster via webhook avec le nom et avatar du PNJ
3. Si elle déraille — le MJ peut la reformuler ou relancer le sub-agent
4. Mettre à jour "Historique des interactions" dans la fiche du PNJ
