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
Créés par le MJ via `/creer-skill`. Gitignorés — persistent dans le container.
Auto-découverts grâce au flag `--add-dir /workspace/custom` passé à OpenCode.

**Règle** : chaque skill est un répertoire contenant exactement un fichier `SKILL.md`.
Le nom du répertoire = le nom du skill (celui qu'on tape après `/`).

---

## Lister les skills disponibles

```bash
ls /workspace/skills/
ls /workspace/custom/.opencode/skills/
```

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
| `description` | string | Description affichée dans la liste des skills |

Tous les champs sont optionnels sauf `name` et `description`.

---

## Syntaxe spéciale dans les instructions

### Arguments passés par l'utilisateur
```
$ARGUMENTS
```
Remplacé par tout ce que l'utilisateur tape après le nom du skill.
Exemple : `/lire-logs last` → `$ARGUMENTS` vaut `last`.

---

## Créer ou modifier un skill

**Utiliser le skill `/creer-skill`** pour créer un nouveau skill pas à pas.

**Manuellement** :
1. `Bash(mkdir -p /workspace/custom/.opencode/skills/<nom>)`
2. `Write` → `/workspace/custom/.opencode/skills/<nom>/SKILL.md`
3. Le frontmatter doit être du YAML valide (pas de tabulations, indentation 2 espaces)

**Modifier** :
1. `Read` → `/workspace/skills/<nom>/SKILL.md` (intégré) ou `/workspace/custom/.opencode/skills/<nom>/SKILL.md` (custom)
2. `Edit` pour modifier

**Lister** :
- `Glob(/workspace/skills/*/SKILL.md)` pour les skills intégrés
- `Glob(/workspace/custom/.opencode/skills/*/SKILL.md)` pour les skills custom

---

## Ce que le MJ peut faire

- ✅ Créer des skills custom : `mkdir -p` via Bash + Write dans `/workspace/custom/.opencode/skills/`
- ✅ Lire et modifier des skills custom existants : Read + Edit
- ✅ Lister les skills : Glob sur les deux emplacements
- ❌ Modifier les skills intégrés (`/workspace/skills/`) sans permission de l'admin

---

## Exemples

### Skill minimal
```markdown
---
name: bonjour
description: Dit bonjour avec le nom passé en argument
---

Dis bonjour à $ARGUMENTS de façon chaleureuse.
```
Invocation : `/bonjour Joueur`

### Skill avec procédure complexe
```markdown
---
name: resoudre-combat
description: Résoudre un combat selon les règles maison — passer les participants en argument
---

# Combat : $ARGUMENTS

## Procédure
1. Lire les fiches des participants dans /workspace/memory/characters/
2. Appliquer les règles de /workspace/config/regles_combat.md
3. Narrer le résultat via skill narrer
```
