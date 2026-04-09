# CostView Workspace

이 워크스페이스에는 두 개의 Python 배치 패키지와 TypeScript 라이브러리 코드가 함께 있습니다.

## Packages

- `proposal/`: 소비재 관련 뉴스 수집 후 `raw_news`에 저장
- `prd/`: 적재된 `raw_news`를 Gemini로 분석 후 `news_analyses`, `causal_chains`에 저장
- `src/`: CostView 웹앱용 TypeScript 라이브러리와 테스트

## Path Rules

- Python 배치는 모두 레포 루트에서 모듈 실행을 기본 규칙으로 사용합니다.
- 권장 실행 방식:
  - `python -m proposal.main`
  - `python -m prd.main`
- 내부 import는 모두 패키지 절대경로를 유지합니다.
  - 예: `from proposal...`, `from prd...`
- `proposal/main.py`, `prd/main.py`에는 IDE 직접 실행을 위한 보조 경로 처리도 들어 있지만, 협업 기준 명령은 항상 `python -m ...` 입니다.

## Environment Rules

- 레포 루트 `.env`는 공통 기본값입니다.
- `proposal/.env`, `prd/.env`는 각 패키지 전용 override 파일입니다.
- 샘플은 각 패키지의 `.env.example`을 기준으로 맞춥니다.

## Install

```bash
python -m pip install -r proposal/requirements.txt
python -m pip install -r prd/requirements.txt
npm.cmd test
```

## Run

```bash
python -m proposal.main
python -m prd.main
```

