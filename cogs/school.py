import logging
import sqlite3
from dataclasses import dataclass
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from cogs.common import (
    add_field_safely,
    is_private_response,
    make_embed,
    school_field,
)
from services.neis import NeisError


def school_max_grade(school_type: str) -> int:
    if "초등" in school_type:
        return 6
    if "중" in school_type or "고" in school_type:
        return 3
    return 0


@dataclass
class SettingsDraft:
    school: dict[str, Any] | None = None
    grade: int | None = None
    class_num: int | None = None
    closed: bool = False

    def is_complete(self) -> bool:
        return (
            self.school is not None
            and self.grade is not None
            and self.class_num is not None
        )

    def make_embed(self) -> discord.Embed:
        embed = make_embed(
            "🏫 내 학교 설정",
            "학교, 학년, 반을 설정해주세요.",
        )
        embed.add_field(
            name="학교",
            value=(
                f"{self.school['SCHUL_NM']} ({self.school['SCHUL_KND_SC_NM']})"
                if self.school
                else "미설정"
            ),
            inline=False,
        )
        embed.add_field(
            name="학년",
            value=f"{self.grade}학년" if self.grade is not None else "미설정",
            inline=True,
        )
        embed.add_field(
            name="반",
            value=f"{self.class_num}반" if self.class_num is not None else "미설정",
            inline=True,
        )
        return embed


class OwnerView(discord.ui.View):
    def __init__(
        self,
        owner_id: int,
        draft: SettingsDraft,
        message: discord.InteractionMessage | None = None,
        timeout: float = 600,
    ) -> None:
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        self.draft = draft
        self.message = message

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "🔒 이 버튼은 명령어를 실행한 사용자만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return False
        if self.draft.closed:
            await interaction.response.send_message(
                "이 설정 화면은 이미 저장되었거나 만료되었습니다.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        if self.message is not None:
            try:
                await self.message.edit(view=None)
            except discord.HTTPException:
                logging.debug("만료된 설정 화면의 버튼을 정리하지 못했습니다.")

class SettingsView(OwnerView):
    def __init__(
        self,
        owner_id: int,
        draft: SettingsDraft,
        message: discord.InteractionMessage | None = None,
        timeout: float = 600,
    ) -> None:
        super().__init__(owner_id, draft, message, timeout)
        self.save.disabled = not draft.is_complete()

    @discord.ui.button(
        label="🔍 학교 검색 및 선택",
        style=discord.ButtonStyle.primary,
        row=0,
    )
    async def search_school(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.send_modal(
            SchoolSearchModal(self.owner_id, self.draft, self.message)
        )

    @discord.ui.button(label="학년 선택", style=discord.ButtonStyle.secondary, row=1)
    async def choose_grade(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if self.draft.school is None:
            await interaction.response.send_message(
                "먼저 학교 검색 및 선택을 완료해 주세요.",
                ephemeral=is_private_response(interaction),
            )
            return
        max_grade = school_max_grade(str(self.draft.school["SCHUL_KND_SC_NM"]))
        if max_grade == 0:
            await interaction.response.send_message(
                "지원하는 학교급(초등학교·중학교·고등학교)을 선택해 주세요.",
                ephemeral=is_private_response(interaction),
            )
            return
        view = GradeSelectView(
            self.owner_id, self.draft, self.message, max_grade, self.timeout
        )
        await interaction.response.edit_message(
            embed=self.draft.make_embed(), view=view
        )

    @discord.ui.button(label="반 선택", style=discord.ButtonStyle.secondary, row=1)
    async def choose_class(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if self.draft.school is None:
            await interaction.response.send_message(
                "먼저 학교 검색 및 선택을 완료해 주세요.",
                ephemeral=is_private_response(interaction),
            )
            return
        if self.draft.grade is None:
            await interaction.response.send_message(
                "반을 선택하기 전에 학년을 먼저 선택해 주세요.",
                ephemeral=is_private_response(interaction),
            )
            return
        await interaction.response.send_modal(
            ClassSelectModal(self.owner_id, self.draft, self.message)
        )

    @discord.ui.button(
        label="💾 설정 저장하기",
        style=discord.ButtonStyle.success,
        row=2,
    )
    async def save(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        school = self.draft.school
        grade = self.draft.grade
        class_num = self.draft.class_num
        if school is None or grade is None or class_num is None:
            await interaction.response.send_message(
                "학교, 학년, 반을 모두 선택해 주세요.",
                ephemeral=is_private_response(interaction),
            )
            return
        try:
            interaction.client.db.save_settings(
                self.owner_id,
                str(school["SCHUL_NM"]),
                str(school["SCHUL_KND_SC_NM"]),
                str(school["ATPT_OFCDC_SC_CODE"]),
                str(school["SD_SCHUL_CODE"]),
                grade,
                class_num,
            )
        except sqlite3.Error:
            logging.exception("사용자 학교 설정 저장에 실패했습니다.")
            await interaction.response.send_message(
                "설정을 저장하지 못했습니다. 잠시 후 다시 시도해 주세요.",
                ephemeral=is_private_response(interaction),
            )
            return

        self.draft.closed = True
        embed = make_embed(
            "🏫 학교 설정 완료",
            "✅ 설정이 성공적으로 저장되었습니다.",
        )
        add_field_safely(embed, "학교", str(school["SCHUL_NM"]))
        add_field_safely(embed, "학년", f"{grade}학년", inline=True)
        add_field_safely(embed, "반", f"{class_num}반", inline=True)
        await interaction.response.edit_message(embed=embed, view=None)


class GradeSelect(discord.ui.Select):
    def __init__(
        self,
        owner_id: int,
        draft: SettingsDraft,
        message: discord.InteractionMessage | None,
        max_grade: int,
    ) -> None:
        self.owner_id = owner_id
        self.draft = draft
        self.message = message
        super().__init__(
            placeholder="학년을 선택해 주세요",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label=f"{grade}학년", value=str(grade))
                for grade in range(1, max_grade + 1)
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        self.draft.grade = int(self.values[0])
        view = SettingsView(self.owner_id, self.draft, self.message)
        await interaction.response.edit_message(
            embed=self.draft.make_embed(), view=view
        )


class GradeSelectView(OwnerView):
    def __init__(
        self,
        owner_id: int,
        draft: SettingsDraft,
        message: discord.InteractionMessage | None,
        max_grade: int,
        timeout: float,
    ) -> None:
        super().__init__(owner_id, draft, message, timeout)
        self.add_item(GradeSelect(owner_id, draft, message, max_grade))

    @discord.ui.button(label="설정으로 돌아가기", style=discord.ButtonStyle.secondary)
    async def back(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.edit_message(
            embed=self.draft.make_embed(),
            view=SettingsView(
                self.owner_id, self.draft, self.message, timeout=self.timeout
            ),
        )


class SchoolResultsSelect(discord.ui.Select):
    def __init__(
        self,
        owner_id: int,
        draft: SettingsDraft,
        message: discord.InteractionMessage | None,
        rows: list[dict[str, Any]],
    ) -> None:
        self.draft = draft
        self.message = message
        options = []
        self.rows = rows[:25]
        for index, row in enumerate(self.rows):
            name = str(row.get("SCHUL_NM", "학교명 없음"))
            kind = str(row.get("SCHUL_KND_SC_NM", "학교급 미상"))
            address = str(row.get("ORG_RDNMA") or row.get("ORG_RDNZC") or "주소 정보 없음")
            code = (
                f"{row.get('ATPT_OFCDC_SC_CODE', '?')}/"
                f"{row.get('SD_SCHUL_CODE', '?')}"
            )
            options.append(
                discord.SelectOption(
                    label=f"{name} ({kind})"[:100],
                    description=f"{address} · 코드 {code}"[:100],
                    value=str(index),
                )
            )
        super().__init__(
            placeholder="학교 이름·학교급·주소를 확인해 선택하세요",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.owner_id = owner_id

    async def callback(self, interaction: discord.Interaction) -> None:
        row = self.rows[int(self.values[0])]
        required = (
            "SCHUL_NM",
            "SCHUL_KND_SC_NM",
            "ATPT_OFCDC_SC_CODE",
            "SD_SCHUL_CODE",
        )
        if any(not row.get(key) for key in required):
            await interaction.response.send_message(
                "학교 설정에 필요한 코드 정보가 검색 결과에 없습니다. 다른 결과를 선택해 주세요.",
                ephemeral=is_private_response(interaction),
            )
            return

        previous = self.draft.school
        changed = previous is None or (
            previous.get("ATPT_OFCDC_SC_CODE") != row.get("ATPT_OFCDC_SC_CODE")
            or previous.get("SD_SCHUL_CODE") != row.get("SD_SCHUL_CODE")
        )
        self.draft.school = row
        if changed:
            self.draft.grade = None
            self.draft.class_num = None

        await interaction.response.edit_message(
            content="✅ 학교 선택을 반영했습니다. 통합 설정 화면을 확인해 주세요.",
            embed=None,
            view=None,
        )
        if isinstance(self.view, SchoolResultsView):
            self.view.picker_message = interaction.message
        if self.message is not None:
            await self.message.edit(
                embed=self.draft.make_embed(),
                view=SettingsView(self.owner_id, self.draft, self.message),
            )


class SchoolResultsView(OwnerView):
    def __init__(
        self,
        owner_id: int,
        draft: SettingsDraft,
        message: discord.InteractionMessage | None,
        rows: list[dict[str, Any]],
    ) -> None:
        super().__init__(owner_id, draft, message, timeout=180)
        self.picker_message: discord.InteractionMessage | None = None
        self.add_item(SchoolResultsSelect(owner_id, draft, message, rows))

    async def on_timeout(self) -> None:
        if self.picker_message is not None:
            try:
                await self.picker_message.edit(view=None)
            except discord.HTTPException:
                logging.debug("만료된 학교 검색 결과를 정리하지 못했습니다.")


class SchoolSearchModal(discord.ui.Modal, title="학교 검색"):
    school_name = discord.ui.TextInput(
        label="학교 이름",
        placeholder="예: 무릉중학교",
        min_length=1,
        max_length=50,
    )

    def __init__(
        self,
        owner_id: int,
        draft: SettingsDraft,
        message: discord.InteractionMessage | None,
    ) -> None:
        super().__init__(timeout=300)
        self.owner_id = owner_id
        self.draft = draft
        self.message = message

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "이 설정 화면을 연 사용자만 학교를 검색할 수 있습니다.",
                ephemeral=is_private_response(interaction),
            )
            return
        private_response = is_private_response(interaction)
        await interaction.response.defer(
            ephemeral=private_response, thinking=True
        )
        try:
            rows = await interaction.client.neis.search_schools(
                str(self.school_name.value).strip()
            )
        except NeisError as exc:
            await interaction.followup.send(
                f"⚠️ 학교 검색에 실패했습니다: {exc}",
                ephemeral=private_response,
            )
            return
        if not rows:
            await interaction.followup.send(
                "검색 결과가 없습니다. 학교명을 확인해 주세요.",
                ephemeral=private_response,
            )
            return
        note = "학교 이름, 학교급, 주소를 확인해 결과를 선택해 주세요."
        if len(rows) > 25:
            note += " 결과가 많아 상위 25개만 표시합니다. 학교명을 더 구체적으로 입력해 주세요."
        picker_view = SchoolResultsView(
            self.owner_id, self.draft, self.message, rows
        )
        picker_message = await interaction.followup.send(
            note,
            view=picker_view,
            ephemeral=private_response,
            wait=True,
        )
        picker_view.picker_message = picker_message


class ClassSelectModal(discord.ui.Modal, title="반 선택"):
    class_number = discord.ui.TextInput(
        label="반 번호 (1~50)",
        placeholder="예: 1",
        min_length=1,
        max_length=2,
    )

    def __init__(
        self,
        owner_id: int,
        draft: SettingsDraft,
        message: discord.InteractionMessage | None,
    ) -> None:
        super().__init__(timeout=300)
        self.owner_id = owner_id
        self.draft = draft
        self.message = message

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "이 설정 화면을 연 사용자만 반을 설정할 수 있습니다.",
                ephemeral=is_private_response(interaction),
            )
            return
        value = str(self.class_number.value).strip()
        if not value.isdecimal() or not 1 <= int(value) <= 50:
            await interaction.response.send_message(
                "반은 1부터 50 사이의 숫자로 입력해 주세요.",
                ephemeral=is_private_response(interaction),
            )
            return
        if self.draft.grade is None or self.draft.school is None:
            await interaction.response.send_message(
                "학교와 학년을 먼저 선택해 주세요.",
                ephemeral=is_private_response(interaction),
            )
            return

        self.draft.class_num = int(value)
        private_response = is_private_response(interaction)
        await interaction.response.defer(
            ephemeral=private_response, thinking=True
        )
        if self.message is not None:
            await self.message.edit(
                embed=self.draft.make_embed(),
                view=SettingsView(self.owner_id, self.draft, self.message),
            )
        await interaction.followup.send(
            f"반을 **{self.draft.class_num}반**으로 임시 선택했습니다. 저장 버튼을 눌러 완료해 주세요.",
            ephemeral=private_response,
        )


class SchoolCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="설정", description="학교, 학년, 반을 한 번에 설정합니다")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def configure(self, interaction: discord.Interaction) -> None:
        existing = self.bot.db.get_settings(interaction.user.id)
        draft = SettingsDraft()
        if existing:
            draft.school = {
                "SCHUL_NM": existing["school_name"],
                "SCHUL_KND_SC_NM": existing["school_type"],
                "ATPT_OFCDC_SC_CODE": existing["office_code"],
                "SD_SCHUL_CODE": existing["school_code"],
            }
            draft.grade = existing["grade"]
            draft.class_num = existing["class_num"]
        view = SettingsView(interaction.user.id, draft)
        await interaction.response.send_message(
            embed=draft.make_embed(),
            view=view,
            ephemeral=is_private_response(interaction),
        )
        view.message = await interaction.original_response()

    @app_commands.command(name="학교정보", description="내 설정 학교의 정보를 확인합니다")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def school_info(self, interaction: discord.Interaction) -> None:
        settings = self.bot.db.get_settings(interaction.user.id)
        if not settings:
            await interaction.response.send_message(
                "먼저 `/설정`에서 학교, 학년, 반을 등록해 주세요.",
                ephemeral=is_private_response(interaction),
            )
            return
        private_response = is_private_response(interaction)
        await interaction.response.defer(
            thinking=True, ephemeral=private_response
        )
        try:
            matches = await self.bot.neis.fetch_all(
                "school",
                {
                    "ATPT_OFCDC_SC_CODE": settings["office_code"],
                    "SD_SCHUL_CODE": settings["school_code"],
                },
            )
        except NeisError as exc:
            await interaction.followup.send(
                f"⚠️ 학교 정보를 조회하지 못했습니다: {exc}",
                ephemeral=private_response,
            )
            return
        row = matches[0] if matches else {}
        embed = make_embed(f"🏫 {settings['school_name']}")
        add_field_safely(embed, "학교급", settings["school_type"])
        add_field_safely(embed, "주소", school_field(row, "ORG_RDNMA"))
        add_field_safely(embed, "교육청", school_field(row, "ATPT_OFCDC_SC_NM"))
        add_field_safely(embed, "학교 코드", settings["school_code"])
        website = row.get("HMPG_ADRES")
        if website:
            embed.add_field(name="공식 홈페이지", value=str(website)[:1000], inline=False)
        await interaction.followup.send(
            embed=embed, ephemeral=private_response
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SchoolCog(bot))
