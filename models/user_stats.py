from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

DEFAULT_CACHE_DATE = "2000-01-01"


@dataclass(frozen=True)
class BojUserData:
    solvedCount: int = -1
    createdCount: str = "-1"
    reviewedCount: str = "-1"
    fixedCount: int = -1

    @classmethod
    def failure(cls) -> "BojUserData":
        return cls()

    @property
    def is_failure(self) -> bool:
        return self.fixedCount < 0


@dataclass(frozen=True)
class SolvedUserData:
    solvedCount: int = 0
    voteCount: int = 0
    tier: int = 0
    classValue: int = 0

    @classmethod
    def failure(cls) -> "SolvedUserData":
        return cls(solvedCount=-1, voteCount=-1, tier=-1, classValue=-1)

    @property
    def has_error(self) -> bool:
        return min(self.solvedCount, self.voteCount, self.tier, self.classValue) < 0


@dataclass(frozen=True)
class UserStats:
    handle: str
    solvedCount: int = 0
    createdCount: str = "0"
    reviewedCount: str = "0"
    fixedCount: int = 0
    voteCount: int = 0
    tier: int = 0
    classValue: int = 0
    date: Optional[str] = None

    @classmethod
    def empty(cls, handle: str, date: Optional[str] = None) -> "UserStats":
        return cls(handle=handle, date=date)

    @classmethod
    def from_db_row(cls, row: Sequence[object]) -> "UserStats":
        return cls(
            handle=row[0],
            solvedCount=row[1],
            createdCount=row[2],
            reviewedCount=row[3],
            fixedCount=row[4],
            voteCount=row[5],
            tier=row[6],
            classValue=row[7],
            date=row[8],
        )

    @classmethod
    def from_sources(
        cls,
        handle: str,
        boj_data: BojUserData,
        solved_data: SolvedUserData,
        date: str,
    ) -> "UserStats":
        return cls(
            handle=handle,
            solvedCount=max(boj_data.solvedCount, solved_data.solvedCount),
            createdCount=boj_data.createdCount,
            reviewedCount=boj_data.reviewedCount,
            fixedCount=boj_data.fixedCount,
            voteCount=solved_data.voteCount,
            tier=solved_data.tier,
            classValue=solved_data.classValue,
            date=date,
        )

    def is_stale(self, current_date: str) -> bool:
        return self.date != current_date

    def to_insert_params(self) -> tuple[object, ...]:
        return (
            self.handle,
            self.solvedCount,
            self.createdCount,
            self.reviewedCount,
            self.fixedCount,
            self.voteCount,
            self.tier,
            self.classValue,
            self.date,
        )

    def to_update_params(self) -> tuple[object, ...]:
        return (
            self.solvedCount,
            self.createdCount,
            self.reviewedCount,
            self.fixedCount,
            self.voteCount,
            self.tier,
            self.classValue,
            self.date,
            self.handle,
        )
