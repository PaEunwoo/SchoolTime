from datetime import date


def sort_timetable(rows: list[dict]) -> list[dict]:
    def period(row: dict) -> tuple[int, str]:
        value = str(row.get("PERIO", ""))
        try:
            return int(value), value
        except ValueError:
            return 10_000, value

    return sorted(rows, key=period)


def format_timetable_lines(rows: list[dict]) -> list[str]:
    periods: dict[int, str] = {}
    for row in rows:
        try:
            period = int(row["PERIO"])
        except (KeyError, TypeError, ValueError):
            continue
        if period >= 1:
            periods[period] = str(row.get("ITRT_CNTNT") or "-")

    last_period = max(8, max(periods, default=0))
    return [
        f"{period}교시  │ {periods.get(period, '-')}"
        for period in range(1, last_period + 1)
    ]


def weekday_label(day: date) -> str:
    return ("월", "화", "수", "목", "금", "토", "일")[day.weekday()]
