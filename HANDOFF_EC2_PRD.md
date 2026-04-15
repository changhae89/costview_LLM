# PRD EC2 Deployment Handoff

## 목적

이 문서는 현재 `costview_LLM` 저장소에서 진행 중인 `prd` 배치의 EC2 배포 작업을 다음 작업자가 이어서 진행할 수 있도록 정리한 인수인계 문서입니다.

## 현재 프로젝트 이해

- 프로젝트명: `CostView`
- 현재 중심 모듈: `prd`
- `prd`는 웹 서버가 아니라 **뉴스 분석 배치**입니다.
- 실행 진입점: `python -m prd.main`
- 역할:
  - 미처리 뉴스 조회
  - LLM 기반 분석 수행
  - 분석 결과를 DB 또는 Supabase에 저장

## 최근 코드베이스 변화

- 최근 upstream merge 이후 `prd`가 LangGraph 기반 분석 파이프라인으로 고도화됨
- `proposal`은 현재 upstream 기준으로 사실상 제거된 상태
- 따라서 이번 배포 작업은 `proposal`이 아니라 `prd` 중심으로 정리해야 함

## 이번 로컬 작업에서 반영한 내용

### 1. 배포 방식 재정의

기존 가정:
- `prd`를 웹 서비스처럼 EC2에서 상시 컨테이너로 띄우는 흐름

현재 재정의:
- `prd`는 **배치 실행형 컨테이너**
- `main` 브랜치 push 시 GitHub Actions가 EC2에 SSH 접속
- EC2에서 최신 코드 pull
- Docker 이미지 build
- `prd` 컨테이너 1회 실행
- 로그 출력 후 종료 상태 확인

### 2. 추가/수정 파일

#### 수정됨

- `prd/main.py`
  - 문법 문제 수정
  - 로그 문구 일부 정리

- `prd/db/connection.py`
  - `psycopg2` 대신 `psycopg` 기준으로 import 수정

- `prd/db/fetch.py`
  - `psycopg2.extras.RealDictCursor` 대신 `psycopg.rows.dict_row` 사용하도록 수정

#### 새로 추가됨

- `.github/workflows/deploy.yml`
  - EC2 SSH 기반 PRD 배치 실행용 GitHub Actions 워크플로우

- `prd/Dockerfile`
  - `prd` 배치를 Docker 이미지로 실행하기 위한 파일

- `infra/aws/ec2-bootstrap.sh`
  - EC2 서버 초기 세팅 스크립트

- `infra/aws/README.md`
  - EC2 초기 세팅 안내 문서

## deploy.yml 현재 정의

파일:
- `.github/workflows/deploy.yml`

트리거:
- `main` 브랜치 push

동작:
1. GitHub Actions가 EC2에 SSH 접속
2. `~/costview-prd/.env` 존재 확인
3. `~/.ssh/costview_github_deploy` 존재 확인
4. EC2에서 private repo pull
5. 기존 `costview-prd-run` 컨테이너 삭제
6. Docker image rebuild
7. `prd` 배치 컨테이너 1회 실행
8. 컨테이너 로그 출력
9. 종료 상태 확인

중요:
- 현재 `prd`는 웹 API 서버가 아니므로 `-p 8000:8000` 같은 포트 바인딩은 제거함
- `docker run -d`가 아니라 **foreground 1회 실행**으로 정의되어 있음

## 로컬 검증 결과

### 성공한 것

- `prd/main.py` 문법 확인 성공
- `prd` 테스트 성공

실행 결과:
- `11 passed`

### 실패한 것

- `python -m prd.main` 실제 실행은 실패

실패 원인:
- 로컬 환경의 외부 네트워크 접근 제약
- 에러:
  - `WinError 10013`

해석:
- 코드 로직 문제라기보다 Supabase 또는 외부 API로 나가는 네트워크가 막힌 상태
- 즉 테스트는 통과했고, 실제 런타임 네트워크만 현재 환경에서 차단됨

## 중요한 기술 메모

### DB 드라이버 이슈

upstream 코드 일부는 `psycopg2`를 import하고 있었지만:
- `prd/requirements.txt`에는 `psycopg[binary]`가 명시되어 있었음

그래서 로컬 검증을 위해 아래처럼 정리함:
- `prd/db/connection.py` -> `import psycopg`
- `prd/db/fetch.py` -> `from psycopg.rows import dict_row`

이 수정 이후 테스트 통과 확인함.

## 현재 git 상태 기준 커밋 추천 범위

### 이번 커밋에 포함 추천

- `prd/main.py`
- `prd/db/connection.py`
- `prd/db/fetch.py`
- `prd/Dockerfile`
- `.github/workflows/deploy.yml`
- `infra/aws/ec2-bootstrap.sh`
- `infra/aws/README.md`

### 이번 커밋에서 제외 추천

- `.dockerignore`
- `infra/azure/**`
- `.github/workflows/build-batch-images.yml`
- `.github/workflows/deploy-batch-jobs.yml`
- `proposal/**`

이유:
- 현재 목표는 `EC2 + GitHub Actions + prd 배치 실행`
- Azure 관련 파일과 `proposal` 잔재는 혼선을 줄 수 있음

## EC2 관련 현재 전제

GitHub Secrets는 사용자가 설정했다고 보고 있음:
- `EC2_HOST`
- `EC2_USERNAME`
- `EC2_PORT`
- `EC2_SSH_KEY`

EC2 내부에서 추가로 필요:
- GitHub private repo 접근용 deploy key
- `~/costview-prd/.env`
- 최초 clone
- Docker 권한 확인

## 동료가 이어서 해야 할 일

### 1. git 상태 최종 확인

확인할 것:
- staging에 `.env`가 포함되지 않았는지
- `proposal` 폴더 잔재가 포함되지 않았는지
- Azure 관련 파일이 섞이지 않았는지

### 2. 커밋

추천 커밋 메시지:

```bash
chore: add EC2 batch deployment for prd
```

### 3. push 전략 결정

주의:
- `deploy.yml`은 `main` push 시 작동
- `dev`에 먼저 올릴지, `main`까지 바로 반영할지 결정 필요

### 4. EC2 서버 사전 상태 확인

필수 확인:
- `~/costview-prd/.env` 존재
- `~/.ssh/costview_github_deploy` 존재
- `ssh -T git@github.com` 동작
- `docker ps` 가능

### 5. 실배포 검증

가능하면 아래 순서:
1. `main` 반영
2. GitHub Actions 실행
3. EC2 로그 확인
4. 컨테이너 종료 코드 확인

## 참고 파일

- `prd/main.py`
- `prd/db/connection.py`
- `prd/db/fetch.py`
- `prd/Dockerfile`
- `.github/workflows/deploy.yml`
- `infra/aws/ec2-bootstrap.sh`
- `infra/aws/README.md`

## 한 줄 요약

현재 상태는 `prd`를 EC2에서 GitHub Actions + Docker로 1회 배치 실행하는 구조로 재정의했고, 로컬 테스트는 통과했으며, 남은 작업은 **커밋 정리 -> EC2 사전 준비 확인 -> main 반영 후 실제 배포 검증**입니다.
