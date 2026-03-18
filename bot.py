import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import io
import os

# ===== CONFIG =====
TOKEN = os.getenv("TOKEN")
GUILD_ID = 1483270417056665806
TICKET_CATEGORY_ID = 1483271654736920646
SUPPORT_ROLE_ID = 1483551910635114672
TICKET_LOG_CHANNEL = 1483553693872820235
# ==================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== CONFIRMATION =====
class ConfirmCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.value = False

    @discord.ui.button(label="✅ Confirmer", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()
        await interaction.response.send_message("Fermeture confirmée", ephemeral=True)

    @discord.ui.button(label="❌ Annuler", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        await interaction.response.send_message("Annulé", ephemeral=True)


# ===== VIEW =====
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔒 Fermer",
        style=discord.ButtonStyle.red,
        custom_id="close_ticket_button"
    )
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        guild = interaction.guild

        if not channel or not guild:
            return

        topic = channel.topic or ""
        if not topic.startswith("ticket-"):
            await interaction.response.send_message("Erreur ticket", ephemeral=True)
            return

        owner_id = int(topic.split("-")[1])
        owner = guild.get_member(owner_id)

        # Vérification permissions
        if interaction.user.id != owner_id and SUPPORT_ROLE_ID not in [r.id for r in interaction.user.roles]:
            await interaction.response.send_message("❌ Tu ne peux pas fermer ce ticket", ephemeral=True)
            return

        confirm = ConfirmCloseView()
        await interaction.response.send_message("Confirmer la fermeture ?", view=confirm, ephemeral=True)
        await confirm.wait()

        if not confirm.value:
            return

        # Transcript
        logs = []
        async for msg in channel.history(limit=200):
            logs.append(f"{msg.author}: {msg.content}")

        file = discord.File(io.BytesIO("\n".join(logs).encode()), filename="transcript.txt")

        # Logs
        log_channel = guild.get_channel(TICKET_LOG_CHANNEL)
        if log_channel:
            await log_channel.send(file=file)

        # MP user
        if owner:
            try:
                await owner.send("Ton ticket a été fermé", file=file)
            except:
                pass

        await channel.delete()


# ===== SELECT =====
class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Question"),
            discord.SelectOption(label="Cartes cadeaux"),
            discord.SelectOption(label="Jeux PC"),
            discord.SelectOption(label="Jeux Console"),
        ]
        super().__init__(
            placeholder="Choisis",
            options=options,
            custom_id="ticket_select"
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user

        if not guild:
            return

        # Anti double ticket
        for ch in guild.text_channels:
            if ch.topic and f"ticket-{member.id}" in ch.topic:
                await interaction.response.send_message(
                    "❌ Tu as déjà un ticket ouvert !",
                    ephemeral=True
                )
                return

        category_name = self.values[0]
        category = guild.get_channel(TICKET_CATEGORY_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True),
            guild.get_role(SUPPORT_ROLE_ID): discord.PermissionOverwrite(view_channel=True)
        }

        channel_name = category_name.lower().replace(" ", "-")

        channel = await guild.create_text_channel(
            name=channel_name,
            topic=f"ticket-{member.id}-{category_name}",
            category=category,
            overwrites=overwrites
        )

        if category_name == "Cartes cadeaux":
            question = "Quelle carte cadeau veux-tu ?"
        elif "Jeux" in category_name:
            question = "Quel jeu veux-tu ?"
        else:
            question = "Quelle est ta question ?"

        embed = discord.Embed(
            title="🎫 Nouveau ticket",
            description=f"👤 {member.mention}\n📂 {category_name}\n\n❓ {question}",
            color=0x00ff00
        )

        await channel.send(f"{member.mention} <@&{SUPPORT_ROLE_ID}>", embed=embed, view=TicketView())
        await interaction.response.send_message(f"✅ Ticket créé : {channel.mention}", ephemeral=True)


# ===== PANEL =====
class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


# ===== COMMANDE =====
@app_commands.command(name="panel", description="Créer panel ticket")
async def panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 Support",
        description="Choisis une catégorie",
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
