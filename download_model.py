#!/usr/bin/env python3
"""
Google Drive에서 모델 파일 자동 다운로드 스크립트
"""
import os
import sys
import requests
import zipfile
from pathlib import Path
from tqdm import tqdm

# 구글 드라이브 파일 ID (공유 링크에서 추출)
# 예: https://drive.google.com/file/d/{FILE_ID}/view?usp=sharing
MODEL_FILE_ID = "1q2MhGM7zTMsC4P2XYiU4E4TXAhprN641"
MODEL_ZIP_NAME = "final_moderation_model.zip"
MODEL_DIR = "final_moderation_model"

def download_from_google_drive(file_id, destination):
    """구글 드라이브에서 대용량 파일 다운로드 (바이러스 검사 우회 포함)"""
    
    def get_confirm_token(response):
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                return value
        return None
    
    def get_confirm_code_from_html(response_text):
        """HTML에서 confirm 코드 추출"""
        import re
        # Google Drive 경고 페이지에서 confirm 코드 찾기
        match = re.search(r'confirm=([^&\s"]+)', response_text)
        if match:
            return match.group(1)
        
        # 다른 패턴들도 시도
        patterns = [
            r'"confirm"\s*:\s*"([^"]+)"',
            r'&amp;confirm=([^&\s"]+)',
            r'&confirm=([^&\s"]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response_text)
            if match:
                return match.group(1)
        return None

    def save_response_content(response, destination):
        CHUNK_SIZE = 32768
        total_size = int(response.headers.get('content-length', 0))
        
        with open(destination, "wb") as f:
            if total_size > 0:
                with tqdm(total=total_size, unit='B', unit_scale=True, desc="다운로드 중") as pbar:
                    for chunk in response.iter_content(CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
            else:
                print("파일 크기를 알 수 없어 진행률 표시 없이 다운로드합니다...")
                downloaded = 0
                for chunk in response.iter_content(CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        print(f"다운로드됨: {downloaded // (1024*1024)}MB", end='\r')

    URL = "https://docs.google.com/uc?export=download"
    
    session = requests.Session()
    
    print("📥 초기 요청 중...")
    response = session.get(URL, params={'id': file_id}, stream=True)
    
    # 쿠키에서 토큰 확인
    token = get_confirm_token(response)
    
    # HTML 응답인 경우 (바이러스 검사 경고)
    if not token and 'text/html' in response.headers.get('content-type', ''):
        print("⚠️ 바이러스 검사 경고 감지됨. 우회 시도 중...")
        response_text = response.text
        
        # HTML에서 confirm 코드 추출
        confirm_code = get_confirm_code_from_html(response_text)
        
        if confirm_code:
            print(f"✅ Confirm 코드 발견: {confirm_code[:10]}...")
            params = {'id': file_id, 'confirm': confirm_code}
            response = session.get(URL, params=params, stream=True)
        else:
            # 다른 방법들 시도
            print("🔄 대안 방법 시도 중...")
            alternative_urls = [
                f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t",
                f"https://drive.google.com/uc?export=download&id={file_id}&confirm=1",
                f"https://drive.google.com/u/0/uc?id={file_id}&export=download&confirm=t"
            ]
            
            for alt_url in alternative_urls:
                print(f"   시도: {alt_url[:60]}...")
                response = session.get(alt_url, stream=True)
                
                # ZIP 파일인지 확인
                content_type = response.headers.get('content-type', '')
                if 'application' in content_type or 'binary' in content_type:
                    print("   ✅ 바이너리 파일 응답 확인됨")
                    break
                elif response.status_code == 200:
                    # 응답 크기가 큰 경우 (실제 파일일 가능성)
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > 1000000:  # 1MB 이상
                        print(f"   ✅ 큰 파일 응답 확인됨 ({content_length} bytes)")
                        break
                        
                print(f"   ❌ HTML 응답, 다음 시도...")
    
    elif token:
        print(f"✅ 토큰 확인됨: {token[:10]}...")
        params = {'id': file_id, 'confirm': token}
        response = session.get(URL, params=params, stream=True)

    # 최종 응답 확인
    content_type = response.headers.get('content-type', '')
    if 'text/html' in content_type:
        print("❌ 여전히 HTML 응답을 받고 있습니다.")
        print("   수동 다운로드를 시도해주세요:")
        print(f"   https://drive.google.com/file/d/{file_id}/view?usp=sharing")
        raise Exception("자동 다운로드 실패: 바이러스 검사 우회 불가")
    
    print("📦 파일 다운로드 시작...")
    save_response_content(response, destination)

def extract_model():
    """ZIP 파일 압축 해제"""
    print(f"📦 {MODEL_ZIP_NAME} 압축 해제 중...")
    
    with zipfile.ZipFile(MODEL_ZIP_NAME, 'r') as zip_ref:
        zip_ref.extractall('.')
    
    print(f"✅ {MODEL_DIR} 디렉토리에 압축 해제 완료!")
    
    # ZIP 파일 삭제
    os.remove(MODEL_ZIP_NAME)
    print(f"🗑️ {MODEL_ZIP_NAME} 정리 완료")

def main():
    """메인 함수"""
    print("🤖 모델 파일 다운로드 시작...")
    
    # 모델 디렉토리가 이미 있는지 확인
    if os.path.exists(MODEL_DIR):
        print(f"✅ {MODEL_DIR} 이미 존재합니다. 다운로드를 건너뜁니다.")
        return
    
    # 필수 패키지 확인
    try:
        import requests
        import tqdm
    except ImportError:
        print("📦 필요한 패키지를 설치합니다...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "tqdm"])
        import requests
        import tqdm
    
    # 파일 ID 확인
    if MODEL_FILE_ID == "your-google-drive-file-id-here":
        print("❌ 구글 드라이브 파일 ID를 설정해주세요!")
        print("   1. 구글 드라이브에 모델 ZIP 파일 업로드")
        print("   2. 공유 링크 생성 (누구나 액세스 가능)")
        print("   3. 링크에서 파일 ID 복사")
        print("   4. download_model.py에서 MODEL_FILE_ID 수정")
        sys.exit(1)
    
    try:
        # 다운로드
        print(f"📥 구글 드라이브에서 다운로드 중... (파일 ID: {MODEL_FILE_ID[:20]}...)")
        download_from_google_drive(MODEL_FILE_ID, MODEL_ZIP_NAME)
        
        # 압축 해제
        extract_model()
        
        # 검증
        required_files = [
            "pytorch_model-001.pth",
            "tokenizer.json",
            "tokenizer_config.json"
        ]
        
        missing_files = []
        for file in required_files:
            if not os.path.exists(os.path.join(MODEL_DIR, file)):
                missing_files.append(file)
        
        if missing_files:
            print(f"⚠️ 누락된 파일: {missing_files}")
        else:
            print("🎉 모델 다운로드 및 설정 완료!")
            
    except Exception as e:
        print(f"❌ 다운로드 실패: {e}")
        # 정리
        if os.path.exists(MODEL_ZIP_NAME):
            os.remove(MODEL_ZIP_NAME)
        sys.exit(1)

if __name__ == "__main__":
    main()