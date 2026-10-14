import unittest

import discord

from cogs.school import (
    GradeSelectView,
    SchoolResultsSelect,
    SettingsDraft,
    SettingsView,
    school_max_grade,
)


class SettingsUiTests(unittest.IsolatedAsyncioTestCase):
    async def test_save_button_requires_complete_draft(self):
        draft = SettingsDraft()
        self.assertTrue(SettingsView(1, draft).save.disabled)

        draft.school = {
            "SCHUL_NM": "예시학교",
            "SCHUL_KND_SC_NM": "중학교",
            "ATPT_OFCDC_SC_CODE": "B10",
            "SD_SCHUL_CODE": "12345",
        }
        draft.grade = 2
        draft.class_num = 1
        self.assertFalse(SettingsView(1, draft).save.disabled)

    async def test_grade_options_follow_school_level(self):
        self.assertEqual(school_max_grade("초등학교"), 6)
        self.assertEqual(school_max_grade("중학교"), 3)
        self.assertEqual(school_max_grade("고등학교"), 3)

        view = GradeSelectView(1, SettingsDraft(), None, 6, 600)
        select = next(item for item in view.children if isinstance(item, discord.ui.Select))
        self.assertEqual([option.value for option in select.options], ["1", "2", "3", "4", "5", "6"])

    async def test_school_results_are_distinguishable_by_codes(self):
        rows = [
            {
                "SCHUL_NM": "중앙중학교",
                "SCHUL_KND_SC_NM": "중학교",
                "ORG_RDNMA": "서울시 가구 나로",
                "ATPT_OFCDC_SC_CODE": "B10",
                "SD_SCHUL_CODE": "10001",
            },
            {
                "SCHUL_NM": "중앙중학교",
                "SCHUL_KND_SC_NM": "중학교",
                "ORG_RDNMA": "서울시 가구 나로",
                "ATPT_OFCDC_SC_CODE": "C10",
                "SD_SCHUL_CODE": "20002",
            },
        ]
        select = SchoolResultsSelect(1, SettingsDraft(), None, rows)

        self.assertEqual(len(select.options), 2)
        self.assertIn("10001", select.options[0].description)
        self.assertIn("20002", select.options[1].description)


if __name__ == "__main__":
    unittest.main()
