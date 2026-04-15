# AWS 배포 정리

## 1. 현재 상태

CostView `prd` 배치의 AWS EC2 기반 배포 흐름은 현재 정상 동작 직전 또는 정상 동작 상태까지 정리된 상태다.

확인된 완료 항목:

- GitHub Actions에서 EC2로 SSH 접속 가능
- EC2에서 GitHub private repository 접근 가능
- `prd` Docker 이미지 빌드 가능
- EC2에서 Docker 실행 가능
- 배치 실행에 필요한 `.env` 분리 및 적용 경로 수정 완료
- `psycopg2` 관련 코드 오류 수정 완료
- 이전 컨테이너 이름 충돌 문제 수정 완료
- Supabase URL / Key 설정 오류 원인 확인 및 재설정 완료

---

## 2. 최종 배포 구조

배포 흐름은 아래와 같다.

1. `main` 브랜치에 push
2. GitHub Actions `Run PRD Batch On EC2` 실행
3. `appleboy/ssh-action` 으로 EC2 접속
4. EC2에서 private repo 동기화
5. `prd/Dockerfile` 기준 Docker 이미지 빌드
6. EC2 서버의 외부 `.env` 파일을 주입하여 배치 컨테이너 실행
7. 컨테이너 로그 출력

---

## 3. 핵심 파일

### 배포 워크플로우

- `.github/workflows/deploy.yml`

주요 역할:

- EC2 SSH 접속
- 저장소 동기화
- 기존 컨테이너 제거
- Docker 이미지 재빌드
- 배치 컨테이너 실행

### Docker 실행 파일

- `prd/Dockerfile`

주요 역할:

- Python 3.11 slim 이미지 사용
- `prd/requirements.txt` 설치
- `prd` 코드 복사
- `python -m prd.main` 실행

---

## 4. 서버 측 필수 조건

EC2 서버에서 아래 항목이 준비되어 있어야 한다.

### 4.1 앱 디렉토리

- `~/costview-prd`

### 4.2 외부 환경변수 파일

- `~/costview-prd.env`

주의:

- 더 이상 `~/costview-prd/.env`를 사용하지 않음
- 배포 시 repo 동기화 과정에서 앱 디렉토리가 갱신될 수 있으므로, `.env`는 repo 밖에 둠

### 4.3 GitHub Deploy Key

필수 파일:

- `~/.ssh/costview_github_deploy`
- `~/.ssh/costview_github_deploy.pub`
- `~/.ssh/config`

GitHub 연결 확인 명령:

```bash
ssh -T git@github.com
```

정상 메시지 예시:

```bash
Hi changhae89/costview_LLM! You've successfully authenticated, but GitHub does not provide shell access.
```

### 4.4 Docker

확인 명령:

```bash
docker --version
docker ps
```

---

## 5. 서버 `.env` 기준

현재 `prd` 코드 기준으로 실제 사용되는 핵심 환경변수는 아래다.

필수:

```env
GEMINI_API_KEY=실제값
SUPABASE_URL=https://ijhgmemuzeujpvdlywjn.supabase.co
SUPABASE_SERVICE_ROLE_KEY=실제값
PRD_MAX_BATCH=100
```

선택:

```env
GEMINI_MODEL=gemini-2.5-flash
GEMINI_FLASH_MODEL=gemini-2.5-flash
```

주의:

- `SUPABASE_URL=...` 같은 placeholder 값이면 안 됨
- `SUPABASE_SERVICE_ROLE_KEY`는 anon key가 아니라 service role key를 권장

---

## 6. 진행 중 발생했던 실제 이슈와 해결 내용

### 6.1 `.env` 파일 없음

증상:

- `Missing /home/.../costview-prd/.env`

원인:

- 서버에 `.env`가 없었음

해결:

- EC2에 환경변수 파일 생성

### 6.2 GitHub deploy key 없음

증상:

- `Missing GitHub deploy key: /home/.../.ssh/costview_github_deploy`

원인:

- EC2에서 private repo 접근용 SSH key 미설정

해결:

- EC2에서 deploy key 생성 후 GitHub Deploy Keys 등록

### 6.3 `.env` 파일이 배포 중 사라짐

증상:

- 실행 시점에 `.env` 파일을 못 찾음

원인:

- `APP_DIR` 내부 `.env`가 repo 동기화 과정에서 사라짐

해결:

- `deploy.yml` 수정
- `.env` 위치를 `~/costview-prd.env`로 분리

### 6.4 `psycopg2` 모듈 오류

증상:

```text
ModuleNotFoundError: No module named 'psycopg2'
```

원인:

- 코드가 `psycopg2` import를 사용했지만, 이미지에는 `psycopg` 기준 의존성만 설치됨

해결:

- `prd/db/connection.py`
- `prd/db/fetch.py`

를 `psycopg` 기준으로 수정

### 6.5 컨테이너 이름 충돌

증상:

```text
The container name "/costview-prd-run" is already in use
```

원인:

- 이전 실패 컨테이너가 남아 있음

해결:

- `deploy.yml`에서 기존 컨테이너를 무조건 강제 삭제하도록 수정

### 6.6 Supabase Invalid URL

증상:

```text
SupabaseException: Invalid URL
```

원인:

- 서버 `.env`에 `SUPABASE_URL=...` placeholder가 들어가 있었음

해결:

- 실제 Supabase URL로 재설정

---

## 7. 최근 반영된 배포 관련 수정

### main 반영 사항

- `6bfafad`  
  `fix: keep EC2 env file outside app directory`

- `6fb6d61`  
  `fix: use psycopg in PRD postgres fetchers`

- `b90c5b8`  
  `fix: always remove previous PRD container before run`

---

## 8. 현재 기준 재배포 방법

### 8.1 코드 반영

- `main` 브랜치에 push

### 8.2 GitHub Actions 재실행

- 저장소 `Actions` 탭 이동
- `Run PRD Batch On EC2` 클릭
- `Re-run all jobs`

---

## 9. 서버 점검 명령어

### `.env` 확인

```bash
ls -la ~/costview-prd.env
grep '^SUPABASE_URL' ~/costview-prd.env
```

### Docker 확인

```bash
docker ps -a
docker images
docker logs costview-prd-run
```

### 코드 확인

```bash
cd ~/costview-prd
git log --oneline -3
```

---

## 10. 현재 판단

현재 AWS 연동은 아래 범위까지 완료된 상태다.

- GitHub → EC2 SSH 연동 완료
- EC2 → GitHub private repo 접근 완료
- Docker 기반 배치 실행 구조 완료
- 배포 워크플로우 주요 오류 수정 완료

즉, 현재 단계는:

**“배포 기반 구성 완료 + 실제 배치 실행 검증 단계”**

---

## 11. 다음 확인 포인트

최종적으로 아래 3가지를 보면 된다.

1. GitHub Actions 마지막 로그에서 `processed` / `complete success` 출력 여부
2. EC2에서 `docker logs costview-prd-run` 결과
3. Supabase/Postgres에 분석 결과 실제 반영 여부

이 3가지가 정상이라면 AWS 배포는 사실상 완료다.
