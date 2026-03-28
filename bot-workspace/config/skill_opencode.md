# Skills OpenCode — Format et gestion

Ce fichier documente le système de skills OpenCode (ACP).
Les skills sont des modules invocables par le MJ, avec un format et un emplacement précis.

---

## Où se trouvent les skills

### Skills intégrés (versionnés dans git)
```
/workspace/skills/<nom>/SKILL.md
```
Livrés avec Augure. Modifiables par l'admin uniquement.
Exemples : `narrer`, `orchestrer`, `briefer-pnj`, `creer-pnj`, `creer-lieu`, etc.

### Skills custom (créés en cours de jeu, gitignorés)
```
/workspace/custom/.opencode/skills/<nom>/SKILL.md
```
Créés par le MJ sur demande de l'admin. Gitignorés — persistent dans le container.
Auto-découverts grâce au flag `--add-dir /workspace/custom` passé à OpenCode.

**Règle** : chaque skill est un répertoire contenant exactement un fichier `SKILL.md`.
Le nom du répertoire = le nom du skill.

---

## Format d'un SKILL.md

```markdown
---
name: nom-du-skill
description: Ce que fait le skill et quand l'utiliser (une phrase)
---

Instructions en markdown.
$ARGUMENTS est remplacé par ce que l'utilisateur tape après /nom-du-skill.
```

### Champs du frontmatter YAML

| Champ | Valeur | Effet |
|-------|--------|-------|
| `name` | string | Nom du skill (doit correspondre au nom du répertoire) |
| `description` | string | Description du skill |

---

## Ce que le MJ peut faire

- Lire les skills : `Read /workspace/skills/<nom>/SKILL.md`
- Modifier les skills custom : `Edit /workspace/custom/.opencode/skills/<nom>/SKILL.md`
- Créer un skill custom : `Bash(mkdir -p ...)` + `Write`
- Lister les skills : `Glob(/workspace/skills/*/SKILL.md)`

**Modifier les skills intégrés** (`/workspace/skills/`) : admin uniquement.

---

## Lister les skills disponibles

```bash
ls /workspace/skills/
ls /workspace/custom/.opencode/skills/
```

---

## Créer un skill custom

1. `Bash(mkdir -p /workspace/custom/.opencode/skills/<nom>)`
2. `Write` → `/workspace/custom/.opencode/skills/<nom>/SKILL.md`
3. Le frontmatter doit être du YAML valide (pas de tabulations, indentation 2 espaces)
