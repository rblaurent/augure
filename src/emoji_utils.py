"""Emoji resolution — converts ':name:' shortcodes to Unicode or discord.Emoji objects."""

import discord
import emoji as emoji_lib


def resolve_emoji(emoji_str: str, guild: discord.Guild | None = None):
    """
    Resolve an emoji string to something discord.py accepts in add_reaction().

    Accepts:
      - raw Unicode character → returned as-is
      - ':name:' shortcode → custom guild emoji if found, else standard Unicode via emoji package
    """
    s = emoji_str.strip()
    if s.startswith(":") and s.endswith(":"):
        name = s[1:-1]
        if guild:
            custom = discord.utils.get(guild.emojis, name=name)
            if custom:
                return custom
        resolved = emoji_lib.emojize(s, language="alias")
        if resolved != s:
            return resolved
    return s
