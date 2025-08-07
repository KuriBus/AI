# 🤖 AI 채팅 순화 모델 API

## 📦 설치 및 실행

### 1. 저장소 복사
```bash
git clone <your-repo-url>
cd AI
```

### 2. Google Drive 모델 설정
1. `final_moderation_model/pytorch_model-001.pth` 파일을 Google Drive에 업로드
2. 파일 공유 설정: "링크가 있는 모든 사용자"
3. 공유 링크에서 파일 ID 복사:
   ```
   https://drive.google.com/file/d/1a2b3c4d5e6f7g8h9i0j/view?usp=sharing
                                ↑ 이 부분이 파일 ID
   ```
4. `download_model.py` 파일에서 파일 ID 수정:
   ```python
   "file_id": "1a2b3c4d5e6f7g8h9i0j",  # 실제 파일 ID로 교체
   ```

### 3. 모델 다운로드
```bash
pip install requests tqdm
python download_model.py
```

### 4. 서버 실행

#### Windows (간편):
- **시작**: `start.bat` 더블클릭
- **중지**: `stop.bat` 더블클릭

#### 3. HyperCLOVA X API 설정 (선택사항)
⚠️ **신규 API 키 필요**: 구 버전 키는 작동하지 않습니다!

📋 **새 API 키 발급**:
1. [네이버 클라우드 콘솔](https://console.ncloud.com) → AI Services → CLOVA Studio
2. 좌측 **API 키** → **[테스트]** 탭 → **[테스트 API 키 발급]**

🔧 **환경 변수 설정**:
```bash
# .env 파일 생성
HYPERCLOVA_API_KEY=새_발급받은_키

# 또는 환경변수로
set HYPERCLOVA_API_KEY=새_발급받은_키  # Windows
export HYPERCLOVA_API_KEY=새_발급받은_키  # Linux/Mac
```

📖 **참고**: [공식 API 문서](https://api.ncloud-docs.com/docs/ai-naver-clovastudio-summary)

#### 수동 실행:
```bash
# 패키지 설치
pip install -r requirements.txt

# 서버 시작
uvicorn main:app --host 0.0.0.0 --port 8000

# 또는 Docker 사용
docker build -t moderation-api .
docker run -p 8000:8000 moderation-api
```

## 🔧 API 사용법

### 텍스트 모더레이션 (메인 기능)
```bash
curl -X POST "http://localhost:8000/moderate" \
  -H "Content-Type: application/json" \
  -d '{"text": "테스트할 텍스트"}'
```

**응답 예시:**

**안전한 텍스트:**
```json
{
  "text": "안녕하세요 좋은 하루입니다",
  "malice_score": 0.1234,
  "is_harmful": false,
  "confidence": "안전",
  "purified_text": null
}
```

**유해한 텍스트 (AI 순화):**
```json
{
  "text": "시발 진짜 열받네",
  "malice_score": 0.8567,
  "is_harmful": true,
  "confidence": "매우 위험",
  "purified_text": "정말 많이 화가 나네요"
}
```

**순화 방식:**
- **HyperCLOVA X API**: 자연스럽고 문맥 고려한 AI 순화 (권장)
- **규칙 기반**: API 실패 시 백업 순화

### 서버 상태 확인
```bash
curl http://localhost:8000/quick-health
```

## 📁 파일 구조
```
AI/
├── main.py                     # 메인 서버 파일
├── download_model.py           # Google Drive 모델 다운로드
├── requirements.txt            # 패키지 목록
├── Dockerfile                  # Docker 설정
├── start.bat / stop.bat        # Windows 실행/중지 스크립트
├── test_api.py                 # API 테스트
└── final_moderation_model/     # 모델 폴더 (다운로드됨)
    └── pytorch_model-001.pth   # 모델 파일 (2.1GB)
```

## 🚀 AWS 배포
```bash
# EC2에서
git clone <your-repo-url>
cd AI

# Google Drive 파일 ID 설정
nano download_model.py

# Docker로 배포
docker build -t moderation-api .
docker run -d -p 8000:8000 --restart unless-stopped moderation-api
```

## 🔧 문제 해결

**모델 다운로드 실패 시:**
1. Google Drive 파일 ID 확인
2. 파일 공유 권한 확인 ("링크가 있는 모든 사용자")
3. 수동 다운로드: `python download_model.py`

**서버 시작 실패 시:**
1. 포트 8000이 사용 중인지 확인
2. 모델 파일이 다운로드되었는지 확인
3. 의존성 설치: `pip install -r requirements.txt`

그게 다입니다! 🎯