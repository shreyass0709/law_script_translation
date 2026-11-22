"use client";
import { useState } from "react";

const DISCLAIMER =
  "Machine translation for legal awareness only. Not a certified legal translation. " +
  "Verify with a qualified person before any official use.";
const MAX_CHARS = 20000; // same cap as the API

// The API's own message (FastAPI puts it in `detail`), else a hint that it is not running.
async function apiError(res) {
  try {
    const { detail } = await res.json();
    if (typeof detail === "string") return new Error(detail);
    if (Array.isArray(detail)) return new Error(detail.map((d) => d.msg).join("; "));
  } catch {}
  return new Error(`Server error ${res.status}. Is the API running?`);
}

export default function Home() {
  const [text, setText] = useState("");
  const [lang, setLang] = useState("kn");
  const [segments, setSegments] = useState([]);
  const [resultLang, setResultLang] = useState("kn");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setSegments([]);
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
      setError(err.message === "Failed to fetch" ? "Cannot reach the server. Is the website running?" : err.message);
    } finally {
      setLoading(false);
    }
  }

  async function onPdf(e) {
    const file = e.target.files[0];
    e.target.value = ""; // allow choosing the same file again
    if (!file) return;
    setError("");
    setNotice("");
    setLoading(true);
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
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function onDownload() {
    const name = resultLang === "kn" ? "Kannada" : "Konkani (Kannada script)";
    const body = segments
      .map((s) => `${s.source}\n${s.needs_review ? "[Needs review] " : ""}${s.translation}`)
      .join("\n\n");
    const blob = new Blob([`${DISCLAIMER}\n\nEnglish → ${name}\n\n${body}\n`], { type: "text/plain;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `translation-${resultLang}.txt`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  return (
    <main>
      <h1>Law Script Translation</h1>
      <p role="note" style={{ background: "#fff4e5", border: "1px solid #f0b46c", padding: "0.75rem" }}>
        <strong>Disclaimer:</strong> {DISCLAIMER}
      </p>

      <form onSubmit={onSubmit}>
        <label htmlFor="pdf">Upload a PDF (text PDFs only, not scanned pages): </label>
        <input id="pdf" type="file" accept="application/pdf,.pdf" onChange={onPdf} disabled={loading} />
        {notice && <p role="status" style={{ margin: "0.5rem 0" }}>{notice}</p>}
        <label htmlFor="text" style={{ display: "block", marginTop: "0.75rem" }}>
          English legal text (paste a section or a few pages; it is split into clauses automatically)
        </label>
        <textarea
          id="text"
          rows={8}
          maxLength={MAX_CHARS}
          required
          value={text}
          onChange={(e) => setText(e.target.value)}
          style={{ width: "100%", display: "block", margin: "0.5rem 0" }}
        />
        <fieldset style={{ border: "none", padding: 0 }}>
          <legend>Translate into</legend>
          <label><input type="radio" name="lang" value="kn" checked={lang === "kn"} onChange={() => setLang("kn")} /> Kannada</label>{" "}
          <label><input type="radio" name="lang" value="kok" checked={lang === "kok"} onChange={() => setLang("kok")} /> Konkani (Kannada script)</label>
        </fieldset>
        <button type="submit" disabled={loading} style={{ marginTop: "0.75rem" }}>
          {loading ? "Translating…" : "Translate"}
        </button>
      </form>

      {error && <p role="alert" style={{ color: "#b00020" }}>{error}</p>}

      {segments.length > 0 && (
        <button type="button" onClick={onDownload} style={{ marginTop: "1.5rem" }}>
          Download translation (.txt)
        </button>
      )}

      {segments.length > 0 && (
        <table style={{ width: "100%", marginTop: "1rem", borderCollapse: "collapse" }}>
          <thead>
            <tr><th align="left">English</th><th align="left">{resultLang === "kn" ? "Kannada" : "Konkani"}</th></tr>
          </thead>
          <tbody>
            {segments.map((s, i) => (
              <tr key={i} style={{ borderTop: "1px solid #ddd", verticalAlign: "top", background: s.needs_review ? "#fff8e1" : undefined }}>
                <td style={{ padding: "0.5rem" }}>{s.source}</td>
                <td style={{ padding: "0.5rem" }}>
                  {s.needs_review && <strong style={{ color: "#8a5a00" }}>Needs review: </strong>}
                  {s.translation}
                  {s.terms.length > 0 && (
                    <ul style={{ listStyle: "none", padding: 0, margin: "0.4rem 0 0", fontSize: "0.85em" }}>
                      {s.terms.map((t) => (
                        <li key={t.en} style={{ color: t.found ? "#2e6b30" : "#b00020" }}>
                          {t.found ? "✓" : "✗"} {t.en} → {t.target}
                          {!t.found && " (approved term not used)"}
                        </li>
                      ))}
                    </ul>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
