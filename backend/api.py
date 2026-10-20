"""HTTP API around translate.py.

Run from the repo root: `uvicorn api:app --app-dir backend`
Docs at http://127.0.0.1:8000/docs
"""
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from segment import segment
from translate import _load, translate

DISCLAIMER = "Machine translation for legal awareness only. Not a certified legal translation."


@asynccontextmanager
async def lifespan(app: FastAPI):
    _load()  # load the model once at startup, not on the first request
    yield


app = FastAPI(title="Law Script Translation", lifespan=lifespan)


class TranslateRequest(BaseModel):
    # ponytail: 20,000-char cap (a few pages) keeps one request to a couple of minutes on CPU.
    # Bigger documents need the file-upload route with background jobs.
    text: str = Field(min_length=1, max_length=20000)
    target_lang: Literal["kn", "kok"]


class Segment(BaseModel):
    source: str
    translation: str


class TranslateResponse(BaseModel):
    target_lang: str
    segments: list[Segment]
    disclaimer: str = DISCLAIMER


@app.post("/translate")
def translate_text(req: TranslateRequest) -> TranslateResponse:
    segs = segment(req.text)
    outputs = translate(segs, req.target_lang) if segs else []
    return TranslateResponse(
        target_lang=req.target_lang,
        segments=[Segment(source=s, translation=t) for s, t in zip(segs, outputs)],
    )
