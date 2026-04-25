"""
CornicBot — Cog Commandes Personnalisées
Création via modal interactif (mise en forme markdown Discord complète).
"""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from utils.embed_factory import EmbedFactory


_MARKDOWN_HINT = (
    "**gras**  *italique*  __souligné__  ~~barré~~\n"
    "`code`   ```bloc de code```\n"
    "# Titre  ## Sous-titre  ### Petit titre\n"
    "> Citation    -  élément de liste"
)

_CONTENT_PLACEHOLDER = (
    "Exemple :\n"
    "**🛒 Nos prix**\n\n"
    "> Pack Starter — 5€\n"
    "> Pack Pro     — 15€\n\n"
    "Contactez le staff pour commander !"
)


# ──────────────────────────────────────────────────────────────────────────────
#  Modals
# ──────────────────────────────────────────────────────────────────────────────

class CreateCommandModal(discord.ui.Modal, title="✏️  Nouvelle commande"):
    cmd_name = discord.ui.TextInput(
        label="Nom (sans $)",
        placeholder="ex: regles, prix, info, faq…",
        min_length=1,
        max_length=30,
    )
    content = discord.ui.TextInput(
        label="Contenu — markdown Discord supporté",
        placeholder=_CONTENT_PLACEHOLDER,
        style=discord.TextStyle.paragraph,
        min_length=1,
        max_length=2000,
    )

    def __init__(self, cog: "CustomCommandsCog") -> None:
        super().__init__()
        self._cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        name = self.cmd_name.value.strip().lower()

        if self._cog.bot.get_command(name):
            await interaction.response.send_message(
                embed=EmbedFactory.error(
                    "Nom réservé",
                    f"`{name}` est une commande native du bot.",
                    guild=interaction.guild,
                ),
                ephemeral=True,
            )
            return

        await self._cog.bot.db.create_command(
            interaction.guild_id, name, self.content.value, interaction.user.id
        )

        # Aperçu du rendu final
        preview = EmbedFactory.custom_command_frame(
            cmd_name=name,
            content=self.content.value,
            author=interaction.user,
            guild=interaction.guild,
        )
        confirm = EmbedFactory.custom_command_created(name, interaction.guild)

        await interaction.response.send_message(
            embeds=[confirm, preview],
            ephemeral=True,
        )


class EditCommandModal(discord.ui.Modal, title="✏️  Modifier une commande"):
    content = discord.ui.TextInput(
        label="Nouveau contenu — markdown Discord supporté",
        style=discord.TextStyle.paragraph,
        min_length=1,
        max_length=2000,
    )

    def __init__(self, cog: "CustomCommandsCog", name: str, current_content: str) -> None:
        super().__init__()
        self._cog = cog
        self._name = name
        self.content.default = current_content

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self._cog.bot.db.create_command(
            interaction.guild_id, self._name, self.content.value, interaction.user.id
        )

        preview = EmbedFactory.custom_command_frame(
            cmd_name=self._name,
            content=self.content.value,
            author=interaction.user,
            guild=interaction.guild,
        )
        confirm = EmbedFactory.success(
            "Commande mise à jour",
            f"La commande `${self._name}` a été modifiée.",
            guild=interaction.guild,
        )

        await interaction.response.send_message(
            embeds=[confirm, preview],
            ephemeral=True,
        )


# ──────────────────────────────────────────────────────────────────────────────
#  Cog
# ──────────────────────────────────────────────────────────────────────────────

class CustomCommandsCog(commands.Cog, name="CustomCommandsCog"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ── Listener : exécution des commandes ────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return
        if not message.content.startswith("$"):
            return

        parts = message.content[1:].split(maxsplit=1)
        if not parts:
            return
        cmd_name = parts[0].lower()

        if self.bot.get_command(cmd_name):
            return

        row = await self.bot.db.get_command(message.guild.id, cmd_name)
        if not row:
            return

        embed = EmbedFactory.custom_command_frame(
            cmd_name=cmd_name,
            content=row["content"],
            author=message.author,
            guild=message.guild,
        )
        await message.channel.send(embed=embed)

        try:
            await message.delete()
        except discord.Forbidden:
            pass

    # ── Slash commands ─────────────────────────────

    cmds_group = app_commands.Group(
        name="cmd",
        description="Gestion des commandes personnalisées",
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @cmds_group.command(name="create", description="Crée une commande via une interface de mise en forme.")
    async def slash_create(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(CreateCommandModal(self))

    @cmds_group.command(name="edit", description="Modifie le contenu d'une commande existante.")
    @app_commands.describe(name="Nom de la commande à modifier")
    async def slash_edit(self, interaction: discord.Interaction, name: str) -> None:
        row = await self.bot.db.get_command(interaction.guild_id, name.lower())
        if not row:
            await interaction.response.send_message(
                embed=EmbedFactory.error(
                    "Introuvable",
                    f"La commande `${name}` n'existe pas sur ce serveur.",
                    guild=interaction.guild,
                ),
                ephemeral=True,
            )
            return
        await interaction.response.send_modal(
            EditCommandModal(self, name.lower(), row["content"])
        )

    @cmds_group.command(name="delete", description="Supprime une commande personnalisée.")
    @app_commands.describe(name="Nom de la commande à supprimer")
    async def slash_delete(self, interaction: discord.Interaction, name: str) -> None:
        deleted = await self.bot.db.delete_command(interaction.guild_id, name.lower())
        if deleted:
            await interaction.response.send_message(
                embed=EmbedFactory.custom_command_deleted(name, interaction.guild),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                embed=EmbedFactory.error(
                    "Introuvable",
                    f"La commande `${name}` n'existe pas.",
                    guild=interaction.guild,
                ),
                ephemeral=True,
            )

    @cmds_group.command(name="list", description="Liste toutes les commandes du serveur.")
    async def slash_list(self, interaction: discord.Interaction) -> None:
        rows = await self.bot.db.list_commands(interaction.guild_id)
        await interaction.response.send_message(
            embed=EmbedFactory.custom_commands_list(rows, interaction.guild),
            ephemeral=True,
        )

    @cmds_group.command(name="preview", description="Affiche un aperçu d'une commande.")
    @app_commands.describe(name="Nom de la commande")
    async def slash_preview(self, interaction: discord.Interaction, name: str) -> None:
        row = await self.bot.db.get_command(interaction.guild_id, name.lower())
        if not row:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Introuvable", f"`${name}` n'existe pas.", guild=interaction.guild),
                ephemeral=True,
            )
            return
        embed = EmbedFactory.custom_command_frame(
            cmd_name=name.lower(),
            content=row["content"],
            author=interaction.user,
            guild=interaction.guild,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @cmds_group.command(name="aide", description="Affiche la liste des balises markdown disponibles.")
    async def slash_aide(self, interaction: discord.Interaction) -> None:
        embed = EmbedFactory.info(
            "Mise en forme — Markdown Discord",
            (
                "Utilisez ces balises dans le contenu de vos commandes :\n\n"
                "```\n"
                "**gras**          → gras\n"
                "*italique*        → italique\n"
                "__souligné__      → souligné\n"
                "~~barré~~         → barré\n"
                "`code`            → code inline\n"
                "```bloc```        → bloc de code\n"
                "# Titre           → grand titre\n"
                "## Titre          → titre moyen\n"
                "### Titre         → petit titre\n"
                "> texte           → citation\n"
                "- élément         → liste\n"
                "```\n\n"
                f"Utilisez `/cmd create` pour ouvrir l'éditeur."
            ),
            guild=interaction.guild,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── Préfixe (compatibilité) ────────────────────

    @commands.command(name="createcmd", aliases=["addcmd"])
    @commands.has_permissions(manage_guild=True)
    async def createcmd(self, ctx: commands.Context) -> None:
        """Redirige vers /cmd create (interface graphique)."""
        await ctx.send(
            embed=EmbedFactory.info(
                "Utilisez la commande slash",
                "La création de commandes se fait maintenant via `/cmd create` "
                "pour profiter de l'éditeur de mise en forme.",
                guild=ctx.guild,
            )
        )

    @commands.command(name="delcmd", aliases=["deletecmd", "removecmd"])
    @commands.has_permissions(manage_guild=True)
    async def delcmd(self, ctx: commands.Context, name: str) -> None:
        deleted = await self.bot.db.delete_command(ctx.guild.id, name.lower())
        if deleted:
            await ctx.send(embed=EmbedFactory.custom_command_deleted(name, ctx.guild))
        else:
            await ctx.send(
                embed=EmbedFactory.error(
                    "Introuvable", f"La commande `${name}` n'existe pas.", guild=ctx.guild
                )
            )

    @commands.command(name="listcmds", aliases=["cmds"])
    async def listcmds(self, ctx: commands.Context) -> None:
        rows = await self.bot.db.list_commands(ctx.guild.id)
        await ctx.send(embed=EmbedFactory.custom_commands_list(rows, ctx.guild))

    # ── Erreurs ────────────────────────────────────

    @delcmd.error
    async def cmd_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(
                embed=EmbedFactory.error(
                    "Permissions insuffisantes",
                    "Vous avez besoin de **Gérer le serveur**.",
                    guild=ctx.guild,
                )
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                embed=EmbedFactory.warning(
                    "Argument manquant", "`$delcmd <nom>`", guild=ctx.guild
                )
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CustomCommandsCog(bot))
