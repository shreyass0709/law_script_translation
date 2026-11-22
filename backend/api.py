"""HTTP API around translate.py.

Run from the repo root: `uvicorn api:app --app-dir backend`
Docs at http://127.0.0.1:8000/docs
"""
from contextlib import asynccontextmanager
from typing import Literal

import pymupdf
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

import glossary
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


class Term(BaseModel):
    en: str
    target: str
    found: bool  # approved term present in the translation


class Segment(BaseModel):
    source: str
    translation: str
    terms: list[Term]
    needs_review: bool  # an approved legal term is missing from the translation


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
        segments=[_segment(s, t, req.target_lang) for s, t in zip(segs, outputs)],
    )


def _segment(source: str, translation: str, lang: str) -> Segment:
    terms = glossary.check(source, translation, lang)
    return Segment(source=source, translation=translation, terms=terms,
                   needs_review=not all(t["found"] for t in terms))


MAX_PDF_BYTES = 10 * 1024 * 1024


class ExtractResponse(BaseModel):
    text: str
    pages: int


@app.post("/extract")
async def extract_pdf(request: Request) -> ExtractResponse:
    """PDF bytes in the request body -> its English text, for the page to fill the text box.

    Only PDFs with a text layer work: there is no OCR, so scanned pages are refused.
    """
    data = await request.body()
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(413, "PDF is larger than 10 MB.")
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception:
        raise HTTPException(400, "Not a readable PDF file.")
    with doc:
        text = "\n".join(page.get_text() for page in doc)
        pages = doc.page_count
    if sum(c.isascii() and c.isalpha() for c in text) < 50 * pages:
        raise HTTPException(422, "No English text found. Scanned PDFs are not supported; paste the text instead.")
    return ExtractResponse(text=text.strip(), pages=pages)


@app.get("/glossary")
def get_glossary(lang: Literal["kn", "kok"]) -> list[dict]:
    return glossary.entries(lang)
