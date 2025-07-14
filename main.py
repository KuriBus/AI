from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional
import requests
import json
import logging
from dataclasses import dataclass
import os
from datetime import datetime
import uvicorn
from contextlib import asynccontextmanager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('purification_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class MaliciousnessResult:
    """악의성 판단 모델의 출력 형태"""
    original_text: str
    maliciousness_score: float

class SentencePurificationModel:
    """HyperCLOVA X API를 사용한 문장 순화 모델"""
    
    def __init__(self, api_key: str, api_url: str = "https://clovastudio.stream.ntruss.com/testapp/v1/chat-completions/HCX-003"):
        self.api_key = api_key
        self.api_url = api_url
        self.maliciousness_threshold = 0.7
        
        # 순화 매핑 사전
        self.purification_mapping = {
            "좆같다": "불쾌하다",
            "시발": "젠장",
            "씨발": "이런",
            "지랄": "말도 안 되는 소리",
            "개새끼": "나쁜 사람",
            "병신": "바보",
            "닥쳐": "조용히 해줘",
            "존나": "매우"
        }
        
        # 요청 헤더
        self.headers = {
            "X-NCP-CLOVASTUDIO-API-KEY": self.api_key,
            "X-NCP-APIGW-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
    
    def _create_purification_prompt(self, text: str) -> str:
        """순화를 위한 프롬프트 생성"""
        rules = "\n".join([f"- {k} → {v}" for k, v in self.purification_mapping.items()])
        
        prompt = f"""다음 문장을 순화해주세요. 아래 규칙을 따라서 순화해야 합니다:

순화 규칙:
{rules}

순화 스타일 가이드라인:
1. 부분 순화: 욕설이나 비속어만 순화하고 나머지는 그대로 유지
2. 문체 톤 유지: 원문이 격식체면 순화도 격식체, 원문이 반말이면 순화도 반말
3. 감정 표현 최대한 동일하게 유지
4. 문장의 의미를 동일하게 갖고 순화
5. 문맥에 맞는 자연스러운 순화

원문: {text}

순화된 문장만 출력해주세요."""
        
        return prompt
    
    def _call_hyperclova_api(self, prompt: str) -> Optional[str]:
        """HyperCLOVA X API 호출"""
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": "당신은 문장을 자연스럽게 순화하는 전문가입니다. 주어진 규칙에 따라 욕설이나 비속어를 적절한 표현으로 바꿔주세요."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "topP": 0.8,
            "topK": 0,
            "maxTokens": 512,  # TODO: 최대 토큰 수 제한 확인 필요
            "temperature": 0.3,
            "repeatPenalty": 1.2,
            "stopBefore": [],
            "includeAiFilters": True
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            if "result" in result and "message" in result["result"]:
                return result["result"]["message"]["content"].strip()
            else:
                logger.error(f"Unexpected API response format: {result}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during API call: {e}")
            return None
    
    def purify_sentence(self, maliciousness_result: MaliciousnessResult) -> str:
        """문장 순화 메인 함수"""
        if maliciousness_result.maliciousness_score < self.maliciousness_threshold:
            logger.info(f"Maliciousness score ({maliciousness_result.maliciousness_score}) below threshold ({self.maliciousness_threshold}). Returning original text.")
            return maliciousness_result.original_text
        
        logger.info(f"Maliciousness score ({maliciousness_result.maliciousness_score}) above threshold. Purifying sentence...")
        
        prompt = self._create_purification_prompt(maliciousness_result.original_text)
        purified_text = self._call_hyperclova_api(prompt)
        
        if purified_text is None:
            logger.error("Failed to purify sentence. Returning original text.")
            return maliciousness_result.original_text
        
        logger.info(f"Successfully purified: '{maliciousness_result.original_text}' -> '{purified_text}'")
        return purified_text

# Pydantic 모델 정의
class PurificationRequest(BaseModel):
    text: str = Field(..., description="순화할 문장", example="이런 시발 뭐하는 거야")
    maliciousness_score: float = Field(..., description="악의성 수치 (0.0 ~ 1.0)", ge=0.0, le=1.0, example=0.8)

class BatchPurificationRequest(BaseModel):
    sentences: List[PurificationRequest] = Field(..., description="순화할 문장 리스트")

class PurificationResponse(BaseModel):
    original_text: str = Field(..., description="원본 문장")
    purified_text: str = Field(..., description="순화된 문장")
    maliciousness_score: float = Field(..., description="악의성 수치")
    is_purified: bool = Field(..., description="순화 여부")
    processing_time: float = Field(..., description="처리 시간 (초)")

class BatchPurificationResponse(BaseModel):
    results: List[PurificationResponse] = Field(..., description="순화 결과 리스트")
    total_processing_time: float = Field(..., description="총 처리 시간 (초)")

class HealthResponse(BaseModel):
    status: str = Field(..., description="서버 상태")
    timestamp: datetime = Field(..., description="응답 시간")
    api_status: str = Field(..., description="API 연결 상태")

# 전역 변수
purifier = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 초기화
    global purifier
    api_key = os.getenv("HYPERCLOVA_API_KEY")
    if not api_key:
        logger.error("HYPERCLOVA_API_KEY environment variable not set")
        raise ValueError("API key is required")
    
    api_url = os.getenv("HYPERCLOVA_API_URL", "https://clovastudio.stream.ntruss.com/testapp/v1/chat-completions/HCX-003")
    purifier = SentencePurificationModel(api_key, api_url)
    logger.info("Purification model initialized successfully")
    
    yield
    
    # 종료 시 정리
    logger.info("Server shutting down")

# FastAPI 앱 초기화
app = FastAPI(
    title="문장 순화 서버",
    description="HyperCLOVA X API를 사용한 문장 순화 서비스",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """서버 상태 확인"""
    try:
        # 간단한 API 연결 테스트
        test_result = MaliciousnessResult("테스트", 0.1)
        purifier.purify_sentence(test_result)
        api_status = "healthy"
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        api_status = "unhealthy"
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        api_status=api_status
    )

@app.post("/purify", response_model=PurificationResponse)
async def purify_sentence(request: PurificationRequest):
    """단일 문장 순화"""
    try:
        start_time = datetime.now()
        
        # 악의성 결과 생성
        maliciousness_result = MaliciousnessResult(
            original_text=request.text,
            maliciousness_score=request.maliciousness_score
        )
        
        # 순화 처리
        purified_text = purifier.purify_sentence(maliciousness_result)
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        return PurificationResponse(
            original_text=request.text,
            purified_text=purified_text,
            maliciousness_score=request.maliciousness_score,
            is_purified=request.maliciousness_score >= purifier.maliciousness_threshold,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error in purify_sentence: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/purify/batch", response_model=BatchPurificationResponse)
async def purify_batch(request: BatchPurificationRequest):
    """배치 문장 순화"""
    try:
        start_time = datetime.now()
        results = []
        
        for sentence_request in request.sentences:
            sentence_start_time = datetime.now()
            
            # 악의성 결과 생성
            maliciousness_result = MaliciousnessResult(
                original_text=sentence_request.text,
                maliciousness_score=sentence_request.maliciousness_score
            )
            
            # 순화 처리
            purified_text = purifier.purify_sentence(maliciousness_result)
            
            sentence_end_time = datetime.now()
            sentence_processing_time = (sentence_end_time - sentence_start_time).total_seconds()
            
            results.append(PurificationResponse(
                original_text=sentence_request.text,
                purified_text=purified_text,
                maliciousness_score=sentence_request.maliciousness_score,
                is_purified=sentence_request.maliciousness_score >= purifier.maliciousness_threshold,
                processing_time=sentence_processing_time
            ))
        
        end_time = datetime.now()
        total_processing_time = (end_time - start_time).total_seconds()
        
        return BatchPurificationResponse(
            results=results,
            total_processing_time=total_processing_time
        )
        
    except Exception as e:
        logger.error(f"Error in purify_batch: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "문장 순화 서버",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "purify": "/purify",
            "batch_purify": "/purify/batch",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=1,
        log_level="info"
    )