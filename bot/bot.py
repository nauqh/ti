import bot
import hikari
import lightbulb
from dotenv import load_dotenv
import os

load_dotenv()

app = lightbulb.BotApp(
    os.getenv("TOKEN"),
    intents=hikari.Intents.ALL,
    default_enabled_guilds=[int(os.getenv("GUILD_ID"))],
    help_slash_command=True,
    banner=None,
)

app.load_extensions_from("./bot/extensions", must_exist=True)


def run() -> None:
    app.run(
        activity=hikari.Activity(
            name=f"v{bot.__version__}",
            type=hikari.ActivityType.LISTENING,
        )
    )
