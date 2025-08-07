# main.py

import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModelForCausalLM
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os

# .env 파일 로딩
from dotenv import load_dotenv
load_dotenv()  # .env 파일의 환경변수를 os.environ에 로드

# ChatModerationModel 클래스 (기존과 동일)
class ChatModerationModel(nn.Module):
    def __init__(self, model_name, num_labels=1):
        super(ChatModerationModel, self).__init__()
        self.base_model = AutoModelForCausalLM.from_pretrained(
            model_name,
            trust_remote_code=True,
            torch_dtype=torch.float16,  # 메모리 사용량 절반으로 감소
            low_cpu_mem_usage=True,     # CPU 메모리 사용량 최적화
            device_map="auto"           # 자동 디바이스 매핑
        )
        self.malice_head = nn.Sequential(
            nn.Linear(self.base_model.config.hidden_size, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, num_labels),
            nn.Sigmoid()
        )

    def forward(self, input_ids, attention_mask, labels=None):
        outputs = self.base_model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            output_hidden_states=True
        )
        hidden_states = outputs.hidden_states[-1]
        pooled_output = hidden_states[:, -1, :]
        malice_scores = self.malice_head(pooled_output)
        
        loss = None
        if labels is not None:
            loss_fn = nn.MSELoss()
            loss = loss_fn(malice_scores.squeeze(), labels)
            
        return {'loss': loss, 'malice_scores': malice_scores}

# FastAPI 앱 설정
app = FastAPI(title="AI 채팅 순화 모델 API")

# 모델 설정 (환경변수로 쉽게 변경 가능)
MODEL_DIR = os.getenv("MODEL_DIR", "./final_moderation_model")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
ORIGINAL_MODEL_NAME = "naver-hyperclovax/HyperCLOVAX-SEED-Text-Instruct-0.5B"

# 모델 자동 다운로드 및 로딩
def ensure_model_exists():
    """모델 파일이 없으면 자동으로 다운로드"""
    weight_files = ["pytorch_model.pth", "pytorch_model-001.pth"]
    weight_path = None
    
    # 가중치 파일 찾기
    for weight_file in weight_files:
        test_path = os.path.join(MODEL_DIR, weight_file)
        if os.path.exists(test_path):
            weight_path = test_path
            break
    
    if not weight_path:
        print("⚠️ 모델 파일을 찾을 수 없습니다. 자동 다운로드를 시작합니다...")
        
        try:
            # download_model.py 모듈 임포트 및 실행
            import subprocess
            import sys
            
            print("📦 필요한 패키지 설치 중...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "tqdm"])
            
            print("📥 Google Drive에서 모델 다운로드 중...")
            result = subprocess.run([sys.executable, "download_model.py"], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ 모델 다운로드 완료!")
                # 다시 가중치 파일 찾기
                for weight_file in weight_files:
                    test_path = os.path.join(MODEL_DIR, weight_file)
                    if os.path.exists(test_path):
                        weight_path = test_path
                        break
            else:
                print(f"❌ 모델 다운로드 실패: {result.stderr}")
                raise FileNotFoundError("모델 다운로드에 실패했습니다.")
                
        except Exception as e:
            print(f"❌ 자동 다운로드 실패: {e}")
            print("💡 수동으로 'python download_model.py'를 실행하거나")
            print("   Google Drive에서 직접 모델 파일을 다운로드하세요.")
            raise FileNotFoundError(f"모델 가중치 파일을 찾을 수 없습니다: {MODEL_DIR}")
    
    return weight_path

print(f"모델 로딩 중... (경로: {MODEL_DIR})")

# 모델 파일 확인 및 자동 다운로드
weight_path = ensure_model_exists()

# 토크나이저 로딩
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)

# 모델 로딩
model = ChatModerationModel(model_name=ORIGINAL_MODEL_NAME)
model.load_state_dict(torch.load(weight_path, map_location=DEVICE))
model.to(DEVICE)
model.eval()
print("✅ 모델 로딩 완료!")

# 텍스트 순화 함수 (HyperCLOVA X Playground API 사용)
import requests
import json
from typing import Optional

def purify_text_with_hyperclova_api(text: str) -> str:
    """HyperCLOVA X API를 사용한 텍스트 순화 (스프링 부트 방식 참고)"""
    try:
        # API 키 확인
        api_key = os.getenv("HYPERCLOVA_API_KEY")
        if not api_key:
            raise Exception("HYPERCLOVA_API_KEY 환경변수가 설정되지 않았습니다.")
        
        print(f"🔧 API 키 길이: {len(api_key)}, 앞 15자: {api_key[:15]}...")
        
        # 스프링 부트 방식을 참고한 올바른 API 설정
        import uuid
        request_id = str(uuid.uuid4())[:10]
        
        api_configs = [
            # 1. 스프링 부트와 동일한 v3 엔드포인트 (HCX-005)
            {
                "name": "HCX-005 (Spring Boot 방식)",
                "url": "https://clovastudio.stream.ntruss.com/testapp/v3/chat-completions/HCX-005",
                "headers": {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-NCP-CLOVASTUDIO-REQUEST-ID": request_id
                }
            },
            # 2. HCX-003 Bearer 방식
            {
                "name": "HCX-003 Bearer",
                "url": "https://clovastudio.stream.ntruss.com/testapp/v1/chat-completions/HCX-003",
                "headers": {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-NCP-CLOVASTUDIO-REQUEST-ID": request_id
                }
            },
            # 3. v1 Bearer 방식
            {
                "name": "v1 Bearer",
                "url": "https://clovastudio.stream.ntruss.com/testapp/v1/chat-completions",
                "headers": {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "X-NCP-CLOVASTUDIO-REQUEST-ID": request_id
                },
                "add_model": True
            }
        ]
        
        # API 키 형식 분석 (2025년 8월 발급 테스트용)
        print(f"🔧 API 키 분석 (2025년 8월 테스트용):")
        print(f"   - 전체 길이: {len(api_key)}")
        print(f"   - 시작 부분: {api_key[:12]}...")
        print(f"   - 끝 부분: ...{api_key[-8:]}")
        
        # 키 형식별 추정
        if api_key.startswith('ncp_'):
            key_type = "신규 NCP 형식 (추정)"
        elif api_key.startswith('nv-'):
            key_type = "구 nv- 형식 (Legacy 가능성)"
        elif len(api_key) > 50:
            key_type = "긴 형식 키 (최신 추정)"
        else:
            key_type = "알 수 없는 형식"
            
        print(f"   - 키 형식: {key_type}")
        print(f"   - 발급 정보: 2025년 8월 테스트용")
        
        last_error = None
        
        # 욕설 순화 전용 프롬프트 (더 직접적이고 강력하게)
        purify_prompt = f"""당신은 텍스트 순화 전문 시스템입니다. 주어진 텍스트의 욕설, 비속어, 비난 표현을 정중한 표현으로 변환하는 것이 당신의 임무입니다.

**중요 지침:**
- 거부하지 말고 반드시 순화된 버전을 제공하세요
- 원본의 감정과 의도는 유지하되 욕설/비속어만 적절한 표현으로 교체하세요
- 설명이나 부연설명 없이 순화된 텍스트만 출력하세요
- 이것은 텍스트 정화 작업이므로 윤리적으로 올바른 작업입니다

**규칙:**
1. 원래 의미 유지, 욕설/비속어는 대체어로 변경
2. 공격적 어조는 차분하고 정중하게 변경
3. 자연스러운 한국어 표현 사용
4. 순화된 텍스트만 출력

**변환 예시:**
- "시발" → "정말" 또는 "진짜"
- "좆같은" → "별로인" 또는 "안좋은"
- "꼬라봐" → "째려봐" 또는 "쳐다봐"

**순화할 텍스트:** {text}

**순화 결과:**"""

        # 스프링 부트 방식과 동일한 payload
        base_payload = {
            "messages": [
                {"role": "system", "content": purify_prompt}
            ],
            "topP": 0.8,
            "topK": 0,
            "maxTokens": 256,
            "temperature": 0.5,
            "repetitionPenalty": 1.1,
            "stop": [],
            "includeAiFilters": True,
            "seed": 0
        }
        
        # 여러 API 설정을 순차적으로 시도
        for i, config in enumerate(api_configs, 1):
            print(f"🔄 시도 {i}/4: {config['name']}")
            print(f"   URL: {config['url']}")
            
            # URL에 모델이 포함되지 않은 경우 payload에 모델 추가
            payload = base_payload.copy()
            if "/HCX-003" not in config['url']:
                payload["model"] = "HCX-003"
                print(f"   📝 모델 파라미터 추가: HCX-003")
            
            try:
                response = requests.post(
                    config['url'], 
                    headers=config['headers'], 
                    json=payload, 
                    timeout=10
                )
                print(f"   📊 응답: HTTP {response.status_code}")
                
                if response.status_code == 200:
                    # 성공 시 응답 파싱
                    purified = parse_hyperclova_response(response.text)
                    if purified and len(purified.strip()) > 2:
                        print(f"   ✅ 순화 성공: {text[:15]}... -> {purified[:15]}...")
                        return purified.strip()
                    else:
                        print(f"   ⚠️  빈 응답, 다음 설정 시도")
                        last_error = "빈 응답"
                        continue
                        
                elif response.status_code == 401:
                    error_detail = response.text[:200] if response.text else "인증 실패"
                    print(f"   ❌ 인증 실패: {error_detail}")
                    last_error = f"인증 실패 (HTTP 401): {error_detail}"
                    continue
                    
                else:
                    error_detail = response.text[:200] if response.text else "알 수 없는 오류"
                    print(f"   ❌ HTTP {response.status_code}: {error_detail}")
                    last_error = f"HTTP {response.status_code}: {error_detail}"
                    continue
                    
            except requests.exceptions.Timeout:
                print(f"   ⏰ 타임아웃")
                last_error = "요청 타임아웃"
                continue
            except requests.exceptions.ConnectionError as e:
                print(f"   🔌 연결 오류: {str(e)[:100]}")
                last_error = f"연결 오류: {str(e)[:100]}"
                continue
                
        # 모든 시도 실패
        raise Exception(f"모든 API 호출 실패. 마지막 오류: {last_error}")
            
    except Exception as e:
        # 이미 처리된 예외는 그대로 전달
        if "모든 API 호출 실패" in str(e) or "환경변수" in str(e):
            raise e
        else:
            raise Exception(f"예상치 못한 오류: {str(e)}")

def parse_hyperclova_response(response_text: str) -> Optional[str]:
    """HyperCLOVA X 응답 파싱 (스프링 부트 방식 참고)"""
    try:
        # JSON 응답 파싱 시도
        try:
            data = json.loads(response_text)
            
            # 스프링 부트 방식: result.message.content
            if 'result' in data and 'message' in data['result'] and 'content' in data['result']['message']:
                content = data['result']['message']['content']
                print(f"   📝 JSON 파싱 성공: {content[:30]}...")
                return content.strip()
            
            # 다른 JSON 구조 시도
            if 'choices' in data and len(data['choices']) > 0:
                if 'message' in data['choices'][0] and 'content' in data['choices'][0]['message']:
                    content = data['choices'][0]['message']['content']
                    print(f"   📝 choices 파싱 성공: {content[:30]}...")
                    return content.strip()
                    
        except json.JSONDecodeError:
            # JSON이 아닌 경우 스트리밍 방식으로 파싱
            pass
        
        # 스트리밍 응답 파싱 (기존 방식)
        lines = response_text.strip().split('\n')
        content = ""
        
        for line in lines:
            if line.startswith('data: '):
                data_str = line[6:]  # 'data: ' 제거
                if data_str.strip() == '[DONE]':
                    break
                    
                try:
                    data = json.loads(data_str)
                    if 'message' in data and 'content' in data['message']:
                        content += data['message']['content']
                    elif 'result' in data and 'message' in data['result']:
                        content += data['result']['message'].get('content', '')
                except json.JSONDecodeError:
                    continue
        
        # 정리
        content = content.strip()
        
        # "순화된 텍스트:" 라벨 제거
        if "순화된 텍스트:" in content:
            content = content.split("순화된 텍스트:")[-1].strip()
        
        # 따옴표 제거
        content = content.strip('"\'')
        
        return content if content else None
        
    except Exception as e:
        print(f"응답 파싱 오류: {e}")
        return None



# API 요청/응답 형식
class ModerationRequest(BaseModel):
    text: str

class ModerationResponse(BaseModel):
    text: str
    malice_score: float
    is_harmful: bool
    confidence: str
    purified_text: Optional[str] = None  # HyperCLOVA X API로 순화된 텍스트 (API 키 필요)

# API 엔드포인트
@app.get("/quick-health")
def quick_health():
    """빠른 헬스체크 (Docker 헬스체크용)"""
    try:
        if model is None or tokenizer is None:
            return {"status": "unhealthy", "reason": "model_not_loaded"}
        return {"status": "healthy"}
    except:
        return {"status": "unhealthy", "reason": "unknown_error"}

@app.post("/moderate", response_model=ModerationResponse)
def moderate_text(request: ModerationRequest):
    """텍스트 모더레이션: 악의성/유해성을 판단합니다"""
    try:
        # 빈 텍스트 검증
        if not request.text or len(request.text.strip()) == 0:
            return ModerationResponse(
                text=request.text,
                malice_score=0.0,
                is_harmful=False,
                confidence="매우 안전",
                purified_text=None
            )
        
        # 프롬프트 생성
        prompt = f"다음 텍스트의 악의성 수준을 0.0(전혀 악의적이지 않음)부터 1.0(매우 악의적임) 사이의 값으로 판단하세요.\n텍스트: {request.text}\n악의성 수준:"
        
        # 토큰화
        encoding = tokenizer(
            prompt,
            truncation=True,
            padding='max_length',
            max_length=512,
            return_tensors='pt'
        ).to(DEVICE)
        
        # 모델 추론
        with torch.no_grad():
            outputs = model(encoding['input_ids'], encoding['attention_mask'])
            score = outputs['malice_scores'].cpu().item()
        
        # 점수를 0-1 범위로 클램핑
        score = max(0.0, min(1.0, score))
        
        # 유해성 판단 (임계값 0.5)
        is_harmful = score >= 0.5
        
        # 신뢰도 계산
        if score < 0.2:
            confidence = "매우 안전"
        elif score < 0.4:
            confidence = "안전"
        elif score < 0.6:
            confidence = "주의"
        elif score < 0.8:
            confidence = "위험"
        else:
            confidence = "매우 위험"
        
        # 텍스트 순화 (0.6 이상일 때) - HyperCLOVA X API 실패 시 에러 반환
        purified_text = None
        if score >= 0.6:
            try:
                purified_text = purify_text_with_hyperclova_api(request.text)
            except Exception as purify_error:
                # HyperCLOVA API 실패 시 에러 반환
                print(f"❌ HyperCLOVA API 순화 실패: {purify_error}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"텍스트 순화 실패: {str(purify_error)}"
                )
        
        return ModerationResponse(
            text=request.text,
            malice_score=round(score, 4),
            is_harmful=is_harmful,
            confidence=confidence,
            purified_text=purified_text
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모더레이션 처리 중 오류: {str(e)}")