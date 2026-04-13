from __future__ import annotations

# nflverse combine `school` strings -> CFBD `team` query parameter (school display name).
# CFBD uses full names like "Ohio State"; combine often abbreviates.
COMBINE_SCHOOL_TO_CFBD_TEAM: dict[str, str] = {
    "Ohio St.": "Ohio State",
    "Florida St.": "Florida State",
    "Michigan St.": "Michigan State",
    "Arizona St.": "Arizona State",
    "Iowa St.": "Iowa State",
    "Kansas St.": "Kansas State",
    "Oregon St.": "Oregon State",
    "Washington St.": "Washington State",
    "Oklahoma St.": "Oklahoma State",
    "Colorado St.": "Colorado State",
    "Boise St.": "Boise State",
    "Fresno St.": "Fresno State",
    "Georgia St.": "Georgia State",
    "North Carolina St.": "NC State",
    "Mississippi St.": "Mississippi State",
    "South Dakota St.": "South Dakota State",
    "North Dakota St.": "North Dakota State",
    "Boston Col.": "Boston College",
    "Central Florida": "UCF",
    "Mississippi": "Ole Miss",
    "Southern Mississippi": "Southern Miss",
    "Penn St.": "Penn State",
    "Virginia St.": "Virginia State",
    "Southeast Missouri St.": "Southeast Missouri State",
}


def cfbd_team_for_combine_school(school: str) -> str:
    s = (school or "").strip()
    return COMBINE_SCHOOL_TO_CFBD_TEAM.get(s, s)
