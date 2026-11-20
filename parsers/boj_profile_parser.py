import logging

from bs4 import BeautifulSoup

from models.user_stats import BojUserData

logger = logging.getLogger(__name__)

SOLVED_COUNT_LABEL = "맞은 문제"
CREATED_COUNT_LABEL = "만든 문제"
REVIEWED_COUNT_LABEL = "문제를 검수"
FIXED_COUNT_LABELS = (
    "번역한 문제",
    "오타를 찾음",
    "잘못된 데이터를 찾음",
    "잘못된 조건을 찾음",
    "데이터를 추가",
    "문제를 각색",
    "빠진 조건을 찾음",
    "잘못된 번역을 찾음",
    "데이터를 만듦",
    "어색한 표현을 찾음",
    "스페셜 저지를 만듦",
    "시간 제한을 수정",
    "메모리 제한을 수정",
    "문제를 재창조",
    "스페셜 저지 오류를 찾음",
    "내용을 추가",
    "문제를 다시 작성",
    "입력 형식 오류를 찾음",
)


class BojProfileParser:
    def parse(self, html: str) -> BojUserData:
        try:
            soup = BeautifulSoup(html, "html.parser")
            # A profile always has this row, even when the user has solved zero problems.
            solved_count = int(self._find_raw_value(soup, SOLVED_COUNT_LABEL, required=True))
            created_count = self._find_raw_value(soup, CREATED_COUNT_LABEL)
            reviewed_count = self._find_raw_value(soup, REVIEWED_COUNT_LABEL)
            fixed_count = sum(self._find_count(soup, label) for label in FIXED_COUNT_LABELS)
            return BojUserData(
                solvedCount=solved_count,
                createdCount=created_count,
                reviewedCount=reviewed_count,
                fixedCount=fixed_count,
            )
        except ValueError as exc:
            logger.warning("Could not read BOJ profile statistics: %s", exc)
            return BojUserData.failure()

    @staticmethod
    def _find_raw_value(soup: BeautifulSoup, label: str, *, required: bool = False) -> str:
        tag = next(
            (candidate for candidate in soup.find_all("th") if candidate.get_text(strip=True) == label),
            None,
        )
        if tag is None:
            if required:
                raise ValueError(f"missing profile row: {label}")
            return "0"
        sibling = tag.find_next_sibling("td")
        value = sibling.get_text(strip=True) if sibling is not None else ""
        if not value:
            raise ValueError(f"missing count for profile row: {label}")
        return value

    def _find_count(self, soup: BeautifulSoup, label: str) -> int:
        return int(self._find_raw_value(soup, label))
