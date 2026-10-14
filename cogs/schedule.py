from datetime import date, datetime
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands

from cogs.common import is_private_response, korean_date, make_embed, split_lines
from services.neis import NeisError
from services.schedule import format_neis_date, sort_events

SEOUL = ZoneInfo("Asia/Seoul")


class ScheduleCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _events(
        self, interaction: discord.Interaction, start: date, end: date, title: str
    ) -> None:
        private_response = is_private_response(interaction)
        await interaction.response.defer(
            thinking=True, ephemeral=private_response
        )
        settings = self.bot.db.get_settings(interaction.user.id)
        if not settings:
            await interaction.followup.send(
                "먼저 `/설정`에서 학교, 학년, 반을 등록해 주세요.",
                ephemeral=private_response,
            )
            return
        try:
            rows = sort_events(
                await self.bot.neis.get_schedule(
                    settings["office_code"],
                    settings["school_code"],
                    start.isoformat(),
                    end.isoformat(),
                )
            )
        except NeisError as exc:
            await interaction.followup.send(
                f"⚠️ 학사일정을 조회하지 못했습니다: {exc}",
                ephemeral=private_response,
            )
            return
        if not rows:
            await interaction.followup.send(
                "📭 해당 기간에 등록된 학사일정이 없습니다.",
                ephemeral=private_response,
            )
            return
        lines = []
        for row in rows:
            event_day = format_neis_date(str(row.get("AA_YMD", "")))
            event_name = str(row.get("EVENT_NM", "행사명 없음"))
            detail = str(row.get("EVENT_CNTNT", "")).strip()
            line = f"📅 **{event_day}** — {event_name}"
            if detail:
                line += f"\n　{detail}"
            lines.append(line)
        chunks = split_lines(lines)
        for index, chunk in enumerate(chunks, start=1):
            page_title = title if len(chunks) == 1 else f"{title} ({index}/{len(chunks)})"
            embed = make_embed(f"🗓️ {settings['school_name']} {page_title}", chunk)
            embed.set_footer(text="데이터 출처: 나이스 교육정보 개방 포털")
            if index == 1:
                await interaction.followup.send(
                    embed=embed, ephemeral=private_response
                )
            else:
                await interaction.followup.send(
                    embed=embed, ephemeral=private_response
                )

    @app_commands.command(name="오늘일정", description="오늘의 학사일정을 확인합니다")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def today(self, interaction: discord.Interaction) -> None:
        today = datetime.now(SEOUL).date()
        await self._events(interaction, today, today, korean_date(today))

    @app_commands.command(name="월간일정", description="이번 달 학사일정을 확인합니다")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def this_month(self, interaction: discord.Interaction) -> None:
        await self._this_month(interaction)

    async def _this_month(self, interaction: discord.Interaction) -> None:
        today = datetime.now(SEOUL).date()
        start = today.replace(day=1)
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)
        end = date.fromordinal(next_month.toordinal() - 1)
        await self._events(
            interaction, start, end, f"{today.year}년 {today.month}월 학사일정"
        )

    @app_commands.command(name="학사일정", description="이번 달 학사일정을 확인합니다")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def school_calendar(self, interaction: discord.Interaction) -> None:
        await self._this_month(interaction)

    @app_commands.command(name="날짜일정", description="지정한 날짜의 학사일정을 확인합니다")
    @app_commands.describe(날짜="YYYY-MM-DD 형식")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def for_date(self, interaction: discord.Interaction, 날짜: str) -> None:
        try:
            day = date.fromisoformat(날짜)
            if day.isoformat() != 날짜:
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "날짜 형식이 올바르지 않습니다. `YYYY-MM-DD` 형식으로 입력해 주세요.",
                ephemeral=is_private_response(interaction),
            )
            return
        await self._events(interaction, day, day, korean_date(day))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ScheduleCog(bot))
