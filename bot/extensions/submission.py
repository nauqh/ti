import hikari
import lightbulb
import websockets
import json
import asyncio
from dotenv import load_dotenv

load_dotenv()

submissions_plugin = lightbulb.Plugin("Submissions")


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
                        message = (
                            f"@everyone\n"
                            f"- Exam: {content['exam_name']}\n"
                            f"- Email: {content['email']}\n"
                            f"- Urls: https://nauqh.dev"
                        )
                        await submissions_plugin.bot.rest.create_message(
                            947032992063303730,
                            message
                        )

                        await submissions_plugin.bot.rest.create_message(
                            947032992063303730,
                            f"```python\n{content['submission']}\n```"
                        )

        except websockets.ConnectionClosed:
            await asyncio.sleep(5)


@submissions_plugin.listener(hikari.StartedEvent)
async def on_started(_: hikari.StartedEvent) -> None:
    asyncio.create_task(websocket_client())


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(submissions_plugin)
