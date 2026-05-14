from datetime import datetime
from os import environ, path
from traceback import format_exc
import json
import re
import xml.etree.ElementTree as ET
from typing import Any

from pydantic import ValidationError

from src.api import (
    APIClient,
    CaptchaException,
    LoginException,
    NotFoundException,
    UnauthorizedException,
)
from src.database import Database
from src.schema import DatabaseEntry, Summary, User
from src.synchronizer import check_database_change, sync_database_with_summaries


def create_svg_group(file_path: str, x: int, y: int, width: int, height: int) -> str:
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        original_width_str = root.get("width", "1")
        original_height_str = root.get("height", "1")
        original_width = float(re.sub(r"px$", "", original_width_str))
        original_height = float(re.sub(r"px$", "", original_height_str))
        scale_x = width / original_width if original_width else 1
        scale_y = height / original_height if original_height else 1
        group = ET.Element(
            "g", {"transform": f"translate({x}, {y}) scale({scale_x}, {scale_y})"})
        for child in root:
            group.append(child)
        return ET.tostring(group, encoding="unicode")
    except Exception as e:
        return f"<!-- Error loading {file_path}: {e} -->"


def log(message: str) -> None:
    print(f"[JDV] {message}")


def build_profile(raw_user: dict[str, Any], user: User) -> dict[str, Any]:
    username = raw_user.get("username") or raw_user.get("name") or "unknown"
    total_xp = raw_user.get("totalXp") or raw_user.get("total_xp") or 0
    language_levels_raw = environ.get("DUOSTATS_LANGUAGE_LEVELS", "")
    try:
        language_levels = json.loads(
            language_levels_raw) if language_levels_raw else {}
    except Exception:
        language_levels = {}
        for pair in language_levels_raw.split(","):
            if not pair.strip():
                continue
            name, _, value = pair.partition(":")
            if name and value:
                language_levels[name.strip()] = int(value.strip())

    languages: list[dict[str, Any]] = []
    for language in raw_user.get("languages", []) or []:
        points = int(language.get("points") or 0)
        if points <= 0:
            continue
        name = language.get("language_string") or language.get(
            "language") or "Unknown"
        manual_level = language_levels.get(name)
        languages.append(
            {
                "code": language.get("language") or "",
                "name": name,
                "xp": points,
                "level": int(manual_level) if manual_level is not None else 0,
                "streak": int(language.get("streak") or 0),
            }
        )

    if not total_xp:
        total_xp = sum(language["xp"] for language in languages)

    return {
        "username": username,
        "total_xp": int(total_xp),
        "streak": user.site_streak,
        "languages": languages,
    }


def build_weekly_series(
    database: dict[str, DatabaseEntry], days: int
) -> tuple[list[str], list[int]]:
    dates = sorted(database.keys())
    recent_dates = dates[-days:]
    values = [database[date].xp_today for date in recent_dates]
    return recent_dates, values


def write_card_svg(
    svg_path: str, profile: dict[str, Any], database: dict[str, DatabaseEntry]
) -> None:
    dates, values = build_weekly_series(database, 7)
    max_value = 900
    chart_left, chart_right = 70, 560
    chart_top, chart_bottom = 140, 250
    step = (chart_right - chart_left) / 6 if len(values) > 1 else 0
    points = []
    for index, value in enumerate(values):
        clamped = min(int(value), max_value)
        ratio = clamped / max_value if max_value else 0
        x = chart_left + step * index
        y = chart_bottom - ratio * (chart_bottom - chart_top)
        points.append((x, y))

    def day_letter(date_str: str) -> str:
        return datetime.strptime(date_str, "%Y/%m/%d").strftime("%a")[0]

    total_weekly = sum(values)
    username = profile.get("username", "username")
    streak = profile.get("streak", 0)
    total_xp = profile.get("total_xp", 0)
    languages = profile.get("languages", [])

    svg_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg width="600" height="300" viewBox="0 0 600 300" xmlns="http://www.w3.org/2000/svg">',
        '<rect x="0.5" y="0.5" width="599" height="299" rx="16" fill="#1F1F1F" stroke="#3A3A3A" />',
        '<text x="36" y="34" fill="#AAAAAA" font-size="12" font-family="DIN Round Pro, system-ui, sans-serif">DuoStats</text>',
        f'<text x="36" y="70" fill="#FFFFFF" font-size="20" font-family="DIN Round Pro, system-ui, sans-serif">@{username}</text>',
    ]

    svg_lines.append(create_svg_group(
        path.join("web", "Images", "Streak.svg"), 23, 86, 23, 23))

    stats = [
        (36, "Streak", f"{streak} days", "#FF4B00", "flame"),
        (236, "Total XP", f"{total_xp}", "#78C800", "bolt"),
        (450, "Languages", "", "#AAAAAA", "globe"),
    ]
    for x, label, value, color, icon in stats:
        if icon == "flame":
            pass
        elif icon == "star":
            svg_lines.append(
                f'<polygon points="{x} 86 {x+4} 94 {x+13} 95 {x+6} 101 {x+8} 110 {x} 105 {x-8} 110 {x-6} 101 {x-13} 95 {x-4} 94" fill="{color}" />'
            )
        elif icon == "bolt":
            svg_lines.append(
                f'<path d="M{x+4} 84 {x-6} 100h8l-2 14 12-16h-8l2-14z" fill="{color}" />'
            )
        elif icon == "globe":
            svg_lines.append(
                create_svg_group(
                    path.join("web", "Images", "Languages.svg"), 415, 85, 800, 800)
            )
        svg_lines.append(
            f'<text x="{452 if label == "Languages" else x+14}" y="92" fill="#AAAAAA" font-size="10" font-family="DIN Round Pro, system-ui, sans-serif">{label}</text>'
        )
        if value:
            svg_lines.append(
                f'<text x="{x+14}" y="108" fill="#FFFFFF" font-size="12" font-family="DIN Round Pro, system-ui, sans-serif">{value}</text>'
            )

    if languages:
        preferred_order = ["Japanese", "English"]
        ordered = sorted(
            languages,
            key=lambda language: (
                preferred_order.index(language.get("name"))
                if language.get("name") in preferred_order
                else 99
            ),
        )
        start_x = 452
        y = 100
        for index, language in enumerate(ordered[:2]):
            name = language.get("name", "Unknown")
            file_name = name.replace(" ", "") + ".svg"
            x = start_x + index * 30
            svg_lines.append(
                create_svg_group(
                    path.join("web", "Images", file_name), x, y, 25, 15
                )
            )

    svg_lines.extend(
        [
            '<g stroke="#3A3A3A" stroke-width="1">',
            '<line x1="70" y1="250" x2="560" y2="250" />',
            '<line x1="70" y1="210" x2="560" y2="210" />',
            '<line x1="70" y1="170" x2="560" y2="170" />',
            '<line x1="70" y1="130" x2="560" y2="130" />',
            "</g>",
            '<g fill="#AAAAAA" font-size="10" font-family="DIN Round Pro, system-ui, sans-serif">',
            '<text x="30" y="254">0</text>',
            '<text x="24" y="214">300</text>',
            '<text x="24" y="174">600</text>',
            '<text x="24" y="134">900</text>',
            "</g>",
        ]
    )

    polyline_points = " ".join(f"{x},{y}" for x, y in points)
    svg_lines.append(
        f'<polyline points="{polyline_points}" fill="none" stroke="#1DB0F6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />'
    )
    for x, y in points:
        svg_lines.append(
            f'<circle cx="{x}" cy="{y}" r="3.5" fill="#1DB0F6" />')

    for index, date_str in enumerate(dates):
        label = day_letter(date_str)
        x = chart_left + step * index
        svg_lines.append(
            f'<text x="{x}" y="272" fill="#AAAAAA" font-size="10" text-anchor="middle" font-family="DIN Round Pro, system-ui, sans-serif">{label}</text>'
        )

    svg_lines.extend(
        [
            '<circle cx="70" cy="284" r="4" fill="#1DB0F6" />',
            f'<text x="82" y="288" fill="#AAAAAA" font-size="10" font-family="DIN Round Pro, system-ui, sans-serif">{username}</text>',
            f'<text x="560" y="288" fill="#AAAAAA" font-size="10" text-anchor="end" font-family="DIN Round Pro, system-ui, sans-serif">{total_weekly} XP</text>',
            "</svg>",
        ]
    )

    with open(svg_path, "w", encoding="UTF-8") as svg_file:
        svg_file.write("\n".join(svg_lines))


def run() -> tuple[bool, bool]:
    # Initialize environment.
    base_api_url = "https://www.duolingo.com"
    username = environ["DUOLINGO_USERNAME"]
    credential, passwordless = (
        (credential, True)
        if (credential := environ.get("DUOLINGO_JWT")) is not None
        else (environ["DUOLINGO_PASSWORD"], False)
    )

    # Declare paths.
    progression_database_path = path.join("data", "duolingo-progress.json")
    statistics_database_path = path.join("data", "statistics.json")
    profile_database_path = path.join("data", "profile.json")
    card_svg_path = path.join("web", "card.svg")

    # Initialize required infrastructures.
    api = APIClient(base_url=base_api_url)
    progression_database = Database(filename=progression_database_path)
    statistics_database = Database(filename=statistics_database_path)
    profile_database = Database(filename=profile_database_path)

    # If the supplied credential is the password, login to Duolingo first.
    token, passwordless = (
        (credential, True) if passwordless else (
            api.login(username, credential), False)
    )

    # Get the possible data.
    raw_user, raw_summary = api.fetch_data(username, token)

    # Transform them into our internal schema.
    user = User(**raw_user)
    summaries = [Summary(**summary) for summary in raw_summary["summaries"]]
    profile = build_profile(raw_user, user)

    # Get all existing data from the database. Add the new data to the end of the database
    # declaratively. `0` means the first entry, or today (when the script is run). Initially,
    # we try to transform the existing data from the database into our own structure so it's easier
    # to process.
    current_progression = progression_database.get()
    database_entries: dict[str, DatabaseEntry] = {
        **{key: DatabaseEntry(**entry) for key, entry in current_progression.items()},
        **{summaries[0].date: DatabaseEntry.create(summaries[0], user.site_streak)},
    }

    # Synchronize the database with the summaries.
    synchronized_database = sync_database_with_summaries(
        database_entries, summaries)

    # Check whether we have synchronized the data or not.
    is_database_changed = check_database_change(
        synchronized_database, database_entries)

    # Store the synchronized database in our repository.
    progression_database.set(
        {key: value.model_dump() for key, value in synchronized_database.items()}
    )

    # On the other hand, get all of the statistics of the cron run, and then immutably
    # add the current cron statistics.
    current_date = datetime.now().strftime("%Y/%m/%d")
    current_time = datetime.now().strftime("%H:%M:%S")
    current_statistics = statistics_database.get()
    statistics_entries: dict[str, str] = {
        **current_statistics,
        **{current_date: current_time},
    }

    # Store the statistics in our repository.
    statistics_database.set(statistics_entries)

    # Store the profile data used for the public card.
    profile_database.set(profile)

    # Render the SVG card for static access.
    write_card_svg(card_svg_path, profile, synchronized_database)

    # Return flags from the program to consolidate the print statements in the outer loop,
    # minimizing side effects.
    return passwordless, is_database_changed


def main() -> None:
    log("Script is starting and running now.")
    try:
        passwordless, is_database_changed = run()
        match passwordless:
            case True:
                log("Script authenticated with your JWT.")
            case False:
                log("Script authenticated with your password. Please change it to JWT.")

        match is_database_changed:
            case True:
                log(
                    "Script found discrepancies between current data and online data. Synchronization is done automatically."
                )
            case False:
                log(
                    "Script did not find discrepancies between current data and online data. Synchronization not required."
                )

        log(
            "Script run successfully! Please check the specified path to see your newly updated data."
        )
    except ValidationError as error:
        log(
            f"Error encountered when parsing data. Potentially, a breaking API change: {error}"
        )
    except (
        CaptchaException,
        LoginException,
        NotFoundException,
        UnauthorizedException,
    ) as error:
        log(f"{error.__class__.__name__}: {error}")
    except Exception as error:
        log(f"Unexpected Exception: {error.__class__.__name__}: {error}")
        log(format_exc())
    finally:
        log("Japanese Duolingo Visualizer script has finished running.")


if __name__ == "__main__":
    main()
