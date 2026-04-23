import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

const DRAFT_ORDER = [
  { pick: 1, team: "Las Vegas Raiders", abbr: "LV" },
  { pick: 2, team: "New York Jets", abbr: "NYJ" },
  { pick: 3, team: "Arizona Cardinals", abbr: "ARI" },
  { pick: 4, team: "Tennessee Titans", abbr: "TEN" },
  { pick: 5, team: "New York Giants", abbr: "NYG" },
  { pick: 6, team: "Cleveland Browns", abbr: "CLE" },
  { pick: 7, team: "Washington Commanders", abbr: "WSH" },
  { pick: 8, team: "New Orleans Saints", abbr: "NO" },
  { pick: 9, team: "Kansas City Chiefs", abbr: "KC" },
  { pick: 10, team: "Cincinnati Bengals", abbr: "CIN" },
  { pick: 11, team: "Miami Dolphins", abbr: "MIA" },
  { pick: 12, team: "Dallas Cowboys", abbr: "DAL" },
  { pick: 13, team: "Los Angeles Rams", abbr: "LAR" },
  { pick: 14, team: "Baltimore Ravens", abbr: "BAL" },
  { pick: 15, team: "Tampa Bay Buccaneers", abbr: "TB" },
  { pick: 16, team: "Atlanta Falcons", abbr: "ATL" },
  { pick: 17, team: "Detroit Lions", abbr: "DET" },
  { pick: 18, team: "Minnesota Vikings", abbr: "MIN" },
  { pick: 19, team: "Carolina Panthers", abbr: "CAR" },
  { pick: 20, team: "Indianapolis Colts", abbr: "IND" },
  { pick: 21, team: "Pittsburgh Steelers", abbr: "PIT" },
  { pick: 22, team: "Los Angeles Chargers", abbr: "LAC" },
  { pick: 23, team: "Philadelphia Eagles", abbr: "PHI" },
  { pick: 24, team: "Green Bay Packers", abbr: "GB" },
  { pick: 25, team: "Chicago Bears", abbr: "CHI" },
  { pick: 26, team: "Buffalo Bills", abbr: "BUF" },
  { pick: 27, team: "San Francisco 49ers", abbr: "SF" },
  { pick: 28, team: "Houston Texans", abbr: "HOU" },
  { pick: 29, team: "Jacksonville Jaguars", abbr: "JAX" },
  { pick: 30, team: "Denver Broncos", abbr: "DEN" },
  { pick: 31, team: "New England Patriots", abbr: "NE" },
  { pick: 32, team: "Seattle Seahawks", abbr: "SEA" },
];

const PROSPECTS = [
  {
    id: "reese",
    name: "Arvell Reese",
    pos: "EDGE",
    school: "Ohio State",
    rank: 1,
    posRank: "EDGE1",
    grade: 92,
    forty: "N/A",
    weight: 238,
    height: "6'4\"",
    notes:
      "Scouts Inc. #1. Hybrid LB/EDGE, 6.5 sacks + 46 pressures in 2025, elite sideline-to-sideline range.",
  },
  {
    id: "mendoza",
    name: "Fernando Mendoza",
    pos: "QB",
    school: "Indiana",
    rank: 2,
    posRank: "QB1",
    grade: 92,
    forty: "N/A",
    weight: 220,
    height: "6'3\"",
    notes:
      "Heisman winner, 72% completion rate, unanimous QB1. Lock for pick 1 to Raiders.",
  },
  {
    id: "bailey",
    name: "David Bailey",
    pos: "EDGE",
    school: "Texas Tech",
    rank: 3,
    posRank: "EDGE2",
    grade: 92,
    forty: "4.50",
    weight: 258,
    height: "6'5\"",
    notes:
      "Tied FBS lead 14.5 sacks 2025, polished pass rusher, 33.75\" arms.",
  },
  {
    id: "love",
    name: "Jeremiyah Love",
    pos: "RB",
    school: "Notre Dame",
    rank: 4,
    posRank: "RB1",
    grade: 91,
    forty: "4.43",
    weight: 210,
    height: "5'11\"",
    notes:
      "1,372 rush yards, 18 TDs, 64 career catches — elite three-down back.",
  },
  {
    id: "mauigoa",
    name: "Francis Mauigoa",
    pos: "OT",
    school: "Miami (FL)",
    rank: 5,
    posRank: "OT1",
    grade: 91,
    forty: "N/A",
    weight: 336,
    height: "6'6\"",
    notes:
      "OT1 consensus, three-year starter, elite run-blocking force and power.",
  },
  {
    id: "downs",
    name: "Caleb Downs",
    pos: "S",
    school: "Ohio State",
    rank: 6,
    posRank: "S1",
    grade: 91,
    forty: "4.45",
    weight: 206,
    height: "6'0\"",
    notes:
      "Jim Thorpe Award, unanimous All-American, elite range and tackling — comp: Budda Baker.",
  },
  {
    id: "styles",
    name: "Sonny Styles",
    pos: "LB",
    school: "Ohio State",
    rank: 7,
    posRank: "LB1",
    grade: 91,
    forty: "4.52",
    weight: 244,
    height: "6'4\"",
    notes:
      "21.5 TFL over 3 seasons, coverage ability rare for his size, elite athlete.",
  },
  {
    id: "delane",
    name: "Mansoor Delane",
    pos: "CB",
    school: "LSU",
    rank: 8,
    posRank: "CB1",
    grade: 89,
    forty: "4.38",
    weight: 192,
    height: "6'1\"",
    notes:
      "Allowed only 10 completions for 119 yards in 2025, unanimous CB1.",
  },
  {
    id: "bain",
    name: "Rueben Bain Jr.",
    pos: "EDGE",
    school: "Miami (FL)",
    rank: 9,
    posRank: "EDGE3",
    grade: 89,
    forty: "4.55",
    weight: 268,
    height: "6'3\"",
    notes:
      "9.5 sacks, sub-31\" arms are only knock, elite motor and get-off.",
  },
  {
    id: "lemon",
    name: "Makai Lemon",
    pos: "WR",
    school: "USC",
    rank: 10,
    posRank: "WR1",
    grade: 89,
    forty: "4.43",
    weight: 191,
    height: "5'10\"",
    notes:
      "WR1 consensus, 1,156 rec yards 11 TDs, slot-routes master — comp: Amon-Ra St. Brown.",
  },
  {
    id: "sadiq",
    name: "Kenyon Sadiq",
    pos: "TE",
    school: "Oregon",
    rank: 11,
    posRank: "TE1",
    grade: 89,
    forty: "4.39",
    weight: 241,
    height: "6'3\"",
    notes:
      "TE1 unanimous. 4.39 combine record for TE. 51 rec/560 yds/8 TDs. Historic athlete.",
  },
  {
    id: "tyson",
    name: "Jordyn Tyson",
    pos: "WR",
    school: "Arizona State",
    rank: 12,
    posRank: "WR2",
    grade: 89,
    forty: "4.40",
    weight: 198,
    height: "6'2\"",
    notes:
      "Biletnikoff Award winner, elite contested catch, hamstring kept him from combine testing.",
  },
  {
    id: "tate",
    name: "Carnell Tate",
    pos: "WR",
    school: "Ohio State",
    rank: 13,
    posRank: "WR3",
    grade: 89,
    forty: "4.48",
    weight: 195,
    height: "6'2\"",
    notes:
      "Zero drops in 2025, 51 rec/875 yds/9 TDs, precise route runner in OSU pipeline.",
  },
  {
    id: "freeling",
    name: "Monroe Freeling",
    pos: "OT",
    school: "Georgia",
    rank: 14,
    posRank: "OT2",
    grade: 88,
    forty: "5.05",
    weight: 312,
    height: "6'6\"",
    notes:
      "Long, athletic tackle — high ceiling despite only 18 college starts.",
  },
  {
    id: "ioane",
    name: "Olaivavega Ioane",
    pos: "IOL",
    school: "Penn State",
    rank: 15,
    posRank: "IOL1",
    grade: 88,
    forty: "N/A",
    weight: 336,
    height: "6'4\"",
    notes:
      "Played LG, C, and RG in college — rare interior versatility, power run blocker.",
  },
  {
    id: "mccoy",
    name: "Jermod McCoy",
    pos: "CB",
    school: "Tennessee",
    rank: 16,
    posRank: "CB2",
    grade: 88,
    forty: "4.41",
    weight: 188,
    height: "6'0\"",
    notes:
      "Missed 2025 with knee injury; legitimate CB1 when healthy. All-American 2024.",
  },
  {
    id: "proctor",
    name: "Kadyn Proctor",
    pos: "OT",
    school: "Alabama",
    rank: 17,
    posRank: "OT3",
    grade: 88,
    forty: "5.10",
    weight: 352,
    height: "6'7\"",
    notes:
      "Mammoth frame, 40 career starts, 3 sacks allowed 2025 — comp: Tyler Guyton.",
  },
  {
    id: "mesidor",
    name: "Akheem Mesidor",
    pos: "EDGE",
    school: "Miami (FL)",
    rank: 18,
    posRank: "EDGE4",
    grade: 88,
    forty: "4.65",
    weight: 262,
    height: "6'3\"",
    notes:
      "12.5 sacks 2025, polished repertoire, 25 on draft day — veteran-ready rusher.",
  },
  {
    id: "fano",
    name: "Spencer Fano",
    pos: "OT",
    school: "Utah",
    rank: 19,
    posRank: "OT4",
    grade: 88,
    forty: "4.91",
    weight: 311,
    height: "6'5\"",
    notes:
      "Outland Trophy winner, elite athlete for position, can play all 5 OL spots.",
  },
  {
    id: "thieneman",
    name: "Dillon Thieneman",
    pos: "S",
    school: "Oregon",
    rank: 20,
    posRank: "S2",
    grade: 88,
    forty: "4.35",
    weight: 201,
    height: "6'0\"",
    notes:
      "S2 consensus. 300+ career tackles, 8 INTs at Purdue+Oregon. 4.35 combine speed.",
  },
  {
    id: "mcneil",
    name: "Emmanuel McNeil-Warren",
    pos: "S",
    school: "Toledo",
    rank: 21,
    posRank: "S3",
    grade: 87,
    forty: "4.52",
    weight: 201,
    height: "6'3\"",
    notes:
      "PFF #1 coverage safety 2025 (92.0 grade), 9 career forced fumbles, 6'3\" enforcer.",
  },
  {
    id: "terrell",
    name: "Avieon Terrell",
    pos: "CB",
    school: "Clemson",
    rank: 22,
    posRank: "CB3",
    grade: 87,
    forty: "4.63",
    weight: 187,
    height: "5'11\"",
    notes:
      "Elite IQ, zone specialist — ran mid-4.6 at pro day which may cause slide.",
  },
  {
    id: "boston",
    name: "Denzel Boston",
    pos: "WR",
    school: "Washington",
    rank: 23,
    posRank: "WR4",
    grade: 87,
    forty: "4.44",
    weight: 205,
    height: "6'3\"",
    notes:
      "Big-bodied boundary WR, contested catch specialist, plus YAC ability.",
  },
  {
    id: "cooper",
    name: "Omar Cooper Jr.",
    pos: "WR",
    school: "Indiana",
    rank: 24,
    posRank: "WR5",
    grade: 87,
    forty: "4.48",
    weight: 215,
    height: "6'2\"",
    notes:
      "13 TDs 2025, dense frame, slot-to-boundary versatility — Panthers had 30-visit.",
  },
  {
    id: "faulk",
    name: "Keldric Faulk",
    pos: "EDGE",
    school: "Auburn",
    rank: 25,
    posRank: "EDGE5",
    grade: 87,
    forty: "4.68",
    weight: 262,
    height: "6'6\"",
    notes:
      "6'6\", 32\" arms, high-motor developmental pass rusher with elite frame.",
  },
  {
    id: "mcdonald",
    name: "Kayden McDonald",
    pos: "IDL",
    school: "Ohio State",
    rank: 26,
    posRank: "IDL1",
    grade: 87,
    forty: "4.93",
    weight: 316,
    height: "6'3\"",
    notes:
      "Interior disruptor from OSU pipeline, multiple top-30 visits from teams.",
  },
  {
    id: "woods",
    name: "Peter Woods",
    pos: "IDL",
    school: "Clemson",
    rank: 27,
    posRank: "IDL2",
    grade: 87,
    forty: "N/A",
    weight: 299,
    height: "6'3\"",
    notes:
      "3-technique pass rusher, excellent get-off — stock slightly down after 2025.",
  },
  {
    id: "lomu",
    name: "Caleb Lomu",
    pos: "OT",
    school: "Utah",
    rank: 28,
    posRank: "OT5",
    grade: 87,
    forty: "5.15",
    weight: 328,
    height: "6'6\"",
    notes:
      "Utah's other first-round OT. Powerful run blocker, played alongside Fano.",
  },
  {
    id: "young",
    name: "Zion Young",
    pos: "EDGE",
    school: "Missouri",
    rank: 29,
    posRank: "EDGE6",
    grade: 86,
    forty: "4.62",
    weight: 255,
    height: "6'6\"",
    notes:
      "6.5 sacks + 46 pressures 2025, powerful with elite motor — Kiper R1 pick.",
  },
  {
    id: "howell",
    name: "Cashius Howell",
    pos: "EDGE",
    school: "Texas A&M",
    rank: 30,
    posRank: "EDGE7",
    grade: 86,
    forty: "4.58",
    weight: 248,
    height: "6'4\"",
    notes:
      "Led SEC with 11.5 sacks, twitchy with elite first step — multiple R1 mocks.",
  },
  {
    id: "hood",
    name: "Colton Hood",
    pos: "CB",
    school: "Tennessee",
    rank: 31,
    posRank: "CB4",
    grade: 86,
    forty: "4.42",
    weight: 190,
    height: "6'0\"",
    notes:
      "Stepped in for injured McCoy in 2025, fluid athlete with instincts in coverage.",
  },
  {
    id: "concepcion",
    name: "KC Concepcion",
    pos: "WR",
    school: "Texas A&M",
    rank: 32,
    posRank: "WR6",
    grade: 86,
    forty: "4.41",
    weight: 188,
    height: "5'10\"",
    notes:
      "Slot-first receiver, 13-TD upside — Jeremiah mocked to Panthers at pick 19.",
  },
  {
    id: "bisontis",
    name: "Chase Bisontis",
    pos: "IOL",
    school: "Texas A&M",
    rank: 33,
    posRank: "IOL2",
    grade: 86,
    forty: "N/A",
    weight: 318,
    height: "6'4\"",
    notes:
      "Interior road-grader, fits zone and gap schemes, Miller has him 51st overall.",
  },
  {
    id: "banks",
    name: "Caleb Banks",
    pos: "IDL",
    school: "Florida",
    rank: 34,
    posRank: "IDL3",
    grade: 86,
    forty: "5.04",
    weight: 327,
    height: "6'6\"",
    notes:
      "Rare size/athleticism at DT — missed most of 2025 with foot injury, wild-card.",
  },
  {
    id: "hill",
    name: "Anthony Hill Jr.",
    pos: "LB",
    school: "Texas",
    rank: 35,
    posRank: "LB2",
    grade: 86,
    forty: "4.56",
    weight: 240,
    height: "6'2\"",
    notes:
      "Three-down linebacker with leadership qualities — Kiper LB2, Miller LB3.",
  },
  {
    id: "stowers",
    name: "Eli Stowers",
    pos: "TE",
    school: "Vanderbilt",
    rank: 36,
    posRank: "TE2",
    grade: 85,
    forty: "4.62",
    weight: 248,
    height: "6'5\"",
    notes:
      "TE2 consensus on all four ESPN boards. Record combine vertical. Zone reader.",
  },
  {
    id: "simpson",
    name: "Ty Simpson",
    pos: "QB",
    school: "Alabama",
    rank: 37,
    posRank: "QB2",
    grade: 85,
    forty: "4.68",
    weight: 215,
    height: "6'2\"",
    notes:
      "QB2 on Kiper, Miller, Reid boards. One starting season, raw upside QB.",
  },
  {
    id: "cisse",
    name: "Brandon Cisse",
    pos: "CB",
    school: "South Carolina",
    rank: 38,
    posRank: "CB5",
    grade: 85,
    forty: "4.39",
    weight: 187,
    height: "6'1\"",
    notes:
      "4.39 speed, press-man specialist, upside corner — CB4 on Kiper's board.",
  },
  {
    id: "cjohnson",
    name: "Chris Johnson",
    pos: "CB",
    school: "San Diego State",
    rank: 39,
    posRank: "CB6",
    grade: 85,
    forty: "4.40",
    weight: 184,
    height: "6'0\"",
    notes:
      "Length, speed, instincts — Kiper has him 34th overall, strong value option.",
  },
  {
    id: "branch",
    name: "Zachariah Branch",
    pos: "WR",
    school: "Georgia",
    rank: 40,
    posRank: "WR7",
    grade: 85,
    forty: "4.31",
    weight: 175,
    height: "5'10\"",
    notes:
      "4.31 combine speed, elite return specialist, gadget/vertical threat at WR.",
  },
  {
    id: "allen",
    name: "CJ Allen",
    pos: "LB",
    school: "Georgia",
    rank: 41,
    posRank: "LB3",
    grade: 84,
    forty: "4.54",
    weight: 236,
    height: "6'1\"",
    notes:
      "Georgia LB product, sideline coverage — Kiper 31st overall pick in superteam.",
  },
  {
    id: "rodriguez",
    name: "Jacob Rodriguez",
    pos: "LB",
    school: "Texas Tech",
    rank: 42,
    posRank: "LB4",
    grade: 84,
    forty: "4.58",
    weight: 232,
    height: "6'2\"",
    notes:
      "183 tackles over 2 seasons, instinctive gap-filler — Reid LB3, strong R2.",
  },
  {
    id: "dennis",
    name: "Dani Dennis-Sutton",
    pos: "EDGE",
    school: "Penn State",
    rank: 43,
    posRank: "EDGE8",
    grade: 84,
    forty: "4.68",
    weight: 258,
    height: "6'6\"",
    notes:
      "Back-to-back 8.5 sack seasons, near 11-ft broad jump at combine. Miller R2.",
  },
  {
    id: "pregnon",
    name: "Emmanuel Pregnon",
    pos: "IOL",
    school: "Oregon",
    rank: 44,
    posRank: "IOL3",
    grade: 84,
    forty: "N/A",
    weight: 318,
    height: "6'4\"",
    notes:
      "Interior guard with experience at multiple spots, powerful — Miller 52nd overall.",
  },
  {
    id: "christen",
    name: "Christen Miller",
    pos: "IDL",
    school: "Georgia",
    rank: 45,
    posRank: "IDL4",
    grade: 83,
    forty: "N/A",
    weight: 309,
    height: "6'3\"",
    notes:
      "Georgia DL pipeline product — Miller has 53rd overall, interior disruptor.",
  },
  {
    id: "lomu2",
    name: "Caleb Lomu (OT/G)",
    pos: "IOL",
    school: "Utah",
    rank: 46,
    posRank: "IOL4",
    grade: 83,
    forty: "N/A",
    weight: 328,
    height: "6'6\"",
    notes:
      "Some teams project Lomu inside as guard — scheme-dependent versatility.",
  },
  {
    id: "golday",
    name: "Jake Golday",
    pos: "LB",
    school: "Cincinnati",
    rank: 47,
    posRank: "LB5",
    grade: 83,
    forty: "4.63",
    weight: 240,
    height: "6'4\"",
    notes:
      "105 tackles 2025, senior bowl standout — Miller 67th, strong R2/R3 LB.",
  },
  {
    id: "stukes",
    name: "Treydan Stukes",
    pos: "S",
    school: "Arizona",
    rank: 48,
    posRank: "S4",
    grade: 83,
    forty: "4.41",
    weight: 196,
    height: "6'0\"",
    notes:
      "Slot-safety hybrid, elite athleticism — 25 on draft day drops him from R1.",
  },
  {
    id: "miller_ot",
    name: "Blake Miller",
    pos: "OT",
    school: "Clemson",
    rank: 49,
    posRank: "OT6",
    grade: 83,
    forty: "5.09",
    weight: 316,
    height: "6'6\"",
    notes:
      "Primarily RT, athleticism to flip left — Miller superteam pick, R2 value.",
  },
  {
    id: "williams",
    name: "Antonio Williams",
    pos: "WR",
    school: "Clemson",
    rank: 50,
    posRank: "WR8",
    grade: 83,
    forty: "4.45",
    weight: 200,
    height: "6'2\"",
    notes:
      "Big-bodied perimeter receiver, reliable hands — Miller 65th, strong R2 WR.",
  },
  {
    id: "hurst",
    name: "Ted Hurst",
    pos: "WR",
    school: "Georgia State",
    rank: 51,
    posRank: "WR9",
    grade: 83,
    forty: "4.42",
    weight: 210,
    height: "6'4\"",
    notes:
      "6'4\" frame, 99th pct broad jump, 60% contested catch rate — PFSN sleeper.",
  },
  {
    id: "bernard",
    name: "Germie Bernard",
    pos: "WR",
    school: "Alabama",
    rank: 52,
    posRank: "WR10",
    grade: 83,
    forty: "4.45",
    weight: 195,
    height: "6'1\"",
    notes:
      "Yates R2 pick in superteam, routes everywhere, elite YAC — top mid-round WR.",
  },
  {
    id: "nussmeier",
    name: "Garrett Nussmeier",
    pos: "QB",
    school: "LSU",
    rank: 53,
    posRank: "QB3",
    grade: 82,
    forty: "N/A",
    weight: 213,
    height: "6'2\"",
    notes:
      "Reid's QB pick in superteam draft — arm talent, needs development.",
  },
  {
    id: "beck",
    name: "Carson Beck",
    pos: "QB",
    school: "Miami (FL)",
    rank: 54,
    posRank: "QB4",
    grade: 82,
    forty: "N/A",
    weight: 218,
    height: "6'4\"",
    notes:
      "Kiper QB3 — familiarity with Miami OL prospects, boom-or-bust arm-talent QB.",
  },
  {
    id: "allar",
    name: "Drew Allar",
    pos: "QB",
    school: "Penn State",
    rank: 55,
    posRank: "QB5",
    grade: 82,
    forty: "N/A",
    weight: 220,
    height: "6'4\"",
    notes:
      "Kiper/Miller QB4 — experienced starter, developed at Penn State, solid floor.",
  },
  {
    id: "ponds",
    name: "D'Angelo Ponds",
    pos: "CB",
    school: "Indiana",
    rank: 56,
    posRank: "CB7",
    grade: 82,
    forty: "4.41",
    weight: 185,
    height: "6'0\"",
    notes:
      "Yates pick in superteam — corner from Indiana's title team, fluid coverage.",
  },
  {
    id: "price",
    name: "Jadarian Price",
    pos: "RB",
    school: "Notre Dame",
    rank: 57,
    posRank: "RB2",
    grade: 82,
    forty: "4.39",
    weight: 204,
    height: "5'10\"",
    notes:
      "Notre Dame RB2 behind Love — Yates pick in superteam, elite speed at position.",
  },
  {
    id: "coleman",
    name: "Jonah Coleman",
    pos: "RB",
    school: "Washington",
    rank: 58,
    posRank: "RB3",
    grade: 82,
    forty: "4.42",
    weight: 208,
    height: "5'11\"",
    notes:
      "Reid's R2 RB pick — vision and contact balance, high floor at position.",
  },
  {
    id: "washington",
    name: "Mike Washington Jr.",
    pos: "RB",
    school: "Arkansas",
    rank: 59,
    posRank: "RB4",
    grade: 81,
    forty: "4.45",
    weight: 215,
    height: "6'0\"",
    notes:
      "Miller superteam RB pick — power back with receiving ability out of backfield.",
  },
  {
    id: "klare",
    name: "Max Klare",
    pos: "TE",
    school: "Ohio State",
    rank: 60,
    posRank: "TE3",
    grade: 81,
    forty: "4.73",
    weight: 255,
    height: "6'5\"",
    notes:
      "Miller 71st overall — TE3 on all ESPN boards. Blocking-first with rec upside.",
  },
];

const TEAM_NEEDS = {
  "Las Vegas Raiders": ["QB", "EDGE"],
  "New York Jets": ["EDGE", "LB"],
  "Arizona Cardinals": ["EDGE", "OT"],
  "Tennessee Titans": ["RB", "EDGE"],
  "New York Giants": ["OT", "S"],
  "Cleveland Browns": ["WR", "OT"],
  "Washington Commanders": ["CB", "EDGE"],
  "New Orleans Saints": ["WR", "EDGE"],
  "Kansas City Chiefs": ["TE", "WR"],
  "Cincinnati Bengals": ["OT", "CB"],
  "Miami Dolphins": ["WR", "CB"],
  "Dallas Cowboys": ["CB", "LB"],
  "Los Angeles Rams": ["WR", "OT"],
  "Baltimore Ravens": ["TE", "WR"],
  "Tampa Bay Buccaneers": ["EDGE", "OT"],
  "Atlanta Falcons": ["WR", "CB"],
  "Detroit Lions": ["OT", "WR"],
  "Minnesota Vikings": ["S", "CB"],
  "Carolina Panthers": ["TE", "EDGE"],
  "Indianapolis Colts": ["OT", "CB"],
  "Pittsburgh Steelers": ["OT", "QB"],
  "Los Angeles Chargers": ["EDGE", "IOL"],
  "Philadelphia Eagles": ["WR", "EDGE"],
  "Green Bay Packers": ["WR", "LB"],
  "Chicago Bears": ["EDGE", "OT"],
  "Buffalo Bills": ["WR", "CB"],
  "San Francisco 49ers": ["EDGE", "RB"],
  "Houston Texans": ["RB", "EDGE"],
  "Jacksonville Jaguars": ["EDGE", "QB"],
  "Denver Broncos": ["WR", "CB"],
  "New England Patriots": ["QB", "WR"],
  "Seattle Seahawks": ["RB", "EDGE"],
};

/** Platform palette (gridironiq_platform.html) */
const INK = "#050709";
const SURFACE = "#131928";
const SURFACE2 = "#1a2235";
const GOLD = "#d4a843";
const GREEN = "#3ecf7a";
const AMBER = "#e67e22";
const RED = "#e05252";
const TEXT = "#dde4ef";
const TEXT2 = "#7d8fa8";
const TEXT3 = "#5c6b82";
const BORDER = "rgba(255,255,255,0.08)";

function posMatchesNeed(prospectPos, needPos) {
  const map = {
    QB: ["QB"],
    EDGE: ["EDGE"],
    LB: ["LB", "EDGE"],
    OT: ["OT", "OT/G"],
    IOL: ["IOL", "OT/G", "OG"],
    WR: ["WR"],
    TE: ["TE"],
    RB: ["RB"],
    CB: ["CB"],
    S: ["S"],
    IDL: ["IDL", "DT"],
  };
  const upper = (prospectPos || "").toUpperCase();
  return (map[needPos] || [needPos]).some((v) => upper.includes(v));
}

function projectPicks(teamName, availableProspects) {
  const needs = TEAM_NEEDS[teamName] || [];
  return availableProspects
    .map((p) => {
      let score = (60 - p.rank) * 3;
      score += p.grade * 0.8;
      if (needs[0] && posMatchesNeed(p.pos, needs[0])) score += 40;
      if (needs[1] && posMatchesNeed(p.pos, needs[1])) score += 20;
      if (["QB", "EDGE", "OT", "CB", "WR"].includes(p.pos)) score += 10;
      return { ...p, projScore: score };
    })
    .sort((a, b) => b.projScore - a.projScore)
    .slice(0, 3);
}

function posBadgeClass(pos) {
  const m = {
    QB: "bg-red-500/15 text-red-300",
    EDGE: "bg-orange-500/15 text-orange-300",
    WR: "bg-sky-500/15 text-sky-300",
    TE: "bg-teal-500/15 text-teal-300",
    OT: "bg-emerald-500/15 text-emerald-300",
    IOL: "bg-emerald-500/15 text-emerald-200",
    CB: "bg-violet-500/15 text-violet-300",
    S: "bg-indigo-500/15 text-indigo-300",
    LB: "bg-amber-500/15 text-amber-200",
    RB: "bg-pink-500/15 text-pink-300",
    IDL: "bg-zinc-500/20 text-zinc-300",
  };
  return m[pos] || "bg-zinc-500/20 text-zinc-300";
}

export default function DraftSimulator() {
  const [phase, setPhase] = useState("select-team");
  const [userPickIdx, setUserPickIdx] = useState(null);
  const [picks, setPicks] = useState(
    () => DRAFT_ORDER.map((d) => ({ ...d, prospect: null }))
  );
  const [currentIdx, setCurrentIdx] = useState(0);
  const [available, setAvailable] = useState(
    () => new Set(PROSPECTS.map((p) => p.id))
  );
  const [query, setQuery] = useState("");
  const [confirming, setConfirming] = useState(null);
  const [autoAdv, setAutoAdv] = useState(true);
  const [countdown, setCountdown] = useState(null);
  const [projections, setProjections] = useState([]);
  const [aiTopAtUserPick, setAiTopAtUserPick] = useState(null);
  const searchRef = useRef(null);
  const currentRowRef = useRef(null);
  const timerRef = useRef(null);
  const countdownRef = useRef(null);
  const currentIdxRef = useRef(0);

  const userTeamName =
    userPickIdx !== null ? DRAFT_ORDER[userPickIdx].team : null;
  const userNeeds = userTeamName ? TEAM_NEEDS[userTeamName] || [] : [];

  useEffect(() => {
    currentIdxRef.current = currentIdx;
  }, [currentIdx]);

  const availableList = useMemo(
    () => PROSPECTS.filter((p) => available.has(p.id)),
    [available]
  );

  const resetDraft = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = null;
    if (countdownRef.current) clearInterval(countdownRef.current);
    countdownRef.current = null;
    setPhase("select-team");
    setUserPickIdx(null);
    setPicks(DRAFT_ORDER.map((d) => ({ ...d, prospect: null })));
    setCurrentIdx(0);
    setAvailable(new Set(PROSPECTS.map((p) => p.id)));
    setQuery("");
    setConfirming(null);
    setAutoAdv(true);
    setCountdown(null);
    setProjections([]);
    setAiTopAtUserPick(null);
  }, []);

  const selectTeam = useCallback((idx) => {
    setUserPickIdx(idx);
    setPicks(DRAFT_ORDER.map((d) => ({ ...d, prospect: null })));
    setCurrentIdx(0);
    setAvailable(new Set(PROSPECTS.map((p) => p.id)));
    setQuery("");
    setConfirming(null);
    setCountdown(null);
    setProjections([]);
    setAiTopAtUserPick(null);
    setPhase("simulating");
  }, []);

  const lockInPick = useCallback((prospect) => {
    const idx = currentIdxRef.current;
    setPicks((prev) =>
      prev.map((p, i) => (i === idx ? { ...p, prospect } : p))
    );
    setAvailable((prev) => {
      const next = new Set(prev);
      next.delete(prospect.id);
      return next;
    });
    setConfirming(null);
    setQuery("");
    setCountdown(null);
    setCurrentIdx((prev) => prev + 1);
  }, []);

  useEffect(() => {
    if (phase === "simulating" && currentIdx >= 32) {
      setPhase("complete");
    }
  }, [currentIdx, phase]);

  useEffect(() => {
    if (phase !== "simulating" || currentIdx >= 32) return;
    const slot = picks[currentIdx];
    if (!slot) return;
    const list = PROSPECTS.filter((p) => available.has(p.id));
    const projs = projectPicks(slot.team, list);
    setProjections(projs);
  }, [currentIdx, available, phase, picks]);

  useEffect(() => {
    if (phase !== "simulating" || userPickIdx === null) return;
    if (currentIdx !== userPickIdx) return;
    const slot = picks[currentIdx];
    if (!slot) return;
    const list = PROSPECTS.filter((p) => available.has(p.id));
    const projs = projectPicks(slot.team, list);
    setAiTopAtUserPick(projs[0] || null);
  }, [currentIdx, userPickIdx, phase, available, picks]);

  useEffect(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    if (phase !== "simulating" || currentIdx >= 32) return;
    if (currentIdx === userPickIdx) return;
    if (!autoAdv) return;
    if (projections.length === 0) return;
    const top = projections[0];
    timerRef.current = setTimeout(() => {
      lockInPick(top);
    }, 1500);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = null;
    };
  }, [
    phase,
    currentIdx,
    userPickIdx,
    autoAdv,
    projections,
    lockInPick,
  ]);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (countdownRef.current) clearInterval(countdownRef.current);
    };
  }, []);

  useEffect(() => {
    if (phase !== "simulating") {
      if (countdownRef.current) {
        clearInterval(countdownRef.current);
        countdownRef.current = null;
      }
      setCountdown(null);
    }
  }, [phase]);

  useEffect(() => {
    if (
      phase === "simulating" &&
      currentIdx === userPickIdx &&
      searchRef.current
    ) {
      searchRef.current.focus();
    }
  }, [phase, currentIdx, userPickIdx]);

  useEffect(() => {
    if (currentRowRef.current && phase === "simulating") {
      currentRowRef.current.scrollIntoView({
        block: "nearest",
        behavior: "smooth",
      });
    }
  }, [currentIdx, phase]);

  const filteredProspects = useMemo(() => {
    const q = query.trim().toLowerCase();
    let list = availableList;
    if (q) {
      list = list.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.pos.toLowerCase().includes(q) ||
          p.school.toLowerCase().includes(q)
      );
    }
    return list.sort((a, b) => a.rank - b.rank).slice(0, 20);
  }, [availableList, query]);

  const onAutoPick = useCallback(() => {
    if (projections[0]) lockInPick(projections[0]);
  }, [projections, lockInPick]);

  const startCountdown = useCallback(() => {
    if (countdownRef.current) clearInterval(countdownRef.current);
    if (!projections[0]) return;
    let n = 3;
    setCountdown(n);
    countdownRef.current = setInterval(() => {
      n -= 1;
      if (n <= 0) {
        clearInterval(countdownRef.current);
        countdownRef.current = null;
        setCountdown(null);
        lockInPick(projections[0]);
      } else {
        setCountdown(n);
      }
    }, 1000);
  }, [projections, lockInPick]);

  const userPickRow = userPickIdx !== null ? picks[userPickIdx] : null;
  const userProspect = userPickRow?.prospect;

  const gradeUserPick = useMemo(() => {
    if (!userProspect || !aiTopAtUserPick) return null;
    const ai = aiTopAtUserPick;
    if (userProspect.id === ai.id) {
      return { label: "Consensus Pick 🎯", tone: "green", sub: null };
    }
    const diff = userProspect.rank - ai.rank;
    if (Math.abs(diff) <= 5) {
      return { label: "Solid Value 👍", tone: "blue", sub: null };
    }
    if (diff > 10) {
      return {
        label: "Reach ⚠️",
        tone: "amber",
        sub: `AI projected: ${ai.name}`,
      };
    }
    const needHit =
      (userNeeds[0] && posMatchesNeed(userProspect.pos, userNeeds[0])) ||
      (userNeeds[1] && posMatchesNeed(userProspect.pos, userNeeds[1]));
    const aiNeedHit =
      (userNeeds[0] && posMatchesNeed(ai.pos, userNeeds[0])) ||
      (userNeeds[1] && posMatchesNeed(ai.pos, userNeeds[1]));
    if (needHit && userProspect.id !== ai.id && !aiNeedHit) {
      return {
        label: "Value",
        tone: "blue",
        sub: "Need Pick 🔵",
      };
    }
    return { label: "On the board", tone: "gray", sub: null };
  }, [userProspect, aiTopAtUserPick, userNeeds]);

  if (phase === "select-team") {
    return (
      <div className="rounded-lg border py-10 px-4" style={{ backgroundColor: INK, borderColor: BORDER }}>
        <div className="mx-auto max-w-4xl">
          <h1 className="mb-2 text-center text-3xl font-bold tracking-tight" style={{ color: TEXT }}>
            2026 NFL Draft · Round 1
          </h1>
          <p className="mb-8 text-center font-mono text-[11px] uppercase tracking-[0.14em]" style={{ color: TEXT2 }}>
            32 picks · April 23 · Pittsburgh
          </p>
          <p className="mb-6 text-center text-sm font-medium" style={{ color: TEXT2 }}>
            Select your team — you control the board for pick 1–32
          </p>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {DRAFT_ORDER.map((d, i) => {
              const needs = TEAM_NEEDS[d.team] || [];
              return (
                <button
                  key={d.pick}
                  type="button"
                  onClick={() => selectTeam(i)}
                  className="rounded-lg border p-4 text-left transition-colors"
                  style={{
                    borderColor: BORDER,
                    backgroundColor: SURFACE,
                    color: TEXT,
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = SURFACE2;
                    e.currentTarget.style.borderColor = "rgba(212,168,67,0.35)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = SURFACE;
                    e.currentTarget.style.borderColor = BORDER;
                  }}
                >
                  <div className="text-2xl font-bold">{d.abbr}</div>
                  <div className="mt-1 text-xs opacity-80">{d.team}</div>
                  <div
                    className="mt-2 inline-block rounded px-2 py-0.5 text-xs font-bold"
                    style={{ backgroundColor: "rgba(212,168,67,0.15)", color: GOLD }}
                  >
                    Pick #{d.pick}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {needs.slice(0, 2).map((n) => (
                      <span
                        key={n}
                        className={`rounded px-1.5 py-0.5 text-xs ${posBadgeClass(n)}`}
                      >
                        {n}
                      </span>
                    ))}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  if (phase === "complete") {
    return (
      <div className="rounded-lg border py-10 px-4" style={{ backgroundColor: INK, borderColor: BORDER }}>
        <div className="mx-auto max-w-2xl">
          <h1 className="mb-8 text-center text-2xl font-bold" style={{ color: TEXT }}>
            Round 1 complete
          </h1>
          {userPickRow && userProspect && (
            <div
              className="mb-8 rounded-lg border-2 p-6 text-center"
              style={{ borderColor: "rgba(212,168,67,0.45)", backgroundColor: SURFACE }}
            >
              <p className="text-lg font-semibold" style={{ color: TEXT }}>
                {userPickRow.team} selected {userProspect.name} at pick #
                {userPickRow.pick}
              </p>
              {gradeUserPick && (
                <div className="mt-4">
                  <span
                    className="inline-block rounded-full px-4 py-2 font-bold text-white"
                    style={{
                      backgroundColor:
                        gradeUserPick.tone === "green"
                          ? GREEN
                          : gradeUserPick.tone === "blue"
                            ? "#2563eb"
                            : gradeUserPick.tone === "amber"
                              ? AMBER
                              : TEXT3,
                    }}
                  >
                    {gradeUserPick.label}
                  </span>
                  {gradeUserPick.sub && (
                    <p className="mt-2 text-sm" style={{ color: TEXT2 }}>
                      {gradeUserPick.sub}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}
          <div className="overflow-x-auto rounded-lg border" style={{ borderColor: BORDER }}>
            <table className="w-full text-sm" style={{ color: TEXT }}>
              <thead>
                <tr style={{ backgroundColor: SURFACE2 }}>
                  <th className="p-2 text-left text-xs font-normal uppercase tracking-wider" style={{ color: TEXT3 }}>
                    Pick
                  </th>
                  <th className="p-2 text-left text-xs font-normal uppercase tracking-wider" style={{ color: TEXT3 }}>
                    Team
                  </th>
                  <th className="p-2 text-left text-xs font-normal uppercase tracking-wider" style={{ color: TEXT3 }}>
                    Prospect
                  </th>
                  <th className="p-2 text-left text-xs font-normal uppercase tracking-wider" style={{ color: TEXT3 }}>
                    Pos
                  </th>
                  <th className="p-2 text-left text-xs font-normal uppercase tracking-wider" style={{ color: TEXT3 }}>
                    School
                  </th>
                  <th className="p-2 text-left text-xs font-normal uppercase tracking-wider" style={{ color: TEXT3 }}>
                    Grade
                  </th>
                </tr>
              </thead>
              <tbody>
                {picks.map((row, i) => (
                  <tr
                    key={row.pick}
                    style={{
                      backgroundColor: i % 2 === 0 ? SURFACE : INK,
                      ...(i === userPickIdx ? { backgroundColor: "rgba(212,168,67,0.08)" } : {}),
                    }}
                  >
                    <td className="p-2 font-mono">{row.pick}</td>
                    <td className="p-2">{row.abbr}</td>
                    <td className="p-2 font-medium">
                      {row.prospect ? row.prospect.name : "—"}
                    </td>
                    <td className="p-2">
                      {row.prospect ? (
                        <span
                          className={`rounded px-2 py-0.5 text-xs ${posBadgeClass(row.prospect.pos)}`}
                        >
                          {row.prospect.pos}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="p-2" style={{ color: TEXT2 }}>
                      {row.prospect ? row.prospect.school : "—"}
                    </td>
                    <td className="p-2">{row.prospect ? row.prospect.grade : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-8 text-center">
            <button
              type="button"
              onClick={resetDraft}
              className="rounded-lg px-6 py-3 font-bold transition-opacity hover:opacity-90"
              style={{ backgroundColor: GOLD, color: INK }}
            >
              Start new draft
            </button>
          </div>
        </div>
      </div>
    );
  }

  const slot = picks[currentIdx];
  const isUserOnClock = currentIdx === userPickIdx;
  const needsNow = slot ? TEAM_NEEDS[slot.team] || [] : [];

  const topNeedMatch = (p) =>
    userNeeds[0] && posMatchesNeed(p.pos, userNeeds[0]);

  return (
    <div className="rounded-lg border px-2 py-4" style={{ backgroundColor: INK, borderColor: BORDER }}>
      <div className="mx-auto flex max-w-7xl flex-col gap-4">
        {confirming && (
          <div
            className="flex w-full items-center justify-center rounded-lg py-8"
            style={{ backgroundColor: "rgba(0,0,0,0.55)" }}
          >
            <div
              className="mx-4 min-h-48 w-full max-w-md rounded-lg border p-6 shadow-xl"
              style={{ backgroundColor: SURFACE, borderColor: "rgba(212,168,67,0.35)" }}
            >
              <h3 className="text-xl font-bold" style={{ color: TEXT }}>
                {confirming.name}
              </h3>
              <p className="mt-1 flex flex-wrap items-center gap-2 text-sm" style={{ color: TEXT2 }}>
                <span
                  className={`rounded px-2 py-0.5 text-xs font-semibold ${posBadgeClass(confirming.pos)}`}
                >
                  {confirming.pos}
                </span>
                <span>· {confirming.school}</span>
              </p>
              <div className="mt-4 grid grid-cols-2 gap-2 text-sm" style={{ color: TEXT }}>
                <div>
                  <span style={{ color: TEXT3 }}>Rank</span>
                  <div className="font-bold">{confirming.rank}</div>
                </div>
                <div>
                  <span style={{ color: TEXT3 }}>Grade</span>
                  <div className="font-bold">{confirming.grade}</div>
                </div>
                <div>
                  <span style={{ color: TEXT3 }}>40 Time</span>
                  <div className="font-bold">{confirming.forty}</div>
                </div>
                <div>
                  <span style={{ color: TEXT3 }}>Weight</span>
                  <div className="font-bold">{confirming.weight}</div>
                </div>
              </div>
              <p className="mt-4 text-sm italic" style={{ color: TEXT2 }}>
                {confirming.notes}
              </p>
              {userNeeds[0] && posMatchesNeed(confirming.pos, userNeeds[0]) && (
                <p className="mt-2 text-sm font-semibold" style={{ color: GREEN }}>
                  Addresses {userNeeds[0]} — team&apos;s top need
                </p>
              )}
              <div className="mt-6 flex gap-3">
                <button
                  type="button"
                  onClick={() => lockInPick(confirming)}
                  className="flex-1 rounded py-2 font-bold text-white"
                  style={{ backgroundColor: GREEN }}
                >
                  ✓ Confirm Pick
                </button>
                <button
                  type="button"
                  onClick={() => setConfirming(null)}
                  className="flex-1 rounded border-2 py-2 font-bold"
                  style={{ borderColor: BORDER, color: TEXT2 }}
                >
                  ← Back
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="flex flex-col gap-4 lg:flex-row">
          <div className="flex-shrink-0 lg:w-3/12">
            <h2 className="mb-2 font-mono text-[10px] font-semibold uppercase tracking-[0.18em]" style={{ color: GOLD }}>
              // Round 1 board
            </h2>
            <div className="max-h-96 overflow-y-auto rounded border" style={{ borderColor: BORDER, backgroundColor: SURFACE }}>
              {picks.map((row, i) => {
                const done = row.prospect !== null;
                const current = i === currentIdx;
                const userRow = i === userPickIdx;
                const rowInk = userRow && done;
                return (
                  <div
                    key={row.pick}
                    ref={current ? currentRowRef : undefined}
                    className={`flex h-9 items-center gap-2 border-b px-2 py-1 text-sm ${
                      current ? "animate-pulse text-white" : done ? "" : ""
                    }`}
                    style={{
                      borderColor: BORDER,
                      color: current ? TEXT : done ? TEXT2 : TEXT,
                      backgroundColor: current
                        ? SURFACE2
                        : userRow && done
                          ? "rgba(212,168,67,0.22)"
                          : "transparent",
                      borderLeftWidth: userRow && !done ? 3 : 0,
                      borderLeftColor: userRow && !done ? GOLD : "transparent",
                      borderLeftStyle: "solid",
                      ...(rowInk ? { color: INK } : {}),
                    }}
                  >
                    <span className="w-6 font-mono">{row.pick}</span>
                    <span className="w-8 font-bold">{row.abbr}</span>
                    <span className="flex-1 truncate">
                      {done ? row.prospect.name : current ? "ON CLOCK" : "—"}
                    </span>
                    {done && row.prospect && (
                      <span className={`rounded px-1 text-xs ${posBadgeClass(row.prospect.pos)}`}>
                        {row.prospect.pos}
                      </span>
                    )}
                    {done && <span style={{ color: GREEN }}>✓</span>}
                    {userRow && done && <span style={{ color: INK }}>★</span>}
                    {current && <span className="h-2 w-2 animate-pulse rounded-full bg-[#d4a843]" />}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="flex-shrink-0 lg:w-5/12">
            <div
              className="min-h-96 rounded-lg border-2 p-4"
              style={{
                backgroundColor: SURFACE,
                borderColor: isUserOnClock ? GOLD : BORDER,
              }}
            >
              {slot && (
                <>
                  <div className="mb-1 flex items-center gap-2">
                    {isUserOnClock && (
                      <span
                        className="rounded px-2 py-0.5 text-xs font-bold"
                        style={{ backgroundColor: GOLD, color: INK }}
                      >
                        YOUR PICK
                      </span>
                    )}
                  </div>
                  <h2 className="text-xl font-bold" style={{ color: TEXT }}>
                    Pick {slot.pick} — {slot.team}
                  </h2>
                  <div className="mb-4 mt-2 flex gap-2">
                    {needsNow.map((n, ni) => (
                      <span
                        key={n}
                        className="rounded px-2 py-1 text-xs font-semibold text-white"
                        style={{
                          backgroundColor: ni === 0 ? SURFACE2 : RED,
                        }}
                      >
                        {n}
                      </span>
                    ))}
                  </div>

                  {!isUserOnClock && (
                    <>
                      <h3 className="mb-2 font-semibold" style={{ color: TEXT2 }}>
                        Projected picks
                      </h3>
                      {countdown !== null && (
                        <div className="mb-4 py-6 text-center">
                          <div className="text-6xl font-bold" style={{ color: GOLD }}>
                            {countdown}
                          </div>
                          <p className="mt-2" style={{ color: TEXT2 }}>
                            Auto-selecting: {projections[0]?.name}
                          </p>
                        </div>
                      )}
                      <div className="mb-4 space-y-2">
                        {projections.map((p, idx) => (
                          <div
                            key={p.id}
                            className="rounded border p-2"
                            style={{
                              borderColor: idx === 0 ? GREEN : BORDER,
                              borderWidth: idx === 0 ? 2 : 1,
                            }}
                          >
                            <div className="flex items-start justify-between">
                              <div style={{ color: TEXT }}>
                                {idx === 0 && (
                                  <span
                                    className="mr-2 rounded px-2 py-0.5 text-xs font-bold text-white"
                                    style={{ backgroundColor: GREEN }}
                                  >
                                    AI Pick
                                  </span>
                                )}
                                <span className="font-bold">{p.name}</span>
                                <span className={`ml-2 rounded px-2 py-0.5 text-xs ${posBadgeClass(p.pos)}`}>
                                  {p.pos}
                                </span>
                                <div className="text-xs" style={{ color: TEXT3 }}>
                                  {p.school}
                                </div>
                              </div>
                              <span className="font-mono text-xs font-bold" style={{ color: GOLD }}>
                                #{p.rank}
                              </span>
                            </div>
                            <div className="mt-2 h-2 overflow-hidden rounded" style={{ backgroundColor: SURFACE2 }}>
                              <div
                                className="h-full rounded"
                                style={{
                                  width: `${p.grade}%`,
                                  backgroundColor: GOLD,
                                }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                      <div className="mb-4 flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={onAutoPick}
                          className="rounded px-4 py-2 font-semibold text-white"
                          style={{ backgroundColor: SURFACE2 }}
                        >
                          Auto pick — #1 projection
                        </button>
                        <button
                          type="button"
                          onClick={startCountdown}
                          disabled={countdown !== null}
                          className="rounded border-2 px-4 py-2 font-semibold disabled:opacity-50"
                          style={{ borderColor: BORDER, color: TEXT2 }}
                        >
                          Set timer — 3s
                        </button>
                      </div>
                      <label className="flex cursor-pointer items-center gap-2 text-sm" style={{ color: TEXT2 }}>
                        <input
                          type="checkbox"
                          checked={autoAdv}
                          onChange={(e) => setAutoAdv(e.target.checked)}
                        />
                        Auto-advance: {autoAdv ? "ON" : "OFF"}
                      </label>
                    </>
                  )}

                  {isUserOnClock && (
                    <div>
                      <div className="relative mb-3 flex items-center">
                        <input
                          ref={searchRef}
                          type="text"
                          value={query}
                          onChange={(e) => setQuery(e.target.value)}
                          placeholder="Search name, position, school..."
                          className="w-full rounded-lg border px-3 py-2 pr-10"
                          style={{
                            borderColor: BORDER,
                            backgroundColor: INK,
                            color: TEXT,
                          }}
                        />
                        {query && (
                          <button
                            type="button"
                            onClick={() => setQuery("")}
                            className="absolute right-2 font-bold"
                            style={{ color: TEXT3 }}
                          >
                            ✕
                          </button>
                        )}
                      </div>
                      <div className="max-h-80 overflow-y-auto rounded border" style={{ borderColor: BORDER }}>
                        {filteredProspects.length === 0 ? (
                          <div className="p-4 text-center" style={{ color: TEXT3 }}>
                            No prospects match search
                          </div>
                        ) : (
                          filteredProspects.map((p) => (
                            <button
                              key={p.id}
                              type="button"
                              onClick={() => setConfirming(p)}
                              className={`flex h-12 w-full items-center gap-2 border-b px-3 py-2 text-left ${
                                topNeedMatch(p) ? "border-l-4" : ""
                              }`}
                              style={{
                                borderColor: BORDER,
                                color: TEXT,
                                ...(topNeedMatch(p) ? { borderLeftColor: GREEN } : {}),
                              }}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.backgroundColor = SURFACE2;
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.backgroundColor = "transparent";
                              }}
                            >
                              <span
                                className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold text-white"
                                style={{ backgroundColor: SURFACE2 }}
                              >
                                {p.rank}
                              </span>
                              <span className="flex-shrink-0 font-bold">{p.name}</span>
                              <span className={`flex-shrink-0 rounded px-2 py-0.5 text-xs ${posBadgeClass(p.pos)}`}>
                                {p.pos}
                              </span>
                              <span className="flex-1 truncate text-xs" style={{ color: TEXT3 }}>
                                {p.school}
                              </span>
                              <span className="flex-shrink-0 font-bold" style={{ color: GOLD }}>
                                {p.grade}
                              </span>
                            </button>
                          ))
                        )}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          <div className="flex-shrink-0 lg:w-3/12">
            <div className="rounded-lg border p-4" style={{ borderColor: BORDER, backgroundColor: SURFACE }}>
              <h3 className="text-lg font-bold" style={{ color: TEXT }}>
                {userTeamName}
              </h3>
              <p className="text-sm" style={{ color: TEXT2 }}>
                Pick #{DRAFT_ORDER[userPickIdx].pick} of 32
              </p>
              <div className="mt-3">
                <p className="text-xs font-semibold uppercase" style={{ color: TEXT3 }}>
                  Top needs
                </p>
                <ul className="mt-1 space-y-1 text-sm" style={{ color: TEXT }}>
                  {userNeeds.map((n) => {
                    const filled = userProspect && posMatchesNeed(userProspect.pos, n);
                    return (
                      <li key={n} className="flex items-center gap-2">
                        <span style={{ color: filled ? GREEN : TEXT3 }}>{filled ? "●" : "○"}</span>
                        {n}
                      </li>
                    );
                  })}
                </ul>
              </div>
              {userProspect && (
                <div className="mt-4 rounded p-3" style={{ backgroundColor: INK }}>
                  <p className="text-xs" style={{ color: TEXT3 }}>
                    Your selection
                  </p>
                  <p className="font-bold">{userProspect.name}</p>
                  <span className={`mt-1 inline-block rounded px-2 py-0.5 text-xs ${posBadgeClass(userProspect.pos)}`}>
                    {userProspect.pos}
                  </span>
                  <div
                    className="mt-2 inline-block rounded-full px-3 py-1 text-sm font-bold text-white"
                    style={{ backgroundColor: SURFACE2 }}
                  >
                    Grade {userProspect.grade}
                  </div>
                </div>
              )}
              <p className="mt-4 text-xs" style={{ color: TEXT3 }}>
                Draft position: Pick {DRAFT_ORDER[userPickIdx].pick} of 32
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
