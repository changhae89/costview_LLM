# Proposal Ingestion

`proposal/`는 뉴스를 수집해 DB에 적재하는 독립 파이썬 패키지입니다.

## Structure

- `proposal/main.py`: 스케줄러 진입점
- `proposal/config.py`: `.env` 로딩 및 설정 해석
- `proposal/common/supabase_client.py`: Supabase 클라이언트 생성
- `proposal/collectors/`: 외부 데이터 수집기
- `proposal/db/`: Postgres/Supabase 저장 로직

## Environment Priority

1. 레포 루트 `.env`를 기본값으로 로드
2. `proposal/.env`가 있으면 proposal 전용 값으로 덮어씀

## Supported Database Config

- Postgres: `DATABASE_URL` 또는 `POSTGRES_URL`
- Supabase: `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`

하위 호환으로 `API_KEY`가 Postgres URI일 때만 읽습니다.

## Current Flow

- 소비재 키워드를 DB에서 조회
- Exa로 최근 뉴스 수집
- `raw_news`에 중복 제거 후 저장

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r proposal/requirements.txt
python -m proposal.main
```

## Execution Rule

- 협업 기준 실행 명령은 항상 레포 루트에서 `python -m proposal.main` 입니다.
- `proposal/main.py` 직접 실행도 가능하지만, 기본 규칙은 모듈 실행입니다.
- 내부 import는 `from proposal...` 절대경로를 유지합니다.
