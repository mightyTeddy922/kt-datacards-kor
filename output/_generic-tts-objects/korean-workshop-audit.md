# Korean Workshop Patch Audit

## Official Criterion
- Verified against Warhammer Community Korean Team Rules on 2026-08-30.
- Teams with Korean-language titles on the Korean Team Rules list are treated as officially translated.
- Teams whose Korean-tab entry title remains in English are treated as English fallback.

## Files
- Original workshop JSON: `C:\Users\SS\OneDrive\문서\My Games\Tabletop Simulator\Mods\Workshop\3646032507.json`
- Patched TTS save JSON: `C:\Users\SS\OneDrive\문서\My Games\Tabletop Simulator\Saves\KT24 - all team specific cards, tokens & dice (Korean Auto-Updating).json`
- Upload/deliverable JSON: `C:\Users\SS\OneDrive\바탕 화면\kt-datacards-kor\kt-datacards-kor\output\_generic-tts-objects\KT24 - all team specific cards, tokens & dice (Korean Auto-Updating).json`
- Patch summary JSON: `C:\Users\SS\OneDrive\바탕 화면\kt-datacards-kor\kt-datacards-kor\output\_generic-tts-objects\korean-workshop-patch-summary.json`

## Script Repo Audit
- Target repo inside Lua scripts: 1669
- Upstream repo inside Lua scripts: 0
- Source updater/spawner scripts with target repo: 5/5
- Source updater/spawner scripts with upstream repo: 0
- Target repo base: `https://raw.githubusercontent.com/mightyTeddy922/kt-datacards-kor/main`
- Upstream repo base: `https://raw.githubusercontent.com/Wen-Qualtu/kt-datacards/main`

## Feature Preservation
- `Load stats` original=1848 patched=1848
- `KTUI` original=26850 patched=26850
- `KTUIMiniDatacard` original=1387 patched=1387
- `addContextMenuItem("Update"` original=0 patched=0
- `click_update_single_object` original=3334 patched=3334

## Team URL Mode
- Officially translated teams (34): angels-of-death, battleclade, blades-of-khaine, brood-brothers, canoptek-circle, celestian-insidiants, chaos-cult, deathwatch, exaction-squad, exodite-dragon-masters, farstalker-kinband, fellgor-ravagers, goremongers, hand-of-the-archon, hearthkyn-salvagers, hernkyn-yaegirs, hierotek-circle, imperial-navy-breachers, inquisitorial-agents, kasrkin, mandrakes, murderwings, nemesis-claw, plague-marines, ratlings, raveners, sanctifiers, scout-squad, spectre-squad, tempestus-aquilons, vespid-stingwings, wolf-scouts, wrecka-krew, xv26-stealth-battlesuits
- Official English-fallback teams (3): gellerpox-infected, novitiates, pathfinders
- Legacy/no-Korean-entry fallback teams (11): blooded, corsair-voidscarred, death-korps, elucidian-starstriders, hunter-clade, kommandos, legionaries, phobos-strike-team, void-dancer-troupe, warpcoven, wyrmblade
- Korean-applied teams (34): angels-of-death, battleclade, blades-of-khaine, brood-brothers, canoptek-circle, celestian-insidiants, chaos-cult, deathwatch, exaction-squad, exodite-dragon-masters, farstalker-kinband, fellgor-ravagers, goremongers, hand-of-the-archon, hearthkyn-salvagers, hernkyn-yaegirs, hierotek-circle, imperial-navy-breachers, inquisitorial-agents, kasrkin, mandrakes, murderwings, nemesis-claw, plague-marines, ratlings, raveners, sanctifiers, scout-squad, spectre-squad, tempestus-aquilons, vespid-stingwings, wolf-scouts, wrecka-krew, xv26-stealth-battlesuits
- English fallback teams (14): blooded, corsair-voidscarred, death-korps, elucidian-starstriders, gellerpox-infected, hunter-clade, kommandos, legionaries, novitiates, pathfinders, phobos-strike-team, void-dancer-troupe, warpcoven, wyrmblade
- Manager bag contained team boxes: 48

## Representative FaceURL Checks
- Official Korean team `angels-of-death`: `https://raw.githubusercontent.com/mightyTeddy922/kt-datacards-kor/main/output/angels-of-death/cards/datacards/angels-of-death-assault-intercessor-grenadier-front.jpg?v=202608291725`
- Official Korean team `battleclade`: `https://raw.githubusercontent.com/mightyTeddy922/kt-datacards-kor/main/output/battleclade/cards/datacards/battleclade-battleclade-auto-proxy-servitor-front.jpg?v=202608291725`
- Official Korean team `blades-of-khaine`: `https://raw.githubusercontent.com/mightyTeddy922/kt-datacards-kor/main/output/blades-of-khaine/cards/datacards/dire-avenger-exarch-front.jpg`
- English fallback team `gellerpox-infected`: `https://raw.githubusercontent.com/Wen-Qualtu/kt-datacards/main/output/gellerpox-infected/cards/datacards/bloatspawn-front.jpg?v=1783537960`

## Image Resolution Checks
- Localized sample front-image sizes seen: 1211x2115, 1211x2117, 1212x2115, 1212x2117, 2112x1208, 2114x1211, 2114x1214, 2115x1212
- `angels-of-death` officially translated? True
- `angels-of-death`: `assault-intercessor-grenadier-front.jpg` -> 2114x1214
- `battleclade`: `battleclade-auto-proxy-servitor-front.jpg` -> 2114x1214
- `blades-of-khaine`: `dire-avenger-exarch-front.jpg` -> 2114x1211
- `gellerpox-infected`: `bloatspawn-front.jpg` -> 2112x1208

## Save Integrity
- The patched save is produced by patching the original workshop JSON in place rather than rebuilding a simplified substitute.
- Team boxes keep the original object structure; only repo references in scripts and per-team card image URLs are swapped where localized assets exist.

## Final Save Audit
- All officially translated teams' active card decks point at the target repository.
- All English fallback teams' active card decks stayed on the upstream repository.
- No translated team box in the final save contains mixed target/upstream deck URLs.
