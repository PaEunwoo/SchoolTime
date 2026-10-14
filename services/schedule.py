from datetime import date


def sort_events(rows: list[dict]) -> list[dict]:
    return sorted(
        rows,
        key=lambda row: (
            str(row.get("AA_YMD", "")),
            str(row.get("EVENT_NM", "")),
        ),
    )


def format_neis_date(value: str) -> str:
    if len(value) == 8 and value.isdigit():
        return f"{value[:4]}-{value[4:6]}-{value[6:]}"
    return value
