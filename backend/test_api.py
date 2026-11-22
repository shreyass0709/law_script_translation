"""Run from the repo root: `python backend/test_api.py` (loads the real model)."""
import sys

from fastapi.testclient import TestClient

from api import app

SAMPLE = (
    "Section 302 of the Indian Penal Code was amended on 15 August 2023.\nThe Act came into force in 1950.\n"
    "A fine of Rs. 5,000 may be imposed under section 302(2)(b), and article 21A shall apply."
)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    with TestClient(app) as client:
        assert client.post("/translate", json={"text": "hi", "target_lang": "fr"}).status_code == 422
        assert client.post("/translate", json={"text": "", "target_lang": "kn"}).status_code == 422
        for lang in ("kn", "kok"):
            r = client.post("/translate", json={"text": SAMPLE, "target_lang": lang})
            assert r.status_code == 200, r.text
            body = r.json()
            # Single line breaks are treated as PDF line wrapping, so this is one segment.
            assert len(body["segments"]) == 1 and body["disclaimer"]
            terms = {t["en"] for t in body["segments"][0]["terms"]}
            assert {"section", "article", "Act"} <= terms, terms
            out = " ".join(s["translation"] for s in body["segments"])
            print(f"[{lang}] {out}")
            # Project rule: numbers, section references and dates survive unchanged.
            for token in ("302", "15", "2023", "1950", "5,000", "302(2)(b)", "21A"):
                assert token in out, f"{lang}: {token!r} lost in translation"
        g = client.get("/glossary", params={"lang": "kn"}).json()
        assert {"en": "article", "target": "ಅನುಚ್ಛೇದ"} in g
    print("OK")
