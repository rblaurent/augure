DISCORD_LIMIT = 2000


def split_message(text: str, limit: int = DISCORD_LIMIT) -> list[str]:
    """
    Découpe un texte en parties ≤ limit caractères.
    La découpe se fait à la limite de paragraphe la plus proche,
    ou à la limite de phrase si aucun paragraphe n'est disponible.
    """
    if len(text) <= limit:
        return [text]

    parts: list[str] = []
    remaining = text

    while len(remaining) > limit:
        chunk = remaining[:limit]

        # Chercher la dernière limite de paragraphe (double saut de ligne)
        split_at = chunk.rfind("\n\n")

        if split_at == -1 or split_at < limit // 4:
            # Pas de paragraphe convenable — chercher la fin de phrase
            for end_char in (". ", "! ", "? ", ".\n", "!\n", "?\n"):
                pos = chunk.rfind(end_char)
                if pos != -1 and pos > limit // 4:
                    split_at = pos + len(end_char)
                    break

        if split_at == -1 or split_at < limit // 4:
            # Dernier recours : couper au dernier espace
            split_at = chunk.rfind(" ")

        if split_at == -1:
            # Aucune limite trouvée — couper brutalement
            split_at = limit

        parts.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()

    if remaining:
        parts.append(remaining)

    return parts
