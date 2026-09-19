# MANDATE-XXXX: мандат Owner Deputy

Статус: active | revoked | expired

## Правила

1. Записывается в decision log записью type: MANDATE.
2. Не покрывает: R5, release, product boundary, spend.
3. Не делегируется дальше.
4. Отзыв — однострочной записью, мгновенный.
5. Каждое решение deputy ссылается mandateRef.

```text
MANDATE-XXXX
- Grantee: <NAME>
- Scope: <STAGE / типовые решения>
- MaxRiskClass: R?
- IssuedAt: <ISO8601>
- ExpiresAt: <ISO8601>          # по умолчанию +14 дней
- IssuedBy: <OWNER_NAME>
- DecisionRef: DEC-XXXX
- ReceiptSha256: <sha256>
```
