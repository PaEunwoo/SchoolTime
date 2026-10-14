import unittest
from types import SimpleNamespace

import discord
from discord.ext import commands

from cogs.common import is_private_response


class DiscordContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_commands_allow_guild_and_user_installs_in_dm_and_guild(self):
        bot = commands.Bot(
            command_prefix="!",
            intents=discord.Intents.default(),
        )
        try:
            for extension in ("cogs.school", "cogs.timetable", "cogs.schedule"):
                await bot.load_extension(extension)

            commands_by_name = {
                command.name: command for command in bot.tree.get_commands()
            }
            expected = {
                "설정",
                "시간표",
                "주간시간표",
                "학사일정",
                "학교정보",
            }
            self.assertTrue(expected.issubset(commands_by_name))
            for command in commands_by_name.values():
                self.assertTrue(command.allowed_contexts.guild)
                self.assertTrue(command.allowed_contexts.dm_channel)
                self.assertTrue(command.allowed_contexts.private_channel)
                self.assertTrue(command.allowed_installs.guild)
                self.assertTrue(command.allowed_installs.user)
                command.to_dict(bot.tree)
        finally:
            await bot.close()

    async def test_private_response_is_ephemeral_only_in_guilds(self):
        self.assertTrue(is_private_response(SimpleNamespace(guild=object())))
        self.assertFalse(is_private_response(SimpleNamespace(guild=None)))


if __name__ == "__main__":
    unittest.main()
