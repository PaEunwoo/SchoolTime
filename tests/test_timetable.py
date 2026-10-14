import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

from cogs.school import OwnerView, SettingsDraft
from cogs.timetable import TimetableNavigationView
from services.timetable import format_timetable_lines, sort_timetable


class TimetableFormattingTests(unittest.TestCase):
    def test_formats_periods_vertically_and_shows_empty_periods(self):
        rows = [
            {"PERIO": "4", "ITRT_CNTNT": "체육"},
            {"PERIO": "1", "ITRT_CNTNT": "영어"},
            {"PERIO": "7", "ITRT_CNTNT": "수학"},
        ]

        self.assertEqual(
            format_timetable_lines(rows),
            [
                "1교시  │ 영어",
                "2교시  │ -",
                "3교시  │ -",
                "4교시  │ 체육",
                "5교시  │ -",
                "6교시  │ -",
                "7교시  │ 수학",
                "8교시  │ -",
            ],
        )

    def test_includes_periods_after_eight(self):
        lines = format_timetable_lines(
            [
                {"PERIO": "9", "ITRT_CNTNT": "보충"},
                {"PERIO": "1", "ITRT_CNTNT": "국어"},
            ]
        )

        self.assertEqual(len(lines), 9)
        self.assertEqual(lines[8], "9교시  │ 보충")

    def test_sort_timetable_orders_numeric_periods(self):
        rows = [{"PERIO": "10"}, {"PERIO": "2"}, {"PERIO": "1"}]

        self.assertEqual(
            [row["PERIO"] for row in sort_timetable(rows)], ["1", "2", "10"]
        )


class TimetableNavigationTests(unittest.IsolatedAsyncioTestCase):
    async def test_daily_view_has_previous_and_next_buttons(self):
        day = date(2026, 10, 13)
        view = TimetableNavigationView(object(), 123, day)

        self.assertEqual(view.day, day)
        self.assertEqual(
            [item.label for item in view.children],
            ["◀ 이전 날짜", "다음 날짜 ▶"],
        )

    async def test_other_user_gets_private_warning_without_changing_view(self):
        view = TimetableNavigationView(object(), 123, date(2026, 10, 13))
        interaction = SimpleNamespace(
            user=SimpleNamespace(id=456),
            response=SimpleNamespace(send_message=AsyncMock()),
        )

        allowed = await view.interaction_check(interaction)

        self.assertFalse(allowed)
        interaction.response.send_message.assert_awaited_once_with(
            "🔒 이 시간표의 날짜 이동은 명령어를 실행한 사용자만 사용할 수 있습니다.",
            ephemeral=True,
        )
        self.assertEqual(view.day, date(2026, 10, 13))

    async def test_other_user_cannot_operate_settings_view(self):
        view = OwnerView(123, SettingsDraft())
        interaction = SimpleNamespace(
            user=SimpleNamespace(id=456),
            response=SimpleNamespace(send_message=AsyncMock()),
        )

        allowed = await view.interaction_check(interaction)

        self.assertFalse(allowed)
        interaction.response.send_message.assert_awaited_once_with(
            "🔒 이 버튼은 명령어를 실행한 사용자만 사용할 수 있습니다.",
            ephemeral=True,
        )


if __name__ == "__main__":
    unittest.main()
