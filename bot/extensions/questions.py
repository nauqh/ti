import hikari
import lightbulb
from ..agent import DataScienceAssistant
from loguru import logger

QUESTION_CENTERS = {
    "DS": {"forum_id": 1081063200377806899, "ta_id": 1194665960376901773},
    "FSW": {"forum_id": 1077118780523679787, "ta_id": 912553106124972083},
    "MOENASH": {"forum_id": 1195747557335375907, "ta_id": 947046042656981022},
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
        if thread.parent_id not in [guild["forum_id"] for guild in QUESTION_CENTERS.values()]:
            return
        if len(await thread.fetch_history()) <= 1:
            return
        if (
            len(
                [
                    message
                    for message in await thread.fetch_history()
                    if message.author.id == 1316322317889962014
                ]
            )
            >= 2
        ):
            logger.info(f"2 responses found, stop follow-up {thread.name}")
            return

        bot = plugin.app.d.bot

        response, citations = bot.continue_conversation(message.content)
        await thread.send(response)

        if citations:
            logger.info(f"Referenced files: {', '.join(citations)}")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
