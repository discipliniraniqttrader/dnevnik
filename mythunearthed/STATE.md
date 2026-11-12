# MythUnearthed / Станция Зенит: състояние на проекта
Кратко резюме, за да може нова сесия да продължи евтино, без да чете цялата история.

## Канал
- YouTube: **MythUnearthed**, „Bible history, mapped“. Английски, шортове 9:16, ~55–65 сек.
- Водещ: **Ezra**, 3D археолог (`presenter/render.js`).
- Глас: Chatterbox (`voice/venv`, HF_HUB_DISABLE_XET=1), тембър от `out/voice_am_michael.wav`. Резервен: Kokoro `am_michael`.
- Карта: `mapfx/` (релеф, наклон, пинове). Региони: base, mesopotamia, ararat, ethiopia, indian_ocean.

## Станция (табло)
- https://claude.ai/artifact/NbkBMBSCDLB4sx9PKpcS91 (db: agents, items, log, station/main)
- Комплект за качване: https://claude.ai/artifact/SmJnw67hPdTNDqdqYeqFo8 (media/*.mp4, brand/*)

## Екипаж и модели
HELM = Opus (планира, проверява). ORION/ATLAS/SENTRY/ORACLE = Haiku. QUILL/PRISM/HERALD = Sonnet. Детайли: `crew.json`, правила за качество: `QUALITY.md`.

## Видеа
| # | Тема | Файл | Статус |
|---|---|---|---|
| 1 | Journeys of Paul v2 | out/paul_v2.mp4 | готово, чака „качвай“ |
| 2 | Exodus route | out/exodus.mp4 | готово, чака „качвай“ |
| 3 | Noah's Ark: 4 answers | noah/script.json → out/noah.mp4 | в работа |
| 4–8 | Ark of Covenant, Sodom, 10 tribes, Eden, Babel | на станцията (★) | идеи |

## Качване
HERALD работи на компютъра (usr-PC, D:\Claude). Публикува само след „качвай“ от Петър в неговия чат. Chrome file_upload има лимит 10 MB, затова ползва *_9mb.mp4 от комплекта.

## Как се прави ново видео (евтино)
1. QUILL (Sonnet) пише `<тема>/script.json` във формата на `noah/script.json`.
2. HELM преглежда фактите в самия JSON (без рендериране).
3. Рендерира се с една команда (`make_short.py <script.json>`, след като бъде обобщен от noah pipeline).
4. HELM преглежда **един** контакт-лист с 12–20 кадъра, не отделни кадри.
