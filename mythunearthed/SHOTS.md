# Речник на сцените (общ за QUILL и make_short)
Всеки сценарий е `<topic>/script.json` във формата на `noah/script.json`. Ползвай САМО тези типове.

## Правила
- 13–16 изречения, общо 130–155 думи (~55–62 сек с ускорения глас). Кука в изречение 1, въпрос за коментари накрая.
- Всяко изречение има `source` (стих, „tradition“, „archaeology“, „claim by X“). Спорното се казва като спорно. Веднъж ясно: какво НЕ е доказано.
- Произношение: при трудни имена добави `"say": "фонетично изписване"` (само за гласа; надписите остават с правилното изписване).

## Типове кадри (`shot`)
| shot | полета | какво е |
|---|---|---|
| PRESENTER | `action` (idle, wave, point_left, point_right, shrug, surprised, nod), `backdrop` (desert, mountain, city, night, sea) | Ezra говори към камерата |
| MAP | `focus` [lat, lon], `zoom` (close, mid, wide), `pins` [ключове от places] | наклонена карта с релеф, Ezra в ъгъла |
| TEXT | `kind` (quote, word_shatter, glow_word, big_number), `text` | кинетична типография |
| EVENT | `scene` от списъка долу, `label` | илюстрирана сцена |

## EVENT сцени
`tablet` (глинена/каменна плоча с надпис) · `aerial` (въздушна снимка с въпросителна) · `birds` (птици излитат) · `counter` (`number`, расте до числото) · `icon_grid` (`icon`, `count`) · `object` (`object`: ark_box, scroll, jar, crown, gold_pile, ship, tower, gate, fire, ruins, whale; прожектор и бавно въртене) · `split_compare` (`left`, `right`: две версии една срещу друга) · `sea_parting` · `mountain_storm` · `fire_rain` · `crowd`

## places
`"key": [lat, lon, "Label", icon, "solid"|"dashed"]`; icon ∈ peak, walls, temple, tent, ship, ruins, river, dot. `dashed` = спорно място.
