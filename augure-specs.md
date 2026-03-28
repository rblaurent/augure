# Augure — Spécifications Techniques

## Vue d'ensemble

**Augure** est un Maître du Jeu (MJ) autonome pour serveurs Discord de roleplay. Contrairement à Stasia (assistante RP réactive), Augure est **proactif** : il conduit l'histoire, joue les PNJ via des sub-agents dédiés, construit le monde, et orchestre les scènes comme un chef d'orchestre narratif.

**Deux projets, deux repos, deux comptes GitHub.**
- **Stasia** (référence) : `T:\Projects\stasia\` — le bot existant dont Augure hérite. Lecture seule.
- **Augure** (nouveau) : `T:\Projects\augure\` — le nouveau projet. Repo GitHub séparé, compte différent.

Claude Code a accès aux deux simultanément. La consigne est claire : **lire Stasia avant de coder Augure**. Ne pas réinventer ce qui existe. Copier, comprendre, adapter.

**Voix narrative** : inspirée de Divinity: Original Sin 2 — omnisciente, légèrement sardonique, deuxième personne, avec une distance amusée. "Vous poussez la porte de la taverne. L'odeur de bière rance vous saisit avant même que vos yeux ne s'adaptent à la pénombre."

**Joueurs** : nombre variable et ouvert. Un univers par serveur Discord.

**Langue** : français pour la narration et le RP.

---

## Projet de référence : Stasia

Augure est un projet GitHub séparé, sur un compte GitHub différent. Mais il **hérite massivement** de l'architecture et du code de Stasia, un bot Discord RP existant.

**Claude Code a accès aux deux projets simultanément** :
- **Stasia** (référence, lecture seule) : `T:\Projects\stasia\`
- **Augure** (nouveau projet, écriture) : `T:\Projects\augure\`

### Instruction pour Claude Code

Avant de coder un composant d'Augure, **toujours lire le fichier équivalent dans Stasia d'abord**. La majorité du code est reprise et adaptée. Ne pas réinventer ce qui existe — copier, comprendre, puis adapter.

### Ce qu'on copie TEL QUEL depuis Stasia

Ces fichiers peuvent être copiés quasi-verbatim. Lire l'original, comprendre, copier, ajuster les imports si nécessaire.

| Fichier Stasia | → Fichier Augure | Notes |
|---------------|-----------------|-------|
| `src/webhook_manager.py` | `src/webhook_manager.py` | Identique. Gestion webhooks par channel. |
| `src/comfyui_bridge.py` | `src/comfyui_bridge.py` | Identique. Génération images/vidéos via ComfyUI API. WebSocket pour le suivi de progression. |
| `src/suno_bridge.py` | `src/suno_bridge.py` | Identique. Génération musique via Suno API. |
| `src/message_splitter.py` | `src/message_splitter.py` | Identique. Split messages > 2000 chars aux limites de paragraphe. |
| `src/sanitizer.py` | `src/sanitizer.py` | Identique. Scrub paths Windows, PII, tokens. |
| `src/emoji_utils.py` | `src/emoji_utils.py` | Identique. Résolution emoji shortcodes → Unicode/custom. |
| `requirements.txt` | `requirements.txt` | Base identique, ajouter les dépendances OpenCode si nécessaire. |

### Ce qu'on adapte depuis Stasia

Ces fichiers sont la base mais nécessitent des modifications significatives. **Toujours lire l'original Stasia en premier.**

| Fichier Stasia | → Fichier Augure | Ce qui change |
|---------------|-----------------|---------------|
| `src/bot.py` | `src/bot.py` | **Lire en premier.** Même structure (on_ready, on_message, event handlers, watchdog loop, maintenance loop). Adapter : le handler on_message dans #rp déclenche le flow MJ au lieu de répondre directement. Ajouter le buffer d'interruption. Ajouter le stream vers #mj-screen. Le watchdog devient "préparation entre sessions" (pas d'action visible). |
| `src/claude_bridge.py` | `src/opencode_bridge.py` | **Lire en premier.** Même pattern exact : ClaudeQueue → OpenCodeQueue, ClaudeRequest → MJRequest, subprocess avec prompt sur stdin et stream-json sur stdout. Adapter les flags CLI (OpenCode au lieu de `claude`). Garder le pattern workers par user_id, le lock global (qui devient le VRAM lock), la construction du prompt, le logging des invocations. Ajouter : le stream parsing vers MJScreen. |
| `src/internal_api.py` | `src/internal_api.py` | **Lire en premier.** Mêmes routes de base (guilds, history, post, edit, delete, send, react, unreact, generate, music, channel/create). Ajouter les routes : POST /npc/invoke, GET /npc/list, POST /mj-screen/post. Le GenerationProgress est repris tel quel. |
| `src/memory_manager.py` | `src/memory_manager.py` | **Lire en premier.** Même pattern (JSON pour la comptabilité Discord, fichiers MD pour le contenu narratif). Adapter la structure de répertoires (voir section Mémoire). Garder : store_webhook_messages, get_last_sync, update_last_sync, watchdog tracking, music posts, image/video media logging. Ajouter : gestion scènes, gestion arcs. |
| `src/config.py` | `src/config.py` | **Lire en premier.** Même pattern (env vars, load_system_prompts depuis .md, load_sanitizer_patterns, load_workflows). Ajouter : config Ollama (host, port, model), config channels (RP_CHANNEL, MJ_SCREEN_CHANNEL), VRAM arbitrator settings. Retirer : CLAUDE_BIN, CLAUDE_TIMEOUT (remplacer par OPENCODE_BIN, MJ_TIMEOUT, NPC_TIMEOUT). |
| `Dockerfile` | `Dockerfile` | **Lire en premier.** Même base (python:3.12-slim, non-root user, workspace dirs). Remplacer : Node.js + Claude CLI → OpenCode CLI. Ajouter : client Ollama si nécessaire. |
| `docker-compose.yml` | `docker-compose.yml` | **Lire en premier.** Même structure de volumes. Adapter : le volume claude_auth disparaît, ajouter accès réseau vers Ollama (host.docker.internal:11434). |
| `entrypoint.sh` | `entrypoint.sh` | Adapter pour OpenCode au lieu de Claude CLI. |

### Ce qu'on adapte depuis la config Stasia

| Fichier Stasia | → Fichier Augure | Ce qui change |
|---------------|-----------------|---------------|
| `bot-workspace/config/system_prompts.md` | `bot-workspace/config/system_prompts.md` | **Lire en premier.** Même structure (sections # user_request, # watchdog, # maintenance). Réécrire le contenu pour le rôle de MJ au lieu d'assistante. Garder : la structure des endpoints API, les règles de format de réponse, le mécanisme de journal. |
| `bot-workspace/config/identity.md` (dans runtime/) | `bot-workspace/config/identity.md` | Réécrire complètement pour le personnage du MJ (narrateur Divinity OS2). Garder : la structure (sections Qui tu es, Ton ton, Concision, Ce que tu n'es pas, Langue). |
| `bot-workspace/config/output_protocol.md` | `bot-workspace/config/output_protocol.md` | **Lire en premier.** Adapter pour la narration MJ au lieu de l'écriture RP assistée. Garder : le principe du workflow deux passes (écrire dans /tmp, relire, vérifier, poster). |
| `bot-workspace/config/power_fantasy.md` | Non repris | Ce fichier est spécifique à Stasia. Augure utilise `config/guides.md` qui est configurable par serveur. |
| `bot-workspace/config/sanitizer_patterns.md` | `bot-workspace/config/sanitizer_patterns.md` | Copier et adapter (patterns personnels de l'admin). |
| `bot-workspace/config/skill_claude_code.md` | `bot-workspace/config/skill_opencode.md` | **Lire en premier.** Adapter le format des skills pour OpenCode/ACP au lieu de Claude Code. Même principe : répertoire + SKILL.md. |

### Ce qui est entièrement nouveau

Ces composants n'existent pas dans Stasia. Pas de fichier de référence.

| Fichier Augure | Description |
|---------------|-------------|
| `src/vram_arbitrator.py` | Lock asyncio exclusif entre LLM (Ollama) et ComfyUI. Gère le déchargement/rechargement du modèle. |
| `src/mj_screen.py` | Parse le stream d'événements du subprocess OpenCode et poste des embeds formatés dans #mj-screen en temps réel. |
| `src/npc_invoker.py` | Appelle Ollama directement (pas OpenCode) pour les sub-agents PNJ. Construit le brief, envoie, récupère la réponse, poste via webhook. |
| `bot-workspace/config/guides.md` | Règles du serveur (ton, limites, style). Nouveau concept — remplace la config hardcodée de Stasia. |
| `bot-workspace/skills/` | Tout le répertoire de skills MJ (narrer, orchestrer, briefer-pnj, etc.). Nouveau concept pour Augure — les skills Stasia sont dans `.claude/skills/` avec un format différent. |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                 MACHINE WINDOWS                      │
│                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ Ollama/vLLM  │  │ ComfyUI      │  │ Docker     │ │
│  │              │  │              │  │ Container  │ │
│  │ Qwen2.5-32B  │  │ Flux/WanVid  │  │            │ │
│  │ Q6_K (~26GB) │  │ ~12-20GB     │  │ Bot Python │ │
│  │              │  │              │  │ OpenCode   │ │
│  │  :11434  ◄───┼──┼──────────────┼──┤            │ │
│  │              │  │  :8188  ◄────┼──┤ API :8765  │ │
│  │              │  │              │  │            │ │
│  │  ◄── VRAM ──►│  │              │  │ Volumes:   │ │
│  │   EXCLUSIF   │  │              │  │ /workspace │ │
│  └──────────────┘  └──────────────┘  └────────────┘ │
│                                                      │
│  VRAM Arbitrator : un seul à la fois sur le GPU      │
│  LLM chargé par défaut, déchargé avant ComfyUI      │
└─────────────────────────────────────────────────────┘
         │
         │ Discord API (HTTPS)
         ▼
┌─────────────────────────────────────────────────────┐
│              SERVEUR DISCORD                         │
│                                                      │
│  #rp          — Canal de jeu (webhooks uniquement)   │
│  #général     — Discussion hors-jeu                  │
│  #mj-screen   — Thinking + tool calls du MJ          │
│  #encyclopédie — Lore, fiches publiques, images      │
└─────────────────────────────────────────────────────┘
```

---

## Arbitrage VRAM

Le GPU (RTX 5090, 32 GB) est partagé entre le LLM (Ollama/vLLM) et ComfyUI (images/vidéos). Ils ne tournent **jamais en même temps**.

### Composant : `VRAMArbitrator`

```
État par défaut : LLM chargé

Quand une génération image/vidéo est demandée :
  1. Acquérir le lock VRAM
  2. Décharger le LLM (POST http://localhost:11434/api/generate {"model":"...", "keep_alive":0})
  3. Attendre confirmation de libération VRAM
  4. Lancer le job ComfyUI
  5. Attendre la fin du job ComfyUI
  6. Relâcher le lock VRAM
  7. Le prochain appel LLM rechargera le modèle automatiquement (~5-10s)

Quand un appel LLM est demandé :
  1. Acquérir le lock VRAM (attend si ComfyUI tourne)
  2. Appeler OpenCode (qui appelle Ollama, qui charge le modèle si nécessaire)
  3. Relâcher le lock VRAM
```

Le lock VRAM remplace le lock global Claude de Stasia. Tout passe par là — MJ, sub-agents PNJ, et ComfyUI.

---

## Les trois types d'agents

### 1. Agent MJ (principal)

**Déclenché par** : message d'un joueur dans #rp, @mention, DM, ou watchdog.

**Ce qu'il fait** :
- Lit l'état du monde (scène active, PNJ présents, arcs en cours)
- Décide des conséquences de l'action du joueur
- Narre la scène (posté via webhook "Narrateur" dans #rp)
- Décide quels PNJ réagissent et dans quel ordre
- Lance les sub-agents PNJ (séquentiellement, chacun voyant les réponses précédentes)
- Met à jour la mémoire (scène, PNJ, arcs)
- Tout son raisonnement est streamé dans #mj-screen

**System prompt** : lit `config/identity.md`, `config/guides.md`, les skills pertinents, puis le contexte Discord.

**Outils disponibles** : Read, Write, Edit, Glob, WebFetch, Bash (curl vers API interne uniquement).

### 2. Sub-agent PNJ

**Déclenché par** : le MJ, via l'API interne (nouvelle route `/npc/invoke`).

**Ce qu'il reçoit** (le "brief") :
- La fiche complète du PNJ (`characters/{nom}.md`)
- Le filtre de connaissances (ce que le PNJ sait / ne sait pas)
- Les derniers messages du canal #rp (ce qui vient de se passer)
- Ce que les PNJ précédents viennent de dire (pour les réactions naturelles)
- La directive du MJ ("tu es surpris", "tu essaies de cacher ta nervosité")
- La limite de longueur et de scope

**Ce qu'il produit** : uniquement du dialogue et des actions du PNJ, en première personne ou troisième personne selon le guide du serveur.

**Ce qu'il ne peut PAS faire** :
- Lire des fichiers mémoire au-delà de ce que le brief lui donne (pas d'accès Read/Glob)
- Appeler l'API interne (pas de Bash/WebFetch)
- Modifier la mémoire
- Savoir ce que les autres PNJ pensent (seulement ce qu'ils ont dit/fait)

**Outils disponibles** : aucun. Le sub-agent PNJ est un appel LLM pur (prompt in → texte out), sans outils. C'est le MJ qui poste le résultat via webhook.

### 3. Agent Watchdog (préparation entre sessions)

**Déclenché par** : timer périodique (toutes les 15-30 minutes).

**Ce qu'il fait** :
- Lit les nouveaux messages dans tous les channels
- Met à jour la mémoire narrative (scènes, arcs, PNJ)
- Prépare en coulisses (notes pour les prochaines scènes, étoffe les PNJ)
- Réagit avec des emojis si pertinent
- Ne fait RIEN bouger dans le monde — le monde n'avance pas sans les joueurs

**Identique au watchdog Stasia** dans son mécanisme, adapté pour le rôle de MJ.

---

## Flow de jeu détaillé

### Scénario : un joueur agit

```
1. RÉCEPTION
   Joueur poste dans #rp : "Je m'approche du bar et commande une bière."
   → bot.py reçoit on_message, détecte que c'est #rp

2. CONTEXTE
   Le bot construit le contexte :
   - Historique récent de #rp (30-50 messages)
   - ID du joueur, personnage actif
   - Guild, channel

3. INVOCATION MJ
   Le bot lance OpenCode en subprocess avec :
   - System prompt du MJ (identity + guides + skills)
   - Le contexte Discord
   - Le message du joueur

4. MJ RÉFLÉCHIT (streamé dans #mj-screen)
   Le MJ :
   a. Lit active_scene.md → "Taverne du Chien Borgne, soirée"
   b. Lit characters_present.md → "Kael (au fond), Tavernière Marta"
   c. Lit la fiche de Kael et Marta
   d. Décide : "Marta sert la bière. Kael observe depuis son coin."

5. MJ NARRE (webhook "Narrateur" dans #rp)
   "La tavernière lève à peine les yeux de son torchon graisseux.
    Un pichet de bière brune atterrit sur le comptoir avec un bruit
    sourd. Au fond de la salle, une silhouette vous observe."

6. MJ LANCE LES PNJ
   a. POST /npc/invoke — brief pour Marta :
      "Tu sers une bière sans enthousiasme. Réplique courte, bourrue."
      → Sub-agent produit : « Trois pièces. Et essuyez vos bottes. »
      → Bot poste via webhook "Marta" avec son avatar

   b. POST /npc/invoke — brief pour Kael :
      "Tu observes le nouveau venu. Tu ne dis rien pour l'instant,
       mais tu es intrigué. Décris ta réaction intérieure en une phrase."
      → Sub-agent produit : (Kael ne dit rien — le MJ décide de ne pas poster)
      → Le MJ note dans la mémoire de Kael : "A repéré le joueur, intrigué"

7. MJ MET À JOUR LA MÉMOIRE
   - active_scene.md : joueur au bar, a commandé une bière
   - kael.md : note "observe le joueur depuis son coin, intrigué"
   - mj_log.md : trace de la scène

8. MJ REND LA MAIN
   Le MJ attend le prochain message d'un joueur.
```

### Scénario : interruption

```
Le MJ est en train de faire parler Marta (PNJ 1 sur 2).
Le joueur écrit : "Je renverse la table !"

→ Le message est bufferisé.
→ Le MJ finit la réplique de Marta (déjà en cours).
→ Avant de lancer Kael, le MJ voit le message bufferisé.
→ Le MJ décide : l'interruption est narrative, on l'intègre.
→ Le MJ narre la table renversée, puis relance les PNJ
   avec le nouveau contexte (Marta et Kael réagissent à la table).
```

### Scénario : plusieurs joueurs

```
Joueur A écrit dans #rp.
Pendant que le MJ traite → Joueur B écrit aussi.

→ Le MJ traite A d'abord (FIFO).
→ Quand il a fini avec A, il prend le message de B.
→ Il intègre le résultat de A dans le contexte de B.
→ Si A et B agissent dans la même scène, le MJ peut
   combiner les deux dans une seule narration.
```

---

## Channels Discord

### Obligatoires (créés au setup du serveur)

| Channel | Rôle | Qui y poste |
|---------|------|-------------|
| `#rp` | Canal de jeu principal | Webhooks (Narrateur + PNJ) + joueurs |
| `#général` | Discussion hors-jeu, questions au MJ | Tout le monde + le bot |
| `#mj-screen` | Stream du raisonnement du MJ | Le bot uniquement (embeds) |

### Optionnels (créés par le MJ si besoin)

| Channel | Rôle |
|---------|------|
| `#encyclopédie` | Lore public, fiches de personnages, images de référence |
| `#musique` | Générations musicales (hérité de Stasia) |
| Channels RP additionnels | Le MJ peut créer des channels pour des scènes parallèles |

### Embeds dans #mj-screen

| Type | Couleur | Contenu |
|------|---------|---------|
| Thinking | `0x95a5a6` (gris) | Le raisonnement interne du MJ |
| Tool call | `0x3498db` (bleu) | Nom de l'outil + paramètres |
| Tool result | `0x2ecc71` (vert) | Résultat de l'outil (tronqué) |
| Tool error | `0xe74c3c` (rouge) | Erreur |
| NPC brief | `0x9b59b6` (violet) | Brief envoyé à un sub-agent PNJ |
| NPC response | `0xf39c12` (orange) | Réponse brute du sub-agent PNJ |
| Decision | `0x1abc9c` (turquoise) | Décision du MJ (qui parle, quoi faire) |

---

## MJ Screen — Stream vers Discord

### Mécanisme

Le subprocess OpenCode produit un stream d'événements (format à déterminer par Claude Code en examinant l'implémentation ACP d'OpenCode). Le composant `MJScreen` parse ce stream ligne par ligne et poste des embeds formatés dans #mj-screen en temps réel.

### Ce qui est affiché

- **Thinking** : le raisonnement du MJ, affiché en gris. Tronqué à 4096 chars (limite embed Discord).
- **Lecture de fichier** : "📖 Lecture de characters/kael.md" — juste le nom du fichier, pas le contenu.
- **Écriture de fichier** : "✏️ Mise à jour de scenes/active_scene.md" — nom + diff courte.
- **Appel API interne** : endpoint + paramètres clés (ex: "POST /npc/invoke — Kael").
- **Brief PNJ** : le brief complet envoyé au sub-agent (en violet).
- **Réponse PNJ** : la réponse brute avant posting webhook (en orange).
- **Décision** : "→ Marta parle, Kael observe en silence" (en turquoise).

### Ce qui n'est PAS affiché

- Le contenu complet des fichiers lus (juste le nom).
- Les détails techniques (stderr, codes retour).
- Les tokens/coûts.

---

## Structure de la mémoire

```
/workspace/memory/
│
├── world/                          # Encyclopédie du monde (1 par serveur)
│   ├── index.md                   # Vue d'ensemble, cosmogonie, ton
│   ├── locations/
│   │   ├── taverne-du-chien-borgne.md
│   │   └── ...
│   ├── factions/
│   │   └── ...
│   ├── magic/
│   │   └── ...
│   └── history/
│       └── chronologie.md
│
├── characters/                     # Fiches PNJ (format ci-dessous)
│   ├── kael.md
│   ├── marta.md
│   └── ...
│
├── players/                        # Fiches joueurs + leurs personnages
│   ├── player_{discord_id}.md
│   └── ...
│
├── scenes/
│   ├── active_scene.md            # Scène en cours (lieu, ambiance, qui est là)
│   ├── scene_queue.md             # Messages joueurs en attente de traitement
│   └── scene_history.md           # Résumé des scènes passées (compacté)
│
├── arcs/
│   ├── index.md                   # Liste des arcs (actifs + clos)
│   ├── actifs/
│   │   ├── arc_principal.md
│   │   └── ...
│   ├── fils_ouverts.md            # Threads narratifs non résolus
│   └── clos/                      # Archives
│       └── ...
│
├── media/
│   ├── images.md                  # Log des images générées (hérité de Stasia)
│   └── videos.md                  # Log des vidéos générées
│
└── meta/
    ├── mj_notes.md                # Notes privées du MJ (twists, plans secrets)
    ├── mj_log.md                  # Journal des actions du MJ
    ├── watchdog_log.md            # Log du watchdog
    ├── guides.md                  # → symlink vers /workspace/config/guides.md
    ├── missing_features.md        # Fonctionnalités manquantes (hérité de Stasia)
    └── last_sync.json             # Timestamps (hérité de Stasia)
```

### Format d'une fiche PNJ

```markdown
# Kael

- **Rôle** : Mercenaire, habitué de la taverne
- **Créé le** : 2026-03-28
- **Affiché comme** : Kael
- **Avatar** : https://cdn.discordapp.com/attachments/.../kael.png

## Personnalité
Taciturne, observateur, loyal à ceux qui le méritent.
Humour sec. Ne parle que quand c'est nécessaire.

## Apparence (génération d'images)
rugged male warrior, short dark hair, scar across left cheek,
leather armor, brooding expression, tavern lighting

## Secrets (INVISIBLE pour les joueurs et les autres PNJ)
- Travaille secrètement pour la guilde des ombres
- Cherche un artefact caché sous la taverne
- Connaît la véritable identité de Marta

## Objectifs
1. Observer les nouveaux venus (mission de la guilde)
2. Trouver l'entrée du sous-sol de la taverne
3. Ne pas se faire repérer

## Ce que Kael sait
- La taverne est un point de passage pour les contrebandiers
- Marta cache quelque chose dans l'arrière-salle
- Le joueur [nom] est arrivé ce soir (si scène jouée)

## Ce que Kael ne sait PAS
- Les plans des autres PNJ
- Ce que le joueur a fait avant d'arriver
- L'existence de l'arc principal (sauf s'il y est lié)

## Historique des interactions
- [date] : A observé le joueur entrer dans la taverne, n'a rien dit
- [date] : ...

## Voix
Phrases courtes. Pas de fioritures. Tutoie tout le monde.
Exemples : "Trois pièces. Pas de crédit." / "T'as un problème ?"
```

### Format d'une fiche joueur

```markdown
# Joueur : [pseudo Discord]

- **Discord ID** : 123456789
- **Rejoint le** : 2026-03-28

## Personnage actif
- **Nom** : [nom du personnage]
- **Description** : [ce que le joueur a fourni]
- **Apparence** : [tags pour génération d'images]
- **Avatar** : [URL]

## Personnages précédents
(si le joueur en a eu d'autres)

## Préférences de style
- Ton préféré : [dark, léger, épique...]
- Ce qu'il aime : [combat, intrigue, romance, exploration...]
- Ce qu'il n'aime pas : [...]
- Feedback reçu : [notes du MJ sur les réactions du joueur]

## Notes du MJ
[Observations privées sur le joueur — son style, ce qui marche avec lui]
```

---

## Skills — Contenu détaillé

Les skills sont le cœur d'Augure. Ils sont stockés dans `/workspace/skills/` (ou l'équivalent OpenCode) et sont lisibles et modifiables par le MJ lui-même quand un joueur ou l'admin lui demande d'ajuster son comportement.

Chaque skill = un répertoire contenant un fichier `SKILL.md` avec les instructions. Le format exact du frontmatter dépendra de l'implémentation ACP d'OpenCode (Claude Code déterminera l'équivalent du format Claude Code).

### Skill : `narrer`

```markdown
# Narrer une scène

## Quand utiliser
Chaque fois que le MJ doit décrire ce qui se passe dans le monde — après une action
du joueur, en ouverture de scène, en transition entre deux moments.

## Style
- Deuxième personne : "Vous poussez la porte", "Vos yeux s'adaptent à la pénombre"
- Si plusieurs joueurs : alterner ou utiliser les noms ("Alors que [Joueur] entre, [Joueur2] remarque...")
- Omniscient mais avec retenue — le narrateur sait tout mais ne dit que ce que
  les joueurs peuvent percevoir (sauf effet dramatique voulu)
- Légèrement sardonique quand l'occasion se présente, jamais lourd
- Sensoriel : odeurs, textures, sons, lumière. Pas systématiquement, mais quand ça sert la scène.

## Rythme
- Action : phrases courtes, verbes actifs, pas de fioritures
- Exploration : plus lent, plus descriptif, laisse respirer
- Tension : phrases qui s'allongent, suspension, détails qui clochent
- Révélation : coup sec, phrase courte, puis silence narratif

## Longueur
- Narration standard : 2-4 paragraphes
- Ouverture de scène : jusqu'à 6 paragraphes (poser le décor)
- Transition rapide : 1-2 phrases
- Ne JAMAIS dépasser 2000 caractères (limite Discord) sans splitter

## Interdits
- Pas de em-dashes (—)
- Pas de "Ce n'est pas seulement X, mais aussi Y"
- Pas de listes
- Pas de résumé-conclusion en fin de texte
- Ne JAMAIS jouer le personnage du joueur (pas d'actions, pas de dialogue, pas de pensées)
- Ne pas surqualifier ("magnifique", "incroyable", "époustouflant") — montrer, pas dire

## Workflow
1. Écrire le brouillon dans /tmp/draft.md
2. Relire avec Read
3. Vérifier contre les interdits ci-dessus
4. Corriger si nécessaire
5. Poster via webhook "Narrateur" (POST /channel/{guild_id}/{channel}/post)
```

### Skill : `orchestrer`

```markdown
# Orchestrer une scène

## Quand utiliser
Après chaque action d'un joueur, le MJ doit décider la séquence de réponse.

## Processus de décision
1. Lire la scène active (scenes/active_scene.md)
2. Identifier les PNJ présents (characters_present dans active_scene)
3. Pour chaque PNJ, se demander : "Réagirait-il à ce qui vient de se passer ?"
4. Classer les réactions par urgence/naturel :
   - Réaction immédiate (le PNJ est directement interpellé) → en premier
   - Réaction contextuelle (le PNJ observe et commente) → en second
   - Pas de réaction (le PNJ n'a aucune raison de réagir) → skip

## Séquence de réponse
1. NARRER — la conséquence physique/sensorielle de l'action du joueur
2. PNJ DIRECTS — ceux qui sont directement concernés (interpellés, attaqués, etc.)
3. PNJ OBSERVATEURS — ceux qui réagissent de loin (regard, murmure, geste)
4. AMBIANCE — éventuellement une touche narrative finale (optionnel)

## Règles
- Maximum 3 PNJ qui parlent par tour. Au-delà, c'est du bruit.
- Un PNJ peut réagir SANS parler (le MJ le décrit dans la narration).
- Si aucun PNJ ne réagirait naturellement → ne forcer personne.
- Laisser des silences. Tout ne mérite pas une réponse.

## Interruptions
Si un joueur écrit pendant la séquence :
- Finir le PNJ en cours (déjà lancé en subprocess)
- Lire le nouveau message
- Si c'est une interruption narrative ("Je crie STOP !") → intégrer immédiatement
- Si c'est une nouvelle action → la traiter après la séquence en cours
- Ne JAMAIS ignorer un message joueur

## Multi-joueurs
- Premier arrivé, premier traité (FIFO)
- Mais si deux joueurs agissent dans la même scène quasi-simultanément,
  le MJ peut combiner dans une seule narration
- Le MJ décide qui a la "parole" narrativement — comme un chef d'orchestre
```

### Skill : `briefer-pnj`

```markdown
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
2. Si elle est cohérente → poster via webhook avec le nom et avatar du PNJ
3. Si elle déraille → le MJ peut la reformuler ou relancer le sub-agent
4. Mettre à jour "Historique des interactions" dans la fiche du PNJ
```

### Skill : `creer-pnj`

```markdown
# Créer un PNJ

## Quand utiliser
- Un nouveau personnage apparaît dans l'histoire (spontanément ou planifié)
- Un joueur demande l'introduction d'un type de personnage
- Le MJ prépare un arc et a besoin de nouveaux PNJ

## Processus
1. Déterminer le rôle narratif (allié, obstacle, mystère, comic relief, etc.)
2. Créer la fiche dans /workspace/memory/characters/{nom_slug}.md
3. Remplir TOUTES les sections du format (voir format dans les specs mémoire)
4. Générer une image (si pertinent) via /generate et noter l'URL dans Avatar
5. Ajouter le PNJ à active_scene.md s'il est déjà dans la scène

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
```

### Skill : `creer-lieu`

```markdown
# Créer un lieu

## Quand utiliser
- Les joueurs arrivent dans un endroit jamais décrit
- Le MJ prépare une nouvelle zone
- Un lieu est mentionné dans le lore et doit être détaillé

## Processus
1. Créer /workspace/memory/world/locations/{nom_slug}.md
2. Mettre à jour world/index.md avec une entrée courte

## Format

# [Nom du lieu]

## Description
[Ambiance générale, ce qu'on voit/sent/entend en arrivant]

## Détails
[Éléments notables, architecture, particularités]

## Qui s'y trouve
- [PNJ réguliers avec lien vers leur fiche]
- [Type de clientèle / population]

## Secrets
[Ce qui n'est pas visible au premier regard]
[Passages cachés, objets dissimulés, histoires sombres]

## Dangers
[Risques connus ou cachés]

## Apparence (génération d'images)
[Tags visuels : ambiance, éclairage, style architectural, couleurs dominantes]

## Notes du MJ
[Ce que le MJ prévoit pour ce lieu]
```

### Skill : `encyclopedie`

```markdown
# Maintenir l'encyclopédie

## Quand utiliser
- Un fait de lore est établi en jeu (par la narration ou par un joueur)
- Un joueur demande "c'est quoi [X] dans ce monde ?"
- Le MJ prépare et enrichit le monde entre les sessions

## Règle d'or
CHERCHER AVANT D'INVENTER. Toujours Glob + Read dans /workspace/memory/world/
avant de créer du nouveau lore. La cohérence est sacrée.

## Processus quand un fait est établi
1. Identifier le fichier concerné (location, faction, magic, history...)
2. Si le fichier existe → Edit pour ajouter l'info
3. Si le fichier n'existe pas → Write pour le créer
4. Mettre à jour world/index.md si une nouvelle entrée majeure est créée

## Processus quand un joueur demande
1. Chercher dans world/ avec Glob et Read
2. Si trouvé → répondre avec les infos existantes
3. Si non trouvé → le MJ décide s'il invente ou s'il dit "votre personnage ne sait pas"
4. Si inventé → créer/mettre à jour le fichier correspondant immédiatement

## Ce qui va dans l'encyclopédie vs les notes du MJ
- Encyclopédie (world/) : faits ÉTABLIS, visibles, publics dans le monde
- Notes du MJ (meta/mj_notes.md) : plans SECRETS, twists futurs, idées non confirmées
```

### Skill : `accueillir`

```markdown
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

## Ton
Chaleureux, inclusif, sans pression. Le joueur doit se sentir bienvenu.
Le MJ peut poser les questions en DM si le joueur préfère.
```

### Skill : `preparer`

```markdown
# Préparer entre les sessions (watchdog MJ)

## Quand utiliser
Pendant les ticks du watchdog, quand aucun joueur n'est actif.

## Ce que le MJ fait
1. Relire les arcs en cours (arcs/actifs/)
2. Relire les fils ouverts (arcs/fils_ouverts.md)
3. Réfléchir aux prochaines scènes et les noter dans meta/mj_notes.md
4. Étoffer les PNJ qui manquent de profondeur
5. Enrichir l'encyclopédie si des zones sont sous-documentées
6. Préparer des "amorces" — des événements prêts à être déclenchés
   quand un joueur reviendra (ex: "Kael s'approche du joueur et dit...")

## Ce que le MJ ne fait PAS
- Faire avancer le monde sans les joueurs
- Poster dans #rp
- Résoudre des fils ouverts sans les joueurs
- Supprimer ou archiver des arcs sans accord des joueurs

## Amorces
Les amorces sont notées dans scenes/pending_events.md :

## Amorces prêtes
- **Quand** : le joueur revient dans la taverne
  **Quoi** : Kael l'approche et lui propose un travail
  **PNJ** : Kael
  **Urgence** : haute (l'arc principal en dépend)

- **Quand** : n'importe quel moment calme
  **Quoi** : un messager arrive avec une lettre scellée
  **PNJ** : Messager (à créer — figurant)
  **Urgence** : basse (subplot)
```

### Skill : `generer-image`

```markdown
# Générer une image

## Quand utiliser
- En début de scène pour poser l'ambiance (image de lieu)
- Quand un nouveau PNJ apparaît (portrait)
- Quand un joueur le demande
- Quand un moment est visuellement marquant

## Processus
1. Lire les tags d'apparence du PNJ ou du lieu concerné
2. Construire le prompt EN ANGLAIS
3. Appeler POST /generate via l'API interne
4. L'image est postée dans le canal demandé

## Construction du prompt
- Commencer par le style : "Cinematic shot, film grain, fantasy ultrarealistic photography"
- Décrire le sujet de façon narrative (le modèle Lumina2 aime les descriptions longues)
- Ajouter les tags de la fiche personnage/lieu
- Ajouter le contexte de la scène (éclairage, ambiance, action)

## VRAM
La génération d'image décharge le LLM. Le MJ doit avoir FINI son raisonnement
avant de lancer la génération. Ne pas générer d'image au milieu d'une séquence de PNJ.

## Quand NE PAS générer
- Au milieu d'un échange de répliques (ça casse le rythme)
- Pour chaque scène (trop, c'est trop)
- Pendant le watchdog (sauf demande explicite)
```

### Skill : `generer-musique`

Identique au bloc musique de Stasia (voir `system_prompts.md` de Stasia, section musique). À copier et adapter pour le contexte MJ.

---

## Boucle d'auto-modification

Le MJ peut modifier ses propres fichiers quand un joueur ou l'admin lui parle. C'est le mécanisme qui fait vivre Augure — il s'affine en jouant.

### Fichiers modifiables par le MJ via conversation

| Fichier | Qui peut demander la modif | Exemple |
|---------|---------------------------|---------|
| `config/identity.md` | Admin uniquement | "Sois plus sarcastique dans tes narrations" |
| `config/guides.md` | Admin ou joueurs (selon policy) | "Pas de mort permanente sans accord" |
| `skills/*/SKILL.md` | Admin uniquement | "Quand tu crées un PNJ, donne-lui toujours un tic nerveux" |
| `memory/characters/*.md` | MJ spontanément ou sur demande | Mise à jour après chaque scène |
| `memory/world/**` | MJ spontanément ou sur demande | Enrichissement du lore |
| `memory/players/*.md` | MJ spontanément | Préférences observées |
| `memory/meta/mj_notes.md` | MJ uniquement | Notes privées |

### Comment ça marche

Joueur en DM ou @mention : "Tes narrations sont trop longues, raccourcis."

Le MJ :
1. Lit le skill `narrer`
2. Modifie la section "Longueur" pour réduire les valeurs
3. Confirme au joueur : "C'est noté, je serai plus concis."
4. Les prochaines narrations respectent la modification

Aucune intervention de développeur nécessaire. Le MJ s'auto-calibre.

---

## API interne — Routes additionnelles (par rapport à Stasia)

### POST `/npc/invoke`

Lance un sub-agent PNJ. C'est la route centrale du système de sub-agents.

```json
// Request
{
  "character_name": "Kael",
  "brief": "Tu es Kael. [brief complet construit par le skill briefer-pnj]",
  "max_tokens": 500,
  "guild_id": "...",
  "channel_name": "rp",
  "post_as_webhook": true,
  "character_avatar": "https://..."
}

// Response
{
  "ok": true,
  "text": "La réponse brute du sub-agent",
  "message_ids": [123456],  // si post_as_webhook: true
  "tokens_used": 342
}
```

**Comportement** :
1. Acquérir le lock VRAM
2. Appeler le LLM (via Ollama API directement, pas via OpenCode — le sub-agent PNJ n'a pas besoin d'outils)
3. Si `post_as_webhook: true` → poster la réponse via webhook dans le canal
4. Retourner la réponse brute au MJ (pour qu'il la voie et mette à jour la mémoire)
5. Poster le brief + la réponse dans #mj-screen (embeds violet/orange)

### GET `/npc/list`

Liste tous les PNJ avec leurs infos de base (pour que le MJ puisse choisir).

### POST `/mj-screen/post`

Permet au MJ de poster un embed custom dans #mj-screen (pour ses décisions narratives).

```json
{
  "type": "decision",
  "content": "→ Marta sert la bière. Kael observe en silence."
}
```

---

## OpenCode Bridge

### Principe

Remplace `claude_bridge.py` de Stasia. Même pattern : subprocess one-shot, prompt sur stdin, stream-json sur stdout.

Claude Code (l'outil de développement) déterminera l'implémentation exacte en examinant :
1. La documentation ACP d'OpenCode
2. Les flags CLI d'OpenCode (équivalents de `--print`, `--output-format`, `--allowed-tools`, `--add-dir`)
3. Le format de sortie stream

### Ce qui doit être conservé du pattern Stasia
- File d'attente par utilisateur (asyncio.Queue)
- Lock VRAM global (remplace le lock Claude)
- Construction du prompt avec contexte Discord
- Parsing de la sortie stream
- Logging des invocations dans `/workspace/memory/meta/invocation_logs/`

### Sub-agent PNJ ≠ OpenCode

Les sub-agents PNJ n'utilisent PAS OpenCode. Ils n'ont pas besoin d'outils (Read, Write, etc.).
Ils font un appel direct à l'API Ollama :

```
POST http://localhost:11434/api/generate
{
  "model": "qwen2.5:32b-instruct-q6_K",
  "prompt": "[brief du PNJ]",
  "stream": false
}
```

C'est plus rapide (pas de overhead OpenCode) et plus sûr (pas d'accès fichiers).

---

## Configuration

### `.env`

```env
DISCORD_TOKEN=...

# LLM
OLLAMA_HOST=host.docker.internal
OLLAMA_PORT=11434
OLLAMA_MODEL=qwen2.5:32b-instruct-q6_K

# ComfyUI
COMFYUI_HOST=host.docker.internal
COMFYUI_PORT=8188

# Suno
SUNO_API_KEY=...
SUNO_BASE_URL=https://api.sunoapi.org

# Timeouts
MJ_TIMEOUT=180
NPC_TIMEOUT=60

# Watchdog
WATCHDOG_INTERVAL=15

# Channels (noms par défaut, modifiables)
RP_CHANNEL=rp
GENERAL_CHANNEL=général
MJ_SCREEN_CHANNEL=mj-screen

# Access control
ADMIN_USER_IDS=...
```

---

## Démarrage

### Script de démarrage (`startup_augure.bat`)

```batch
@echo off
REM 1. Lancer Ollama (si pas déjà lancé)
start "" ollama serve

REM 2. Lancer ComfyUI
start "" "T:\Projects\ComfyUI\run_comfyui.bat"

REM 3. Attendre que les services soient prêts
timeout /t 15

REM 4. Précharger le modèle LLM
curl -s http://localhost:11434/api/generate -d "{\"model\":\"qwen2.5:32b-instruct-q6_K\",\"prompt\":\"test\",\"stream\":false}" >nul

REM 5. Lancer le bot
cd /d "T:\Projects\augure"
docker-compose up -d
```

---

## Résumé des décisions

| Question | Réponse |
|----------|---------|
| Nom du projet | Augure |
| Modèle LLM | Qwen 2.5 32B Q6_K (~26 GB) via Ollama |
| CLI agent | OpenCode via ACP |
| VRAM | Lock exclusif LLM ↔ ComfyUI |
| Langue | Français |
| Joueurs | Nombre ouvert et variable |
| Sub-agents PNJ | Systématique, chaque PNJ = appel Ollama direct |
| Orchestration | MJ décide dynamiquement, séquentiel avec réactions |
| Autonomie | MJ prépare entre sessions, monde ne bouge pas sans joueur |
| MJ Screen | Tout le raisonnement streamé, visible par tous (accès contrôlé par admin Discord) |
| Univers | Un par serveur, MJ construit l'encyclopédie |
| Power fantasy / érotique | Selon les guides du serveur |
| Auto-modification | Skills, identité, guides, mémoire — tout modifiable par conversation |
| Base de code | Hérite de Stasia, adapté |
