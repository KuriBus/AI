# 🤖 AI 텍스트 모더레이션 API

한국어 텍스트의 악의성을 탐지하고 욕설/비속어를 자동으로 순화해주는 FastAPI 서버입니다.

## ✨ 주요 기능

- **악의성 탐지**: 파인튜닝된 AI 모델로 텍스트 악의성 점수 계산 (0.0-1.0)
- **자동 순화**: HyperCLOVA X API를 활용한 지능형 텍스트 순화
- **RESTful API**: FastAPI 기반의 간단한 HTTP API
- **헬스체크**: 서버 상태 모니터링 엔드포인트

## 🚀 빠른 시작

### 1. 저장소 클론
```bash
git clone <your-repo-url>
cd <repo-name>
```

### 2. 가상환경이 활성화되었는지 확인
```bash
# 현재 디렉토리 확인
pwd
# /home/ubuntu/AI 또는 /home/ubuntu/moderation-api 여야 함

# 가상환경 활성화 (중요!)
source venv/bin/activate

# 프롬프트가 (venv) ubuntu@... 로 바뀌어야 함
```
### 2. Python 환경 설정
```bash
# Python 3.11+ 권장
# requests와 tqdm 설치
pip install requests tqdm

# 또는 requirements.txt로 모든 패키지 설치
pip install -r requirements.txt
```

### 3. 모델 다운로드
```bash
# gdown 설치 (Google Drive 전용 다운로더)
pip install gdown

# gdown으로 다운로드
gdown "{구글 드라이브의 공유 링크 id}" -O final_moderation_model.zip
```

### 4. HyperCLOVA X API 키 설정 (필수)
```bash
# 환경변수로 설정
export HYPERCLOVA_API_KEY="your-api-key-here"

# 또는 .env 파일 생성
echo "HYPERCLOVA_API_KEY=your-api-key-here" > .env
```

#### API 키 발급 방법:
1. [네이버 클라우드 콘솔](https://console.ncloud.com) 접속
2. **AI Services** → **CLOVA Studio** → **API 키**
3. **[테스트]** 탭에서 **테스트 API 키 발급**

### 5. 서버 실행
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

서버가 시작되면 `http://localhost:8000`에서 API를 사용할 수 있습니다.

## 📡 API 사용법

### 텍스트 모더레이션
```bash
curl -X POST "http://localhost:8000/moderate" \
  -H "Content-Type: application/json" \
  -d '{"text": "테스트할 텍스트를 입력하세요"}'
```

**응답 예시:**

**일반 텍스트 (안전):**
```json
{
  "text": "안녕하세요 좋은 하루입니다",
  "malice_score": 0.1234,
  "is_harmful": false,
  "confidence": "안전",
  "purified_text": null
}
```

**유해 텍스트 (순화됨):**
```json
{
  "text": "뭘 꼬라봐 좆같은놈아",
  "malice_score": 0.9759,
  "is_harmful": true,
  "confidence": "매우 위험",
  "purified_text": "뭘 째려봐 안 좋은 놈아"
}
```

### 헬스체크
```bash
curl http://localhost:8000/quick-health
```

응답:
```json
{"status": "healthy"}
```

## 🏗️ AWS 배포

### EC2 직접 배포 (권장)

1. **EC2 인스턴스 생성** (Ubuntu 22.04, t3.small 권장)
2. **보안 그룹 설정**: SSH(22), HTTP(8000) 포트 오픈
3. **서버 설정**:

```bash
# SSH 접속 후
sudo apt update && sudo apt upgrade -y

# Python 3.11 설치
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.11 python3.11-pip python3.11-venv

# 프로젝트 클론
git clone <your-repo-url>
cd <repo-name>

# 가상환경 설정
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 환경변수 설정
export HYPERCLOVA_API_KEY="your-api-key"

# 모델 다운로드
python download_model.py

# 서버 실행 (백그라운드)
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &

# 그냥 실행
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

4. **서비스 등록** (자동 시작):
```bash
sudo tee /etc/systemd/system/moderation-api.service > /dev/null <<EOF
[Unit]
Description=Moderation API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
Environment=HYPERCLOVA_API_KEY=your-api-key
ExecStart=$(pwd)/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable moderation-api
sudo systemctl start moderation-api
```

## 📁 프로젝트 구조

```
├── main.py                    # 메인 FastAPI 애플리케이션
├── requirements.txt           # Python 패키지 의존성
├── download_model.py          # Google Drive 모델 자동 다운로드
├── README.md                  # 프로젝트 문서
├── .gitignore                # Git 제외 파일 목록
└── final_moderation_model/    # AI 모델 파일들 (자동 다운로드)
    ├── pytorch_model-001.pth  # 파인튜닝된 모델 가중치
    ├── tokenizer.json         # 토크나이저 설정
    ├── tokenizer_config.json  # 토크나이저 구성
    └── ...                    # 기타 모델 파일들
```

## 🔧 문제 해결

### 모델 다운로드 실패
```bash
# Google Drive 파일 ID 확인
# download_model.py에서 MODEL_FILE_ID 수정 필요

# 수동 다운로드
python download_model.py
```

### API 키 인증 실패
```bash
# API 키 확인
echo $HYPERCLOVA_API_KEY

# 새 API 키 발급 (테스트 탭에서)
# Bearer 토큰 방식으로 변경됨
```

### 서버 시작 실패
```bash
# 포트 사용 여부 확인
lsof -i :8000

# 의존성 재설치
pip install -r requirements.txt

# 로그 확인
tail -f app.log
```

## 🔧 모니터링

### 로그 확인
```bash
# 애플리케이션 로그
tail -f app.log

# 시스템 서비스 로그 (서비스 등록한 경우)
sudo journalctl -u moderation-api -f
```

### 성능 모니터링
```bash
# 서버 리소스 확인
htop

# API 응답 시간 테스트
time curl -X POST "http://localhost:8000/moderate" \
  -H "Content-Type: application/json" \
  -d '{"text": "테스트"}'
```

## 📋 요구사항

- **Python**: 3.11+
- **메모리**: 최소 2GB (모델 로딩용)
- **디스크**: 최소 3GB (모델 파일용)
- **네트워크**: HyperCLOVA X API 접근 가능

## 🔐 보안 고려사항

- API 키를 환경변수로 안전하게 관리
- HTTPS 사용 권장 (프로덕션 환경)
- 방화벽으로 필요한 포트만 오픈
- 정기적인 보안 업데이트

---

🎯 **완전 자동화된 텍스트 모더레이션 솔루션을 경험해보세요!**
