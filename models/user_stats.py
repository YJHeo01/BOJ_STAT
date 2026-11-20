from __future__ import annotations

from dataclasses import dataclass, replace
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
    solvedCount: int | None = None
    createdCount: str | None = None
    reviewedCount: str | None = None
    fixedCount: int | None = None
    voteCount: int | None = None
    tier: int | None = None
    classValue: int | None = None
    date: Optional[str] = None
    boj_updated_on: str | None = None
    solved_updated_on: str | None = None
    boj_solved_count: int | None = None
    solved_solved_count: int | None = None

    @classmethod
    def empty(cls, handle: str, date: Optional[str] = None) -> "UserStats":
        return cls(handle=handle, date=date)

    @classmethod
    def from_db_row(cls, row: Sequence[object]) -> "UserStats":
        # Before independent refreshes, a real date meant both lookups succeeded.
        last_full_date = row[8] if row[8] != DEFAULT_CACHE_DATE else None
        boj_date, solved_date, boj_count, solved_count = row[9:13]
        boj_date = boj_date or last_full_date
        solved_date = solved_date or last_full_date
        return cls(
            handle=row[0],
            solvedCount=row[1] if boj_date or solved_date else None,
            createdCount=row[2] if boj_date else None,
            reviewedCount=row[3] if boj_date else None,
            fixedCount=row[4] if boj_date else None,
            voteCount=row[5] if solved_date else None,
            tier=row[6] if solved_date else None,
            classValue=row[7] if solved_date else None,
            date=row[8],
            boj_updated_on=boj_date,
            solved_updated_on=solved_date,
            boj_solved_count=boj_count,
            solved_solved_count=solved_count,
        )

    def apply_refresh(
        self, current_date: str, boj_data: BojUserData | None, solved_data: SolvedUserData | None
    ) -> "UserStats":
        stats = self
        if boj_data is not None:
            stats = replace(
                stats,
                createdCount=boj_data.createdCount,
                reviewedCount=boj_data.reviewedCount,
                fixedCount=boj_data.fixedCount,
                boj_solved_count=boj_data.solvedCount,
                boj_updated_on=current_date,
            )
        if solved_data is not None:
            stats = replace(
                stats,
                voteCount=solved_data.voteCount,
                tier=solved_data.tier,
                classValue=solved_data.classValue,
                solved_solved_count=solved_data.solvedCount,
                solved_updated_on=current_date,
            )

        counts = [n for n in (stats.boj_solved_count, stats.solved_solved_count) if n is not None]
        # Legacy rows contain only the merged count. Retain it until both raw counts exist.
        legacy_boj_count = stats.boj_updated_on is not None and stats.boj_solved_count is None
        legacy_solved_count = stats.solved_updated_on is not None and stats.solved_solved_count is None
        if self.solvedCount is not None and (legacy_boj_count or legacy_solved_count):
            counts.append(self.solvedCount)
        full_date = current_date if stats.boj_updated_on == stats.solved_updated_on == current_date else self.date
        return replace(stats, solvedCount=max(counts, default=None), date=full_date)

    def to_insert_params(self) -> tuple[object, ...]:
        # Keep the original nine columns readable by older versions of the badge server.
        # Source dates distinguish these placeholder zeroes from observed zeroes.
        return (
            self.handle,
            self.solvedCount or 0,
            self.createdCount or "0",
            self.reviewedCount or "0",
            self.fixedCount or 0,
            self.voteCount or 0,
            self.tier or 0,
            self.classValue or 0,
            self.date,
        )
