import logging

import discord
from discord.ext import commands

from config import load_config
from database import Database
from services.neis import NeisClient

EXTENSIONS = ("cogs.school", "cogs.timetable", "cogs.schedule")


class NeisBot(commands.Bot):
    def __init__(self, token: str, api_key: str) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.token = token
        self.db = Database()
        self.neis = NeisClient(api_key)

    async def setup_hook(self) -> None:
        self.db.initialize()
        await self.neis.start()
        for extension in EXTENSIONS:
            await self.load_extension(extension)
        synced = await self.tree.sync()
        logging.info("슬래시 명령어 %d개를 동기화했습니다.", len(synced))

    async def close(self) -> None:
        await self.neis.close()
        self.db.close()
        await super().close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = load_config()
    bot = NeisBot(config.discord_token, config.neis_api_key)
    bot.run(bot.token, log_handler=None)


if __name__ == "__main__":
    main()
