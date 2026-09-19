# 03. Data и fixture strategy

## Обязательно

1. Synthetic fixture.
2. Reference fixture.
3. Запрет реальных персональных данных.
4. Provenance.
5. Anonymization.
6. Expected oracle.
7. Separation expected/observed.

## Data classification

| Класс | Обработка |
| --- | --- |
| Public | Свободно |
| Internal | Ограниченный доступ |
| Confidential | Шифрование, audit |
| Restricted | Минимальный доступ, шифрование, retention |

## Правила

1. Fixture version и hash фиксируются.
2. Expected source запечатывается до прогона.
3. Менять accepted fixture после observed result запрещено.
4. Именованная staging-среда (копия боевых данных) с командой обновления —
   стандартный паттерн для мутирующих тестов и миграций. Мутации staging не
   затрагивают прод.
