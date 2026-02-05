"""Data-layer exceptions for missing data or schema issues."""


class SeasonNotAvailableError(Exception):
    """Raised when no rows exist for the requested year/season_type (e.g. data not published yet)."""

    def __init__(self, message: str, year: int | None = None, season_type: str | None = None) -> None:
        super().__init__(message)
        self.year = year
        self.season_type = season_type


class MissingColumnsError(Exception):
    """Raised when PBP is missing columns required for a specific key or feature."""

    def __init__(
        self,
        message: str,
        *,
        missing_columns: list[str] | None = None,
        context: str | None = None,
    ) -> None:
        super().__init__(message)
        self.missing_columns = missing_columns or []
        self.context = context or ""
