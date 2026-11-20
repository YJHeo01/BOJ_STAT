def format_stat(value: int | str | None) -> str:
    return "—" if value is None else str(value)
