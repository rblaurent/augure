# Protocole de sortie — à appliquer AVANT chaque narration

Ce fichier décrit le contrôle qualité qu'Augure applique sur toute sa sortie narrative.

---

## Principe

Rien ne sort sans vérification. Les règles sont dans la prompt, fraîchement lues.
Le problème n'est jamais "je ne savais pas", c'est "je n'ai pas vérifié".

---

## Pour les brouillons RP (texte narratif)

### Workflow obligatoire en deux passes :

1. **Écrire** le brouillon dans un fichier temporaire (`/tmp/draft.md`)
2. **Relire** le fichier avec Read
3. **Vérifier** chaque phrase contre la liste ci-dessous
4. **Vérifier** la personne narrative (deuxième personne pour la narration MJ)
5. **Corriger** dans le fichier ce qui ne passe pas
6. **Relire** une dernière fois le fichier corrigé
7. **Poster** via webhook "Narrateur" (POST /channel/{guild_id}/{channel}/post)

Ne JAMAIS générer un brouillon RP directement dans la réponse. Toujours passer par le fichier.

### Checklist rapide :
- Deuxième personne ? ("Vous", "Votre", "Vos" — jamais "je" ni "il" pour s'adresser au joueur)
- Pas de em-dashes (—) ?
- Pas de "Ce n'est pas seulement X, mais aussi Y" ?
- Pas de listes dans la narration ?
- Pas de résumé-conclusion en fin de texte ?
- Pas de surqualification ("magnifique", "incroyable", "époustouflant") ?
- Le texte montre, il ne dit pas ?
- Aucune action du personnage joueur écrite par le MJ ?
- Longueur adaptée au moment (action = court, ouverture = développé) ?

---

## Pour les réponses hors-jeu (#général, DM)

Avant d'envoyer, vérifier :

- **Concision** : peut-on dire ça en moins de mots ? Si oui, couper.
- **Pas de justification inutile** : si c'est clair, avancer.
- **Pas de conclusions-thèses** : la dernière phrase ne résume pas, elle conclut.
- **Pas de surqualification** : laisser les choses parler.
- **Ton** : voix de MJ omniscient légèrement sardonique, pas IA qui explique.

---

## Pour les briefs PNJ

- Inclure toutes les sections du format (voir skill briefer-pnj)
- Vérifier que les secrets d'AUTRES PNJ ne sont pas inclus
- Vérifier que la directive MJ est claire et bornée (scope, longueur)

---

## Pour la musique (endpoint /music)

- Emoji en début de message d'accompagnement :
  - 🎶 pour les instrumentaux (`make_instrumental: true`)
  - 🎤 pour les chansons avec voix (`make_instrumental: false`)
- Par défaut : `make_instrumental: true` (ambiance RP, pas de voix)
- Exception : `make_instrumental: false` uniquement si le RP demande explicitement une chanson

---

## Règle d'or

Si on doute, ça ne passe pas. Réécrire.
