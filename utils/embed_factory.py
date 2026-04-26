"""
CornicBot — EmbedFactory
Centralise la création de tous les embeds pour garantir une cohérence visuelle.
"""

from __future__ import annotations

import discord
from datetime import datetime, timezone
from typing import Optional

from config import Colors, Emojis


class EmbedFactory:
    """Fabrique centralisée d'embeds stylisés."""

    BOT_NAME: str = "CornicBot"
    BOT_ICON: Optional[str] = None

    @classmethod
    def set_bot_icon(cls, url: str) -> None:
        cls.BOT_ICON = url

    # ──────────────────────────────────────────────
    #  Base interne
    # ──────────────────────────────────────────────

    @classmethod
    def _base(
        cls,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: int = Colors.PRIMARY,
        guild: Optional[discord.Guild] = None,
        thumbnail_url: Optional[str] = None,
        image_url: Optional[str] = None,
    ) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now(tz=timezone.utc),
        )
        embed.set_author(name=cls.BOT_NAME, icon_url=cls.BOT_ICON)
        if guild and guild.icon:
            embed.set_footer(text=guild.name, icon_url=guild.icon.url)
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
        if image_url:
            embed.set_image(url=image_url)
        return embed

    # ──────────────────────────────────────────────
    #  Embeds génériques
    # ──────────────────────────────────────────────

    @classmethod
    def success(
        cls,
        title: str,
        description: str,
        guild: Optional[discord.Guild] = None,
    ) -> discord.Embed:
        return cls._base(
            title=f"{Emojis.CHECK} {title}",
            description=description,
            color=Colors.SUCCESS,
            guild=guild,
        )

    @classmethod
    def error(
        cls,
        title: str,
        description: str,
        guild: Optional[discord.Guild] = None,
    ) -> discord.Embed:
        return cls._base(
            title=f"{Emojis.CROSS} {title}",
            description=description,
            color=Colors.DANGER,
            guild=guild,
        )

    @classmethod
    def warning(
        cls,
        title: str,
        description: str,
        guild: Optional[discord.Guild] = None,
    ) -> discord.Embed:
        return cls._base(
            title=f"{Emojis.WARNING} {title}",
            description=description,
            color=Colors.WARNING,
            guild=guild,
        )

    @classmethod
    def info(
        cls,
        title: str,
        description: str,
        guild: Optional[discord.Guild] = None,
    ) -> discord.Embed:
        return cls._base(
            title=f"{Emojis.INFO} {title}",
            description=description,
            color=Colors.INFO,
            guild=guild,
        )

    # ──────────────────────────────────────────────
    #  Panel d'accueil des tickets
    # ──────────────────────────────────────────────

    @classmethod
    def ticket_panel(
        cls,
        guild: discord.Guild,
        description: str = "",
        banner_url: Optional[str] = None,
    ) -> discord.Embed:
        default_desc = (
            f"**🎫 Besoin d'aide ?**\n\n"
            f"💭 Pour toute question, commande ou demande particulière, "
            f"merci d'ouvrir un ticket et de détailler votre demande au maximum.\n\n"
            f"⚡ Un membre de l'équipe vous répondra dans les plus brefs délais !"
        )
        body = description or default_desc

        embed = discord.Embed(
            description=body,
            color=Colors.PRIMARY,
            timestamp=datetime.now(tz=timezone.utc),
        )

        # Titre avec nom du serveur mis en valeur
        embed.set_author(
            name=f"══ Support — {guild.name} ══",
            icon_url=guild.icon.url if guild.icon else cls.BOT_ICON,
        )

        # Séparateur visuel + champs d'info rapide
        embed.add_field(name="​", value="​", inline=False)
        embed.add_field(
            name="🕐  Temps de réponse",
            value="> Moins de **24h** en général",
            inline=True,
        )
        embed.add_field(
            name="🛡️  Staff disponible",
            value="> Équipe dédiée au support",
            inline=True,
        )
        embed.add_field(name="​", value="​", inline=False)

        # Bannière optionnelle en bas de l'embed
        if banner_url:
            embed.set_image(url=banner_url)

        # Pied de page discret
        footer_icon = guild.icon.url if guild.icon else cls.BOT_ICON
        embed.set_footer(
            text=f"{guild.name}  •  Powered by {cls.BOT_NAME}",
            icon_url=footer_icon,
        )

        return embed

    @classmethod
    def ticket_panel_button_hint(cls) -> discord.Embed:
        """Petit embed minimaliste qui vient juste au-dessus du bouton."""
        embed = discord.Embed(
            description="** **",   # espace invisible — force la hauteur minimale
            color=Colors.PRIMARY,
        )
        return embed

    # ──────────────────────────────────────────────
    #  Message de bienvenue dans un ticket
    # ──────────────────────────────────────────────

    @classmethod
    def ticket_welcome(
        cls,
        user: discord.Member,
        ticket_id: str,
        guild: discord.Guild,
    ) -> discord.Embed:
        embed = cls._base(
            title=f"{Emojis.TICKET}  Ticket #{ticket_id}",
            description=(
                f"Bonjour {user.mention}, votre ticket a bien été créé !\n\n"
                f"{Emojis.INFO} **Comment procéder :**\n"
                f"> Décrivez votre problème en détail ci-dessous.\n"
                f"> Un membre du staff vous répondra sous peu.\n\n"
                f"**{Emojis.GEAR} Actions disponibles :**\n"
                f"> {Emojis.CLAIM} **Claim** — Un staff prend en charge le ticket\n"
                f"> {Emojis.LOCK} **Fermer** — Clôturer le ticket (transcript généré)\n"
                f"> {Emojis.ARCHIVE} **Archiver** — Archiver sans supprimer"
            ),
            color=Colors.PRIMARY,
            guild=guild,
            thumbnail_url=user.display_avatar.url,
        )
        embed.add_field(
            name=f"{Emojis.ID} Identifiant",
            value=f"```{ticket_id}```",
            inline=True,
        )
        embed.add_field(
            name=f"{Emojis.USER} Client",
            value=user.mention,
            inline=True,
        )
        embed.add_field(
            name=f"{Emojis.STAFF} Staff Assigné",
            value=f"`Non assigné`",
            inline=True,
        )
        return embed

    @classmethod
    def ticket_claimed(
        cls,
        user: discord.Member,
        ticket_id: str,
        staff: discord.Member,
        guild: discord.Guild,
    ) -> discord.Embed:
        embed = cls._base(
            title=f"{Emojis.TICKET}  Ticket #{ticket_id}",
            description=(
                f"{user.mention}, votre ticket a été pris en charge !\n\n"
                f"{Emojis.STAFF} {staff.mention} est maintenant votre interlocuteur.\n"
                f"Décrivez votre problème et attendez sa réponse."
            ),
            color=Colors.INFO,
            guild=guild,
            thumbnail_url=staff.display_avatar.url,
        )
        embed.add_field(name=f"{Emojis.ID} Identifiant",   value=f"```{ticket_id}```", inline=True)
        embed.add_field(name=f"{Emojis.USER} Client",      value=user.mention,         inline=True)
        embed.add_field(name=f"{Emojis.STAFF} Staff",      value=staff.mention,        inline=True)
        return embed

    # ──────────────────────────────────────────────
    #  Logs & Fermeture
    # ──────────────────────────────────────────────

    @classmethod
    def ticket_closed_log(
        cls,
        ticket_id: str,
        user: discord.Member,
        closed_by: discord.Member,
        staff: Optional[discord.Member],
        reason: str,
        guild: discord.Guild,
        message_count: int = 0,
    ) -> discord.Embed:
        embed = cls._base(
            title=f"{Emojis.LOCK}  Ticket Fermé — #{ticket_id}",
            description=f"> {Emojis.ARROW} **Raison :** {reason}",
            color=Colors.DANGER,
            guild=guild,
        )
        embed.add_field(name=f"{Emojis.ID} Ticket",        value=f"`{ticket_id}`",        inline=True)
        embed.add_field(name=f"{Emojis.USER} Client",      value=user.mention,            inline=True)
        embed.add_field(name=f"{Emojis.STAFF} Staff",      value=staff.mention if staff else "`—`", inline=True)
        embed.add_field(name=f"{Emojis.CLOSE} Fermé par",  value=closed_by.mention,       inline=True)
        embed.add_field(name=f"{Emojis.STATS} Messages",   value=f"`{message_count}`",    inline=True)
        embed.add_field(name=f"{Emojis.TIME} Date",        value=f"<t:{int(datetime.now().timestamp())}:F>", inline=True)
        embed.set_thumbnail(url=user.display_avatar.url)
        return embed

    @classmethod
    def ticket_archived_log(
        cls,
        ticket_id: str,
        user: discord.Member,
        archived_by: discord.Member,
        guild: discord.Guild,
    ) -> discord.Embed:
        embed = cls._base(
            title=f"{Emojis.ARCHIVE}  Ticket Archivé — #{ticket_id}",
            description=f"Le ticket de {user.mention} a été archivé par {archived_by.mention}.",
            color=Colors.WARNING,
            guild=guild,
        )
        embed.add_field(name=f"{Emojis.ID} Ticket",        value=f"`{ticket_id}`",   inline=True)
        embed.add_field(name=f"{Emojis.USER} Client",      value=user.mention,       inline=True)
        embed.add_field(name=f"{Emojis.CLOSE} Archivé par",value=archived_by.mention,inline=True)
        return embed

    @classmethod
    def ticket_opened_log(
        cls,
        ticket_id: str,
        user: discord.Member,
        channel: discord.TextChannel,
        guild: discord.Guild,
    ) -> discord.Embed:
        embed = cls._base(
            title=f"{Emojis.OPEN}  Nouveau Ticket — #{ticket_id}",
            description=f"{user.mention} a ouvert un ticket : {channel.mention}",
            color=Colors.SUCCESS,
            guild=guild,
        )
        embed.add_field(name=f"{Emojis.ID} Ticket",    value=f"`{ticket_id}`",  inline=True)
        embed.add_field(name=f"{Emojis.USER} Auteur",  value=user.mention,      inline=True)
        embed.add_field(name=f"{Emojis.CALENDAR} Date",value=f"<t:{int(datetime.now().timestamp())}:F>", inline=True)
        embed.set_thumbnail(url=user.display_avatar.url)
        return embed

    # ──────────────────────────────────────────────
    #  Commandes personnalisées
    # ──────────────────────────────────────────────

    @classmethod
    def custom_command_frame(
        cls,
        cmd_name: str,
        content: str,
        author: discord.Member,
        guild: discord.Guild,
        title: Optional[str] = None,
    ) -> discord.Embed:
        """Encapsule une commande personnalisée dans un 'Template Frame' stylisé."""
        display_title = title if title else f"{Emojis.CMD}  Commande : `{cmd_name}`"
        embed = cls._base(
            title=display_title,
            description=content,
            color=Colors.DARK,
            guild=guild,
        )
        embed.set_footer(
            text=f"Demandé par {author.display_name} • {guild.name}",
            icon_url=author.display_avatar.url,
        )
        return embed

    @classmethod
    def custom_command_created(
        cls,
        cmd_name: str,
        guild: discord.Guild,
    ) -> discord.Embed:
        return cls.success(
            "Commande créée",
            f"La commande `${cmd_name}` est maintenant disponible sur ce serveur.",
            guild=guild,
        )

    @classmethod
    def custom_command_deleted(
        cls,
        cmd_name: str,
        guild: discord.Guild,
    ) -> discord.Embed:
        return cls.success(
            "Commande supprimée",
            f"La commande `${cmd_name}` a été supprimée.",
            guild=guild,
        )

    @classmethod
    def custom_commands_list(
        cls,
        commands: list[tuple],
        guild: discord.Guild,
    ) -> discord.Embed:
        embed = cls._base(
            title=f"{Emojis.CMD}  Commandes Personnalisées",
            description=f"**{len(commands)}** commande(s) disponible(s) sur ce serveur.",
            color=Colors.PRIMARY,
            guild=guild,
        )
        if commands:
            lines = "\n".join(
                f"{Emojis.ARROW} `${row[0]}` — *{row[1][:50]}{'…' if len(row[1]) > 50 else ''}*"
                for row in commands
            )
            embed.add_field(name="Liste", value=lines, inline=False)
        else:
            embed.add_field(name=f"{Emojis.INFO} Aucune commande", value="Utilisez `$createcmd <nom> <contenu>` pour en créer une.", inline=False)
        return embed

    # ──────────────────────────────────────────────
    #  Setup / Configuration
    # ──────────────────────────────────────────────

    @classmethod
    def setup_complete(
        cls,
        guild: discord.Guild,
        category: discord.CategoryChannel,
        log_channel: discord.TextChannel,
        support_role: discord.Role,
    ) -> discord.Embed:
        embed = cls._base(
            title=f"{Emojis.WRENCH}  Configuration Terminée",
            description="Le système de tickets a été configuré avec succès !",
            color=Colors.SUCCESS,
            guild=guild,
        )
        embed.add_field(name=f"{Emojis.ARCHIVE} Catégorie",      value=category.mention,      inline=True)
        embed.add_field(name=f"{Emojis.BELL} Logs",              value=log_channel.mention,   inline=True)
        embed.add_field(name=f"{Emojis.STAFF} Rôle Support",     value=support_role.mention,  inline=True)
        return embed
