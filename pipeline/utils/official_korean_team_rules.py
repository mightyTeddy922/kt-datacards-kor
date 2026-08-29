"""Official Kill Team Korean Team Rules availability, verified on 2026-08-30.

Source of truth:
  Warhammer Community search API for Kill Team downloads, Korean language, Team Rules.

Rule used by this project:
  - If the Korean downloads entry title is written in Korean, treat the team as
    having official Korean card assets.
  - If the Korean-language PDF exists but the title is still written in English,
    treat it as untranslated for card-image swap purposes.
"""

from __future__ import annotations

VERIFIED_DATE = "2026-08-30"

OFFICIAL_KOREAN_TEAM_RULES: dict[str, dict[str, str | bool]] = {
    "angels-of-death": {"title": "죽음의 천사", "translated": True, "file": "kor_26-08_killteam_angels_of_death_online_rules-r5xuw7hgvi-vonnpicgnb.pdf"},
    "battleclade": {"title": "전투계통 킬 팀", "translated": True, "file": "kor_battleclade_online_rules-5apjy22pmq-ftrz9xfsrv.pdf"},
    "blades-of-khaine": {"title": "케인의 칼날", "translated": True, "file": "kor_17-06_kill_team_team_rules_blades_of_khaine-2nerb8mcmy-v6shz34y1u.pdf"},
    "brood-brothers": {"title": "무리 형제단", "translated": True, "file": "kor_brood_brothers_online_rules-uc4ew3fkpj-5vinjwdiyz.pdf"},
    "canoptek-circle": {"title": "카놉텍 회합", "translated": True, "file": "kor_canoptek_circle_online_rules-wikook2dov-l0h0txujjz.pdf"},
    "celestian-insidiants": {"title": "셀레스티안 항마단", "translated": True, "file": "kor_celestian_insidiants_online_rules-v20zvidwvs-dwh8ja7cse.pdf"},
    "chaos-cult": {"title": "카오스 사교도", "translated": True, "file": "kor_17-06_kill_team_team_rules_chaos_cult-arqg12jhka-hqfonlsjv9.pdf"},
    "deathwatch": {"title": "데스워치", "translated": True, "file": "kor_deathwatch_online_rules-sqe8opi21n-9ypk3dlady.pdf"},
    "exaction-squad": {"title": "집행 분대", "translated": True, "file": "kor_17-06_kill_team_team_rules_exaction_squad_online_rules-yh7fxyymdp-uqwhygqzml.pdf"},
    "exodite-dragon-masters": {"title": "엑소다이트 용의 달인", "translated": True, "file": "kor_22-07_kill_team_team_rules_exodite_dragon_masters-vilbsyvz5g-q85rts4nh7.pdf"},
    "farstalker-kinband": {"title": "먼길밟이 혈족단", "translated": True, "file": "kor_22-07_kill_team_team_rules_farstalker_kinband-rmrukcfcat-f9ptwjidrj.pdf"},
    "fellgor-ravagers": {"title": "펠고어 약탈자", "translated": True, "file": "kor_fellgor_ravagers_online_rules-zmwak9gbam-6l2owdvxpe.pdf"},
    "gellerpox-infected": {"title": "Gellerpox Infected", "translated": False, "file": "kor_gellerpox_infected_online_rules-pxbmtwi59n-nsjrv0zozu.pdf"},
    "goremongers": {"title": "유혈광 킬", "translated": True, "file": "kor_goremongers_online_rules-mxyfmm78n8-l1ckzkdcdz.pdf"},
    "hand-of-the-archon": {"title": "집정관의 손", "translated": True, "file": "kor_17-06_kill_team_team_rules_hand_of_the_archon-p0jqfcjo4h-uikvfaukqn.pdf"},
    "hearthkyn-salvagers": {"title": "하스킨 인양단", "translated": True, "file": "kor_17-06_kill_team_team_rules_hearthkyn_salvagers-dakr010bjt-yca5yvykya.pdf"},
    "hernkyn-yaegirs": {"title": "헤른킨 예이기르", "translated": True, "file": "kor_hernkyn_yaegirs_online_rules-b7jcww3n9k-z7d4rawlop.pdf"},
    "hierotek-circle": {"title": "히에로텍 회합", "translated": True, "file": "kor_hierotek_circle_online_rules-rtakayfib3-kskm4g8vv1.pdf"},
    "imperial-navy-breachers": {"title": "제국 해군 돌파조", "translated": True, "file": "kor_imperial_navy_breachers_online_rules-6hcpovyqiu-emmsuuect8.pdf"},
    "inquisitorial-agents": {"title": "이단심문관 심복요원", "translated": True, "file": "kor_inquisitorial_agents_online_rules-7leh0thks4-fqufq1ehaa.pdf"},
    "kasrkin": {"title": "카스르킨", "translated": True, "file": "kor_17-06_kill_team_team_rules_kasrkin-lohblfwkro-j4skz9ccyd.pdf"},
    "mandrakes": {"title": "맨드레이크", "translated": True, "file": "kor_17-06_kill_team_team_rules_mandrakes-yixqmf0iz5-whnzg2qekh.pdf"},
    "murderwings": {"title": "살육날개", "translated": True, "file": "kor_murderwing_online_rules-xktufcekby-d7vx5fqcev.pdf"},
    "nemesis-claw": {"title": "천벌갈퀴", "translated": True, "file": "kor_17-06_kill_team_team_rules_nemesis_claw_online_rules-btwshwzgzg-rsexs0mc5t.pdf"},
    "novitiates": {"title": "Novitiates", "translated": False, "file": "kor_novitiates_online_rules-aeztaes8sf-fr2f69msxi.pdf"},
    "pathfinders": {"title": "Pathfinders", "translated": False, "file": "kor_pathfinders_online_rules-mvdmpydrpn-h75nk9woqq.pdf"},
    "plague-marines": {"title": "플레이그 마린", "translated": True, "file": "kor_plague_marines_online_rules-rghmkgcxji-otgfx8dzr7.pdf"},
    "ratlings": {"title": "래틀링 킬 팀", "translated": True, "file": "kor_17-06_kill_team_team_rules_ratlings-7wzv7mgq7g-aulpas7gbh.pdf"},
    "raveners": {"title": "래버너 킬 팀", "translated": True, "file": "kor_raveners_online_rules-axzrgzcxgy-6do8i7jri4.pdf"},
    "sanctifiers": {"title": "정화사역단 킬 팀", "translated": True, "file": "kor_17-06_kill_team_team_rules_sanctifiers-zpq1gsisey-llkxxdtjuy.pdf"},
    "scout-squad": {"title": "스카웃 분대", "translated": True, "file": "kor_17-06_kill_team_team_rules_scout_squad-9khlcsacm7-haukcwdqon.pdf"},
    "spectre-squad": {"title": "유령 분대", "translated": True, "file": "kor_spectre_squad_online_rules-iqtpzn3myl-ggkxtvnvdm.pdf"},
    "tempestus-aquilons": {"title": "템페스투스 아퀼론", "translated": True, "file": "kor_tempestus_aquilons_online_rules-arkmkhd2qs-hihb4tw2uk.pdf"},
    "vespid-stingwings": {"title": "베스피드 독침날개", "translated": True, "file": "kor_vespid_stingwings_online_rules-2ygjvo7pef-mihaguqmqd.pdf"},
    "wolf-scouts": {"title": "늑대 척후", "translated": True, "file": "kor_wolf_scouts_online_rules-dpywmrs9ta-2drksof6pe.pdf"},
    "wrecka-krew": {"title": "레카 크루", "translated": True, "file": "kor_17-06_kill_team_team_rules_wrecka_krew_online_rules-nhvu6mtar3-kqonvedzxi.pdf"},
    "xv26-stealth-battlesuits": {"title": "XV26 스텔스 배틀슈트", "translated": True, "file": "kor_xv26_stealth_battlesuits_online_rules-g7hlq4wfle-gia9rin0kp.pdf"},
}


def has_official_korean_translation(team_slug: str) -> bool:
    entry = OFFICIAL_KOREAN_TEAM_RULES.get(team_slug)
    return bool(entry and entry.get("translated"))


def has_korean_team_rules_entry(team_slug: str) -> bool:
    return team_slug in OFFICIAL_KOREAN_TEAM_RULES


def official_korean_title(team_slug: str) -> str:
    entry = OFFICIAL_KOREAN_TEAM_RULES.get(team_slug) or {}
    return str(entry.get("title") or "")
