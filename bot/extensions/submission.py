import hikari
import lightbulb
import miru
import websockets
import json
import asyncio
from dotenv import load_dotenv

load_dotenv()

plugin = lightbulb.Plugin("Submissions", include_datastore=True)


class ReturnModal(miru.Modal):
    def __init__(self, content: dict, message_id: int) -> None:
        super().__init__("Return Submission")
        self.content = content
        self.message_id = message_id
        self.reason = miru.TextInput(
            label="Reason for return",
            placeholder="Enter reason for returning the submission",
            required=True,
            style=hikari.TextInputStyle.PARAGRAPH
        )
        self.add_item(self.reason)

    async def callback(self, ctx: miru.ModalContext) -> None:
        # Update original submission message
        await ctx.bot.rest.edit_message(
            947032992063303730,
            self.message_id,
            f"{ctx.message.content}\n**Returned by TA {ctx.author.mention}**\nReason: {self.reason.value}",
            components=None
        )
        await ctx.respond("Submission returned successfully", flags=hikari.MessageFlag.EPHEMERAL)


class SubmissionView(miru.View):
    def __init__(self, content: dict) -> None:
        super().__init__(timeout=None)
        self.content = content

    @miru.button(label="Accept", style=hikari.ButtonStyle.SUCCESS)
    async def accept_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        try:
            view = miru.View()
            view.add_item(miru.Button(
                label="Return",
                style=hikari.ButtonStyle.DANGER,
                custom_id=f"return_{ctx.message.id}"
            ))

            await ctx.author.send(
                f"Grading assignment:\n"
                f"- Exam: {self.content['exam_name']}\n"
                f"- Email: {self.content['email']}\n"
                f"- Urls: https://nauqh.dev",
                components=view
            )

            await ctx.message.edit(
                f"{ctx.message.content}\n**Accepted by TA {ctx.author.mention}**",
                components=None
            )

            await ctx.respond(
                "Submission accepted successfully",
                flags=hikari.MessageFlag.EPHEMERAL
            )

        except hikari.ForbiddenError:
            await ctx.respond(
                "Could not send DM. Please check your privacy settings.",
                flags=hikari.MessageFlag.EPHEMERAL
            )


@plugin.listener(hikari.InteractionCreateEvent)
async def on_component_interaction(event: hikari.InteractionCreateEvent) -> None:
    if not isinstance(event.interaction, hikari.ComponentInteraction):
        return

    if event.interaction.custom_id.startswith("return_"):
        message_id = int(event.interaction.custom_id.split("_")[1])
        modal = ReturnModal(
            {"exam_name": "Example", "email": "test@email.com"}, message_id)
        await event.interaction.create_modal_response(modal)


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

        except websockets.ConnectionClosed:
            await asyncio.sleep(5)


@plugin.listener(hikari.StartedEvent)
async def on_started(event: hikari.StartedEvent) -> None:
    plugin.d.miru = miru.Client(plugin.bot)
    asyncio.create_task(websocket_client())


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)
