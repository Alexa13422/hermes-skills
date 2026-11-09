# OmniRoute: де лежить логіка роутингу

Локальний OmniRoute — Node-сервіс, слухає :20128, стан у
`~/.omniroute/storage.sqlite`. Служить уніфікованим OpenAI-сумісним API до
багатьох провайдерів і має власний авто-роутер.

## Вихідники: два дерева, не одне

Встановлений пакет: `/usr/lib/node_modules/omniroute/`.

- `src/` — серверні хендлери: `src/sse/handlers/autoRouting.ts`,
  `src/sse/handlers/resolveRoutingModel.ts`, `src/domain/assessment/types.ts`
- `open-sse/` — сам рушій авто-комбо: `open-sse/services/autoCombo/`

Шукати треба в обох: `src/` імпортує з `@omniroute/open-sse/…`, тому grep
лише по `src/` дає тільки обгортки без реальної логіки.

Ключові файли `open-sse/services/autoCombo/`:

| Файл | Що в ньому |
|---|---|
| `complexityRouter.ts` | класифікація складності запиту → `recommendedTier` |
| `scoring.ts` | скоринг кандидатів (`tierAffinity`, `specificityMatch`) |
| `routerStrategy.ts` | стратегії: rules / cost / latency / SLA / LKGP |
| `pipelineRouter.ts` | багатостадійні пайплайни, модель на стадію за fitness tier |
| `taskFitness.ts` | придатність моделі до типу задачі |
| `selfHealing.ts` | автовідновлення після фейлів |
| `builtinCatalog.ts` | вбудовані `auto/*` варіанти |
| `suffixComposition.ts` | розбір суфіксів типу `auto/coding:cheap` |

Плюс `open-sse/services/specificityDetector.ts` (підрахунок score) і
`open-sse/services/comboConfig.ts` (`DEFAULT_COMBO_CONFIG`, прапорці).

## Вбудований класифікатор складності

Не викликає LLM: детермінований підрахунок 0–100 по шести сигналах:
`codeComplexity`, `mathComplexity`, `reasoningDepth`, `contextSize`,
`toolCalling`, `domainSpecificity`. Пороги в `specificityDetector.ts`:

```text
score ≤ 5    trivial   → free
score ≤ 20   simple    → free
score ≤ 40   moderate  → cheap
score ≤ 65   complex   → cheap
score > 65   expert    → premium
```

Чим саме набирається score — `open-sse/services/specificityRules.ts`:
`codeComplexity` = код-блоки ×5 + інлайн-бектіки ×0.5 + регексп-індикатори
мов (`function \w+(`, `import … from`, `class`, `def`, `SELECT … FROM`) ×2,
стеля 25; `contextSize` дає **0 балів до 1000 токенів** і 15 лише понад
64k; `reasoningDepth` — ключові слова (`therefore`, `step by step`,
нумеровані списки). Наслідок, який треба перевіряти живими запитами:
коротка проза без код-блоків набирає одиниці балів незалежно від
семантичної складності, тож і «rename variable» і «design a consensus
algorithm with linearizability proof» однаково дають `level=trivial`.
Пороги зашиті в `specificityDetector.ts`, конфігом не змінюються — зміна
вимагає патчу файлу, який злітає при оновленні пакета.

`complexityRouter.ts` додає жорстке правило: якщо в тілі запиту є `tools`,
tier піднімається мінімум до `cheap`. `escalateTier` лише підвищує tier,
ніколи не знижує. При будь-якому винятку `buildComplexityRoutingHint`
віддає `null` — fail-open, скоринг стає tier-нейтральним замість падіння.

`analyzeSpecificity` повертає `confidence` = покриття категорій × 0.8
(+0.1 при ≥2 повідомленнях). Це готовий поріг для вирішення, чи варто
доплатити за LLM-класифікатор.

## Прапорець, через який все це не працює «з коробки»

У `comboConfig.ts`: `complexityAwareRouting: false` — opt-in, виключений типово.
Поки він `false`, класифікатор НЕ впливає на вибір моделі — роутинг іде лише
за стратегією комбо. Перевіряти саме прапорець, а не наявність коду, перш
ніж робити висновки про можливості сервісу.

Друга умова: увімкнений прапорець марний, якщо в комбо всі моделі одного
рівня — `tierAffinity` ні на що не впливає, класифікатору нема куди роутити.
Змінювати прапорець і склад комбо разом, інакше зміна нічого не дасть.

Третя умова — ваги. Прапорець лише додає два фактори до скорингу, а в них
дефолтна вага близько 5% кожен (`DEFAULT_WEIGHTS` у `scoring.ts`:
`specificityMatch` і `tierAffinity` ≈ 0.0476) проти `health` ≈0.16,
`quota`/`costInv` ≈0.14. Тобто складність запиту впливає на вибір близько
на 10% і практично не перебиває здоров'я й квоти провайдера. Щоб
роутинг реально реагував, підносити ці дві ваги в `scoringWeights`
(вони нормалізуються до суми 1, тому підвищення однієї знижує решту).

### Де цей прапорець можна зберегти, а де ні

Не писати `complexityAwareRouting` у `config` окремого комбо: ключ у списку
видалюваних (міграція `strip_legacy_combo_config_keys` + клієнтський strip у
формі комбо), тому його зітре на наступному збереженні. Живе значення —
у глобальних `comboDefaults` (каскад
`DEFAULT_COMBO_CONFIG → settings.comboDefaults → providerOverrides[provider] → combo.config`).
Ендпоінт: `GET` і **`PATCH`** `/api/settings/combo-defaults`, схема
`updateComboDefaultsSchema` (`comboDefaults`, `providerOverrides`). `PUT`
віддає 405, хоча openapi.yaml перелічує лише `get` — метод перевіряти
фактично. Це `requireManagementAuth` — див. розділ про авторизацію нижче.

`PATCH` **замінює весь `comboDefaults`, а не мержить**: відправка лише
`{complexityAwareRouting: true}` зітре `strategy`, `maxRetries`,
`retryDelayMs` і решту. Спершу `GET`, потім відправляти повний обʼєкт із
додатковими ключами.

Прапорець діє лише там, де працює скоринг-рушій:
`buildComplexityRoutingHint` викликається тільки з `resolveAutoStrategy.ts`,
а туди веде `targetResolution.ts` по умові `if (strategy === "auto")`.
Тобто це не лише `auto/*` моделі — **власне комбо зі стратегією `auto`**
(в UI «Intelligent Auto») теж проходить через класифікатор. Усі інші
стратегії зі списку (`priority`, `reset-aware`, `round-robin`,
`cost-optimized` …) розподіляють трафік і не дивляться на зміст запиту
взагалі. Тому рецепт «complexity-роутинг для свого комбо» = перевести
комбо на стратегію `auto`, а не створювати окреме `auto/*`.

## Стратегії роутингу, які взагалі існують

`src/shared/constants/routingStrategies.ts`:

- комбо-стратегії: `priority`, `weighted`, `round-robin`, `context-relay`,
  `fill-first`, `p2c`, `random`, `least-used`, `cost-optimized`, `reset-aware`,
  `reset-window`, `headroom`, `strict-random`, `auto`, `lkgp`,
  `context-optimized`, `cache-optimized`, `fusion`, `pipeline`
- auto-стратегії (всередині `auto`): `rules`, `cost`, `eco`, `latency`, `fast`, …
- вагові профілі в `modePacks.ts`: `ship-fast`, `cost-saver`, `quality-first`,
  `offline-friendly` — у всіх трьох перших `tierAffinity` і `specificityMatch`
  стоять в 0, тобто mode pack гасить complexity-роутинг повністю

## Як прочитати фактичну конфігурацію комбо

Бінарника `sqlite3` в системі може не бути — читати через Python stdlib,
обов'язково read-only, щоб не зачепити живий сервер із WAL:

```python
import sqlite3, json
db = sqlite3.connect(
    'file:/home/alexa/.omniroute/storage.sqlite?mode=ro&immutable=1', uri=True)
cur = db.cursor()
for name, data in cur.execute("select name, data from combos"):
    j = json.loads(data)
    print(name, j['strategy'], [m['model'] for m in j['models']], j['config'])
```

Схема не очевидна: уся конфігурація комбо лежить у текстовій колонці `data`
як JSON (`models`, `strategy`, `config`); колонки `config_json` немає — запит до
неї падає `no such column`. База має близько 130 таблиць; розвідку починати
з `select name from sqlite_master where type='table'`.

Корисні таблиці:

- `combos` — власні комбо з `strategy` і `config`
- `routing_decisions` — лог рішень (`task_type`, `model_selected`, `score`,
  `factors_json`, `fallbacks_triggered`, `success`, `latency_ms`, `cost`)
- `reasoning_routing_rules` — правила effort: `model_pattern`, `source_effort`,
  `target_effort`, `target_model`, `priority`
- `model_combo_mappings`, `combo_adaptation_state`, `tier_config`

Порожня `routing_decisions` при `trackMetrics: true` означає, що історії для
налаштування порогів немає — перш ніж тюнити роутинг, накопити дані.

## Management API: спершу спробувати `/v1`-ключ через curl

Авторизація `/api/*` залежить від збірки — **перевіряти фактично, не
припускати**. На поточній збірці `GET /api/combos` і
`GET /api/settings/combo-defaults` віддають **200 зі звичайним `/v1` Bearer
ключем**, тобто читання конфігу не вимагає ні браузера, ні SQLite:

```bash
OKEY=$(grep -h "HERMES_CUSTOM_LOCALHOST_20128_API_KEY" ~/.hermes/.env | head -1 | cut -d= -f2- | tr -d '"'"'"' ')
curl -s -m 25 -H "Authorization: Bearer $OKEY" http://localhost:20128/api/combos > /tmp/combos.json
curl -s -m 25 -H "Authorization: Bearer $OKEY" http://localhost:20128/api/settings/combo-defaults
```

Починати з curl: логін у дашборд через браузер — довгий обхід для того, що
читається одним запитом.

Курлити у файл і парсити через heredoc `python3 - <<'EOF'`, а не inline
`python3 -c`: і ключ, і JSON містять лапки, які вкладене shell-квотування
калічить.

`/api/combos` на одних збірках віддає `{"combos":[…]}`, на інших — голий
масив. Розрулювати через
`d['combos'] if isinstance(d, dict) and 'combos' in d else d`, інакше парс
падає з `KeyError`.

Якщо ендпоінт **запису** все ж відкидає `/v1`-ключ
(`AUTH_001 Authentication required`, `requireManagementAuth`, особливо коли
в `key_value` стоїть `settings.requireLogin = true`) — тоді переходити на
dashboard-сесію з CSRF: браузер + логін-кука, або читати/писати через
SQLite.

Неіснуючі шляхи під `/v1/` віддають виразний `unknown_route` із путтю —
зручно швидко перебрати припущення щодо ендпоінтів. Але надійніше не
вгадувати, а взяти фактичний перелік із
`dist/.build/next/server/app/api/` або з `dist/public/openapi.yaml`
(openapi може мати лише `get`, тоді як реальний роут підтримує й `PUT` —
перевіряти по зібраному роуту, не лише по специфікації).

## Що експоноване в дашборді

Сторінки — `dist/.build/next/server/app/(dashboard)/dashboard/`. Релевантні для
роутингу: `auto-combo`, `combos`, `settings`, `resilience`, `provider-stats`,
`playground`. Вибір моделей, порядку, стратегії та retry для власних комбо
робиться саме на `combos`.

Як дізнатися, чи ключ налаштування має галочку в UI: grep по
`dist/.build/next/static/chunks/`. Якщо ключ трапляється тільки в масиві
видалюваних legacy-ключів — контрола в інтерфейсі немає, лише API/БД.
Шукати також людську підпис-метку (напр. «Complexity») — відсутність
лейбла при наявному ключі — та сама ознака.

## Де живуть налаштування в БД

Таблиці `settings` немає. Глобальні налаштування — у `key_value`
(`namespace`, `key`, `value`), намеспейси: `settings`, `compression`,
`databaseSettings`, `modelAliases`, `lkgp` (last-known-good provider по комбо),
`providerLimitsCache` (живі квоти й плани провайдерів з `resetAt`).
Швидкий огляд:

```python
for ns, k, v in cur.execute(
        "select namespace, key, substr(value,1,200) from key_value order by namespace, key"):
    print(f"[{ns}] {k} = {v}")
```


## Пайплайн із критиком (reflect)

Критик уже вбудований — не писати свій. Стадії задані в `src/domain/pipeline.ts`
по `taskType` і виражені в fitness-tier, не в конкретних моделях. Для
`taskType: code`:

```text
plan    → best-reasoning
execute → cheapest
reflect → moderate      ← критик
fix     → cheapest
```

Критик віддає строгий JSON `{status, issues[], corrected}`; при `pass`
стадія `fix` скіпається (токени не витрачаються дарма), при `fail` —
цикл перезапуску в межах `max_reflection_loops`.

`strategy: "auto"` і пайплайн **компонуються**: `pipeline_enabled: true` у
рантайм-конфігу auto-комбо дає й класифікатор складності, й критика.
Окрема стратегія `pipeline` — не єдиний шлях до стадій.

Конфіг для комбо з критиком:

```js
{strategy: "auto",
 models: [/* три-чотири моделі різних tier */],
 config: {pipeline_enabled: true,
          max_reflection_loops: 2,
          skip_pipeline_for_tokens_under: 50,
          modePack: "quality-first", routerStrategy: "rules"}}
```

`skip_pipeline_for_tokens_under` обов'язковий — без нього короткі запити
платять троєкратним викликом за ніщо. Ці ключі в snake_case, на відміну
від camelCase-решти рантайм-конфігу; підтверджувати їх збереження в
відповіді `POST /api/combos`, а не лише по статусу 201 — невідомі ключі
іноді вирізаються мовчки.

Стадії в логах (`~/.omniroute/logs/application/app.log`, тег `PIPELINE`):

```text
{"tag":"PIPELINE","msg":"Intent: code → task: code"}
{"tag":"PIPELINE","msg":"Stage: tier=best-reasoning, model=claude/claude-opus-5-high"}
{"tag":"PIPELINE","msg":"Stage: tier=cheapest, model=codex/gpt-5.6-terra-medium"}
{"tag":"PIPELINE","msg":"Stage: tier=moderate, model=claude/claude-opus-5-high"}
```

Відсутність четвертого `Stage` — це й є підтвердження, що критик віддав
`pass`. Оскільки стадії зв'язані з tier, а не з вендором, змішаний пул
дасть різних вендорів на різних стадіях — кеш рветься по стадіях за
визначенням, тому «одновендорні групи для caching» для пайплайн-комбо
не мають сенсу.

Живий тест критика робити задачею з реальними крайніми випадками
(парсер із валідацією й помилками), а не коротким промптом — короткий
відсічеться порогом і пайплайн не відпрацює. Час на запит з трьома
стадіями — десятки секунд, тому curl-таймаут ставити від 300 с.

## Створення комбо через API

`POST /api/combos` (201 при успіху). Тіло — `createComboSchema`:
`name`, `strategy`, `models[]`, `config`. Крок моделі:
`{kind:"model", provider:"claude", model:"claude/claude-opus-5-high"}` —
effort задається суфіксом у самому ID моделі.

Smart-конфіг для стратегії `auto` (ключі з `comboRuntimeConfigSchema`):
`modePack`, `routerStrategy`, `explorationRate`, `budgetCap`,
`candidatePool`, `scoringWeights`, `responseValidation`.

Вкладені комбо для фолбеку між вендорами:

```js
{name:"main-smart", strategy:"priority",
 models:[{kind:"combo-ref", comboName:"claude-smart"},
         {kind:"combo-ref", comboName:"codex-smart",
          fallbackOnlyOnQuotaExhaustion:true}],
 config:{nestedComboMode:"execute", maxComboDepth:3}}
```

`fallbackOnlyOnQuotaExhaustion: true` відрізняє «виснажилася квота» від
«будь-яка помилка». Без `nestedComboMode: "execute"` валідація
(`requiresQuotaOnlyComboRefExecute`) відкидає такий combo-ref з 400.

`responseValidation` — дешевий verify-шар на рівні шлюзу: `forbiddenSubstrings`
(ловить відмови типу `I cannot help`), `requiredSubstrings`,
`minContentLength`, `jsonPathPredicates`. 200 OK, що не пройшов перевірку,
фейловиться на наступну цілі так само, як HTTP-помилка. Панель «Agent
Features» (override system message, tool filter regex, context length) до
роутингу за складністю не стосується — лишати порожньою.

## Де дивитися, що класифікатор реально вирішив

`~/.omniroute/logs/application/app.log`, pino-JSON. Рядок на кожен запит:

```text
{"tag":"COMBO","msg":"Complexity-aware routing: level=trivial score=1 minTier=free tools=false"}
```

Фактично вибрану модель видно у відповіді `/v1/chat/completions` у полі
`model` (повертається конкретна модель, не назва комбо) — найшвидший спосіб
підтвердити, що роутинг не завис на першому кандидаті.

## Перевірка, що сервіс живий і віддає моделі

`GET /v1/models` без ключа віддає `invalid_api_key` — це ознака живого сервісу,
не поломки. Ключ береться з `~/.hermes/.env` за іменем, що походить від хоста
і порту (`HERMES_CUSTOM_<host>_<port>_API_KEY`) — брати саме той, який відповідає
`base_url` у `hermes config get model`, інакше прилетить 401 і виглядатиме це
як непрацюючий сервіс.
