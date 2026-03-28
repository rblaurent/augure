---
name: lire-logs
description: Lire et interpréter les logs d'une invocation passée — outils appelés, résultats, erreurs, coût. Passer un nom de fichier en argument, ou "last" pour le plus récent, ou rien pour lister.
---

# Skill : lire-logs

Les logs d'invocation sont dans `/workspace/memory/meta/invocation_logs/`.
Chaque fichier `.jsonl` = une invocation complète (une session OpenCode).

## Utilisation

- `/lire-logs` — liste les 20 logs les plus récents
- `/lire-logs last` — lit le log le plus récent
- `/lire-logs 20260327_212000_user_710765431090315334.jsonl` — lit un fichier précis

Arguments reçus : $ARGUMENTS

## Procédure

1. Si $ARGUMENTS est vide → liste les fichiers avec Glob(`/workspace/memory/meta/invocation_logs/*.jsonl`), retourne les 20 derniers triés par date.

2. Si $ARGUMENTS est "last" → Glob pour trouver le plus récent, lis-le.

3. Sinon → lis `/workspace/memory/meta/invocation_logs/$ARGUMENTS`.

## Structure d'un fichier .jsonl

Chaque ligne est un objet JSON indépendant. Types d'événements :

**Ligne 1 — prompt reçu**
```json
{"type": "prompt", "content": "...texte complet du prompt..."}
```
→ Ce que le système a envoyé comme contexte et instructions.

**Appel d'outil**
```json
{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "/workspace/..."}}]}}
```
→ L'outil `Read` a été appelé avec ce fichier.

**Résultat d'outil**
```json
{"type": "user", "message": {"content": [{"type": "tool_result", "content": "...contenu retourné..."}]}}
```
→ Ce que l'outil a retourné.

**Texte intermédiaire**
```json
{"type": "assistant", "message": {"content": [{"type": "text", "text": "...raisonnement..."}]}}
```
→ Ce qui a été écrit/pensé entre les outils.

**Résultat final**
```json
{"type": "result", "subtype": "success", "result": "...réponse finale...", "total_cost_usd": 0.21}
```
→ Ce que le joueur a reçu, et le coût de l'invocation.

## Ce qu'on peut apprendre d'un log

- Quels fichiers ont été lus (et dans quel ordre)
- Quels appels curl ont été faits et ce qu'ils ont retourné
- Où une erreur a été rencontrée (tool_result avec message d'erreur)
- Pourquoi une décision a été prise (texte intermédiaire)
- Combien ça a coûté

## Nommage des fichiers

```
YYYYMMDD_HHMMSS_user_{discord_user_id}.jsonl    ← requête d'un joueur
YYYYMMDD_HHMMSS_watchdog.jsonl                  ← battement de cœur autonome
YYYYMMDD_HHMMSS_maintenance_{channel}.jsonl     ← mise à jour mémoire
```
