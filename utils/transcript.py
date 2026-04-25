"""
CornicBot — Générateur de transcripts HTML.
Produit un fichier HTML stylisé depuis l'historique d'un salon de ticket.
"""

from __future__ import annotations

import io
import discord
from datetime import datetime, timezone


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Transcript — {ticket_id}</title>
  <style>
    :root {{
      --bg-primary: #1e1f22;
      --bg-secondary: #2b2d31;
      --bg-tertiary: #313338;
      --text-primary: #dbdee1;
      --text-secondary: #949ba4;
      --text-muted: #80848e;
      --blurple: #5865f2;
      --green: #57f287;
      --red: #ed4245;
      --yellow: #fee75c;
      --border: #3f4147;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg-primary);
      color: var(--text-primary);
      font-family: 'gg sans', 'Noto Sans', Whitney, 'Helvetica Neue', Helvetica, Roboto, Arial, sans-serif;
      font-size: 16px;
      line-height: 1.5;
    }}
    /* ── Header ─────────────────────────────────── */
    .header {{
      background: var(--bg-secondary);
      border-bottom: 2px solid var(--blurple);
      padding: 20px 30px;
      display: flex;
      align-items: center;
      gap: 16px;
      position: sticky;
      top: 0;
      z-index: 100;
    }}
    .header-logo {{
      width: 48px; height: 48px;
      border-radius: 50%;
      object-fit: cover;
    }}
    .header-info h1 {{
      font-size: 1.3rem;
      font-weight: 700;
      color: var(--blurple);
    }}
    .header-info p {{ color: var(--text-secondary); font-size: .85rem; }}
    /* ── Meta-info ───────────────────────────────── */
    .meta-bar {{
      background: var(--bg-tertiary);
      display: flex; flex-wrap: wrap; gap: 24px;
      padding: 14px 30px;
      border-bottom: 1px solid var(--border);
    }}
    .meta-item {{ display: flex; flex-direction: column; gap: 2px; }}
    .meta-label {{ font-size: .7rem; text-transform: uppercase; letter-spacing: .06em; color: var(--text-muted); }}
    .meta-value {{ font-size: .9rem; font-weight: 600; }}
    .badge {{
      display: inline-block;
      padding: 2px 10px;
      border-radius: 12px;
      font-size: .75rem;
      font-weight: 700;
    }}
    .badge-open   {{ background: #57f28730; color: var(--green); }}
    .badge-closed {{ background: #ed424530; color: var(--red); }}
    .badge-staff  {{ background: #5865f230; color: var(--blurple); }}
    /* ── Messages ────────────────────────────────── */
    .messages {{ padding: 20px 30px; display: flex; flex-direction: column; gap: 2px; }}
    .message {{
      display: flex;
      gap: 14px;
      padding: 8px 10px;
      border-radius: 6px;
      transition: background .1s;
    }}
    .message:hover {{ background: rgba(255,255,255,.04); }}
    .message.system {{
      background: rgba(88,101,242,.08);
      border-left: 3px solid var(--blurple);
      margin: 8px 0;
    }}
    .avatar {{
      width: 40px; height: 40px;
      border-radius: 50%;
      object-fit: cover;
      flex-shrink: 0;
      margin-top: 2px;
    }}
    .avatar-placeholder {{
      width: 40px; height: 40px;
      border-radius: 50%;
      background: var(--blurple);
      flex-shrink: 0;
      display: flex; align-items: center; justify-content: center;
      font-weight: 700;
      font-size: .9rem;
    }}
    .msg-body {{ flex: 1; min-width: 0; }}
    .msg-header {{ display: flex; align-items: baseline; gap: 8px; margin-bottom: 2px; }}
    .msg-author {{ font-weight: 600; font-size: .9rem; }}
    .msg-author.bot {{ color: var(--blurple); }}
    .msg-author.staff {{ color: #eb459e; }}
    .role-tag {{
      font-size: .65rem; padding: 1px 6px;
      border-radius: 4px;
      background: var(--blurple);
      color: #fff;
      font-weight: 600;
    }}
    .role-tag.staff-tag {{ background: #eb459e; }}
    .msg-time {{ font-size: .75rem; color: var(--text-muted); }}
    .msg-content {{ color: var(--text-primary); font-size: .9rem; word-break: break-word; }}
    .msg-content a {{ color: var(--blurple); }}
    /* ── Attachments ─────────────────────────────── */
    .attachments {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 6px; }}
    .attachment {{
      background: var(--bg-secondary);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 6px 12px;
      font-size: .8rem;
      color: var(--blurple);
    }}
    .attachment img {{ max-width: 400px; max-height: 300px; border-radius: 4px; display: block; margin-top: 4px; }}
    /* ── Embeds ──────────────────────────────────── */
    .embed {{
      border-left: 4px solid var(--blurple);
      background: var(--bg-tertiary);
      border-radius: 0 6px 6px 0;
      padding: 10px 14px;
      margin-top: 6px;
      max-width: 520px;
    }}
    .embed-title {{ font-weight: 700; font-size: .9rem; margin-bottom: 4px; }}
    .embed-desc {{ font-size: .85rem; color: var(--text-secondary); }}
    /* ── Footer ──────────────────────────────────── */
    .footer {{
      background: var(--bg-secondary);
      border-top: 1px solid var(--border);
      padding: 16px 30px;
      text-align: center;
      font-size: .8rem;
      color: var(--text-muted);
    }}
    .footer span {{ color: var(--blurple); font-weight: 600; }}
    @media (max-width: 600px) {{
      .header, .meta-bar, .messages {{ padding-left: 14px; padding-right: 14px; }}
      .meta-bar {{ gap: 14px; }}
    }}
  </style>
</head>
<body>
  <div class="header">
    <img class="header-logo" src="{guild_icon}" alt="Server Icon" onerror="this.style.display='none'">
    <div class="header-info">
      <h1>🎫 Transcript — #{ticket_id}</h1>
      <p>{guild_name} · Exporté le {export_date}</p>
    </div>
  </div>

  <div class="meta-bar">
    <div class="meta-item">
      <span class="meta-label">🏷️ Ticket ID</span>
      <span class="meta-value">#{ticket_id}</span>
    </div>
    <div class="meta-item">
      <span class="meta-label">👤 Client</span>
      <span class="meta-value">{user_name}</span>
    </div>
    <div class="meta-item">
      <span class="meta-label">🛡️ Staff</span>
      <span class="meta-value badge badge-staff">{staff_name}</span>
    </div>
    <div class="meta-item">
      <span class="meta-label">📊 Messages</span>
      <span class="meta-value">{message_count}</span>
    </div>
    <div class="meta-item">
      <span class="meta-label">🔒 Statut</span>
      <span class="meta-value badge badge-closed">Fermé</span>
    </div>
  </div>

  <div class="messages">
    {messages_html}
  </div>

  <div class="footer">
    Généré par <span>CornicBot</span> · {guild_name} · {export_date}
  </div>
</body>
</html>"""


_MSG_TEMPLATE = """
<div class="message {extra_class}">
  {avatar_html}
  <div class="msg-body">
    <div class="msg-header">
      <span class="msg-author {author_class}">{author_name}</span>
      {role_tag}
      <span class="msg-time">{timestamp}</span>
    </div>
    <div class="msg-content">{content}</div>
    {attachments_html}
    {embeds_html}
  </div>
</div>
"""

_SYSTEM_MSG_TEMPLATE = """
<div class="message system">
  <div class="msg-body">
    <div class="msg-content"><em>🔔 {content}</em></div>
  </div>
</div>
"""


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("\n", "<br>")
    )


def _render_message(msg: discord.Message) -> str:
    author = msg.author
    is_bot = author.bot
    display_name = _escape(author.display_name)

    # Avatar
    avatar_url = str(author.display_avatar.url) if hasattr(author, "display_avatar") else ""
    if avatar_url:
        avatar_html = f'<img class="avatar" src="{avatar_url}" alt="{display_name}" loading="lazy">'
    else:
        avatar_html = f'<div class="avatar-placeholder">{display_name[0].upper()}</div>'

    # Author class
    if is_bot:
        author_class = "bot"
        role_tag = '<span class="role-tag">BOT</span>'
    else:
        author_class = ""
        role_tag = ""

    # Timestamp
    ts = msg.created_at.astimezone(timezone.utc).strftime("%d/%m/%Y à %H:%M")

    # Content
    content = _escape(msg.content) if msg.content else ""

    # Attachments
    att_parts = []
    for att in msg.attachments:
        if att.content_type and att.content_type.startswith("image/"):
            att_parts.append(
                f'<div class="attachment"><img src="{att.url}" alt="{_escape(att.filename)}" loading="lazy"></div>'
            )
        else:
            att_parts.append(
                f'<div class="attachment">📎 <a href="{att.url}" target="_blank">{_escape(att.filename)}</a></div>'
            )
    attachments_html = f'<div class="attachments">{"".join(att_parts)}</div>' if att_parts else ""

    # Embeds (résumé simplifié)
    embed_parts = []
    for emb in msg.embeds:
        title_html = f'<div class="embed-title">{_escape(str(emb.title))}</div>' if emb.title else ""
        desc_html = f'<div class="embed-desc">{_escape(str(emb.description))}</div>' if emb.description else ""
        color_hex = f"#{emb.color.value:06x}" if emb.color else "#5865f2"
        embed_parts.append(
            f'<div class="embed" style="border-left-color:{color_hex}">{title_html}{desc_html}</div>'
        )
    embeds_html = "".join(embed_parts)

    if not content and not att_parts and not embed_parts:
        return ""

    return _MSG_TEMPLATE.format(
        extra_class="",
        avatar_html=avatar_html,
        author_name=display_name,
        author_class=author_class,
        role_tag=role_tag,
        timestamp=ts,
        content=content,
        attachments_html=attachments_html,
        embeds_html=embeds_html,
    )


async def generate_html_transcript(
    channel: discord.TextChannel,
    ticket_id: str,
    user: discord.Member,
    staff: discord.Member | None,
) -> tuple[io.BytesIO, int]:
    """
    Génère un transcript HTML depuis l'historique du salon.
    Retourne (buffer_io, message_count).
    """
    messages_html_parts: list[str] = []
    count = 0

    history = []
    async for msg in channel.history(limit=None, oldest_first=True):
        history.append(msg)

    for msg in history:
        rendered = _render_message(msg)
        if rendered:
            messages_html_parts.append(rendered)
            count += 1

    guild = channel.guild
    now_str = datetime.now(tz=timezone.utc).strftime("%d/%m/%Y à %H:%M UTC")

    html = _HTML_TEMPLATE.format(
        ticket_id=ticket_id,
        guild_name=_escape(guild.name),
        guild_icon=str(guild.icon.url) if guild.icon else "",
        export_date=now_str,
        user_name=_escape(user.display_name),
        staff_name=_escape(staff.display_name) if staff else "Non assigné",
        message_count=count,
        messages_html="".join(messages_html_parts) or "<p style='color:#80848e;padding:20px'>Aucun message.</p>",
    )

    buf = io.BytesIO(html.encode("utf-8"))
    buf.seek(0)
    return buf, count
