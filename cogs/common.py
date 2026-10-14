from datetime import date

import discord

from services.timetable import weekday_label

MAX_DESCRIPTION = 4000
MAX_FIELD_VALUE = 1000


def is_private_response(interaction: discord.Interaction) -> bool:
    return interaction.guild is not None


def korean_date(day: date) -> str:
    return f"{day:%Y-%m-%d} ({weekday_label(day)}요일)"


def make_embed(title: str, description: str | None = None) -> discord.Embed:
    return discord.Embed(
        title=title,
        description=(description or "")[:MAX_DESCRIPTION],
        color=discord.Color.blurple(),
    )


def add_field_safely(
    embed: discord.Embed, name: str, value: str, inline: bool = False
) -> None:
    value = value or "정보 없음"
    if len(value) > MAX_FIELD_VALUE:
        value = value[: MAX_FIELD_VALUE - 1] + "…"
    if len(embed.fields) >= 25:
        return
    embed.add_field(name=name[:256], value=value, inline=inline)


def split_lines(lines: list[str], limit: int = MAX_DESCRIPTION) -> list[str]:
    chunks: list[str] = []
    current = ""
    for line in lines:
        if len(line) > limit:
            line = line[: limit - 1] + "…"
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def school_field(row: dict, key: str, fallback: str = "정보 없음") -> str:
    value = row.get(key)
    return str(value).strip() if value else fallback
