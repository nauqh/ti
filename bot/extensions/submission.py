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
    def __init__(self, email: str) -> None:
        super().__init__(timeout=None)
        self.email = email

    @miru.button(label="Accept Submission", style=hikari.ButtonStyle.SUCCESS)
    async def accept_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        try:
            await ctx.author.send(
                f"You have accepted the submission from {self.email}. "
                f"Please review and grade it as soon as possible."
            )

            # Remove the button and update message with text
            await ctx.message.edit(
                f"{ctx.message.content}\nAccepted by {ctx.author.mention}",
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
                        view = SubmissionView(content['email'])

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

                        await plugin.bot.rest.create_message(
                            947032992063303730,
                            f"```python\n{content['submission']}\n```"
                        )

        except websockets.ConnectionClosed:
            await asyncio.sleep(5)


@plugin.listener(hikari.StartedEvent)
async def on_started(event: hikari.StartedEvent) -> None:
    plugin.d.miru = miru.Client(plugin.bot)
    asyncio.create_task(websocket_client())


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)
