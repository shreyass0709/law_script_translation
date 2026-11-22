"use client";
import { useState } from "react";

const DISCLAIMER =
  "Machine translation for legal awareness only. Not a certified legal translation. " +
  "Verify with a qualified person before any official use.";
const MAX_CHARS = 20000; // same cap as the API
const LANGS = {
  kn: { name: "Kannada", native: "ಕನ್ನಡ" },
  kok: { name: "Konkani", native: "ಕೊಂಕಣಿ", note: "Kannada script" },
};
const SAMPLE =
  "1. Short title and commencement.—(1) This Act may be called the Right to Information Act, 2005.\n\n" +
  "(2) A fine of Rs. 5,000 may be imposed under section 302(2)(b), and article 21A shall apply.\n\n" +
  "(3) Every public authority shall maintain all its records duly catalogued and indexed.";

// The API's own message (FastAPI puts it in `detail`), else a hint that it is not running.
async function apiError(res) {
  try {
    const { detail } = await res.json();
    if (typeof detail === "string") return new Error(detail);
    if (Array.isArray(detail)) return new Error(detail.map((d) => d.msg).join("; "));
  } catch {}
  return new Error(`Server error ${res.status}. Is the API running?`);
}

function friendly(err) {
  return err.message === "Failed to fetch" ? "Cannot reach the server. Is the website running?" : err.message;
}

export default function Home() {
  const [text, setText] = useState("");
  const [lang, setLang] = useState("kn");
  const [segments, setSegments] = useState([]);
  const [resultLang, setResultLang] = useState("kn");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(""); // "", "pdf" or "translate"
  const [over, setOver] = useState(false);
  const [onlyReview, setOnlyReview] = useState(false);
  const [copied, setCopied] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setBusy("translate");
    setError("");
    setSegments([]);
    setOnlyReview(false);
    try {
      const res = await fetch("/api/translate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, target_lang: lang }),
      });
      if (!res.ok) throw await apiError(res);
      setSegments((await res.json()).segments);
      setResultLang(lang);
    } catch (err) {
      setError(friendly(err));
    } finally {
      setBusy("");
    }
  }

  async function loadPdf(file) {
    if (!file) return;
    setError("");
    setNotice("");
    setBusy("pdf");
    try {
      const res = await fetch("/api/extract", { method: "POST", body: file });
      if (!res.ok) throw await apiError(res);
      const { text: pdfText, pages } = await res.json();
      setText(pdfText.slice(0, MAX_CHARS));
      setNotice(
        pdfText.length > MAX_CHARS
          ? `Loaded ${file.name} (${pages} pages), but only the first ${MAX_CHARS.toLocaleString()} characters fit. Translate it in parts.`
          : `Loaded ${file.name} (${pages} pages). Check the text, then click Translate.`
      );
    } catch (err) {
      setError(friendly(err));
    } finally {
      setBusy("");
    }
  }

  function onDrop(e) {
    e.preventDefault();
    setOver(false);
    const file = e.dataTransfer.files[0];
    if (file && !/\.pdf$/i.test(file.name)) return setError("Only PDF files can be uploaded.");
    loadPdf(file);
  }

  const langLabel = (l) => (l === "kn" ? "Kannada" : "Konkani (Kannada script)");
  const plain = () =>
    segments.map((s) => `${s.needs_review ? "[Needs review] " : ""}${s.translation}`).join("\n\n");

  function onDownload() {
    const body = segments
      .map((s) => `${s.source}\n${s.needs_review ? "[Needs review] " : ""}${s.translation}`)
      .join("\n\n");
    const blob = new Blob([`${DISCLAIMER}\n\nEnglish → ${langLabel(resultLang)}\n\n${body}\n`], {
      type: "text/plain;charset=utf-8",
    });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `translation-${resultLang}.txt`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  async function onCopy() {
    try {
      await navigator.clipboard.writeText(plain());
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setError("Copy failed. Use the download button instead.");
    }
  }

  const terms = segments.flatMap((s) => s.terms);
  const found = terms.filter((t) => t.found).length;
  const reviewCount = segments.filter((s) => s.needs_review).length;
  const shown = onlyReview ? segments.filter((s) => s.needs_review) : segments;

  return (
    <>
      <header className="top">
        <div className="wrap">
          <div className="brand">
            <div className="mark" aria-hidden="true">ಅ</div>
            <div>
              <h1>Law Script Translation</h1>
              <p>English legal text → Kannada · Konkani</p>
            </div>
          </div>
          <span className="badge">Research prototype</span>
        </div>
      </header>

      <main className="wrap">
        <p className="disclaimer" role="note">
          <strong>Disclaimer:</strong> <span>{DISCLAIMER}</span>
        </p>

        <form className="card" onSubmit={onSubmit}>
          <fieldset className="langs">
            <legend>Translate into</legend>
            <div className="seg">
              {Object.entries(LANGS).map(([code, l]) => (
                <label key={code}>
                  <input type="radio" name="lang" value={code} checked={lang === code} onChange={() => setLang(code)} />
                  <span>
                    {l.name}
                    <small>{l.native}</small>
                    {l.note && <small style={{ fontFamily: "var(--font)" }}>({l.note})</small>}
                  </span>
                </label>
              ))}
            </div>
          </fieldset>

          <div
            className={`drop${over ? " over" : ""}`}
            onDragOver={(e) => { e.preventDefault(); setOver(true); }}
            onDragLeave={() => setOver(false)}
            onDrop={onDrop}
          >
            <label className="btn small" htmlFor="pdf">
              {busy === "pdf" ? <><span className="spinner" aria-hidden="true" /> Reading PDF…</> : "Upload PDF"}
            </label>
            <input
              id="pdf"
              type="file"
              accept="application/pdf,.pdf"
              disabled={!!busy}
              onChange={(e) => { const f = e.target.files[0]; e.target.value = ""; loadPdf(f); }}
            />
            <span>or drop a PDF here. Text PDFs only; scanned pages can't be read.</span>
          </div>

          <label className="field-label" htmlFor="text">
            English legal text
            <span>{text.length.toLocaleString()} / {MAX_CHARS.toLocaleString()}</span>
          </label>
          <textarea
            id="text"
            maxLength={MAX_CHARS}
            required
            value={text}
            placeholder="Paste a section or a few pages. It is split into clauses automatically; numbers, sections and dates are kept unchanged."
            onChange={(e) => setText(e.target.value)}
          />
          {notice && <p className="notice" role="status">{notice}</p>}

          <div className="actions">
            <button type="submit" className="btn primary" disabled={!!busy || !text.trim()}>
              {busy === "translate" ? <><span className="spinner" aria-hidden="true" /> Translating…</> : "Translate"}
            </button>
            <button type="button" className="btn" disabled={!!busy} onClick={() => { setText(SAMPLE); setNotice(""); }}>
              Try a sample
            </button>
            {text && (
              <button type="button" className="btn" disabled={!!busy} onClick={() => { setText(""); setNotice(""); }}>
                Clear
              </button>
            )}
          </div>
          {error && <p className="error" role="alert">{error}</p>}
        </form>

        {segments.length > 0 && (
          <section className="card" aria-labelledby="results">
            <div className="results-head">
              <h2 id="results">Translation · {langLabel(resultLang)}</h2>
              <div className="actions" style={{ marginTop: 0 }}>
                <button type="button" className="btn small" onClick={onCopy}>{copied ? "Copied ✓" : "Copy"}</button>
                <button type="button" className="btn small primary" onClick={onDownload}>Download .txt</button>
              </div>
            </div>

            <ul className="stats">
              <li><b>{segments.length}</b> segments</li>
              {terms.length > 0 && <li><b>{found}/{terms.length}</b> approved legal terms used</li>}
              <li className={reviewCount ? "warn" : ""}><b>{reviewCount}</b> need review</li>
            </ul>

            {reviewCount > 0 && (
              <label className="filter">
                <input type="checkbox" checked={onlyReview} onChange={(e) => setOnlyReview(e.target.checked)} />
                Show only segments that need review
              </label>
            )}

            <div className="cols" aria-hidden="true" style={{ marginTop: "0.75rem" }}>
              <span>English</span><span>{LANGS[resultLang].name}</span>
            </div>
            {shown.map((s, i) => (
              <div key={i} className={`seg-row${s.needs_review ? " review" : ""}`}>
                <div className="src">{s.source}</div>
                <div>
                  {s.needs_review && <span className="flag">Needs review</span>}
                  <div className="tgt" lang="kn">{s.translation}</div>
                  {s.terms.length > 0 && (
                    <ul className="terms" aria-label="Glossary check">
                      {s.terms.map((t) => (
                        <li key={t.en} className={t.found ? "found" : "missing"}
                            title={t.found ? "Approved term used" : "Approved term not used"}>
                          {t.found ? "✓" : "✗"} {t.en} → <span className="kn">{t.target}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            ))}
            {shown.length === 0 && <p className="empty">No segments need review.</p>}
          </section>
        )}
      </main>

      <footer>
        <div className="wrap">
          <p>Model: AI4Bharat IndicTrans2. Konkani is shown in Kannada script.</p>
          <p>{DISCLAIMER}</p>
        </div>
      </footer>
    </>
  );
}
