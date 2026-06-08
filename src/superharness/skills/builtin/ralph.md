---
name: ralph
description: 검증 완료까지 멈추지 않는 지속/검증 루프
triggers: ["ralph", "don't stop", "must complete", "until done"]
mode: ralph
---
목표가 검증으로 완료될 때까지 verify→fix 루프를 반복한다.
부분 완료로 종료하지 않으며, 실패한 항목만 다시 실행해 재검증한다 (persistence 모드).
