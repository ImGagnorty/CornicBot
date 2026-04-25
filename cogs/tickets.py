"""
CornicBot — Cog Tickets
Gère le cycle de vie complet : panel, ouverture, claim, fermeture, archivage, logs.
"""

from __future__ import annotations

import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from config import Colors, Emojis, TICKET_OPEN_PREFIX, TICKET_CLAIM_PREFIX, TICKET_CLOSED_PREFIX
from utils.embed_factory import EmbedFactory
from utils.transcript import generate_html_transcript


# ──────────────────────────────────────────────────────────────────────────────
#  Modal : Raison de fermeture
# ──────────────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────────────
#  Modal : Configuration du panel (description multi-lignes)
# ──────────────────────────────────────────────────────────────────────────────

_DEFAULT_PANEL_DESC = (
    "🎫 Besoin d'aide ?\n\n"
    "💭 Pour toute question, commande ou demande particulière, merci d'ouvrir "
    "un ticket et de détailler votre demande au maximum.\n\n"
    "⚡ Un membre de l'équipe vous répondra dans les plus brefs délais !"
)


class PanelSetupModal(discord.ui.Modal, title="✏️  Personnaliser le panel"):
    description_input = discord.ui.TextInput(
        label="Texte affiché dans le panel",
        style=discord.TextStyle.paragraph,
        placeholder="🎫 Besoin d'aide ?\n\n💭 Décrivez votre demande…",
        default=_DEFAULT_PANEL_DESC,
        max_length=2000,
        required=True,
    )

    def __init__(
        self,
        cog: "TicketsCog",
        category: discord.CategoryChannel,
        log_channel: discord.TextChannel,
        support_role: discord.Role,
        banner_url: Optional[str],
        target_channel: discord.TextChannel,
    ) -> None:
        super().__init__()
        self._cog = cog
        self._category = category
        self._log_channel = log_channel
        self._support_role = support_role
        self._banner_url = banner_url
        self._target_channel = target_channel

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        description = self.description_input.value

        await self._cog.bot.db.upsert_guild_config(
            interaction.guild_id,
            self._category.id,
            self._log_channel.id,
            self._support_role.id,
        )

        panel_embed = EmbedFactory.ticket_panel(
            interaction.guild,
            description=description,
            banner_url=self._banner_url,
        )

        ch = self._target_channel

        # ── Message 1 : l'embed seul, SANS composants.
        #    Sans bouton → Discord n'affiche pas de croix "supprimer les intégrations".
        await ch.send(embed=panel_embed)

        # ── Message 2 : le bouton seul.
        #    Si l'utilisateur clique accidentellement sur la croix, seul ce message
        #    disparaît ; l'embed du panel reste intact au-dessus.
        view = TicketCreateView()
        panel_msg = await ch.send(content="​", view=view)

        await self._cog.bot.db.set_panel_info(
            interaction.guild_id, ch.id, panel_msg.id
        )

        await interaction.followup.send(
            embed=EmbedFactory.setup_complete(
                interaction.guild, self._category, self._log_channel, self._support_role
            ),
            ephemeral=True,
        )


# ──────────────────────────────────────────────────────────────────────────────
#  Modal : Raison de fermeture
# ──────────────────────────────────────────────────────────────────────────────

class CloseModal(discord.ui.Modal, title="Fermer le ticket"):
    reason = discord.ui.TextInput(
        label="Raison de fermeture",
        placeholder="Problème résolu, ticket inactif…",
        style=discord.TextStyle.paragraph,
        max_length=300,
        required=False,
    )

    def __init__(self, view: "TicketActionView") -> None:
        super().__init__()
        self._action_view = view

    async def on_submit(self, interaction: discord.Interaction) -> None:
        reason_text = self.reason.value or "Aucune raison fournie"
        await self._action_view.process_close(interaction, reason_text)


# ──────────────────────────────────────────────────────────────────────────────
#  View persistante : bouton de création dans le panel
# ──────────────────────────────────────────────────────────────────────────────

class TicketCreateView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Ouvrir un ticket",
        emoji=Emojis.TICKET,
        style=discord.ButtonStyle.success,
        custom_id="cornic:ticket_create",
    )
    async def create_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        cog: Optional[TicketsCog] = interaction.client.get_cog("TicketsCog")  # type: ignore[attr-defined]
        if cog is None:
            return
        await cog.open_ticket(interaction)


# ──────────────────────────────────────────────────────────────────────────────
#  View persistante : actions dans le salon ticket
# ──────────────────────────────────────────────────────────────────────────────

class TicketActionView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    # ── Claim ────────────────────────────────────

    @discord.ui.button(
        label="Claim",
        emoji=Emojis.CLAIM,
        style=discord.ButtonStyle.primary,
        custom_id="cornic:ticket_claim",
    )
    async def claim_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        cog: Optional[TicketsCog] = interaction.client.get_cog("TicketsCog")  # type: ignore[attr-defined]
        if cog is None:
            return

        db = interaction.client.db  # type: ignore[attr-defined]
        ticket = await db.get_ticket_by_channel(interaction.channel_id)
        if not ticket:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Erreur", "Ce salon n'est pas un ticket."),
                ephemeral=True,
            )
            return

        cfg = await db.get_guild_config(interaction.guild_id)
        support_role = interaction.guild.get_role(cfg["support_role_id"]) if cfg else None

        if support_role and support_role not in interaction.user.roles:
            await interaction.response.send_message(
                embed=EmbedFactory.error(
                    "Accès refusé",
                    f"Seuls les membres ayant le rôle {support_role.mention} peuvent claim un ticket.",
                ),
                ephemeral=True,
            )
            return

        if ticket["status"] == "claimed":
            await interaction.response.send_message(
                embed=EmbedFactory.warning("Déjà claim", "Ce ticket a déjà été pris en charge."),
                ephemeral=True,
            )
            return

        await db.claim_ticket(interaction.channel_id, interaction.user.id)

        user = interaction.guild.get_member(ticket["user_id"])
        ticket_id = ticket["ticket_id"]

        # Renommer le salon
        try:
            suffix = user.name if user else "ticket"
            await interaction.channel.edit(name=f"{TICKET_CLAIM_PREFIX}{suffix}")
        except discord.Forbidden:
            pass

        # Mettre à jour l'embed d'accueil
        embed = EmbedFactory.ticket_claimed(user, ticket_id, interaction.user, interaction.guild)
        await interaction.response.edit_message(embed=embed, view=self)

        # Notification dans le salon
        await interaction.channel.send(
            embed=EmbedFactory.success(
                "Ticket claim",
                f"{interaction.user.mention} a pris en charge ce ticket {Emojis.CLAIM}",
                guild=interaction.guild,
            )
        )

        # Log
        await cog._send_log(
            interaction.guild,
            EmbedFactory.info(
                f"Ticket Claim — #{ticket_id}",
                f"{interaction.user.mention} a claim le ticket de {user.mention if user else '`inconnu`'}.",
                guild=interaction.guild,
            ),
        )

    # ── Fermer ────────────────────────────────────

    @discord.ui.button(
        label="Fermer",
        emoji=Emojis.LOCK,
        style=discord.ButtonStyle.danger,
        custom_id="cornic:ticket_close",
    )
    async def close_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        db = interaction.client.db  # type: ignore[attr-defined]
        ticket = await db.get_ticket_by_channel(interaction.channel_id)
        if not ticket:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Erreur", "Ce salon n'est pas un ticket."),
                ephemeral=True,
            )
            return

        user = interaction.guild.get_member(ticket["user_id"])
        can_close = (
            interaction.user.guild_permissions.manage_channels
            or (user and interaction.user.id == user.id)
        )
        if not can_close:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Accès refusé", "Vous ne pouvez pas fermer ce ticket."),
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(CloseModal(self))

    async def process_close(
        self, interaction: discord.Interaction, reason: str
    ) -> None:
        cog: Optional[TicketsCog] = interaction.client.get_cog("TicketsCog")  # type: ignore[attr-defined]
        if cog is None:
            return

        db = interaction.client.db  # type: ignore[attr-defined]
        ticket = await db.get_ticket_by_channel(interaction.channel_id)
        if not ticket:
            return

        # Acquitter le modal immédiatement (obligatoire sous 3 s)
        await interaction.response.defer(ephemeral=True)

        user  = interaction.guild.get_member(ticket["user_id"])
        staff = interaction.guild.get_member(ticket["staff_id"]) if ticket["staff_id"] else None

        # Transcript
        buf, msg_count = await generate_html_transcript(
            interaction.channel, ticket["ticket_id"], user, staff
        )
        transcript_file = discord.File(buf, filename=f"transcript-{ticket['ticket_id']}.html")

        # Enregistrer en DB
        await db.close_ticket(interaction.channel_id, reason)

        # Log dans le salon admin
        log_embed = EmbedFactory.ticket_closed_log(
            ticket["ticket_id"], user, interaction.user, staff, reason,
            interaction.guild, msg_count
        )
        await cog._send_log(interaction.guild, log_embed, file=transcript_file)

        # DM à l'utilisateur
        if user:
            try:
                await user.send(
                    embed=EmbedFactory.info(
                        "Ticket Fermé",
                        f"Votre ticket **#{ticket['ticket_id']}** sur **{interaction.guild.name}** a été fermé.\n"
                        f"{Emojis.ARROW} **Raison :** {reason}",
                        guild=interaction.guild,
                    )
                )
            except discord.Forbidden:
                pass

        # Annonce visible par tous dans le salon, puis suppression
        await interaction.channel.send(
            embed=EmbedFactory.success(
                "Ticket fermé",
                f"{Emojis.TRANSCRIPT} Transcript sauvegardé. Fermeture dans 5 secondes…",
                guild=interaction.guild,
            )
        )

        await asyncio.sleep(5)

        try:
            await interaction.channel.delete(reason=f"Ticket fermé par {interaction.user}")
        except discord.Forbidden:
            pass

    # ── Archiver ─────────────────────────────────

    @discord.ui.button(
        label="Archiver",
        emoji=Emojis.ARCHIVE,
        style=discord.ButtonStyle.secondary,
        custom_id="cornic:ticket_archive",
    )
    async def archive_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Accès refusé", "Permissions insuffisantes."),
                ephemeral=True,
            )
            return

        cog: Optional[TicketsCog] = interaction.client.get_cog("TicketsCog")  # type: ignore[attr-defined]
        db = interaction.client.db  # type: ignore[attr-defined]
        ticket = await db.get_ticket_by_channel(interaction.channel_id)
        if not ticket:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Erreur", "Ce salon n'est pas un ticket."),
                ephemeral=True,
            )
            return

        await db.archive_ticket(interaction.channel_id)
        user = interaction.guild.get_member(ticket["user_id"])

        # Retirer les permissions de l'utilisateur
        if user:
            try:
                await interaction.channel.set_permissions(user, read_messages=False)
            except discord.Forbidden:
                pass

        # Renommer
        try:
            suffix = user.name if user else "ticket"
            await interaction.channel.edit(name=f"{TICKET_CLOSED_PREFIX}{suffix}")
        except discord.Forbidden:
            pass

        # Désactiver les boutons
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)

        await interaction.channel.send(
            embed=EmbedFactory.warning(
                "Ticket Archivé",
                f"Archivé par {interaction.user.mention}. L'accès client a été retiré.",
                guild=interaction.guild,
            )
        )

        # Log
        log_embed = EmbedFactory.ticket_archived_log(
            ticket["ticket_id"], user, interaction.user, interaction.guild
        )
        if cog:
            await cog._send_log(interaction.guild, log_embed)


# ──────────────────────────────────────────────────────────────────────────────
#  Cog principal
# ──────────────────────────────────────────────────────────────────────────────

class TicketsCog(commands.Cog, name="TicketsCog"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ── Helpers ───────────────────────────────────

    async def _get_cfg(self, guild_id: int):
        return await self.bot.db.get_guild_config(guild_id)

    async def _send_log(
        self,
        guild: discord.Guild,
        embed: discord.Embed,
        file: Optional[discord.File] = None,
    ) -> None:
        cfg = await self._get_cfg(guild.id)
        if not cfg or not cfg["log_channel_id"]:
            return
        channel = guild.get_channel(cfg["log_channel_id"])
        if channel:
            kwargs = {"embed": embed}
            if file:
                kwargs["file"] = file
            try:
                await channel.send(**kwargs)
            except discord.Forbidden:
                pass

    # ── Ouverture d'un ticket ─────────────────────

    async def open_ticket(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        db = self.bot.db
        cfg = await self._get_cfg(guild.id)

        if not cfg or not cfg["category_id"]:
            await interaction.followup.send(
                embed=EmbedFactory.error(
                    "Non configuré",
                    "Le système de tickets n'est pas encore configuré. "
                    "Un administrateur doit utiliser `/setup_tickets`.",
                ),
                ephemeral=True,
            )
            return

        # Anti-spam : un seul ticket ouvert par utilisateur
        existing = await db.get_open_ticket_by_user(guild.id, interaction.user.id)
        if existing:
            ch = guild.get_channel(existing["channel_id"])
            msg = (
                f"Vous avez déjà un ticket ouvert : {ch.mention}"
                if ch else
                "Vous avez déjà un ticket ouvert."
            )
            await interaction.followup.send(
                embed=EmbedFactory.warning("Ticket existant", msg),
                ephemeral=True,
            )
            return

        category = guild.get_channel(cfg["category_id"])
        if not category:
            await interaction.followup.send(
                embed=EmbedFactory.error("Erreur", "Catégorie introuvable. Reconfigurez avec `/setup_tickets`."),
                ephemeral=True,
            )
            return

        # Incrémenter compteur
        counter = await db.increment_ticket_counter(guild.id)
        ticket_id = f"{counter:04d}"

        # Permissions du nouveau salon
        support_role = guild.get_role(cfg["support_role_id"])
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(
                read_messages=True, send_messages=True, attach_files=True, embed_links=True
            ),
            guild.me: discord.PermissionOverwrite(
                read_messages=True, send_messages=True, manage_channels=True, manage_permissions=True
            ),
        }
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(
                read_messages=True, send_messages=True, attach_files=True, embed_links=True
            )

        # Créer le salon
        channel = await guild.create_text_channel(
            name=f"{TICKET_OPEN_PREFIX}{interaction.user.name}",
            category=category,
            overwrites=overwrites,
            topic=f"Ticket #{ticket_id} — {interaction.user} ({interaction.user.id})",
            reason=f"Ticket #{ticket_id} par {interaction.user}",
        )

        # Enregistrer en DB
        await db.create_ticket(ticket_id, guild.id, channel.id, interaction.user.id)

        # Message de bienvenue
        welcome_embed = EmbedFactory.ticket_welcome(interaction.user, ticket_id, guild)
        view = TicketActionView()
        await channel.send(
            content=interaction.user.mention,
            embed=welcome_embed,
            view=view,
        )

        # Confirmation éphémère
        await interaction.followup.send(
            embed=EmbedFactory.success(
                "Ticket créé",
                f"Votre ticket a été ouvert : {channel.mention}",
                guild=guild,
            ),
            ephemeral=True,
        )

        # Log
        await self._send_log(
            guild,
            EmbedFactory.ticket_opened_log(ticket_id, interaction.user, channel, guild),
        )

    # ──────────────────────────────────────────────
    #  Slash commands
    # ──────────────────────────────────────────────

    @app_commands.command(name="setup_tickets", description="Configure le système de tickets et personnalise le panel.")
    @app_commands.describe(
        category="Catégorie où créer les tickets",
        log_channel="Salon pour les logs",
        support_role="Rôle du staff de support",
        banner_url="URL d'une bannière à afficher sous le panel (optionnel)",
    )
    @app_commands.default_permissions(administrator=True)
    async def setup_tickets(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel,
        log_channel: discord.TextChannel,
        support_role: discord.Role,
        banner_url: Optional[str] = None,
    ) -> None:
        # Ouvre un modal pour saisir la description avec retours à la ligne
        modal = PanelSetupModal(
            cog=self,
            category=category,
            log_channel=log_channel,
            support_role=support_role,
            banner_url=banner_url,
            target_channel=interaction.channel,
        )
        await interaction.response.send_modal(modal)

    @app_commands.command(name="ticket_close", description="Force la fermeture d'un ticket.")
    @app_commands.describe(reason="Raison de la fermeture")
    @app_commands.default_permissions(manage_channels=True)
    async def force_close(
        self,
        interaction: discord.Interaction,
        reason: str = "Fermé par un administrateur",
    ) -> None:
        ticket = await self.bot.db.get_ticket_by_channel(interaction.channel_id)
        if not ticket:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Erreur", "Ce salon n'est pas un ticket."),
                ephemeral=True,
            )
            return

        view = TicketActionView()
        await view.process_close(interaction, reason)

    @app_commands.command(name="ticket_add", description="Ajoute un utilisateur à ce ticket.")
    @app_commands.describe(member="Membre à ajouter")
    @app_commands.default_permissions(manage_channels=True)
    async def ticket_add(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ) -> None:
        ticket = await self.bot.db.get_ticket_by_channel(interaction.channel_id)
        if not ticket:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Erreur", "Ce salon n'est pas un ticket."),
                ephemeral=True,
            )
            return
        await interaction.channel.set_permissions(
            member,
            read_messages=True,
            send_messages=True,
        )
        await interaction.response.send_message(
            embed=EmbedFactory.success(
                "Membre ajouté",
                f"{member.mention} a été ajouté à ce ticket.",
                guild=interaction.guild,
            )
        )

    @app_commands.command(name="ticket_remove", description="Retire un utilisateur de ce ticket.")
    @app_commands.describe(member="Membre à retirer")
    @app_commands.default_permissions(manage_channels=True)
    async def ticket_remove(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ) -> None:
        ticket = await self.bot.db.get_ticket_by_channel(interaction.channel_id)
        if not ticket:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Erreur", "Ce salon n'est pas un ticket."),
                ephemeral=True,
            )
            return
        await interaction.channel.set_permissions(member, overwrite=None)
        await interaction.response.send_message(
            embed=EmbedFactory.warning(
                "Membre retiré",
                f"{member.mention} a été retiré de ce ticket.",
                guild=interaction.guild,
            )
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TicketsCog(bot))
