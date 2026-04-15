# =========================================================
# DISCORD NC KYAMI — MINIMAL BOT (5 ESSENTIAL COMMANDS)
# =========================================================

import discord
from discord.ext import commands
import asyncio
from typing import Dict

# =========================
# CONFIG
# =========================
TOKEN = "MTQ2NjA5NDkyMjk4NDU5MTQ4NQ.Ge-jJv.xyFcFC5fOGhvPBUuCqejZ5aN7jB3ag9w3ZMrII"
OWNER_ID = 1069460715020222514
DEFAULT_DELAY = 1.0

RAID_TEXTS = [
    "×~🌷1🌷×~", "~×🌼2🌼×~", "××🌻3🌻××", "~~🌺4🌺~~", "~×🌹5🌹×~",
    "×~🏵️6🏵️×~", "~×🪷7🪷×~", "××💮8💮××", "~~🌸9🌸~~", "~×🌷10🌷×~",
]

# =========================
# GLOBAL STATE
# =========================

# NC rotation per guild
nc_channels: Dict[int, list[int]] = {}     # key=guild_id -> list of channel_ids
nc_index: Dict[int, int] = {}              # key=guild_id -> current index
nc_task: Dict[int, asyncio.Task] = {}      # key=guild_id -> asyncio.Task

# Spam tasks per channel
spam_task: Dict[int, asyncio.Task] = {}    # key=channel_id -> asyncio.Task

# Channel rename tasks per channel
chname_task: Dict[int, asyncio.Task] = {}  # key=channel_id -> asyncio.Task

# =========================
# PERMISSIONS
# =========================
def only_owner():
    async def predicate(ctx):
        return ctx.author.id == OWNER_ID
    return commands.check(predicate)

# =========================
# DISCORD SETUP
# =========================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# =========================
# NC LOOP
# =========================
async def nc_loop(guild_id: int, text: str):
    """Rotate through saved NC channels, sending text + raid_text"""
    i = 0
    while True:
        try:
            ids = nc_channels.get(guild_id, [])
            if not ids:
                break

            channel_id = ids[i % len(ids)]
            channel = bot.get_channel(channel_id)

            if not channel:
                await asyncio.sleep(DEFAULT_DELAY)
                i += 1
                continue

            raid = RAID_TEXTS[i % len(RAID_TEXTS)]
            msg = f"{text} {raid}"
            await channel.send(msg)

            i += 1
            nc_index[guild_id] = i
            await asyncio.sleep(DEFAULT_DELAY)

        except discord.Forbidden:
            await asyncio.sleep(2)
        except discord.HTTPException:
            await asyncio.sleep(2)
        except Exception:
            await asyncio.sleep(1)

# =========================
# EVENTS
# =========================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        return await ctx.send("❌ Not authorized (OWNER only).")
    raise error

# =========================
# SPAM LOOP
# =========================
async def spam_loop(channel: discord.TextChannel, text: str):
    """Send spam paragraph repeatedly in channel"""
    while True:
        try:
            # Build long paragraph (repeat text 20 times separated by spaces)
            spam_text = " ".join([text] * 20)
            await channel.send(spam_text)
            await asyncio.sleep(DEFAULT_DELAY)

        except discord.Forbidden:
            await asyncio.sleep(2)
        except discord.HTTPException:
            await asyncio.sleep(2)
        except Exception:
            await asyncio.sleep(1)

# =========================
# CHANNEL RENAME LOOP
# =========================
async def chname_loop(channel: discord.TextChannel, text: str):
    """Rename channel repeatedly with text + rotating raid_text"""
    i = 0
    while True:
        try:
            raid = RAID_TEXTS[i % len(RAID_TEXTS)]
            new_name = f"{text}-{raid}"
            await channel.edit(name=new_name)
            i += 1
            await asyncio.sleep(15)  # Rate-limit safe delay

        except Exception as e:
            print("chname loop error:", repr(e))
            await asyncio.sleep(15)

# =========================
# COMMANDS (5 ESSENTIAL)
# =========================

@bot.command(name="setnc")
@only_owner()
async def setnc(ctx, *channel_ids: int):
    """
    !setnc <channel_id1> <channel_id2> ...
    Set NC channels for this guild (accept only numeric IDs).
    """
    if not ctx.guild:
        return await ctx.send("❌ Use inside server, not DM.")

    if not channel_ids:
        return await ctx.send("❌ Example: `!setnc 123456789 987654321`")

    nc_channels[ctx.guild.id] = list(channel_ids)
    nc_index[ctx.guild.id] = 0

    # Format reply with <#id> mentions
    preview = []
    for cid in channel_ids:
        ch = bot.get_channel(cid)
        if ch:
            preview.append(ch.mention)
        else:
            preview.append(f"`{cid}`")

    reply = "✅ NC channels set: " + ", ".join(preview)
    await ctx.send(reply)

@bot.command(name="nc")
@only_owner()
async def nc(ctx, *, text: str = "NC"):
    """
    !nc <text>
    Start NC loop: rotates through saved channels, sends "<text> <raid_text>".
    If loop already running, cancels old one and starts new.
    """
    if not ctx.guild:
        return await ctx.send("❌ Use inside server.")

    ids = nc_channels.get(ctx.guild.id)
    if not ids:
        return await ctx.send("❌ Set channels first: `!setnc 123 456 789`")

    # Cancel existing task
    if ctx.guild.id in nc_task:
        nc_task[ctx.guild.id].cancel()

    # Start new NC loop
    task = asyncio.create_task(nc_loop(ctx.guild.id, text))
    nc_task[ctx.guild.id] = task

    channels_str = ", ".join([f"<#{cid}>" for cid in ids])
    await ctx.send(f"✅ NC loop started — rotating: {channels_str}")

@bot.command(name="ncstop")
@only_owner()
async def ncstop(ctx):
    """
    !ncstop
    Stops NC loop for this guild.
    """
    if not ctx.guild:
        return await ctx.send("❌ Use inside server.")

    if ctx.guild.id not in nc_task:
        return await ctx.send("❌ NC loop not running.")

    nc_task[ctx.guild.id].cancel()
    nc_task.pop(ctx.guild.id, None)

    await ctx.send("🛑 NC loop stopped.")

@bot.command(name="send")
@only_owner()
async def send(ctx, *, text: str):
    """
    !send <text>
    Start spam loop in current channel: builds long paragraph (repeat 20x), sends repeatedly.
    If spam already running in this channel, restarts it.
    """
    if not isinstance(ctx.channel, discord.TextChannel):
        return await ctx.send("❌ Use inside text channel.")

    # Cancel existing spam task in this channel
    if ctx.channel.id in spam_task:
        spam_task[ctx.channel.id].cancel()

    # Start new spam loop
    task = asyncio.create_task(spam_loop(ctx.channel, text))
    spam_task[ctx.channel.id] = task

    await ctx.send(f"✅ Spam loop started in {ctx.channel.mention}")

@bot.command(name="stopspam")
@only_owner()
async def stopspam(ctx):
    """
    !stopspam
    Stops spam loop for current channel.
    """
    if ctx.channel.id not in spam_task:
        return await ctx.send("❌ Spam loop not running.")

    spam_task[ctx.channel.id].cancel()
    spam_task.pop(ctx.channel.id, None)

    await ctx.send("🛑 Spam loop stopped.")

@bot.command(name="chname")
@only_owner()
async def chname(ctx, *, text: str):
    """
    !chname <text>
    Start channel rename loop: renames channel repeatedly as "{text}-{raid_text}".
    Uses safe 60-second delay between renames.
    Requires Manage Channels permission.
    """
    if not isinstance(ctx.channel, discord.TextChannel):
        return await ctx.send("❌ Use inside text channel.")

    # Cancel existing chname task in this channel
    if ctx.channel.id in chname_task:
        chname_task[ctx.channel.id].cancel()

    # Start new chname loop
    try:
        task = asyncio.create_task(chname_loop(ctx.channel, text))
        chname_task[ctx.channel.id] = task
        await ctx.send(f"✅ Channel rename loop started — renaming as `{text}-<raid_text>`")
    except discord.Forbidden:
        await ctx.send("❌ Missing Manage Channels permission.")

@bot.command(name="stopchname")
@only_owner()
async def stopchname(ctx):
    """
    !stopchname
    Stops channel rename loop for current channel.
    """
    if ctx.channel.id not in chname_task:
        return await ctx.send("❌ Channel rename loop not running.")

    chname_task[ctx.channel.id].cancel()
    chname_task.pop(ctx.channel.id, None)

    await ctx.send("🛑 Channel rename loop stopped.")

# =========================
# RUN
# =========================
if __name__ == "__main__":
    bot.run(TOKEN)
