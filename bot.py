import discord
from discord import app_commands
from discord.ext import commands
import io
import os
from datetime import datetime

# ===== CONFIG =====
TOKEN = os.getenv("TOKEN")
GUILD_ID = 1483270417056665806
TICKET_CATEGORY_ID = 1483271654736920646
SUPPORT_ROLE_ID = 1483551910635114672
TICKET_LOG_CHANNEL = 1483812985964200177
# ==================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

EMOJI_MAP = {
    "Question": "❓",
    "Cartes cadeaux": "🎁",
    "Jeux PC": "💻",
    "Jeux Console": "🎮"
}

# ===== VIEW =====
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📌 Claim", style=discord.ButtonStyle.blurple, custom_id="claim_ticket")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if SUPPORT_ROLE_ID not in [r.id for r in interaction.user.roles]:
            await interaction.response.send_message("❌ Réservé au staff", ephemeral=True)
            return

        await interaction.response.send_message(f"📌 Ticket pris par {interaction.user.mention}")

    @discord.ui.button(label="🔒 Fermer", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        guild = interaction.guild

        topic = channel.topic or ""
        owner_id = int(topic.split("-")[1])
        owner = guild.get_member(owner_id)

        logs = []

        async for msg in channel.history(limit=200, oldest_first=True):
            time = msg.created_at.strftime("%d/%m/%Y %H:%M")
            content = msg.content if msg.content else "[aucun texte]"

            # éviter les messages vides / bug
            if len(content.strip()) == 0:
                content = "[message vide]"

            logs.append(f"[{time}] {msg.author}: {content}")

        # 🔥 sécurité anti fichier vide
        if not logs:
            logs.append("Aucun message dans le ticket.")

        transcript_text = "\n".join(logs)

        file = discord.File(
            io.BytesIO(transcript_text.encode("utf-8")),
            filename="transcript.txt"
        )

        # LOG CHANNEL
        log_channel = guild.get_channel(TICKET_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(file=file)

        # MP USER FIX
        if owner:
            try:
                await owner.send(
                    "✅ Votre ticket a été fermé.\n📄 Voici un logs du ticket.\n\nNous vous remercions de soutenir Game Store !",
                    file=file
                )
            except Exception as e:
                print("Erreur MP :", e)

        await channel.delete()

# ===== SELECT =====
class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Question", emoji="❓"),
            discord.SelectOption(label="Cartes cadeaux", emoji="🎁"),
            discord.SelectOption(label="Jeux PC", emoji="💻"),
            discord.SelectOption(label="Jeux Console", emoji="🎮"),
        ]
        super().__init__(placeholder="Choisis une catégorie", options=options, custom_id="ticket_select")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user

        for ch in guild.text_channels:
            if ch.topic and f"ticket-{member.id}" in ch.topic:
                await interaction.response.send_message("❌ Tu as déjà un ticket", ephemeral=True)
                return

        category_name = self.values[0]
        category = guild.get_channel(TICKET_CATEGORY_ID)

        ticket_number = 1
        for ch in guild.text_channels:
            if "ticket-" in ch.name:
                try:
                    num = int(ch.name.split("-")[-1])
                    if num >= ticket_number:
                        ticket_number = num + 1
                except:
                    pass

        ticket_id = str(ticket_number).zfill(3)
        emoji = EMOJI_MAP.get(category_name, "📩")
        channel_name = f"{emoji}-ticket-{ticket_id}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True),
            guild.get_role(SUPPORT_ROLE_ID): discord.PermissionOverwrite(view_channel=True)
        }

        channel = await guild.create_text_channel(
            name=channel_name,
            topic=f"ticket-{member.id}-{category_name}",
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="🎫 Nouveau ticket",
            description=(
                f"👤 **Client :** {member.mention}\n"
                f"🛠️ **Support :** <@&{SUPPORT_ROLE_ID}>\n"
                f"📂 **Catégorie :** {category_name}\n\n"
                f"━━━━━━━━━━━━━━━\n"
                f"💬 Merci d'expliquer votre demande.\n\n"
                f"━━━━━━━━━━━━━━━\n"
                f"💳 **Moyens de paiements :**\n"
                f"• PayPal (amie proche / sans notes)\n"
                f"• LTC"
            ),
            color=0x2b2d31
        )

        await channel.send(embed=embed, view=TicketView())

        await interaction.response.send_message(f"✅ Ticket créé : {channel.mention}", ephemeral=True)

# ===== PANEL =====
class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

@app_commands.command(name="panel", description="Créer panel ticket")
async def panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 Support — Game Store FR",
        description=(
            "Besoin d'aide sur un produit ou une commande ? Ouvre un ticket.\n\n"
            "**1.** Clique sur *Ouvrir un ticket*\n"
            "**2.** Un salon privé est créé\n"
            "**3.** Le staff t'aide directement\n\n"
            "━━━━━━━━━━━━━━━\n"
            "💳 **Moyens de paiements :**\n"
            "• PayPal (amie proche / sans notes)\n"
            "• LTC"
        ),
        color=0x2b2d31
    )

    await interaction.response.send_message(embed=embed, view=PanelView())

bot.tree.add_command(panel)

# ===== READY =====
@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")

    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)

    bot.add_view(TicketView())
    bot.add_view(PanelView())

# ===== RUN =====
bot.run(TOKEN)
