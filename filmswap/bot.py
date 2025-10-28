from __future__ import annotations
from logzero import logger  # type: ignore[import]

import os
import asyncio
import discord
from discord.ext import commands
from gettext import gettext as _

from .db import (
    Swap,
    SwapPeriod,
    check_active_user,
    set_letterboxd,
    review_my_gift_embed,
    review_my_letter_embed,
    receive_gift_embed,
    get_santa,
    get_giftee,
    read_giftee_letter,
    set_gift,
    user_has_letter,
    has_set_gift,
    set_gift_done,
    backup_all_letters,
    set_letter,
    leave_swap,
    has_giftee,
)
from .settings import settings, Environment
from .manage import Manage, JoinSwapButton, update_usernames
from ._types import ClientT

MSG_DESCRIPTION_LIMIT = 4000


def help_embed() -> discord.Embed:
    embed = discord.Embed(title="Help", description=_("Filmswap Help"))
    embed.add_field(
        name=">letter",
        value=_(
            "Set your letter, which your Santa will see. This should include what kinds of films you like/dislike, and can include your accounts on letterboxd/imdb if you have one."
        ),
        inline=False,
    )
    embed.add_field(
        name=">submit",
        value=_("Submit your gift/film-recommendation to your giftee"),
        inline=False,
    )
    embed.add_field(
        name="/read",
        value="Read your letter from your giftee. After you picked something, >submit",
        inline=False,
    )
    # fmt: off
    embed.add_field(
        name="/receive",
        value=_("Read your gift from your Santa. After you've finished watching, /done-watching"),
        inline=False,
    )
    # fmt: on
    embed.add_field(
        name="/review-letter",
        value="Review your current letter",
        inline=True,
    )
    embed.add_field(
        name="/review-gift",
        value="Review the gift you submitted",
        inline=True,
    )
    embed.add_field(
        name=">write-santa",
        value="Write an anonymous message to your Santa",
        inline=True,
    )
    embed.add_field(
        name=">write-giftee",
        value="Write an anonymous message to your giftee",
        inline=True,
    )
    embed.add_field(
        name=_("/done-watching"),
        value=_("Mark your gift as watched"),
        inline=True,
    )
    embed.add_field(
        name=_("/letterboxd"),
        value=_("Set your letterboxd account (this is optional)"),
        inline=True,
    )
    embed.add_field(
        name="/help",
        value="Show this help message",
        inline=True,
    )
    embed.add_field(
        name="/leave",
        value=_("Leave the filmswap, if you're currently in it"),
        inline=True,
    )
    return embed


async def background_tasks(bot: discord.Client) -> None:
    while True:
        gld = bot.get_guild(settings.GUILD_ID)
        if gld is None:
            logger.warning(
                f"Cannot fetch guild with ID {settings.GUILD_ID}, cannot update usernames",
            )
            return
        await update_usernames(gld)
        await asyncio.sleep(60 * 60 * 24)


def create_bot() -> discord.Client:
    intents = discord.Intents.default()
    intents.members = True

    activity = None
    if settings.PRESENCE_TYPE.strip() and settings.PRESENCE_STATUS.strip():
        try:
            act_type = getattr(discord.ActivityType, settings.PRESENCE_TYPE)
        except AttributeError:
            logger.error(
                f"Invalid presence type {settings.PRESENCE_TYPE}, options:{list(discord.ActivityType.__members__)}"
            )
            raise SystemExit(1)

        activity = discord.Activity(type=act_type, name=settings.PRESENCE_STATUS)
    bot = commands.Bot(
        command_prefix=commands.when_mentioned, intents=intents, activity=activity
    )

    async def error_if_not_in_dm(ctx: discord.Interaction[ClientT] | commands.Context) -> bool:  # type: ignore[type-arg]
        if isinstance(ctx, commands.Context):
            if ctx.guild is not None:
                await ctx.author.send(
                    "Hey, that command only works in DMs -- try using it here instead"
                )
                logger.info(
                    f"User {ctx.author.id} {ctx.author.display_name} used command in guild, sending them a DM"
                )
                return True
        else:
            assert isinstance(ctx, discord.Interaction)
            if ctx.guild is not None:
                await ctx.response.send_message(
                    "This command only works in DMs -- try direct messaging this bot instead",
                    ephemeral=True,
                )
                logger.info(
                    f"User {ctx.user.id} {ctx.user.display_name} used command in guild, telling them to use in DM instead"
                )
                return True
        return False

    async def not_active_user(ctx: discord.Interaction[ClientT] | commands.Context) -> bool:  # type: ignore[type-arg]
        """
        returns True if user is not active, False if user is active
        """
        if isinstance(ctx, commands.Context):
            if error := check_active_user(ctx.author.id):
                await ctx.reply(error)
                return True
        else:
            assert isinstance(ctx, discord.Interaction)
            if error := check_active_user(ctx.user.id):
                await ctx.response.send_message(error, ephemeral=True)
                return True
        return False

    @bot.tree.command(name="review-letter", description="Review your letter")  # type: ignore[arg-type]
    async def review_letter(interaction: discord.Interaction[ClientT]) -> None:
        logger.info(
            f"User {interaction.user.id} {interaction.user.name} reviewing their own letter"
        )

        if await error_if_not_in_dm(interaction):
            return

        if await not_active_user(interaction):
            return

        embed = review_my_letter_embed(interaction.user.id)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(  # type: ignore[arg-type]
        name="letter-help",
        description="Write the letter your santa will see. Use >letter [text] instead",
    )
    async def letter_help(interaction: discord.Interaction[ClientT]) -> None:
        logger.info(
            f"User {interaction.user.id} {interaction.user.display_name} used letter"
        )

        if await error_if_not_in_dm(interaction):
            return

        if await not_active_user(interaction):
            return

        await interaction.response.send_message(
            # fmt: off
            _("Use `>letter [text]` to set your letter, where [text] is what kinds of films you like/dislike/want from your santa. If you have a a letterboxd/imdb you can include that as well"),
            # fmt: on
            ephemeral=True,
        )

    @bot.tree.command(  # type: ignore[arg-type]
        name="write-santa-help",
        description="Write an anonymous message to your santa. Use >write-santa [text] instead",
    )
    async def write_santa_help(interaction: discord.Interaction[ClientT]) -> None:
        logger.info(
            f"User {interaction.user.id} {interaction.user.display_name} used write-santa"
        )

        if await error_if_not_in_dm(interaction):
            return

        if await not_active_user(interaction):
            return

        await interaction.response.send_message(
            "Use `>write-santa [text]` to send an anonymous message, where [text] is what you want to say to your santa",
            ephemeral=True,
        )

    @bot.tree.command(  # type: ignore[arg-type]
        name="write-giftee-help",
        description="Write an anonymous message to your giftee. Use >write-giftee [text] instead",
    )
    async def write_giftee_help(interaction: discord.Interaction[ClientT]) -> None:
        logger.info(
            f"User {interaction.user.id} {interaction.user.display_name} used write-giftee"
        )

        if await error_if_not_in_dm(interaction):
            return

        if await not_active_user(interaction):
            return

        await interaction.response.send_message(
            "Use `>write-giftee [text]` to send an anonymous message, where [text] is what you want to say to your giftee",
            ephemeral=True,
        )

    @bot.tree.command(name="review-gift", description="Review your gift")  # type: ignore[arg-type]
    async def review_gift(interaction: discord.Interaction[ClientT]) -> None:
        logger.info(
            f"User {interaction.user.id} {interaction.user.display_name} viewing their own gift (the one they submitted)"
        )

        if await error_if_not_in_dm(interaction):
            return

        if await not_active_user(interaction):
            return

        embed = review_my_gift_embed(interaction.user.id)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(  # type: ignore[arg-type]
        name="submit-help",
        description="Submit gift for your giftee (your recommendation). Use >submit instead",
    )
    async def submit_help(interaction: discord.Interaction[ClientT]) -> None:
        logger.info(
            f"User {interaction.user.id} {interaction.user.display_name} submitting gift"
        )

        if await error_if_not_in_dm(interaction):
            return

        if await not_active_user(interaction):
            return

        # prompt the user to set their gift
        await interaction.response.send_message(
            _(
                "Use `>submit [text]` to submit your gift, where [text] is your gift/film recommendation"
            )
        )

    @bot.tree.command(name="receive", description="Read the gift from your Santa")  # type: ignore[arg-type]
    async def receive(interaction: discord.Interaction[ClientT]) -> None:
        logger.info(
            f"User {interaction.user.id} {interaction.user.display_name} used receive"
        )

        if await error_if_not_in_dm(interaction):
            return

        if await not_active_user(interaction):
            return

        gift = receive_gift_embed(interaction.user.id)
        await interaction.response.send_message(embed=gift, ephemeral=True)

    @bot.tree.command(name="read", description="Read the letter from your giftee")  # type: ignore[arg-type]
    async def read(interaction: discord.Interaction[ClientT]) -> None:
        logger.info(
            f"User {interaction.user.id} {interaction.user.display_name} used read"
        )

        if await error_if_not_in_dm(interaction):
            return

        if await not_active_user(interaction):
            return

        letter = read_giftee_letter(interaction.user.id)
        await interaction.response.send_message(embed=letter, ephemeral=True)

    @bot.tree.command(name="leave", description=_("Leave the film swap"))  # type: ignore[arg-type]
    async def leave(interaction: discord.Interaction[ClientT]) -> None:
        logger.info(
            f"User {interaction.user.id} {interaction.user.display_name} used leave"
        )

        # if user uses this in dm, tell them to use it in the server instead
        if interaction.guild is None:
            await interaction.response.send_message(
                _(
                    "Please use this command in the server (e.g. in the film-swap channel) instead of in DMs"
                ),
                ephemeral=True,
            )
            return

        if await not_active_user(interaction):
            return

        if Swap.get_swap_period() != SwapPeriod.JOIN:
            logger.info(
                f"User {interaction.user.id} {interaction.user.display_name} tried to leave the swap but it's not the JOIN period"
            )
            await interaction.response.send_message(
                "Sorry, you can't leave the swap right now. Wait till the beginning of the next swap period to leave",
                ephemeral=True,
            )
            return

        try:
            leave_swap(interaction.user.id)
        except RuntimeError as e:
            return await interaction.response.send_message(
                f"Error: {e}", ephemeral=True
            )

        await interaction.response.send_message(
            "You have left the swap. You can rejoin by clicking the 'join button' in the swap channel",
            ephemeral=True,
        )

    @bot.tree.command(name=_("done-watching"), description=_("Mark your gift as watched"))  # type: ignore[arg-type]
    async def done_watching(interaction: discord.Interaction[ClientT]) -> None:
        logger.info(
            f"User {interaction.user.id} {interaction.user.display_name} used done-watching"
        )

        if await error_if_not_in_dm(interaction):
            return

        if await not_active_user(interaction):
            return

        if Swap.get_swap_period() == SwapPeriod.JOIN:
            logger.info(
                f"User {interaction.user.id} {interaction.user.display_name} tried to mark their gift as watched during the JOIN period"
            )
            await interaction.response.send_message(
                # fmt: off
                _("Can't set your gift as watched right now. Wait till the swap begins"),
                # fmt: on
                ephemeral=True,
            )
            return

        try:
            set_gift_done(interaction.user.id)
        except RuntimeError as e:
            return await interaction.response.send_message(
                f"Error: {e}", ephemeral=True
            )

        await interaction.response.send_message(
            _("Your gift has been marked as watched"), ephemeral=True
        )

    @bot.tree.command(name=_("letterboxd"), description=_("Set your letterboxd username"))  # type: ignore[arg-type]
    async def letterboxd(
        interaction: discord.Interaction[ClientT], username: str
    ) -> None:
        logger.info(
            f"User {interaction.user.id} {interaction.user.display_name} used letterboxd"
        )

        if await error_if_not_in_dm(interaction):
            return

        if await not_active_user(interaction):
            return

        try:
            set_letterboxd(interaction.user.id, username)
        except RuntimeError as e:
            return await interaction.response.send_message(
                f"Error: {e}", ephemeral=True
            )

        await interaction.response.send_message(
            _("Your letterboxd username has been set to {username}").format(
                username=username
            ),
            ephemeral=True,
        )

    @bot.event
    async def on_command_error(ctx: commands.Context, error: Exception) -> None:  # type: ignore[type-arg]
        logger.exception(f"Error: {error}", exc_info=True)

    @bot.event
    async def on_message(message: discord.Message) -> None:
        # bot is using tree commands, not the discord commands extension, so I dont think this is needed
        # await bot.process_commands(message)

        # these commands only work in DMs, so users can write out long paragraphs
        if (
            message.guild is not None
            or message.author.bot
            or message.author == bot.user
        ):
            return

        content = message.content.strip()
        if content.startswith(">letter"):
            logger.info(f"User {message.author.id} setting letter")

            if error := check_active_user(message.author.id):
                await message.author.send(error)
                return

            if Swap.get_swap_period() != SwapPeriod.JOIN:
                logger.info(
                    f"User {message.author.id} tried to set letter but it's not the JOIN period"
                )

                if user_has_letter(message.author.id):
                    # already has letter, check if they are allowed to change it right now
                    await message.author.send(
                        "Sorry, you can't change your letter right now. Wait till the beginning of the next swap to change it.\nIf you want to review your letter, you can use `/review-letter`",
                    )
                    return

            letter_contents = content[len(">letter") :].strip()

            if not letter_contents:
                logger.info(
                    f"User {message.author.id} tried to set letter but didn't provide any text"
                )
                await message.author.send(
                    _(
                        "Use `>letter [text]` to set your letter, where [text] is what kinds of films you like/dislike/want from your santa. If you have a letterboxd/imdb you can include that as well"
                    ),
                )
                return

            logger.info(f"User {message.author.id} setting letter to {letter_contents}")

            try:
                set_letter(message.author.id, letter_contents)
            except AssertionError:
                await message.author.send(
                    f"Sorry, your letter is too long. It must be less than {MSG_DESCRIPTION_LIMIT} characters (it is currently {len(letter_contents)} characters)"
                )
                return
            await message.reply("Your letter has been set, your santa will see:")
            await message.reply(embed=review_my_letter_embed(message.author.id))
        elif content.startswith(">submit"):
            logger.info(f"User {message.author.id} setting gift")

            if error := check_active_user(message.author.id):
                await message.author.send(error)
                return

            if not has_giftee(message.author.id):
                logger.info(
                    f"User {message.author.id} tried to set gift but they don't have a giftee"
                )
                await message.author.send(
                    "Sorry, you can't set your gift until you've been assigned a giftee",
                )
                return

            current_period = Swap.get_swap_period()
            if current_period == SwapPeriod.JOIN:
                logger.info(
                    f"User {message.author.id} tried to set gift but its currently JOIN period"
                )
                # already has gift, check if they are allowed to change it right now
                await message.author.send(
                    "Sorry, you can't change your gift right now. Wait till the next 'swap' period starts to set your gift",
                )
                return

            assert (
                current_period == SwapPeriod.SWAP or current_period == SwapPeriod.WATCH
            )
            # check if they've already submitted a gift this swap
            # we should not allow people who have already submitted to change during the swap period,
            # but if they haven't submitted yet, they can submit at any time (to allow latecomers to join later)
            if current_period == SwapPeriod.WATCH and has_set_gift(message.author.id):
                logger.info(
                    f"User {message.author.id} tried to set gift but the WATCH period has already started, and they've already set a gift"
                )
                # already has gift, check if they are allowed to change it right now
                await message.author.send(
                    "Sorry, you can't change your gift right now. If you need to communicate with your giftee, you can use >write-giftee to send them a message.\nIf you want to review the gift you sent, use `/review-gift`",
                )
                return

            # this is only possible if its the swap period, or if its the watch period and they haven't set a gift yet
            # that couldve happened if a user was banned, or they forgot to set it but >write-giftee'd their giftee
            gift_contents = content[len(">submit") :].strip()

            if not gift_contents:
                logger.info(
                    f"User {message.author.id} tried to set gift but didn't provide any text"
                )
                await message.author.send(
                    _(
                        "Use `>submit [text]` to submit your gift, where [text] is your gift/film recommendation"
                    ),
                )
                return

            logger.info(f"User {message.author.id} setting gift to {gift_contents}")

            try:
                set_gift(message.author.id, gift_contents)
            except AssertionError:
                await message.author.send(
                    f"Sorry, your gift is too long. It must be less than {MSG_DESCRIPTION_LIMIT} characters (it is currently {len(gift_contents)} characters)"
                )
                return
            await message.reply(
                "Your gift has been set, when the watch period starts your giftee will see:"
            )
            await message.reply(embed=review_my_gift_embed(message.author.id))
            await message.reply(
                "Since you can change your gift by running /submit again before the SWAP period ends, your giftee does not receive their gift immediately.\nIf you're confident in your gift or want to send it early, you can also use >write-giftee to send it to your giftee early"
            )

        elif content.startswith(">write-santa"):
            logger.info(f"User {message.author.id} sending message to santa")

            if error := check_active_user(message.author.id):
                await message.author.send(error)
                return

            santa = get_santa(message.author.id)

            if santa is None:
                logger.info(
                    f"User {message.author.id} tried to send message to santa but they don't have a santa"
                )
                await message.author.send(
                    "You can only send a message to your santa after you've been assigned one"
                )
                return

            message_contents = content[len(">write-santa") :].strip()

            if not message_contents:
                logger.info(
                    f"User {message.author.id} tried to send message to santa but didn't provide any text"
                )
                await message.author.send(
                    "Use >write-santa [text] to send a message to your santa, where [text] is your message"
                )
                return

            if len(message_contents) > MSG_DESCRIPTION_LIMIT:
                logger.info(
                    f"User {message.author.id} tried to send message to santa but their message was too long"
                )
                await message.author.send(
                    f"Sorry, your message is too long. It must be less than {MSG_DESCRIPTION_LIMIT} characters (it is currently {len(message_contents)} characters)"
                )
                return

            assert santa is not None

            try:
                santa_user = await bot.fetch_user(santa.user_id)
            except Exception:
                logger.info(
                    f"User {message.author.id} tried to send message to santa but their santa's ID {santa.user_id} is invalid"
                )
                await message.author.send(
                    "There was an error messaging your santa, could not associate their ID with a discord account."
                )
                return
            else:
                logger.info(
                    f"User {message.author.id} {message.author.display_name} sending message to santa {santa.user_id} {santa.name} {message_contents}"
                )
                embed = discord.Embed(
                    title="Your giftee sent you a message", description=message_contents
                )
                embed.set_footer(text="To reply, use >write-giftee [text]")
                await santa_user.send(embed=embed)

                await message.author.send("Your message has been sent")

        elif content.startswith(">write-giftee"):
            logger.info(f"User {message.author.id} sending message to giftee")

            if error := check_active_user(message.author.id):
                await message.author.send(error)
                return

            giftee = get_giftee(message.author.id)

            if giftee is None:
                logger.info(
                    f"User {message.author.id} tried to send message to giftee but they don't have a giftee"
                )
                await message.author.send(
                    "You can only send a message to your giftee after you've been assigned one"
                )
                return

            message_contents = content[len(">write-giftee") :].strip()

            if not message_contents:
                logger.info(
                    f"User {message.author.id} tried to send message to giftee but didn't provide any text"
                )
                await message.author.send(
                    "Use >write-giftee [text] to send a message to your giftee, where [text] is your message"
                )
                return

            if len(message_contents) > MSG_DESCRIPTION_LIMIT:
                logger.info(
                    f"User {message.author.id} tried to send message to giftee but their message was too long"
                )
                await message.author.send(
                    f"Sorry, your message is too long. It must be less than {MSG_DESCRIPTION_LIMIT} characters (it is currently {len(message_contents)} characters)"
                )
                return

            assert giftee is not None
            try:
                giftee_user = await bot.fetch_user(giftee.user_id)
            except Exception:
                logger.info(
                    f"User {message.author.id} tried to send message to giftee but their giftee's ID {giftee.user_id} is invalid"
                )
                await message.author.send(
                    "There was an error messaging your giftee, could not associate their ID with a discord account."
                )
                return
            else:
                logger.info(
                    f"User {message.author.id} {message.author.display_name} sending message to giftee {giftee.user_id} {giftee.name} {message_contents}"
                )
                embed = discord.Embed(
                    title="Your santa sent you a message", description=message_contents
                )
                embed.set_footer(text="To reply, use >write-santa [text]")
                await giftee_user.send(embed=embed)
                await message.author.send("Your message has been sent")
        elif content.startswith(">"):
            logger.info(
                f"User {message.author.id} {message.author.display_name} sent unknown command {content}"
            )
            await message.author.send(
                "Unknown command. Use `/help` to see a list of commands"
            )

    @bot.tree.command()  # type: ignore[arg-type]
    async def help(interaction: discord.Interaction[ClientT]) -> None:
        logger.info(
            f"User {interaction.user.id} {interaction.user.display_name} requested help"
        )
        await interaction.response.send_message(embed=help_embed(), ephemeral=True)

    @bot.event
    async def setup_hook() -> None:
        logger.info("Setting up persistent join button")
        latest_swap_msg_id = Swap.get_join_button_message_id()
        if latest_swap_msg_id is None:
            logger.info("No join button message ID found")
        else:
            logger.info(f"Found saved button message ID: {latest_swap_msg_id}")
        join_view = JoinSwapButton()
        join_view._bot = bot  # type: ignore
        bot.add_view(join_view, message_id=latest_swap_msg_id)

    @bot.event
    async def on_ready() -> None:
        logger.info(f"Logged in as {bot.user}")
        logger.info(
            f"Period post hook is {'enabled' if settings.PERIOD_POST_HOOK else 'disabled'}"
        )
        if settings.GUILD_ID == -1:
            logger.warning("No guild ID specified, cannot register commands")
            return
        guild = bot.get_guild(settings.GUILD_ID)
        if guild is None:
            logger.warning(
                f"Cannot find guild with ID {settings.GUILD_ID}, cannot register commands",
            )
            return

        manager = Manage(name=_("filmswap-manage"), description="Manage swaps")
        manager._bot = bot  # type: ignore

        os.makedirs(settings.BACKUP_DIR, exist_ok=True)

        bot.tree.add_command(manager)
        if settings.ENVIRONMENT == Environment.DEVELOPMENT:
            logger.info("Syncing dev commands")
            bot.tree.copy_global_to(guild=discord.Object(id=settings.GUILD_ID))
            await bot.tree.sync(guild=discord.Object(id=settings.GUILD_ID))

        # change bot username on boot up
        assert bot.user is not None, "Bot user is None while booting up!"
        await bot.user.edit(username=settings.BOT_NAME)

        await bot.tree.sync()

        backup_all_letters()
        logger.info("Starting background tasks...")
        bot.loop.create_task(background_tasks(bot))

    return bot
