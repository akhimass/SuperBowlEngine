import React, {
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

const NAVY = "#1a2744";
const GOLD = "#c9a84c";
const GREEN = "#27ae60";
const AMBER = "#e67e22";
const RED = "#c0392b";
const GRAY = "#6b7280";

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
    QB: "bg-red-100 text-red-800",
    EDGE: "bg-orange-100 text-orange-800",
    WR: "bg-blue-100 text-blue-800",
    TE: "bg-teal-100 text-teal-800",
    OT: "bg-green-100 text-green-800",
    IOL: "bg-emerald-100 text-emerald-800",
    CB: "bg-purple-100 text-purple-800",
    S: "bg-indigo-100 text-indigo-800",
    LB: "bg-yellow-100 text-yellow-800",
    RB: "bg-pink-100 text-pink-800",
    IDL: "bg-gray-100 text-gray-800",
  };
  return m[pos] || "bg-gray-100 text-gray-800";
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
      <div className="min-h-screen bg-gray-50 py-10 px-4">
        <div className="max-w-4xl mx-auto">
          <h1
            className="text-3xl font-bold text-center mb-2"
            style={{ color: NAVY }}
          >
            GridironIQ · 2026 NFL Draft Simulator
          </h1>
          <p className="text-center mb-8" style={{ color: GRAY }}>
            Round 1 Only · 32 Picks · April 23, Pittsburgh
          </p>
          <p className="text-center font-medium mb-6" style={{ color: NAVY }}>
            Select your team — you are the GM for Round 1
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {DRAFT_ORDER.map((d, i) => {
              const needs = TEAM_NEEDS[d.team] || [];
              return (
                <button
                  key={d.pick}
                  type="button"
                  onClick={() => selectTeam(i)}
                  className="border-2 border-gray-200 rounded-lg p-4 text-left transition-colors hover:text-white"
                  style={{ borderColor: "#e5e7eb" }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = NAVY;
                    e.currentTarget.style.borderColor = NAVY;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = "";
                    e.currentTarget.style.borderColor = "#e5e7eb";
                  }}
                >
                  <div
                    className="text-2xl font-bold"
                    style={{ color: "inherit" }}
                  >
                    {d.abbr}
                  </div>
                  <div className="text-xs mt-1 opacity-80">{d.team}</div>
                  <div
                    className="text-xs font-bold mt-2 inline-block px-2 py-0.5 rounded"
                    style={{ backgroundColor: GOLD, color: NAVY }}
                  >
                    Pick #{d.pick}
                  </div>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {needs.slice(0, 2).map((n) => (
                      <span
                        key={n}
                        className="text-xs px-1.5 py-0.5 rounded bg-gray-200 text-gray-700"
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
      <div className="min-h-screen bg-gray-50 py-10 px-4">
        <div className="max-w-2xl mx-auto">
          <h1
            className="text-2xl font-bold text-center mb-8"
            style={{ color: NAVY }}
          >
            Round 1 Complete — 2026 NFL Draft
          </h1>
          {userPickRow && userProspect && (
            <div
              className="border-2 rounded-lg p-6 mb-8 text-center"
              style={{ borderColor: GOLD, backgroundColor: "#fffef5" }}
            >
              <p className="text-lg font-semibold" style={{ color: NAVY }}>
                {userPickRow.team} selected {userProspect.name} at pick #
                {userPickRow.pick}
              </p>
              {gradeUserPick && (
                <div className="mt-4">
                  <span
                    className="inline-block px-4 py-2 rounded-full font-bold text-white"
                    style={{
                      backgroundColor:
                        gradeUserPick.tone === "green"
                          ? GREEN
                          : gradeUserPick.tone === "blue"
                            ? "#2563eb"
                            : gradeUserPick.tone === "amber"
                              ? AMBER
                              : GRAY,
                    }}
                  >
                    {gradeUserPick.label}
                  </span>
                  {gradeUserPick.sub && (
                    <p className="mt-2 text-sm" style={{ color: NAVY }}>
                      {gradeUserPick.sub}
                    </p>
                  )}
                </div>
              )}
            </div>
          )}
          <div className="overflow-x-auto border border-gray-200 rounded-lg">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-100">
                  <th className="text-left p-2">Pick</th>
                  <th className="text-left p-2">Team</th>
                  <th className="text-left p-2">Prospect</th>
                  <th className="text-left p-2">Pos</th>
                  <th className="text-left p-2">School</th>
                  <th className="text-left p-2">Grade</th>
                </tr>
              </thead>
              <tbody>
                {picks.map((row, i) => (
                  <tr
                    key={row.pick}
                    className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}
                    style={
                      i === userPickIdx
                        ? { backgroundColor: "#fff9e6" }
                        : undefined
                    }
                  >
                    <td className="p-2 font-mono">{row.pick}</td>
                    <td className="p-2">{row.abbr}</td>
                    <td className="p-2 font-medium">
                      {row.prospect ? row.prospect.name : "—"}
                    </td>
                    <td className="p-2">
                      {row.prospect ? (
                        <span
                          className={`text-xs px-2 py-0.5 rounded ${posBadgeClass(row.prospect.pos)}`}
                        >
                          {row.prospect.pos}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="p-2 text-gray-600">
                      {row.prospect ? row.prospect.school : "—"}
                    </td>
                    <td className="p-2">
                      {row.prospect ? row.prospect.grade : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="text-center mt-8">
            <button
              type="button"
              onClick={resetDraft}
              className="px-6 py-3 rounded-lg font-bold text-white transition-opacity hover:opacity-90"
              style={{ backgroundColor: NAVY }}
            >
              Start New Draft
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
    <div className="min-h-screen bg-gray-100 py-4 px-2">
      <div className="max-w-7xl mx-auto flex flex-col gap-4">
        {confirming && (
          <div
            className="w-full py-8 flex justify-center items-center rounded-lg"
            style={{ backgroundColor: "rgba(0,0,0,0.45)" }}
          >
            <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4 min-h-48">
              <h3 className="text-xl font-bold" style={{ color: NAVY }}>
                {confirming.name}
              </h3>
              <p className="text-gray-600 flex flex-wrap items-center gap-2">
                <span
                  className={`text-xs px-2 py-0.5 rounded font-semibold ${posBadgeClass(confirming.pos)}`}
                >
                  {confirming.pos}
                </span>
                <span>· {confirming.school}</span>
              </p>
              <div className="grid grid-cols-2 gap-2 mt-4 text-sm">
                <div>
                  <span className="text-gray-500">Rank</span>
                  <div className="font-bold">{confirming.rank}</div>
                </div>
                <div>
                  <span className="text-gray-500">Grade</span>
                  <div className="font-bold">{confirming.grade}</div>
                </div>
                <div>
                  <span className="text-gray-500">40 Time</span>
                  <div className="font-bold">{confirming.forty}</div>
                </div>
                <div>
                  <span className="text-gray-500">Weight</span>
                  <div className="font-bold">{confirming.weight}</div>
                </div>
              </div>
              <p className="mt-4 text-sm italic text-gray-600">
                {confirming.notes}
              </p>
              {userNeeds[0] && posMatchesNeed(confirming.pos, userNeeds[0]) && (
                <p className="mt-2 text-sm font-semibold" style={{ color: GREEN }}>
                  Addresses {userNeeds[0]} — team&apos;s top need
                </p>
              )}
              <div className="flex gap-3 mt-6">
                <button
                  type="button"
                  onClick={() => lockInPick(confirming)}
                  className="flex-1 py-2 rounded font-bold text-white"
                  style={{ backgroundColor: GREEN }}
                >
                  ✓ Confirm Pick
                </button>
                <button
                  type="button"
                  onClick={() => setConfirming(null)}
                  className="flex-1 py-2 rounded font-bold border-2 border-gray-300"
                >
                  ← Back
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="flex flex-col lg:flex-row gap-4">
          <div className="lg:w-3/12 flex-shrink-0">
            <h2 className="font-bold mb-2" style={{ color: NAVY }}>
              Round 1 Board
            </h2>
            <div className="bg-white rounded border border-gray-200 max-h-96 overflow-y-auto">
              {picks.map((row, i) => {
                const done = row.prospect !== null;
                const current = i === currentIdx;
                const userRow = i === userPickIdx;
                return (
                  <div
                    key={row.pick}
                    ref={current ? currentRowRef : undefined}
                    className={`flex items-center gap-2 px-2 py-1 text-sm border-b border-gray-100 h-9 ${
                      current
                        ? "text-white animate-pulse"
                        : done
                          ? "text-gray-400"
                          : ""
                    }`}
                    style={{
                      backgroundColor: current
                        ? NAVY
                        : userRow && done
                          ? GOLD
                          : "transparent",
                      borderLeftWidth: userRow && !done ? 3 : 0,
                      borderLeftColor: userRow && !done ? GOLD : "transparent",
                      borderLeftStyle: "solid",
                    }}
                  >
                    <span className="w-6 font-mono">{row.pick}</span>
                    <span className="w-8 font-bold">{row.abbr}</span>
                    <span className="flex-1 truncate">
                      {done ? row.prospect.name : current ? "ON CLOCK" : "—"}
                    </span>
                    {done && row.prospect && (
                      <span
                        className={`text-xs px-1 rounded ${posBadgeClass(row.prospect.pos)}`}
                      >
                        {row.prospect.pos}
                      </span>
                    )}
                    {done && <span className="text-green-600">✓</span>}
                    {userRow && done && <span className="text-yellow-900">★</span>}
                    {current && (
                      <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="lg:w-5/12 flex-shrink-0">
            <div
              className={`bg-white rounded-lg border-2 p-4 min-h-96 ${
                isUserOnClock ? "border-yellow-500" : "border-gray-200"
              }`}
              style={
                isUserOnClock ? { borderColor: GOLD } : undefined
              }
            >
              {slot && (
                <>
                  <div className="flex items-center gap-2 mb-1">
                    {isUserOnClock && (
                      <span
                        className="text-xs font-bold px-2 py-0.5 rounded text-white"
                        style={{ backgroundColor: GOLD, color: NAVY }}
                      >
                        YOUR PICK
                      </span>
                    )}
                  </div>
                  <h2 className="text-xl font-bold" style={{ color: NAVY }}>
                    Pick {slot.pick} — {slot.team}
                  </h2>
                  <div className="flex gap-2 mt-2 mb-4">
                    {needsNow.map((n, ni) => (
                      <span
                        key={n}
                        className="text-xs font-semibold px-2 py-1 rounded text-white"
                        style={{
                          backgroundColor: ni === 0 ? NAVY : RED,
                        }}
                      >
                        {n}
                      </span>
                    ))}
                  </div>

                  {!isUserOnClock && (
                    <>
                      <h3 className="font-semibold text-gray-700 mb-2">
                        Projected Picks
                      </h3>
                      {countdown !== null && (
                        <div className="text-center py-6 mb-4">
                          <div
                            className="text-6xl font-bold"
                            style={{ color: NAVY }}
                          >
                            {countdown}
                          </div>
                          <p className="text-gray-600 mt-2">
                            Auto-selecting: {projections[0]?.name}
                          </p>
                        </div>
                      )}
                      <div className="space-y-2 mb-4">
                        {projections.map((p, idx) => (
                          <div
                            key={p.id}
                            className={`border rounded p-2 ${
                              idx === 0 ? "border-2" : "border-gray-200"
                            }`}
                            style={
                              idx === 0
                                ? { borderColor: GREEN }
                                : undefined
                            }
                          >
                            <div className="flex justify-between items-start">
                              <div>
                                {idx === 0 && (
                                  <span
                                    className="text-xs font-bold text-white px-2 py-0.5 rounded mr-2"
                                    style={{ backgroundColor: GREEN }}
                                  >
                                    AI Pick
                                  </span>
                                )}
                                <span className="font-bold">{p.name}</span>
                                <span
                                  className={`ml-2 text-xs px-2 py-0.5 rounded ${posBadgeClass(p.pos)}`}
                                >
                                  {p.pos}
                                </span>
                                <div className="text-xs text-gray-500">
                                  {p.school}
                                </div>
                              </div>
                              <span
                                className="text-xs font-mono font-bold"
                                style={{ color: NAVY }}
                              >
                                #{p.rank}
                              </span>
                            </div>
                            <div className="mt-2 h-2 bg-gray-200 rounded overflow-hidden">
                              <div
                                className="h-full rounded"
                                style={{
                                  width: `${p.grade}%`,
                                  backgroundColor: NAVY,
                                }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                      <div className="flex flex-wrap gap-2 mb-4">
                        <button
                          type="button"
                          onClick={onAutoPick}
                          className="px-4 py-2 rounded font-semibold text-white"
                          style={{ backgroundColor: NAVY }}
                        >
                          Auto Pick — select #1 projection
                        </button>
                        <button
                          type="button"
                          onClick={startCountdown}
                          disabled={countdown !== null}
                          className="px-4 py-2 rounded font-semibold border-2 border-gray-400 disabled:opacity-50"
                        >
                          Set Timer — 3s countdown then auto-pick
                        </button>
                      </div>
                      <label className="flex items-center gap-2 text-sm cursor-pointer">
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
                      <div className="relative flex items-center mb-3">
                        <input
                          ref={searchRef}
                          type="text"
                          value={query}
                          onChange={(e) => setQuery(e.target.value)}
                          placeholder="Search name, position, school..."
                          className="w-full border border-gray-300 rounded-lg px-3 py-2 pr-10"
                        />
                        {query && (
                          <button
                            type="button"
                            onClick={() => setQuery("")}
                            className="absolute right-2 text-gray-500 font-bold"
                          >
                            ✕
                          </button>
                        )}
                      </div>
                      <div className="max-h-80 overflow-y-auto border border-gray-200 rounded">
                        {filteredProspects.length === 0 ? (
                          <div className="p-4 text-center text-gray-500">
                            No prospects match search
                          </div>
                        ) : (
                          filteredProspects.map((p) => (
                            <button
                              key={p.id}
                              type="button"
                              onClick={() => setConfirming(p)}
                              className={`w-full text-left px-3 py-2 border-b border-gray-100 flex items-center gap-2 h-12 hover:bg-gray-50 ${
                                topNeedMatch(p)
                                  ? "border-l-4"
                                  : ""
                              }`}
                              style={
                                topNeedMatch(p)
                                  ? { borderLeftColor: GREEN }
                                  : undefined
                              }
                            >
                              <span
                                className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
                                style={{ backgroundColor: NAVY }}
                              >
                                {p.rank}
                              </span>
                              <span className="font-bold flex-shrink-0">
                                {p.name}
                              </span>
                              <span
                                className={`text-xs px-2 py-0.5 rounded flex-shrink-0 ${posBadgeClass(p.pos)}`}
                              >
                                {p.pos}
                              </span>
                              <span className="text-xs text-gray-500 truncate flex-1">
                                {p.school}
                              </span>
                              <span
                                className="font-bold flex-shrink-0"
                                style={{ color: NAVY }}
                              >
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

          <div className="lg:w-3/12 flex-shrink-0">
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h3 className="font-bold text-lg" style={{ color: NAVY }}>
                {userTeamName}
              </h3>
              <p className="text-sm text-gray-600">
                Pick #{DRAFT_ORDER[userPickIdx].pick} of 32
              </p>
              <div className="mt-3">
                <p className="text-xs font-semibold text-gray-500 uppercase">
                  Top needs
                </p>
                <ul className="text-sm mt-1 space-y-1">
                  {userNeeds.map((n) => {
                    const filled =
                      userProspect && posMatchesNeed(userProspect.pos, n);
                    return (
                      <li key={n} className="flex items-center gap-2">
                        <span
                          className={
                            filled ? "text-green-600" : "text-gray-400"
                          }
                        >
                          {filled ? "●" : "○"}
                        </span>
                        {n}
                      </li>
                    );
                  })}
                </ul>
              </div>
              {userProspect && (
                <div className="mt-4 p-3 rounded bg-gray-50">
                  <p className="text-xs text-gray-500">Your selection</p>
                  <p className="font-bold">{userProspect.name}</p>
                  <span
                    className={`text-xs px-2 py-0.5 rounded inline-block mt-1 ${posBadgeClass(userProspect.pos)}`}
                  >
                    {userProspect.pos}
                  </span>
                  <div
                    className="mt-2 inline-block px-3 py-1 rounded-full text-white text-sm font-bold"
                    style={{ backgroundColor: NAVY }}
                  >
                    Grade {userProspect.grade}
                  </div>
                </div>
              )}
              <p className="mt-4 text-xs text-gray-500">
                Draft position: Pick {DRAFT_ORDER[userPickIdx].pick} of 32
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
