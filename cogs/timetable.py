from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands

from cogs.common import is_private_response, korean_date, make_embed
from services.neis import NeisError
from services.timetable import format_timetable_lines, sort_timetable

SEOUL = ZoneInfo("Asia/Seoul")


class TimetableNavigationView(discord.ui.View):
    def __init__(
        self, cog: "TimetableCog", owner_id: int, day: date
    ) -> None:
        super().__init__(timeout=600)
        self.cog = cog
        self.owner_id = owner_id
        self.day = day

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "🔒 이 시간표의 날짜 이동은 명령어를 실행한 사용자만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(
        label="◀ 이전 날짜",
        style=discord.ButtonStyle.secondary,
    )
    async def previous_day(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()
        await self.cog._edit_day(interaction, self.day - timedelta(days=1))

    @discord.ui.button(
        label="다음 날짜 ▶",
        style=discord.ButtonStyle.secondary,
    )
    async def next_day(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()
        await self.cog._edit_day(interaction, self.day + timedelta(days=1))


class TimetableCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _show_day(
        self, interaction: discord.Interaction, day: date
    ) -> None:
        if interaction.response.is_done():
            await interaction.followup.send(
                "요청이 이미 처리되었습니다.",
                ephemeral=is_private_response(interaction),
            )
            return
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
        if settings["grade"] is None or settings["class_num"] is None:
            await interaction.followup.send(
                "먼저 `/설정`에서 학년과 반을 등록해 주세요.",
                ephemeral=private_response,
            )
            return
        try:
            rows = await self.bot.neis.get_timetable(
                settings["school_type"],
                settings["office_code"],
                settings["school_code"],
                settings["grade"],
                settings["class_num"],
                day.isoformat(),
            )
        except NeisError as exc:
            await interaction.followup.send(
                f"⚠️ 시간표를 조회하지 못했습니다: {exc}",
                ephemeral=private_response,
            )
            return
        rows = sort_timetable(rows)
        if not rows:
            await interaction.followup.send(
                f"📭 {korean_date(day)} 시간표 데이터가 없습니다. 휴일이거나 나이스에 시간표가 미등록되었을 수 있습니다.",
                view=TimetableNavigationView(self, interaction.user.id, day),
                ephemeral=private_response,
            )
            return
        embed = make_embed(
            f"📚 {settings['school_name']} 시간표",
            f"**{settings['grade']}학년 {settings['class_num']}반 · {korean_date(day)}**\n\n"
            + "\n".join(format_timetable_lines(rows)),
        )
        embed.set_footer(text="데이터 출처: 나이스 교육정보 개방 포털")
        await interaction.followup.send(
            embed=embed,
            view=TimetableNavigationView(self, interaction.user.id, day),
            ephemeral=private_response,
        )

    async def _edit_day(
        self, interaction: discord.Interaction, day: date
    ) -> None:
        settings = self.bot.db.get_settings(interaction.user.id)
        if not settings:
            await interaction.edit_original_response(
                content="먼저 `/설정`에서 학교, 학년, 반을 등록해 주세요.",
                embed=None,
                view=None,
            )
            return
        try:
            rows = sort_timetable(
                await self.bot.neis.get_timetable(
                    settings["school_type"],
                    settings["office_code"],
                    settings["school_code"],
                    settings["grade"],
                    settings["class_num"],
                    day.isoformat(),
                )
            )
        except NeisError as exc:
            await interaction.edit_original_response(
                content=f"⚠️ 시간표를 조회하지 못했습니다: {exc}",
                embed=None,
                view=None,
            )
            return

        view = TimetableNavigationView(self, interaction.user.id, day)
        if not rows:
            await interaction.edit_original_response(
                content=f"📭 {korean_date(day)} 시간표 데이터가 없습니다. 휴일이거나 나이스에 시간표가 미등록되었을 수 있습니다.",
                embed=None,
                view=view,
            )
            return
        embed = make_embed(
            f"📚 {settings['school_name']} 시간표",
            f"**{settings['grade']}학년 {settings['class_num']}반 · {korean_date(day)}**\n\n"
            + "\n".join(format_timetable_lines(rows)),
        )
        embed.set_footer(text="데이터 출처: 나이스 교육정보 개방 포털")
        await interaction.edit_original_response(
            content=None,
            embed=embed,
            view=view,
        )

    @app_commands.command(name="시간표", description="오늘의 시간표를 확인합니다")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def today(self, interaction: discord.Interaction) -> None:
        await self._show_day(interaction, datetime.now(SEOUL).date())

    @app_commands.command(name="내일시간표", description="내일의 시간표를 확인합니다")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def tomorrow(self, interaction: discord.Interaction) -> None:
        await self._show_day(interaction, datetime.now(SEOUL).date() + timedelta(days=1))

    @app_commands.command(name="날짜시간표", description="지정한 날짜의 시간표를 확인합니다")
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
        await self._show_day(interaction, day)

    @app_commands.command(name="주간시간표", description="이번 주 월요일부터 금요일까지 시간표를 확인합니다")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def this_week(self, interaction: discord.Interaction) -> None:
        today = datetime.now(SEOUL).date()
        monday = today - timedelta(days=today.weekday())
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
        if settings["grade"] is None or settings["class_num"] is None:
            await interaction.followup.send(
                "먼저 `/설정`에서 학년과 반을 등록해 주세요.",
                ephemeral=private_response,
            )
            return
        lines = []
        try:
            for offset in range(5):
                day = monday + timedelta(days=offset)
                rows = sort_timetable(
                    await self.bot.neis.get_timetable(
                        settings["school_type"], settings["office_code"],
                        settings["school_code"], settings["grade"],
                        settings["class_num"], day.isoformat()
                    )
                )
                if rows:
                    lessons = "\n".join(format_timetable_lines(rows))
                    lines.append(f"**{korean_date(day)}**\n{lessons}")
                else:
                    lines.append(f"**{korean_date(day)}**\n시간표 데이터 없음 (휴일 또는 미등록 가능성)")
        except NeisError as exc:
            await interaction.followup.send(
                f"⚠️ 주간 시간표 조회에 실패했습니다: {exc}",
                ephemeral=private_response,
            )
            return
        embed = make_embed(
            f"📚 {settings['school_name']} 주간 시간표",
            f"{settings['grade']}학년 {settings['class_num']}반 · {korean_date(monday)} ~ {korean_date(monday + timedelta(days=4))}",
        )
        description = "\n\n".join(lines)
        embed.description = description[:4000]
        embed.set_footer(text="데이터 출처: 나이스 교육정보 개방 포털")
        await interaction.followup.send(
            embed=embed, ephemeral=private_response
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TimetableCog(bot))
