# PRD Analysis

`prd/`는 적재된 원시 뉴스를 Gemini로 분석해 `news_analyses`와 `causal_chains`에 저장하는 독립 파이썬 패키지입니다.

## Structure

- `prd/main.py`: 스케줄러 진입점
- `prd/config.py`: `.env` 로딩 및 설정 해석
- `prd/common/supabase_client.py`: Supabase 클라이언트 생성
- `prd/db/`: pending 뉴스 조회 및 결과 저장
- `prd/llm/gemini_client.py`: Gemini 프롬프트와 후처리

## Environment Priority

1. 레포 루트 `.env`를 기본값으로 로드
2. `prd/.env`가 있으면 PRD 전용 값으로 덮어씀

## Required Env Vars

- Gemini: `GEMINI_API_KEY`

DB는 둘 중 하나를 사용합니다.

- Postgres: `DATABASE_URL` 또는 `POSTGRES_URL`
- Supabase: `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`

하위 호환으로 `API_KEY`가 Postgres URI일 때만 읽습니다.

## Runtime Defaults

- `PRD_MAX_BATCH` 기본값은 코드에서 `1`입니다.
- 필요할 때만 선택적으로 환경변수로 override 합니다.

## Run

```bash
python -m pip install -r prd/requirements.txt
python -m prd.main
```

## Execution Rule

- 협업 기준 실행 명령은 항상 레포 루트에서 `python -m prd.main` 입니다.
- `prd/main.py` 직접 실행도 가능하지만, 기본 규칙은 모듈 실행입니다.
- 내부 import는 `from prd...` 절대경로를 유지합니다.
