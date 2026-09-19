# 29. AI и автоматизация

Agent с теми же или меньшими правами, что назначенный actor.

Нет hidden superadmin и bypass PDP.

Tool call связан с domain, purpose, authority, audit.

AI output — proposal, пока policy не разрешила bounded action.

High-impact action — human authority + step-up.

no-AI baseline, evaluation set, harm metrics, kill switch.

Prompt, memory, retrieved content — untrusted input.

Secrets и cross-domain content не в общий AI context.

Agent не подтверждает собственный результат вместо владельца.

Zero Humans Company — доктрина, не утверждение о достигнутом.

## AI-specific guardrails

Tool allowlist.

Network deny by default.

Spend caps.

Context budget management.

Agent audit log.

Human-in-the-loop для destructive/irreversible.

No self-approval.

Kill switch.

Multi-agent coordination rules.

Agent contract: preflight, progress, stop.

Prompt injection defense.

Memory poisoning protection.

## Граница

Этот раздел — конвенция. Какая часть guardrails реально enforced
средой, определяется enforcement level (docs/44). Агент обязан заявлять
фактический уровень, а не заявлять защиту, которой нет.
