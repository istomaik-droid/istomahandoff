# 35. Incident handling

## Немедленные действия

1. Остановить новые mutations.
2. Не удалять и не скрывать изменения.
3. Не делать hard reset.
4. File/status inventory.
5. Сравнить с last verified anchor.
6. Отделить user changes от agent changes.
7. Классифицировать каждое изменение R0–R5.
8. Проверить data, authority, evidence, network, spend, release.
9. Только read-only diagnostics.
10. Представить варианты: сохранить, bounded-correct, rollback.

## Incident report

```text
INCIDENT_ID:
LAST_VALID_DECISION:
LAST_VALID_CHECKPOINT:
UNAUTHORIZED_ACTIONS:
FILES_CHANGED:
PROCESSES_STARTED:
NETWORK_OR_EXTERNAL_EFFECTS:
DATA_TOUCHED:
EVIDENCE_MUTATED:
TESTS_ACTUALLY_RUN:
CURRENT_SAFE_STATE:
ROLLBACK_OPTIONS:
OWNER_DECISION_REQUIRED:
```

## Правило исправления

Исправление не уничтожает evidence нарушения. Сначала incident receipt,
затем owner выбирает correction или rollback.
Агент не принимает собственное оправдание как closure.

## Правило-прецедент

Правило, рождённое инцидентом, содержит inline-ссылку на прецедент
(INC-ID или дату) рядом с формулировкой правила.
Правило с прецедентом — шрам: его нарушение уже случалось.
