import os
import asyncio
import discord
from discord.ext import commands

from sms import SendSms

# ============================
# TOKEN — Render/ortam değişkeninden okunur
# ============================
TOKEN = os.environ.get("TOKEN")

GIF = "https://media.tenor.com/SWiGXYOM8eMAAAAC/russia-soviet.gif"

# sms.py içindeki tüm servis metodlarını topla (Turbo modu için)
servisler_sms = [
    attr for attr in dir(SendSms)
    if callable(getattr(SendSms, attr)) and not attr.startswith("__")
]

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="*", intents=intents, help_command=None)


@bot.event
async def on_ready():
    print(f"{bot.user} çalışmaya başladı!")
    print(f"Yüklü servis sayısı: {len(servisler_sms)}")
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.playing,
        name="https://gitlab.com/tingirifistik/enough/"
    ))


# ---------------------------
# YARDIM
# ---------------------------
@bot.command(name="help")
async def help_cmd(ctx):
    embed = discord.Embed(
        title="Enough SMS Bot — Komutlar",
        description=(
            "`*sms <numara>` → Normal mod, 52 SMS\n"
            "`*turbo <numara>` → Turbo mod (tüm servisler paralel)\n"
            "`*sms <numara> <adet>` → Belirtilen adette SMS\n"
            "`*sms <numara> <adet> <mail>` → Mail ile birlikte\n"
            "`*servisler` → Yüklü servis listesi"
        ),
        color=0x001EFF
    )
    embed.set_thumbnail(url=GIF)
    await ctx.send(embed=embed)


# ---------------------------
# SERVİS LİSTESİ
# ---------------------------
@bot.command(name="servisler")
async def servisler_cmd(ctx):
    if not servisler_sms:
        await ctx.send("Hiç servis bulunamadı. `sms.py` dosyanı kontrol et.")
        return
    liste = "\n".join(f"• `{s}`" for s in servisler_sms)
    await ctx.send(f"**Yüklü Servisler ({len(servisler_sms)}):**\n{liste}")


# ---------------------------
# NORMAL SMS
# Kullanım: *sms 5051234567 [adet] [mail]
# ---------------------------
@bot.command(name="sms")
async def sms_cmd(ctx, telno: str = None, adet: int = 52, mail: str = ""):
    if telno is None or not telno.isdigit() or len(telno) != 10:
        await ctx.send(
            f"Geçerli numara yaz!\n`*sms 5051234567`\n{ctx.author.mention}"
        )
        return

    if adet <= 0 or adet > 5000:
        await ctx.send(f"Adet 1-5000 arasında olmalı.\n{ctx.author.mention}")
        return

    embed = discord.Embed(
        title="SMS Gönderimi Başladı (Normal)",
        description=(
            f"**Numara:** `{telno}`\n"
            f"**Adet:** `{adet}`\n"
            f"**Servis sayısı:** `{len(servisler_sms)}`\n"
            f"**İsteyen:** {ctx.author.mention}"
        ),
        color=0x001EFF
    )
    embed.set_thumbnail(url=GIF)
    msg = await ctx.send(embed=embed)

    try:
        sms = SendSms(telno, mail)
        gonderilen = 0

        while sms.adet < adet:
            for fonk in servisler_sms:
                if sms.adet >= adet:
                    break
                try:
                    await asyncio.to_thread(getattr(sms, fonk))
                except Exception:
                    pass
                gonderilen = sms.adet

        await msg.edit(embed=discord.Embed(
            title="SMS Gönderimi Tamamlandı",
            description=(
                f"**Numara:** `{telno}`\n"
                f"**Gönderilen:** `{sms.adet}`\n"
                f"**İsteyen:** {ctx.author.mention}"
            ),
            color=0x00FF00
        ))
    except Exception as e:
        await ctx.send(f"Hata: `{e}`\n{ctx.author.mention}")


# ---------------------------
# TURBO SMS
# Kullanım: *turbo 5051234567 [mail]
# ---------------------------
@bot.command(name="turbo")
async def turbo_cmd(ctx, telno: str = None, mail: str = ""):
    if telno is None or not telno.isdigit() or len(telno) != 10:
        await ctx.send(
            f"Geçerli numara yaz!\n`*turbo 5051234567`\n{ctx.author.mention}"
        )
        return

    embed = discord.Embed(
        title="SMS Gönderimi Başladı (TURBO)",
        description=(
            f"**Numara:** `{telno}`\n"
            f"**Mod:** Tüm servisler paralel\n"
            f"**Servis sayısı:** `{len(servisler_sms)}`\n"
            f"**İsteyen:** {ctx.author.mention}\n\n"
            f"Durdurmak için `*dur` yaz."
        ),
        color=0xFF0000
    )
    embed.set_thumbnail(url=GIF)
    await ctx.send(embed=embed)

    sms = SendSms(telno, mail)
    dur_event = asyncio.Event()
    turbo_tasks[ctx.channel.id] = dur_event

    try:
        while not dur_event.is_set():
            tasks = [
                asyncio.to_thread(getattr(sms, fonk))
                for fonk in servisler_sms
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        await ctx.send(f"Hata: `{e}`")
    finally:
        turbo_tasks.pop(ctx.channel.id, None)
        await ctx.send(
            f"Turbo durduruldu. **Toplam gönderilen:** `{sms.adet}`\n{ctx.author.mention}"
        )


# ---------------------------
# DURDUR
# ---------------------------
turbo_tasks = {}

@bot.command(name="dur")
async def dur_cmd(ctx):
    ev = turbo_tasks.get(ctx.channel.id)
    if ev:
        ev.set()
        await ctx.send(f"Turbo durduruluyor...\n{ctx.author.mention}")
    else:
        await ctx.send(f"Aktif turbo yok.\n{ctx.author.mention}")


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("TOKEN environment variable tanımlı değil!")
    bot.run(TOKEN)
