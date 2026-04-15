# =========================================================
# DISCORD NC KYAMI — PRODUCTION-GRADE BOT
# =========================================================

import discord
from discord.ext import commands
import asyncio
import logging
import os
import json
import random
from typing import Dict, List, Optional
from pathlib import Path

# =========================
# CONFIGURATION
# =========================

# Environment variables with fallbacks
DISCORD_TOKENS = os.getenv("DISCORD_TOKENS", "MTQ2NjA5NDkyMjk4NDU5MTQ4NQ.GSzz6t.T7EMJivmVkjQpTAKqv2Kzdka8d6tRjPkgd9PL4,MTQ3MDQyNjE0OTMxMzE4Mzc1NQ.GwMVw5.wTFOxSwVSY3xZM7nCGuXLzNvVagck2AiEuIFb8").split(",") if os.getenv("DISCORD_TOKENS") else ["MTQ2NjA5NDkyMjk4NDU5MTQ4NQ.GSzz6t.T7EMJivmVkjQpTAKqv2Kzdka8d6tRjPkgd9PL4", "MTQ3MDQyNjE0OTMxMzE4Mzc1NQ.GwMVw5.wTFOxSwVSY3xZM7nCGuXLzNvVagck2AiEuIFb8"]
DEFAULT_DELAY = float(os.getenv("DEFAULT_DELAY", "0.5"))
OWNER_ID = int(os.getenv("OWNER_ID", "1069460715020222514"))  # Your user ID
SUDO_FILE = Path("sudo_users.json")

# Constants
RAID_TEXTS = [
    "×~🌷1🌷×~", "~×🌼2🌼×~", "××🌻3🌻××", "~~🌺4🌺~~", "~×🌹5🌹×~",
    "×~🏵️6🏵️×~", "~×🪷7🪷×~", "××💮8💮××", "~~🌸9🌸~~", "~×🌷10🌷×~",
]

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('discord_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =========================
# UTILITY FUNCTIONS
# =========================

def load_sudo_users() -> List[int]:
    """Safely load sudo users from JSON file."""
    if not SUDO_FILE.exists():
        return []
    try:
        with open(SUDO_FILE, 'r') as f:
            data = json.load(f)
            return [int(uid) for uid in data if isinstance(uid, (str, int))]
    except (json.JSONDecodeError, ValueError, FileNotFoundError) as e:
        logger.error(f"Failed to load sudo users: {e}")
        return []

def save_sudo_users(users: List[int]) -> None:
    """Safely save sudo users to JSON file."""
    temp_file = SUDO_FILE.with_suffix('.tmp')
    try:
        with open(temp_file, 'w') as f:
            json.dump(users, f, indent=2)
        temp_file.replace(SUDO_FILE)
    except Exception as e:
        logger.error(f"Failed to save sudo users: {e}")
        if temp_file.exists():
            temp_file.unlink()

def parse_user_id(user_str: str) -> Optional[int]:
    """Parse user ID from mention or plain ID."""
    user_str = user_str.strip()
    if user_str.startswith('<@') and user_str.endswith('>'):
        user_str = user_str[2:-1]
        if user_str.startswith('!'):
            user_str = user_str[1:]
    try:
        return int(user_str)
    except ValueError:
        return None

def get_random_delay(base_delay: float) -> float:
    """Add random jitter to delay to avoid detection."""
    jitter = random.uniform(-0.1, 0.1)
    return max(0.5, base_delay + jitter)

# =========================
# BOT INSTANCE CLASS
# =========================

class BotInstance:
    """Individual bot instance with isolated state."""

    def __init__(self, token: str, instance_id: int):
        self.token = token
        self.instance_id = instance_id
        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(
            command_prefix="!",
            intents=intents,
            help_command=None
        )
        self.delay = DEFAULT_DELAY
        self.nc_channels: Dict[int, List[int]] = {}  # guild_id -> channel_ids
        self.nc_index: Dict[int, int] = {}  # guild_id -> current index
        self.nc_task: Dict[int, asyncio.Task] = {}  # guild_id -> task
        self.spam_task: Dict[int, asyncio.Task] = {}  # channel_id -> task
        self.chname_task: Dict[int, asyncio.Task] = {}  # channel_id -> task
        self.command_cooldowns: Dict[str, float] = {}  # command -> last_used

        # Setup events and commands
        self._setup_events()
        self._setup_commands()

    def _setup_events(self):
        @self.bot.event
        async def on_ready():
            logger.info(f"Bot #{self.instance_id} logged in as {self.bot.user} ({self.bot.user.id})")
            await self.bot.change_presence(activity=discord.Game(name=f"Bot #{self.instance_id}"))

        @self.bot.event
        async def on_command_error(ctx, error):
            if isinstance(error, commands.CheckFailure):
                await ctx.send("❌ Not authorized.")
            elif isinstance(error, commands.CommandOnCooldown):
                await ctx.send(f"❌ Command on cooldown. Try again in {error.retry_after:.1f}s.")
            else:
                logger.error(f"Command error: {error}")
                await ctx.send("❌ An error occurred.")

    def _setup_commands(self):
        # Permission checks
        def only_owner():
            async def predicate(ctx):
                return ctx.author.id == OWNER_ID
            return commands.check(predicate)

        def only_sudo():
            async def predicate(ctx):
                sudo_users = load_sudo_users()
                return ctx.author.id in sudo_users or ctx.author.id == OWNER_ID
            return commands.check(predicate)

        @self.bot.command(name="menu")
        @commands.cooldown(1, 5, commands.BucketType.user)
        async def menu(ctx):
            """Show available commands menu."""
            prefix = self.bot.command_prefix
            embed = discord.Embed(
                title="🔥 Discord NC Kyami Menu",
                description="All commands & usage below. Use responsibly!",
                color=0xff6b6b
            )

            embed.add_field(
                name="🔹 **Basic Commands**",
                value=f"""
{prefix}menu
Show this command menu
Example: {prefix}menu
""".strip(),
                inline=False
            )

            embed.add_field(
                name="🔹 **NC (Next Channel) Commands**",
                value=f"""
{prefix}setnc #ch1 #ch2
Set channels for NC rotation
Example: {prefix}setnc #general #spam

{prefix}nc <text>
Start NC loop rotating through channels
Example: {prefix}nc Hello world

{prefix}ncstop
Stop the NC loop
Example: {prefix}ncstop
""".strip(),
                inline=False
            )

            embed.add_field(
                name="🔹 **Loop Commands**",
                value=f"""
{prefix}send <text>
Start spam loop in current channel
Example: {prefix}send Spam message

{prefix}stopspam
Stop spam loop in current channel
Example: {prefix}stopspam

{prefix}chname <text>
Start channel rename loop
Example: {prefix}chname Raid

{prefix}stopchname
Stop channel rename loop
Example: {prefix}stopchname

{prefix}delay <seconds>
Set delay between loop messages (0.5-300s)
Example: {prefix}delay 0.5
""".strip(),
                inline=False
            )

            embed.add_field(
                name="🔹 **SUDO Commands**",
                value=f"""
{prefix}sudo add @user
Add user to sudo list
Example: {prefix}sudo add @friend

{prefix}sudo remove @user
Remove user from sudo list
Example: {prefix}sudo remove @friend

{prefix}sudo list
Show all sudo users
Example: {prefix}sudo list
""".strip(),
                inline=False
            )

            embed.add_field(
                name="🔹 **Utility**",
                value=f"""
{prefix}status
Show active loops and bot status
Example: {prefix}status
""".strip(),
                inline=False
            )

            embed.set_footer(text="Only SUDO users can use most commands")
            await ctx.send(embed=embed)

        @self.bot.command(name="setnc")
        @commands.cooldown(1, 10, commands.BucketType.guild)
        async def setnc(ctx, *channels: discord.TextChannel):
            """Set NC channels for this guild."""
            if not ctx.guild:
                return await ctx.send("❌ Use in a server.")

            if not channels:
                return await ctx.send("❌ Usage: `!setnc #channel1 #channel2 ...`")

            # Validate channels
            valid_channels = []
            invalid_channels = []
            for channel in channels:
                if not isinstance(channel, discord.TextChannel):
                    invalid_channels.append(str(channel))
                    continue
                perms = channel.permissions_for(ctx.guild.me)
                if not perms.send_messages:
                    invalid_channels.append(f"{channel.mention} (no send permission)")
                    continue
                valid_channels.append(channel.id)

            if not valid_channels:
                return await ctx.send("❌ No valid channels provided.")

            self.nc_channels[ctx.guild.id] = valid_channels
            self.nc_index[ctx.guild.id] = 0

            mentions = [f"<#{cid}>" for cid in valid_channels]
            response = f"✅ NC channels set: {', '.join(mentions)}"
            if invalid_channels:
                response += f"\n⚠️ Invalid channels: {', '.join(invalid_channels)}"
            await ctx.send(response)

        @self.bot.command(name="nc")
        @commands.cooldown(1, 30, commands.BucketType.guild)
        async def nc(ctx, *, text: str = "NC"):
            """Start NC loop."""
            if not ctx.guild:
                return await ctx.send("❌ Use in a server.")

            channels = self.nc_channels.get(ctx.guild.id)
            if not channels:
                return await ctx.send("❌ Set channels first: `!setnc #channel1 #channel2`")

            # Cancel existing task
            if ctx.guild.id in self.nc_task:
                self.nc_task[ctx.guild.id].cancel()
                try:
                    await self.nc_task[ctx.guild.id]
                except asyncio.CancelledError:
                    pass

            # Start new task
            task = asyncio.create_task(self._nc_loop(ctx.guild.id, text))
            self.nc_task[ctx.guild.id] = task

            mentions = [f"<#{cid}>" for cid in channels]
            await ctx.send(f"✅ NC loop started — rotating: {', '.join(mentions)}")

        @self.bot.command(name="ncstop")
        async def ncstop(ctx):
            """Stop NC loop."""
            if not ctx.guild:
                return await ctx.send("❌ Use in a server.")

            if ctx.guild.id not in self.nc_task:
                return await ctx.send("❌ NC loop not running.")

            self.nc_task[ctx.guild.id].cancel()
            try:
                await self.nc_task[ctx.guild.id]
            except asyncio.CancelledError:
                pass
            del self.nc_task[ctx.guild.id]
            await ctx.send("🛑 NC loop stopped.")

        @self.bot.command(name="send")
        @commands.cooldown(1, 30, commands.BucketType.channel)
        async def send(ctx, *, text: str):
            """Start spam loop."""
            if not isinstance(ctx.channel, discord.TextChannel):
                return await ctx.send("❌ Use in a text channel.")

            perms = ctx.channel.permissions_for(ctx.guild.me)
            if not perms.send_messages:
                return await ctx.send("❌ No permission to send messages.")

            # Cancel existing task
            if ctx.channel.id in self.spam_task:
                self.spam_task[ctx.channel.id].cancel()
                try:
                    await self.spam_task[ctx.channel.id]
                except asyncio.CancelledError:
                    pass

            # Start new task
            task = asyncio.create_task(self._spam_loop(ctx.channel, text))
            self.spam_task[ctx.channel.id] = task
            await ctx.send(f"✅ Spam loop started in {ctx.channel.mention}")

        @self.bot.command(name="stopspam")
        async def stopspam(ctx):
            """Stop spam loop."""
            if ctx.channel.id not in self.spam_task:
                return await ctx.send("❌ Spam loop not running.")

            self.spam_task[ctx.channel.id].cancel()
            try:
                await self.spam_task[ctx.channel.id]
            except asyncio.CancelledError:
                pass
            del self.spam_task[ctx.channel.id]
            await ctx.send("🛑 Spam loop stopped.")

        @self.bot.command(name="chname")
        @commands.cooldown(1, 60, commands.BucketType.channel)
        async def chname(ctx, *, text: str):
            """Start channel rename loop."""
            if not isinstance(ctx.channel, discord.TextChannel):
                return await ctx.send("❌ Use in a text channel.")

            perms = ctx.channel.permissions_for(ctx.guild.me)
            if not perms.manage_channels:
                return await ctx.send("❌ No permission to manage channels.")

            # Cancel existing task
            if ctx.channel.id in self.chname_task:
                self.chname_task[ctx.channel.id].cancel()
                try:
                    await self.chname_task[ctx.channel.id]
                except asyncio.CancelledError:
                    pass

            # Start new task
            task = asyncio.create_task(self._chname_loop(ctx.channel, text))
            self.chname_task[ctx.channel.id] = task
            await ctx.send(f"✅ Channel rename loop started — renaming as `{text}-<raid_text>`")

        @self.bot.command(name="stopchname")
        async def stopchname(ctx):
            """Stop channel rename loop."""
            if ctx.channel.id not in self.chname_task:
                return await ctx.send("❌ Channel rename loop not running.")

            self.chname_task[ctx.channel.id].cancel()
            try:
                await self.chname_task[ctx.channel.id]
            except asyncio.CancelledError:
                pass
            del self.chname_task[ctx.channel.id]
            await ctx.send("🛑 Channel rename loop stopped.")

        @self.bot.command(name="delay")
        async def delay(ctx, seconds: float):
            """Set loop delay."""
            if seconds < 0.5:
                return await ctx.send("❌ Minimum delay is 0.5 seconds.")
            if seconds > 300.0:
                return await ctx.send("❌ Maximum delay is 300 seconds.")

            self.delay = seconds
            await ctx.send(f"✅ Loop delay set to {seconds} seconds.")

        @self.bot.command(name="status")
        async def status(ctx):
            """Show bot status."""
            embed = discord.Embed(title=f"🤖 Bot #{self.instance_id} Status", color=0x00ff00)

            # NC loops
            nc_info = []
            for guild_id, task in self.nc_task.items():
                if not task.done():
                    channels = self.nc_channels.get(guild_id, [])
                    mentions = [f"<#{cid}>" for cid in channels]
                    nc_info.append(f"Guild {guild_id}: {', '.join(mentions)}")
            embed.add_field(
                name="🔄 Active NC Loops",
                value="\n".join(nc_info) if nc_info else "None",
                inline=False
            )

            # Spam loops
            spam_info = []
            for channel_id, task in self.spam_task.items():
                if not task.done():
                    spam_info.append(f"<#{channel_id}>")
            embed.add_field(
                name="💬 Active Spam Loops",
                value="\n".join(spam_info) if spam_info else "None",
                inline=False
            )

            # Channel rename loops
            chname_info = []
            for channel_id, task in self.chname_task.items():
                if not task.done():
                    chname_info.append(f"<#{channel_id}>")
            embed.add_field(
                name="📝 Active Rename Loops",
                value="\n".join(chname_info) if chname_info else "None",
                inline=False
            )

            embed.add_field(name="⏱️ Current Delay", value=f"{self.delay} seconds", inline=True)
            await ctx.send(embed=embed)

        @self.bot.group(name="sudo")
        @only_owner()
        async def sudo(ctx):
            """Sudo user management."""
            if ctx.invoked_subcommand is None:
                await ctx.send("❌ Usage: `!sudo add @user` or `!sudo remove @user` or `!sudo list`")

        @sudo.command(name="add")
        async def sudo_add(ctx, user: discord.User):
            """Add sudo user."""
            sudo_users = load_sudo_users()
            if user.id in sudo_users:
                return await ctx.send("❌ User already has sudo.")
            sudo_users.append(user.id)
            save_sudo_users(sudo_users)
            await ctx.send(f"✅ Added {user.mention} to sudo users.")

        @sudo.command(name="remove")
        async def sudo_remove(ctx, user: discord.User):
            """Remove sudo user."""
            sudo_users = load_sudo_users()
            if user.id not in sudo_users:
                return await ctx.send("❌ User doesn't have sudo.")
            sudo_users.remove(user.id)
            save_sudo_users(sudo_users)
            await ctx.send(f"✅ Removed {user.mention} from sudo users.")

        @sudo.command(name="list")
        async def sudo_list(ctx):
            """List sudo users."""
            sudo_users = load_sudo_users()
            if not sudo_users:
                return await ctx.send("📝 No sudo users.")
            mentions = [f"<@{uid}>" for uid in sudo_users]
            await ctx.send(f"📝 Sudo users: {', '.join(mentions)}")

    async def _nc_loop(self, guild_id: int, text: str):
        """NC loop with proper cancellation."""
        logger.info(f"Starting NC loop for guild {guild_id}")
        i = self.nc_index.get(guild_id, 0)
        try:
            while True:
                channels = self.nc_channels.get(guild_id, [])
                if not channels:
                    break

                channel_id = channels[i % len(channels)]
                channel = self.bot.get_channel(channel_id)

                if not channel:
                    await asyncio.sleep(get_random_delay(self.delay))
                    i += 1
                    continue

                raid = RAID_TEXTS[i % len(RAID_TEXTS)]
                msg = f"{text} {raid}"

                try:
                    await channel.send(msg)
                except discord.Forbidden:
                    logger.warning(f"Forbidden to send in channel {channel_id}")
                    await asyncio.sleep(2)
                    i += 1
                    continue
                except discord.HTTPException as e:
                    if e.status == 429:
                        retry_after = getattr(e, 'retry_after', 2)
                        logger.warning(f"Rate limited, retrying after {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                    logger.error(f"HTTP error in NC loop: {e}")
                    await asyncio.sleep(2)
                    i += 1
                    continue

                i += 1
                self.nc_index[guild_id] = i
                await asyncio.sleep(get_random_delay(self.delay))

        except asyncio.CancelledError:
            logger.info(f"NC loop cancelled for guild {guild_id}")
            raise
        except Exception as e:
            logger.error(f"NC loop error for guild {guild_id}: {e}")
        finally:
            logger.info(f"NC loop stopped for guild {guild_id}")

    async def _spam_loop(self, channel: discord.TextChannel, text: str):
        """Spam loop with proper cancellation."""
        logger.info(f"Starting spam loop in channel {channel.id}")
        try:
            while True:
                spam_text = " ".join([text] * 20)
                try:
                    await channel.send(spam_text)
                except discord.Forbidden:
                    logger.warning(f"Forbidden to send in channel {channel.id}")
                    break
                except discord.HTTPException as e:
                    if e.status == 429:
                        retry_after = getattr(e, 'retry_after', 2)
                        logger.warning(f"Rate limited, retrying after {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                    logger.error(f"HTTP error in spam loop: {e}")
                    await asyncio.sleep(2)
                    continue

                await asyncio.sleep(get_random_delay(self.delay))

        except asyncio.CancelledError:
            logger.info(f"Spam loop cancelled for channel {channel.id}")
            raise
        except Exception as e:
            logger.error(f"Spam loop error for channel {channel.id}: {e}")
        finally:
            logger.info(f"Spam loop stopped for channel {channel.id}")

    async def _chname_loop(self, channel: discord.TextChannel, text: str):
        """Channel rename loop with proper cancellation."""
        logger.info(f"Starting chname loop in channel {channel.id}")
        i = 0
        try:
            while True:
                raid = RAID_TEXTS[i % len(RAID_TEXTS)]
                new_name = f"{text}-{raid}"

                try:
                    await channel.edit(name=new_name)
                except discord.Forbidden:
                    logger.warning(f"Forbidden to rename channel {channel.id}")
                    break
                except discord.HTTPException as e:
                    if e.status == 429:
                        retry_after = getattr(e, 'retry_after', 15)
                        logger.warning(f"Rate limited, retrying after {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                    logger.error(f"HTTP error in chname loop: {e}")
                    await asyncio.sleep(15)
                    continue

                i += 1
                await asyncio.sleep(15)  # Fixed delay for channel renames

        except asyncio.CancelledError:
            logger.info(f"Chname loop cancelled for channel {channel.id}")
            raise
        except Exception as e:
            logger.error(f"Chname loop error for channel {channel.id}: {e}")
        finally:
            logger.info(f"Chname loop stopped for channel {channel.id}")

    async def start(self):
        """Start the bot."""
        await self.bot.start(self.token)

    async def close(self):
        """Close the bot and cancel all tasks."""
        # Cancel all tasks
        for task in list(self.nc_task.values()):
            task.cancel()
        for task in list(self.spam_task.values()):
            task.cancel()
        for task in list(self.chname_task.values()):
            task.cancel()

        # Wait for tasks to finish
        await asyncio.gather(*self.nc_task.values(), *self.spam_task.values(), *self.chname_task.values(), return_exceptions=True)

        await self.bot.close()

# =========================
# BOT MANAGER
# =========================

class DiscordBotManager:
    """Manages multiple bot instances."""

    def __init__(self):
        self.bots: List[BotInstance] = []

    def create_bots(self):
        """Create bot instances from tokens."""
        if not DISCORD_TOKENS:
            logger.error("No DISCORD_TOKENS environment variable set!")
            return

        for i, token in enumerate(DISCORD_TOKENS, 1):
            token = token.strip()
            if token:
                bot = BotInstance(token, i)
                self.bots.append(bot)
                logger.info(f"Created bot instance #{i}")

    async def run_all(self):
        """Run all bot instances concurrently."""
        if not self.bots:
            logger.error("No bots to run!")
            return

        logger.info(f"Starting {len(self.bots)} bot instances...")

        try:
            await asyncio.gather(*[bot.start() for bot in self.bots], return_exceptions=True)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            logger.info("Shutting down bots...")
            await asyncio.gather(*[bot.close() for bot in self.bots], return_exceptions=True)
            logger.info("All bots shut down")

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    manager = DiscordBotManager()
    manager.create_bots()
    asyncio.run(manager.run_all())
