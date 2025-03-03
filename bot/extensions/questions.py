import hikari
import lightbulb
from ..agent import Assistant
from loguru import logger
import os

QUESTION_CENTERS = {
    "DS": {"forum_id": 1081063200377806899, "ta_id": 1194665960376901773, "staff_channel": 1237424754739253279},
    "FSW": {"forum_id": 1077118780523679787, "ta_id": 912553106124972083},
    "CS50": {"forum_id": 1343930405702865037, "ta_id": 1233260164233297942},
    # "MOENASH": {"forum_id": 1344962762887004160, "ta_id": 947046253609508945},
}

plugin = lightbulb.Plugin("Q&A", "🙋‍♂️ Question Center")


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)


@plugin.listener(hikari.StartingEvent)
async def on_starting(event: hikari.StartingEvent) -> None:
    bot = Assistant(
        [f"docs/{filename}" for filename in os.listdir('docs')])
    plugin.app.d.bot = bot


async def handle_post_creation(post: hikari.GuildThreadChannel, message: hikari.Message) -> None:
    images = [
        att.url for att in message.attachments if att.media_type.startswith("image")]
    files = [
        att.url for att in message.attachments if not att.media_type.startswith("image")]

    try:
        bot = plugin.app.d.bot
        thread = bot.create_thread(
            message=message.content,
            images=images,
            files=files,
            forum_id=post.parent_id  # Pass the forum ID
        )
        bot.posts[post.id] = thread.id
        logger.info(f"Created thread for post: {post.name}")

        messages = bot.create_and_run_thread(thread)
        response, citations = bot.extract_response(messages)
        await post.send(response)

        if citations:
            logger.info(f"Referenced files: {', '.join(citations)}")

    except Exception as e:
        logger.error(f"An error occurred: {e}")


@plugin.listener(hikari.GuildThreadCreateEvent)
async def on_thread_create_cs50(event: hikari.GuildThreadCreateEvent) -> None:
    """Replicate thread creation in the CS50 forum (batch 3, 4) to clone forum"""
    thread: hikari.GuildThreadChannel = await event.fetch_channel()

    if thread.parent_id in [1318582941667819683, 1287676502196092928]:
        messages = await thread.fetch_history()
        if messages:
            message: hikari.Message = messages[0]
            logger.info(
                f"Thread created in CS50 forum: {thread.name}. Start cloning...")
            await event.app.rest.create_forum_post(
                1343930405702865037,
                thread.name,
                message.content,
                attachments=message.attachments,
                tags=[1345779561404567655]
            )


@plugin.listener(hikari.GuildThreadCreateEvent)
async def on_thread_create(event: hikari.GuildThreadCreateEvent) -> None:
    post = await event.fetch_channel()

    forum = await event.app.rest.fetch_channel(post.parent_id)
    tags = {
        tag.id: tag.name for tag in forum.available_tags
    }
    if post.parent_id in [guild["forum_id"] for guild in QUESTION_CENTERS.values()]:
        messages = await post.fetch_history()
        if messages:
            tag_name = tags.get(post.applied_tag_ids[0], "Unknown")
            logger.info(f"Thread created with tag: {tag_name}")

            if tag_name == "Code review":
                messages[0].content = "Please review the following code:\n\n" + \
                    messages[0].content

            await handle_post_creation(post, messages[0])
    else:
        print(
            f"Thread {post.name} does not belong to the question center category.")


async def handle_follow_up(post: hikari.GuildThreadChannel, message: hikari.Message) -> None:
    bot = plugin.app.d.bot
    images = [
        att.url for att in message.attachments if att.media_type.startswith("image")]
    files = [
        att.url for att in message.attachments if not att.media_type.startswith("image")]
    response, citations = bot.continue_thread(
        message.content,
        post.id,
        files=files,
        images=images
    )

    # Double check if bot is the author of the last message (server causes bot to respond twice)
    history = await post.fetch_history()
    if history and history[0].author.id == plugin.app.get_me().id:
        return
    await post.send(response)

    if citations:
        logger.info(f"Referenced files: {', '.join(citations)}")

    feedback_message = await post.send(
        f"{message.author.mention} Thanks for your question! How would you rate my response from 1 to 5?\n Your feedback is greatly appreciated! 😊"
    )

    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    for emoji in emojis:
        await feedback_message.add_reaction(emoji)


@plugin.listener(hikari.GuildMessageCreateEvent)
async def on_message_create(event: hikari.GuildMessageCreateEvent) -> None:
    message = event.message
    if message.author.is_bot:
        return

    try:
        thread: hikari.GuildThreadChannel = await message.fetch_channel()
        if thread.parent_id not in [guild["forum_id"] for guild in QUESTION_CENTERS.values()]:
            return

        for center in QUESTION_CENTERS.values():
            if center['ta_id'] in message.member.role_ids:
                logger.info(
                    f"TA message detected in {thread.name}, skipping response")
                return

        if len(await thread.fetch_history()) <= 1:
            return
        if len([msg for msg in await thread.fetch_history() if msg.author.id == plugin.app.get_me().id]) == 1:
            await handle_follow_up(thread, message)
        elif len([msg for msg in await thread.fetch_history() if msg.author.id == plugin.app.get_me().id]) >= 2:
            logger.info(f"2 responses found, stop follow-up {thread.name}")
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
