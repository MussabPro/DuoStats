from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BaseSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class Summary(BaseSchema):
    date: str = Field(alias="date")
    gained_xp: int = Field(alias="gainedXp")
    num_sessions: int = Field(alias="numSessions")
    total_session_time: int = Field(alias="totalSessionTime")

    @field_validator("gained_xp", "num_sessions", "total_session_time", mode="before")
    @classmethod
    def default_none_to_zero(cls, raw: int | None) -> int:
        return 0 if raw is None else int(raw)

    @field_validator("date", mode="before")
    @classmethod
    def unix_timestamp_transform(cls, raw: int | str) -> str:
        return (
            raw
            if isinstance(raw, str)
            else datetime.fromtimestamp(raw).strftime("%Y/%m/%d")
        )

    @staticmethod
    def create_default(date: str) -> "Summary":
        return Summary(
            date=date,
            gainedXp=0,
            numSessions=0,
            totalSessionTime=0,
        )


class User(BaseSchema):
    site_streak: int = Field(alias="siteStreak")


class DatabaseEntry(BaseSchema):
    xp_today: int
    number_of_sessions: int
    session_time: int
    streak: int

    @staticmethod
    def create(summary: Summary, streak: int) -> "DatabaseEntry":
        return DatabaseEntry(
            xp_today=summary.gained_xp,
            number_of_sessions=summary.num_sessions,
            session_time=summary.total_session_time,
            streak=streak,
        )

    @staticmethod
    def create_default(streak: int) -> "DatabaseEntry":
        return DatabaseEntry(
            xp_today=0,
            number_of_sessions=0,
            session_time=0,
            streak=streak,
        )
