from contextlib import asynccontextmanager
from typing import Final

import torch
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from redis.asyncio import ConnectionPool, Redis
from transformers import MobileBertForSequenceClassification, MobileBertTokenizer

STATIC_PREFIX: Final[str] = "/static/"
CONFIDENCE_THRESHOLD: Final[float] = 0.7

ALLOWED_RESPONSE: Final[Response] = Response(
    content=b'{"allowed":true}',
    media_type="application/json",
)

redis_pool: ConnectionPool | None = None
redis_client: Redis | None = None
device: torch.device | None = None
tokenizer: MobileBertTokenizer | None = None
model: MobileBertForSequenceClassification | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_pool, redis_client, device, tokenizer, model

    redis_pool = ConnectionPool(host="cache", port=6379, db=0, decode_responses=True)
    redis_client = Redis(connection_pool=redis_pool)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = MobileBertTokenizer.from_pretrained("google/mobilebert-uncased")
    model = MobileBertForSequenceClassification.from_pretrained(
        "cssupport/mobilebert-sql-injection-detect"
    )
    model.to(device)
    model.eval()

    yield

    await redis_client.aclose()
    await redis_pool.disconnect()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)


async def get_guardrailv2_status() -> bool:
    value = await redis_client.get("guardrailv2_status")
    if value is None:
        await redis_client.set("guardrailv2_status", "1")
        return True
    return value == "1"


def predict(text: str) -> tuple[bool, float, str]:
    inputs = tokenizer(
        text, padding=False, truncation=True, return_tensors="pt", max_length=512
    )
    input_ids = inputs["input_ids"].to(device)
    attention_mask = inputs["attention_mask"].to(device)

    with torch.no_grad():
        outputs = model(input_ids=input_ids, attention_mask=attention_mask)

    logits = outputs.logits
    probabilities = torch.softmax(logits, dim=1)
    predicted_class = torch.argmax(probabilities, dim=1).item()
    confidence = probabilities[0][predicted_class].item()

    is_sqli = predicted_class == 1 and confidence >= CONFIDENCE_THRESHOLD
    threat_type = "SQL Injection Detected (ML)" if is_sqli else "none"

    return is_sqli, confidence, threat_type


@app.post("/", response_model=None)
async def check_request(request: Request) -> Response:
    if not await get_guardrailv2_status():
        return ALLOWED_RESPONSE

    url = request.headers.get("X-Original-URI", "")

    if url.startswith(STATIC_PREFIX):
        return ALLOWED_RESPONSE

    method = request.headers.get("X-Original-Method", "GET")

    body = await request.body()
    body_str = body.decode("utf-8", errors="replace") if body else ""

    combined_input = f"{url} {body_str}".strip()

    if not combined_input:
        return ALLOWED_RESPONSE

    print(combined_input)
    is_sqli, confidence, threat_type = predict(combined_input)

    if not is_sqli:
        return ALLOWED_RESPONSE

    return JSONResponse(
        status_code=403,
        content={
            "blocked": True,
            "threat_type": threat_type,
            "payload": combined_input[:500],
            "confidence": round(confidence, 4),
            "target_url": url,
            "method": method,
        },
    )


@app.get("/status")
async def status() -> dict[str, bool]:
    return {"active": await get_guardrailv2_status()}


@app.get("/activate")
async def activate() -> dict[str, str]:
    await redis_client.set("guardrailv2_status", "1")
    return {"status": "activated"}


@app.get("/deactivate")
async def deactivate() -> dict[str, str]:
    await redis_client.set("guardrailv2_status", "0")
    return {"status": "deactivated"}
