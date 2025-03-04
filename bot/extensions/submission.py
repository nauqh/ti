import hikari
import lightbulb
import miru
import websockets
import json
import asyncio
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


async def websocket_client():
    """Connect to FastAPI WebSocket and handle submission notifications."""
    uri = "wss://cspyclient.up.railway.app/ws"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)

                    if data["type"] == "submission":
                        content = data["content"]
                        view = SubmissionView(content)

                        message = (
                            f"@everyone\n"
                            f"- Exam: {content['exam_name']}\n"
                            f"- Email: {content['email']}\n"
                            f"- Urls: https://nauqh.dev"
                        )

                        await plugin.bot.rest.create_message(
                            947032992063303730,
                            message,
                            components=view
                        )
                        plugin.d.miru.start_view(view)

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
                            947032992063303730,
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


@plugin.listener(hikari.StartedEvent)
async def on_started(event: hikari.StartedEvent) -> None:
    plugin.d.miru = miru.Client(plugin.bot)
    asyncio.create_task(websocket_client())


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)
