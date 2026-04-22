# src/data_mining/run_pipeline.py
import subprocess
import sys
import os
from datetime import datetime

# 한글 출력 인코딩 설정
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def run_script(script_path):
    """지정한 파이썬 스크립트를 실행하고 결과를 반환합니다."""
    print(f"🚀 실행 중: {script_path}...")
    
    # 환경 변수 유지하며 실행
    env = os.environ.copy()
    
    try:
        # 워크스페이스 루트에서 실행되도록 경로 조정
        result = subprocess.run(
            [sys.executable, script_path], 
            capture_output=True, 
            text=True, 
            encoding='utf-8',
            env=env
        )
        if result.returncode == 0:
            print(f"✅ 완료: {script_path}")
            # 출력 내용 요약 (너무 길면 자름)
            lines = result.stdout.strip().split('\n')
            summary = "\n".join(lines[-3:]) if len(lines) > 3 else result.stdout
            print(f"--- [Output Summary] ---\n{summary}\n")
            return True, result.stdout
        else:
            print(f"❌ 실패: {script_path}")
            print(f"--- [Error] ---\n{result.stderr}\n")
            return False, result.stderr
    except Exception as e:
        print(f"⚠️ 오류 발생: {e}")
        return False, str(e)

def main():
    start_time = datetime.now()
    print(f"============================================================")
    print(f"🏁 Cost-Vue Phase 1 통합 파이프라인 가동")
    print(f"📅 시작 시각: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"============================================================\n")

    # 1. FRED 지표 업데이트 (Daily & Monthly 최신화)
    # 루트 디렉토리 기준 경로 사용
    success_fred, _ = run_script("src/data_mining/fetch_fred_data.py")
    
    # 2. Exa 전쟁/지정학 뉴스 수집 (정제 및 적재)
    success_news, _ = run_script("src/data_mining/exa_search.py")

    print(f"============================================================")
    print(f"🏁 파이프라인 실행 종료 (소요 시간: {datetime.now() - start_time})")
    print(f"📊 결과 요약:")
    print(f"   - 매크로 지표(FRED): {'✅ 성공' if success_fred else '❌ 실패'}")
    print(f"   - 지정학 뉴스(Exa):  {'✅ 성공' if success_news else '❌ 실패'}")
    print(f"============================================================")

if __name__ == "__main__":
    main()
