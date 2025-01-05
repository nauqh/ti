import hikari
import lightbulb
from ..agent import DataScienceAssistant
from loguru import logger

QUESTION_CENTERS = {
    "DS": {"forum_id": 1081063200377806899, "ta_id": 1194665960376901773, "staff_channel": 1237424754739253279},
    "FSW": {"forum_id": 1077118780523679787, "ta_id": 912553106124972083},
    # "MOENASH": {"forum_id": 1195747557335375907, "ta_id": 947046042656981022},
}

plugin = lightbulb.Plugin("Q&A", "🙋‍♂️ Question Center")


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)


@plugin.listener(hikari.StartingEvent)
async def on_starting(event: hikari.StartingEvent) -> None:
    bot = DataScienceAssistant()

    with open("instructions.txt", "r") as file:
        instructions = file.read()
    bot.create_vector_store(["docs/instructions.pdf", "docs/user_manual.pdf"])
    bot.create_assistant(instructions=instructions)
    plugin.app.d.bot = bot


@plugin.listener(hikari.GuildThreadCreateEvent)
async def on_thread_create(event: hikari.GuildThreadCreateEvent) -> None:
    """
    Handles the creation of a new thread in the question center and responds to the first message.
    """
    thread: hikari.GuildThreadChannel = await event.fetch_channel()

    if thread.parent_id in [guild["forum_id"] for guild in QUESTION_CENTERS.values()]:
        messages = await thread.fetch_history()
        if messages:
            message: hikari.Message = messages[0]

            images = [
                att.url
                for att in message.attachments
                if att.media_type.startswith("image")
            ]
            attachments = [
                att.url
                for att in message.attachments
                if not att.media_type.startswith("image")
            ]

            try:
                bot = plugin.app.d.bot

                ds_thread = bot.create_thread(
                    user_message=message.content,
                    image_urls=images,
                    file_paths=attachments,
                )

                # Store the Discord thread ID and the assistant thread ID
                bot.threads[thread.id] = ds_thread.id
                logger.info(f"Added thread {thread.name} to the bot's memory.")

                messages = bot.create_and_run_thread(thread=ds_thread)
                response, citations = bot.extract_response(messages)
                await thread.send(response)

                # Include citations for debugging
                if citations:
                    logger.info(f"Referenced files: {', '.join(citations)}")

            except Exception as e:
                logger.error(f"An error occurred: {e}")
    else:
        print(
            f"Thread {thread.name} does not belong to the question center category.")


@plugin.listener(hikari.GuildMessageCreateEvent)
async def on_message_create(event: hikari.GuildMessageCreateEvent) -> None:
    """
    Handles new messages in the question center thread to respond to follow-up questions.
    """
    message = event.message
    if message.author.is_bot:
        return

    try:
        thread: hikari.GuildThreadChannel = await message.fetch_channel()
        if thread.parent_id not in [
            guild["forum_id"] for guild in QUESTION_CENTERS.values()
        ]:
            return
        if len(await thread.fetch_history()) <= 1:
            return
        if (
            len(
                [
                    message
                    for message in await thread.fetch_history()
                    if message.author.id == plugin.app.get_me().id
                ]
            )
            == 1
        ):
            bot = plugin.app.d.bot
            response, citations = bot.continue_conversation(
                message.content, thread.id)
            await thread.send(response)

            if citations:
                logger.info(f"Referenced files: {', '.join(citations)}")

            message = await thread.send(
                "Thanks for your question! How would you rate my response from 1 to 5?\n Your feedback is greatly appreciated! 😊"
            )

            emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
            for emoji in emojis:
                await message.add_reaction(emoji)

        if (
            len(
                [
                    message
                    for message in await thread.fetch_history()
                    if message.author.id == plugin.app.get_me().id
                ]
            )
            >= 2
        ):
            logger.info(f"2 responses found, stop follow-up {thread.name}")
            return

        bot = plugin.app.d.bot
        response, citations = bot.continue_conversation(
            message.content, thread.id)
        await thread.send(response)

        if citations:
            logger.info(f"Referenced files: {', '.join(citations)}")

    except Exception as e:
        logger.error(f"An error occurred: {e}")


@plugin.listener(hikari.ReactionAddEvent)
async def on_reaction_add(event: hikari.ReactionAddEvent) -> None:
    if event.user_id == plugin.app.get_me().id:
        return

    if event.emoji_name in ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]:

        thread = await plugin.app.rest.fetch_channel(event.channel_id)
        score = event.emoji_name[0]
        user = await plugin.app.rest.fetch_user(event.user_id)
        thread_link = f"https://discord.com/channels/{thread.guild_id}/{thread.id}"
        logger.info(
            f"User {user.display_name} rated the response with {event.emoji_name}")
        await plugin.app.rest.create_message(
            1237424754739253279,  # DS staff-internal
            f"`{user.display_name}` rated the response with a score of {score} in thread {thread_link}"
        )
