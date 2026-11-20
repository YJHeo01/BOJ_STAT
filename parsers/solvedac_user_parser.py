from models.user_stats import SolvedUserData

SQLITE_MAX_INTEGER = (1 << 63) - 1


def _integer(value: object, field: str, maximum: int = SQLITE_MAX_INTEGER) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError(f"Invalid {field} in solved.ac profile")
    return value


class SolvedAcUserParser:
    def parse(self, information: object) -> SolvedUserData:
        if not isinstance(information, dict):
            raise ValueError("Expected a solved.ac profile object")
        if not {"solvedCount", "voteCount", "tier", "class"}.issubset(information):
            raise ValueError("Missing required solved.ac profile fields")

        tier = information["tier"]
        return SolvedUserData(
            solvedCount=_integer(information["solvedCount"], "solvedCount"),
            voteCount=_integer(information["voteCount"], "voteCount"),
            tier=0 if tier is None else _integer(tier, "tier", maximum=31),
            classValue=_integer(information["class"], "class", maximum=10) * 3,
        )
