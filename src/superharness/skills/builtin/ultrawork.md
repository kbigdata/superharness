---
name: ultrawork
description: 최대 병렬 멀티에이전트 오케스트레이션
triggers: ["ultrawork", "ulw", "uw"]
mode: ultrawork
pipeline: ["architect", "executor", "qa-tester"]
---
복잡한 작업을 전문 에이전트들에게 분산하여 최대한 병렬로 실행한다.
plan(architect) → 병렬 exec(executor) → verify(qa-tester) 순으로 공유 태스크 리스트를 처리하되,
가능한 모든 단계를 동시에 디스패치한다.
