# 41. Метрики

## DORA

- Lead time for changes.
- Deployment frequency.
- Change failure rate.
- Mean time to restore (MTTR).

## Процессные

- WIP: 1.
- Rework rate.
- Escaped defects.
- Test flakiness.
- Review time.
- Cost per work item (cloud, CI, AI tokens).
- License compliance.
- SBOM freshness.

## Здоровье authority (docs/46)

- Acceptance-to-evidence read ratio: доля acceptance-решений с валидным evidenceReadHash (цель 1.0).
- Sampling audit findings: число расхождений, найденных выборочной перепроверкой.
- Median time-to-acceptance vs median evidence size: слишком быстрый acceptance — индикатор rubber-stamping.
- Mandate usage: сколько решений принято deputy, в пределах scope / за пределами (цель второго: 0).
- Protocol level drift: доля работ, повышенных агентом по риску (индикатор качества TRIAGE).
- STOPPED_PROTOCOL_MISMATCH count: частота рассинхрона версий.

## Стоимость агента

- Turns per work item: число ходов (tool-вызовов) на задачу; лимит — docs/33 п. 30.
- Cache-read dominance: отношение прочитанного из кэша к выводу модели
  (главный драйвер расхода — перечитывание истории, не ответы).
- Эффект гейт-скриптов: ходов до/после объединения проверок (docs/30).
- Эффект compression gateway: замеряется отдельно по его /stats,
  после внедрения дисциплины ходов, не вместе (DEC-0013).
