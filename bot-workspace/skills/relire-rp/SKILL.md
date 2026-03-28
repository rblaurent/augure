---
name: relire-rp
description: Relire un brouillon RP contre la checklist de patterns bannis avant envoi. Passer le texte en argument, ou le sauvegarder dans /tmp/draft_rp.md et appeler sans argument.
---

# Skill : relire-rp

Texte à relire : $ARGUMENTS

## Procédure

1. **Récupérer le texte à analyser**
   - Si $ARGUMENTS est non vide → analyser directement ce texte.
   - Si $ARGUMENTS est vide → lire `/tmp/draft_rp.md`. Si ce fichier n'existe pas non plus → demander le texte.

2. **Lire la checklist complète**
   Read(`/workspace/memory/meta/banned_patterns.md`)

3. **Analyser le texte pattern par pattern** — vérifier chaque règle :

   **1. Tricolons rythmés** — trois adj/noms/verbes en série cadencée
   → Chercher les groupes de 3 éléments séparés par virgule ou point.
   → Ex. détection : "X, Y, Z." en fin de phrase ou en apposition.

   **2. "Pas X. Y."** — négation courte suivie d'affirmation courte
   → Chercher les phrases courtes commençant par "Pas " suivies immédiatement d'une autre phrase courte.

   **3. "N'était plus X. C'était Y"** — bascule rhétorique
   → Chercher "n'était plus" / "ce n'était plus" suivi de "c'était".

   **4. "Ce n'est pas seulement X, mais aussi Y"**
   → Chercher "pas seulement" + "mais aussi".

   **5. Fermeture poétique-thèse** — dernière phrase qui résume/boucle
   → Lire la dernière phrase. Est-ce une métaphore conclusive ? Un résumé symbolique ? Une image qui "ferme" le texte ?

   **6. Em-dashes (—)**
   → Chercher le caractère — (U+2014). Zéro tolérance.

   **7. Anaphores mécaniques** — "Chaque X... chaque Y... chaque Z..." (3 reprises ou plus)
   → Chercher les répétitions de début de proposition en série.

   **8. Énumérations à fragments** — 3+ phrases nominales courtes en série
   → "La robe noire. Le tissu. La poussière." — fragments sans verbe en série de 3+.

   **9. Résumé-reformulation** — répéter la même idée autrement dans la phrase suivante
   → Lire les paires de phrases consécutives : disent-elles la même chose ?

   **10. Métaphores explicatives** — comparaison + explication de ce qu'elle signifie
   → Chercher "comme [X] qui dit/signifie/montre [Y]" ou structure équivalente.

4. **Produire le rapport**

   Si aucun problème → répondre :
   ```
   ✅ PASS — Aucun pattern banni détecté.
   ```

   Si des problèmes sont trouvés → pour chaque violation :
   ```
   ❌ [Numéro et nom du pattern]
   Texte incriminé : "..."
   Pourquoi : [explication courte]
   Suggestion : [réécriture proposée ou piste]
   ```

   Terminer par :
   ```
   → [N] problème(s) à corriger avant envoi.
   ```

5. **Ne pas corriger automatiquement** — seulement signaler et suggérer.
   La correction reste à la main du MJ pour préserver la voix narrative.

## Règle d'or (rappel)

Si une phrase "sonne bien" de façon trop évidente, c'est probablement une formule.
Le RP est dense et tranchant, pas joli. Brut, imparfait, spécifique — pas lisse et cadencé.
