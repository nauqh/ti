import hikari
import lightbulb
import miru
import websockets
import json
import asyncio
import os
import tempfile
import base64
from dotenv import load_dotenv

load_dotenv()

plugin = lightbulb.Plugin("Submissions", include_datastore=True)


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)


class SubmissionView(miru.View):
    def __init__(self, content: dict) -> None:
        super().__init__(timeout=None)
        self.content = content

    @miru.button(label="Accept", style=hikari.ButtonStyle.SUCCESS)
    async def accept_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        try:
            await ctx.author.send(
                f"🔍 Grading assignment\n"
                f"- Exam: **{self.content['exam_name']}**\n"
                f"- Email: **{self.content['email']}**\n"
            )

            # Remove the button and update message with text
            await ctx.message.edit(
                f"{ctx.message.content}\n**Accepted by TA {ctx.author.mention}**",
                components=None
            )

            # Respond to interaction
            await ctx.respond(
                "Submission accepted successfully",
                flags=hikari.MessageFlag.EPHEMERAL
            )

        except hikari.ForbiddenError:
            await ctx.respond(
                "Could not send DM. Please check your privacy settings.",
                flags=hikari.MessageFlag.EPHEMERAL
            )


@plugin.command
@lightbulb.option("score", "Score for the exam (0-100)", type=int, min_value=0, max_value=100)
@lightbulb.command("grade", "Grade an exam submission (DM only)", guilds=[])
@lightbulb.implements(lightbulb.SlashCommand)
async def grade_command(ctx: lightbulb.Context) -> None:
    # Check if the command is being used in a DM
    channel_id = ctx.get_channel()
    channel = await ctx.app.rest.fetch_channel(channel_id)
    if channel.type != hikari.ChannelType.DM:
        await ctx.respond("This command can only be used in DMs.", flags=hikari.MessageFlag.EPHEMERAL)
        return

    # Get the command options
    score = ctx.options.score
    if not 0 <= score <= 100:
        await ctx.respond("Score must be between 0 and 100.", flags=hikari.MessageFlag.EPHEMERAL)
        return

    # Get the last message from bot to extract exam name and email
    messages = await plugin.bot.rest.fetch_messages(channel_id)

    # Find the most recent message about a grading assignment
    exam_name = None
    email = None
    already_graded = False

    for message in messages:
        # Skip messages not from the bot
        if message.author.id != plugin.bot.get_me().id:
            continue

        # Check if this exam has already been graded
        if "✅ Exam graded successfully" in message.content and "Score:" in message.content:
            # Extract the exam name using regex to check if it's the same assignment
            import re
            graded_exam_match = re.search(
                r"- Exam: \*\*(.+?)\*\*", message.content)
            if graded_exam_match:
                # Store that we've found a graded message
                already_graded = True
                break

        # Check if message has the expected format from the bot
        content = message.content
        if "Grading assignment" in content:
            # Extract exam name and email using regex
            import re
            exam_match = re.search(r"- Exam: (.+)", content)
            email_match = re.search(r"- Email: (.+)", content)

            if exam_match and email_match:
                exam_name = exam_match.group(1).strip()
                email = email_match.group(1).strip()
                break

    # Check if this assignment has already been graded
    if already_graded:
        await ctx.respond("This exam has already been graded. You can only grade each assigned exam once.", flags=hikari.MessageFlag.EPHEMERAL)
        return

    if not exam_name or not email:
        await ctx.respond("Could not find exam details in recent messages. Please make sure you have received a grading assignment message.", flags=hikari.MessageFlag.EPHEMERAL)
        return

    # Send confirmation message
    await ctx.respond(
        f"✅ Exam graded successfully!\n"
        f"- Exam: **{exam_name}**\n"
        f"- Email: **{email}**\n"
        f"- Score: **{score}/100**"
    )

    # You might want to add code here to store the grade in a database
    # or send it to your backend service
    # For example, you could create a websocket call to your backend


class HelpRequestView(miru.View):
    def __init__(self, content: dict) -> None:
        super().__init__(timeout=None)
        self.content = content

    @miru.button(label="Help", style=hikari.ButtonStyle.PRIMARY)
    async def help_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        try:
            await ctx.author.send(
                f"Help Request Details:\n"
                f"- Category: {self.content['category']}\n"
                f"- Subject: {self.content['subject']}\n"
                f"- User ID: {self.content['userId']}\n"
                f"- Description: {self.content['description']}"
            )

            await ctx.message.edit(
                f"{ctx.message.content}\n**Being helped by {ctx.author.mention}**",
                components=None
            )

            await ctx.respond(
                "Help request accepted",
                flags=hikari.MessageFlag.EPHEMERAL
            )

        except hikari.ForbiddenError:
            await ctx.respond(
                "Could not send DM. Please check your privacy settings.",
                flags=hikari.MessageFlag.EPHEMERAL
            )


async def process_base64_files(answers):
    """
    Extract base64 files from answers and convert them to temporary files
    Returns a list of file paths that need to be cleaned up later
    """
    temp_files = []
    attachments = []

    if not answers:
        return temp_files, attachments

    for i, answer in enumerate(answers, 1):
        if "files" in answer:
            for file_info in answer.get("files", []):
                if "content" in file_info and file_info["content"].startswith("data:"):
                    try:
                        # Parse content type and base64 data
                        _, content_string = file_info["content"].split(",", 1) if "," in file_info["content"] else (
                            None, file_info["content"].split(";base64,")[1])

                        # Get original filename and extract extension
                        file_name = file_info.get("name", "file")
                        suffix = os.path.splitext(
                            file_name)[1] if "." in file_name else ""

                        # Remove extension from the filename
                        base_name = os.path.splitext(file_name)[0]

                        # Create temp file with appropriate extension
                        temp_file = tempfile.NamedTemporaryFile(
                            delete=False, suffix=suffix, prefix=f"Q{i}-{base_name}-")
                        temp_file.write(base64.b64decode(content_string))
                        temp_file.close()

                        # Add to cleanup list and attachments list
                        temp_files.append(temp_file.name)
                        attachments.append(temp_file.name)
                    except Exception as e:
                        print(f"Error processing base64 file: {str(e)}")

    return temp_files, attachments


async def handle_websocket(uri: str, channel_id: int):
    """Connect to a FastAPI WebSocket and handle notifications."""
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)

                    if data["type"] == "submission":
                        content = data["content"]
                        view = SubmissionView(content)

                        message_content = (
                            f"@everyone\n"
                            f"- Exam: {content['exam_name']}\n"
                            f"- Email: {content['email']}\n"
                        )

                        # First send the message without attachments
                        await plugin.bot.rest.create_message(
                            channel_id,
                            message_content,
                            components=view
                        )
                        plugin.d.miru.start_view(view)

                        # Process attachments from base64 files in answers
                        temp_files = []
                        attachments = []

                        if "answers" in content:
                            temp_files, file_attachments = await process_base64_files(content["answers"])
                            attachments.extend(file_attachments)

                        try:
                            # Create a thread from the message
                            thread = await plugin.bot.rest.create_thread(
                                channel_id,
                                hikari.ChannelType.GUILD_PUBLIC_THREAD,
                                f"{content['exam_name']} - {content['email']}",
                            )

                            # NOTE: Send learner submission
                            # answers = (
                            #     f"LEARNER SUBMISSION - {content['email']}\n" +
                            #     '\n'.join(f"{i+1}: {ans}" for i,
                            #               ans in enumerate([question['answer'] for question in content['answers']]))
                            # )
                            # exam_type = 'sql' if content['exam_name'].startswith(
                            #     'M1') else 'python'
                            # await thread.send(f"**Learner submission**\n```{exam_type}\n{answers[:answers.find('13:')]}\n```")
                            # await thread.send(f"```{exam_type}\n{answers[answers.find('13:'):]}\n```")

                            if attachments:
                                await thread.send("**Submitted files:**", attachments=attachments)

                            await thread.send(f"**Summary:**\n```{content['summary']}```")
                        finally:
                            # Clean up temp files
                            for file_path in temp_files:
                                try:
                                    os.unlink(file_path)
                                except Exception as e:
                                    print(
                                        f"Error deleting temp file: {str(e)}")

                        # NOTE: TEST: Send a message to DS server
                        await plugin.bot.rest.create_message(
                            1237424754739253279,
                            (
                                f"@everyone New submission added\n"
                                f"- Exam: {content['exam_name']}\n"
                                f"- Email: {content['email']}\n"
                                f"View submission at https://csassessment.it.com/marking/{content['submission_id']}"
                            )
                        )
                    elif data["type"] == "help_request":
                        content = data["content"]
                        view = HelpRequestView(content)

                        message = (
                            f"@everyone\n**New Help Request**\n"
                            f"- Category: {content['category']}\n"
                            f"- Subject: {content['subject']}\n"
                            f"- User ID: {content['userId']}\n"
                            f"- Description: {content['description']}"
                        )

                        # Create list of attachment URLs
                        attachments = []
                        for image_url in content['images']:
                            attachments.append(image_url)

                        await plugin.bot.rest.create_message(
                            channel_id,
                            message,
                            components=view,
                            attachments=attachments
                        )
                        plugin.d.miru.start_view(view)

                    elif data["type"] == "new_submission":
                        content = data["content"]

                        await plugin.bot.rest.create_message(
                            1237424754739253279,
                            (
                                f"@everyone New submission added\n"
                                f"- Exam: {content['exam']}\n"
                                f"- Email: {content['email']}\n"
                            )
                        )

        except websockets.ConnectionClosed:
            await asyncio.sleep(5)


async def start_websocket_clients():
    """Start multiple WebSocket client connections."""
    # First WebSocket connection
    uri1 = "wss://cspyclient.up.railway.app/ws"
    channel_id1 = 947032992063303730

    # Second WebSocket connection
    uri2 = "wss://cspyexamclient.up.railway.app/ws"
    channel_id2 = 947032992063303730  # You can use different channels if needed

    # Create tasks for both connections
    asyncio.create_task(handle_websocket(uri1, channel_id1))
    asyncio.create_task(handle_websocket(uri2, channel_id2))


@plugin.listener(hikari.StartedEvent)
async def on_started(event: hikari.StartedEvent) -> None:
    plugin.d.miru = miru.Client(plugin.bot)
    await start_websocket_clients()
