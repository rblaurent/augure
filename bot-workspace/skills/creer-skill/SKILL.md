---
name: creer-skill
description: Créer un nouveau skill OpenCode. Passer le nom du skill en argument. Guide la création du SKILL.md avec le bon format et au bon emplacement.
---

# Skill : creer-skill

Nom du skill à créer : $ARGUMENTS

## Procédure

1. **Valider l'argument** — Si $ARGUMENTS est vide, demander le nom du skill avant de continuer.

2. **Vérifier qu'il n'existe pas déjà**
   Glob(`/workspace/custom/.opencode/skills/$ARGUMENTS/SKILL.md`)
   Si trouvé → proposer de l'éditer plutôt que d'écraser.

3. **Lire le format de référence**
   Read(`/workspace/config/skill_opencode.md`) pour rappel du format YAML frontmatter.

4. **Collecter les informations nécessaires** :
   - `description` : une phrase qui explique ce que fait le skill et quand l'utiliser
   - Instructions : le corps du skill en markdown — ce que le MJ doit faire, avec $ARGUMENTS si besoin

5. **Créer le répertoire**
   ```bash
   mkdir -p /workspace/custom/.opencode/skills/$ARGUMENTS
   ```

6. **Écrire le fichier** avec Write :
   `/workspace/custom/.opencode/skills/$ARGUMENTS/SKILL.md`

   Format minimal :
   ```markdown
   ---
   name: $ARGUMENTS
   description: <description>
   ---

   # Skill : $ARGUMENTS

   <instructions en markdown>
   $ARGUMENTS est remplacé par ce que l'utilisateur tape après /$ARGUMENTS.
   ```

7. **Confirmer** : afficher le chemin créé et la commande d'invocation (`/$ARGUMENTS`).

## Rappel des champs frontmatter

| Champ | Rôle |
|-------|------|
| `name` | Nom du skill (doit correspondre au nom du répertoire) |
| `description` | Affiché dans la liste des skills |

## Emplacements

- Skills custom (créés en cours de jeu) : `/workspace/custom/.opencode/skills/<nom>/SKILL.md`
  (gitignorés — persistent dans le container, auto-découverts via `--add-dir /workspace/custom`)
- Skills intégrés (versionnés) : `/workspace/skills/<nom>/SKILL.md`
  (modifiables par l'admin uniquement)
- Lister les skills existants :
  ```bash
  ls /workspace/skills/
  ls /workspace/custom/.opencode/skills/
  ```
