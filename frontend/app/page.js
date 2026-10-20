"use client";
import { useState } from "react";

const DISCLAIMER =
  "Machine translation for legal awareness only. Not a certified legal translation. " +
  "Verify with a qualified person before any official use.";

export default function Home() {
  const [text, setText] = useState("");
  const [lang, setLang] = useState("kn");
  const [segments, setSegments] = useState([]);
  const [error, setError] = useState("");
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
      if (!res.ok) throw new Error(`Server error ${res.status}. Is the API running?`);
      setSegments((await res.json()).segments);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <h1>Law Script Translation</h1>
      <p role="note" style={{ background: "#fff4e5", border: "1px solid #f0b46c", padding: "0.75rem" }}>
        <strong>Disclaimer:</strong> {DISCLAIMER}
      </p>

      <form onSubmit={onSubmit}>
        <label htmlFor="text">English legal text (paste a section or a few pages; it is split into clauses automatically)</label>
        <textarea
          id="text"
          rows={8}
          maxLength={20000}
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
        <table style={{ width: "100%", marginTop: "1.5rem", borderCollapse: "collapse" }}>
          <thead>
            <tr><th align="left">English</th><th align="left">{lang === "kn" ? "Kannada" : "Konkani"}</th></tr>
          </thead>
          <tbody>
            {segments.map((s, i) => (
              <tr key={i} style={{ borderTop: "1px solid #ddd", verticalAlign: "top" }}>
                <td style={{ padding: "0.5rem" }}>{s.source}</td>
                <td style={{ padding: "0.5rem" }}>{s.translation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
