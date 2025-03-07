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


class SubmissionView(miru.View):
    def __init__(self, content: dict) -> None:
        super().__init__(timeout=None)
        self.content = content

    @miru.button(label="Accept", style=hikari.ButtonStyle.SUCCESS)
    async def accept_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        try:
            await ctx.author.send(
                f"@everyone\n"
                f"- Exam: {self.content['exam_name']}\n"
                f"- Email: {self.content['email']}\n"
                f"- Urls: https://nauqh.dev"
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


async def process_base64_files(answers, question_id=None):
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

                        # Create temp file with appropriate extension
                        file_name = file_info.get("name", "file")
                        suffix = os.path.splitext(
                            file_name)[1] if "." in file_name else ""
                        
                        # Use question_id in filename if provided
                        if question_id:
                            new_file_name = f"{question_id}_file{i}{suffix}"
                        else:
                            new_file_name = file_name

                        # Create a temp file and write decoded content
                        temp_file = tempfile.NamedTemporaryFile(
                            delete=False, suffix=suffix, prefix=f"{new_file_name}_")
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
                            # Use a combination of email and exam_name for the question_id, or use a dedicated id if available
                            question_id = content.get("id", f"{content['email']}_{content['exam_name']}".replace(" ", "_"))
                            temp_files, file_attachments = await process_base64_files(content["answers"], question_id)
                            attachments.extend(file_attachments)

                        # If we have attachments, create a thread and post them there
                        if attachments:
                            try:
                                # Create a thread from the message
                                thread = await plugin.bot.rest.create_thread(
                                    channel_id,
                                    hikari.ChannelType.GUILD_PUBLIC_THREAD,
                                    f"Submission Files - {content['email']}",
                                )

                                # Send attachments in the thread
                                await plugin.bot.rest.create_message(
                                    thread.id,
                                    "Submitted files:",
                                    attachments=attachments
                                )
                            finally:
                                # Clean up temp files
                                for file_path in temp_files:
                                    try:
                                        os.unlink(file_path)
                                    except Exception as e:
                                        print(
                                            f"Error deleting temp file: {str(e)}")

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


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)
