import hikari
import lightbulb
from ..agent import DataScienceAssistant
from loguru import logger
import os


plugin = lightbulb.Plugin("Q&A", "🙋‍♂️ Question Center")


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)


@plugin.listener(hikari.StartingEvent)
async def on_starting(event: hikari.StartingEvent) -> None:
    bot = DataScienceAssistant()

    with open("instructions.txt", "r") as file:
        instructions = file.read()
    bot.create_vector_store(["docs/instructions.pdf", "docs/user_manual.pdf"])
    bot.create_assistant(
        instructions=instructions
    )
    plugin.app.d.bot = bot


@plugin.listener(hikari.GuildThreadCreateEvent)
async def on_thread_create(event: hikari.GuildThreadCreateEvent) -> None:
    """
    Handles the creation of a new thread in the question center and responds to the first message.
    """
    thread: hikari.GuildThreadChannel = await event.fetch_channel()

    if thread.parent_id == int(os.environ["TEST_FORUM"]):
        messages = await thread.fetch_history()
        if messages:
            message: hikari.Message = messages[0]

            images = [
                att.url for att in message.attachments if att.media_type.startswith("image")
            ]
            attachments = [
                att.url for att in message.attachments if not att.media_type.startswith("image")
            ]

            try:
                bot = plugin.app.d.bot

                ds_thread = bot.create_thread(
                    user_message=message.content,
                    image_urls=images,
                    file_paths=attachments
                )

                messages = bot.create_and_run_thread(thread=ds_thread)
                response, citations = bot.extract_response(messages)
                await thread.send(response)

                # Include citations for debugging
                if citations:
                    citation_message = f"Referenced files: {', '.join(citations)}"
                    logger.info(citation_message)

            except Exception as e:
                await print(f"An error occurred: {e}")

    # elif thread.parent_id == int(os.environ["FORUM"]):
    #     messages = await thread.fetch_history()
    #     if messages:
    #         message: hikari.Message = messages[0]
    #     await plugin.app.rest.create_forum_post(
    #         int(os.environ["TEST_FORUM"]),
    #         thread.name,
    #         message.content,
    #         attachments=message.attachments
    #     )
    else:
        print(
            f"Thread {thread.name} does not belong to the question center category.")
