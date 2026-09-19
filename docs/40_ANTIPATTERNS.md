# 40. Антипаттерны

| Антипаттерн | Почему опасен | Правильная замена |
| --- | --- | --- |
| Сначала красивый экран | UI маскирует отсутствие authority | Foundation и vertical contract до UI |
| Все модули сразу | Нет outcome и rollback | Один primary slice |
| Одинаково 15 файлов | Шаблон подменяет содержание | Файлы по функции |
| PASS по строкам кода | Объём не доказывает behavior | Executable acceptance evidence |
| JWT с ролью = доступ | Claim stale после revoke | Current-state server authorization |
| CORS решает CSRF | Разные классы угроз | CSRF + Origin + Fetch Metadata |
| HTTP 200 = business success | Transport не равен acceptance | Commit + Receipt + readback |
| Retry повторяет POST | Двойной effect | Stable operation ID + idempotency |
| UPDATE вместо correction | Теряется первоисточник | Linked correction/successor |
| Support видит всё | Hidden superadmin | Content-blind + break-glass |
| Checkpoint есть, restore готов | Archive может быть нечитаем | Independent readback |
| Agent сам продолжит | Потеря owner control | Explicit next-stage authorization |
| Ошибку не упомянем | Ложная evidence history | Honest first-fail |
| Красивый отчёт вместо evidence | Слово не доказательство | Machine-generated receipts |
| Markdown-контракт = enforcement | Протокол сам себя не принуждает | Внешний sandbox E1–E3 (docs/44) |
| Один чеклист на всё | Театр на R0, дыра на R4 | Уровни P0/P1/P2 (docs/45) |
| Acceptance одной фразой | Rubber-stamping, формальная evidence | evidenceReadHash + sampling audit (docs/46) |
| Deputy без мандата | Самовольное расширение authority | Mandate с scope/expiry (docs/46) |
| «Агент сказал, что защищён» | Ложное заявление готовности | Заявление фактического enforcement level |
