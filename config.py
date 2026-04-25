"""
CornicBot — Configuration globale : couleurs, emojis, constantes.
"""


class Colors:
    PRIMARY   = 0x5865F2  # Blurple Discord
    SUCCESS   = 0x57F287  # Vert
    WARNING   = 0xFEE75C  # Jaune
    DANGER    = 0xED4245  # Rouge
    DARK      = 0x2B2D31  # Fond sombre (embed invisible)
    INFO      = 0x00B0F4  # Bleu clair
    GOLD      = 0xF1C40F  # Or


class Emojis:
    # Tickets
    TICKET    = "🎫"
    OPEN      = "🎟️"
    LOCK      = "🔒"
    ARCHIVE   = "🗂️"
    CLAIM     = "👤"
    TRANSCRIPT = "📋"
    CLOSE     = "🚫"

    # Status / UI
    CHECK     = "✅"
    CROSS     = "❌"
    WARNING   = "⚠️"
    INFO      = "ℹ️"
    ARROW     = "➤"
    STAR      = "⭐"
    BELL      = "🔔"
    WRENCH    = "🔧"
    PENCIL    = "✏️"
    TRASH     = "🗑️"

    # Méta
    USER      = "👥"
    STAFF     = "🛡️"
    CALENDAR  = "📅"
    TIME      = "⏰"
    ID        = "🏷️"
    STATS     = "📊"
    CMD       = "📝"
    SHIELD    = "🔰"
    GEAR      = "⚙️"


# Préfixe des salons de tickets
TICKET_OPEN_PREFIX   = "🎫・"
TICKET_CLAIM_PREFIX  = "🛡️・"
TICKET_CLOSED_PREFIX = "✅・"
