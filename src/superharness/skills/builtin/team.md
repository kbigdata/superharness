---
name: team
description: 공유 태스크 리스트 기반 협업형 멀티에이전트 파이프라인
triggers: ["team", "team up", "collaborate"]
mode: team
pipeline: ["planner", "executor", "qa-tester"]
---
단계형 파이프라인(plan → exec → verify → fix loop)으로 다중 에이전트가 공유 태스크
리스트에서 협업한다. 각 단계는 도메인×티어 에이전트로 디스패치되며, verify 실패 시
fix 루프로 진입한다.
