import React, { useState } from "react";
import "./GamePage.css";

const CODE_SNIPPET = `1  // Server receives JSON from client
2  function handleRequest(req) {
3    const data = JSON.parse(req.body);
4
5    // take user-provided id and use it in query
6    const userId = data.userId;
7    const query = "SELECT * FROM users WHERE id = " + userId;
8
9    // run the query
10   db.query(query, (err, rows) => {
11     if (err) {
12       console.error(err);
13       return sendError();
14     }
15     sendRows(rows);
16   });
17 }
`;

const OPTIONS = [
  { id: "opt1", label: "Lines 3-5", lines: [3, 4, 5] },
  { id: "opt2", label: "Lines 6-8", lines: [6, 7, 8] }, // CORRECT in this example
  { id: "opt3", label: "Lines 9-11", lines: [9, 10, 11] },
  { id: "opt4", label: "Lines 12-16", lines: [12, 13, 14, 15, 16] },
];

export default function GamePage() {
  const [selected, setSelected] = useState("");
  const [result, setResult] = useState(null);

  // in this toy example the correct choice is option 2 (string concatenation -> SQL injection)
  const correctOptionId = "opt4";

  function handleSubmit(e) {
    e.preventDefault();
    if (!selected) {
      setResult({ ok: false, msg: "Please select an option." });
      return;
    }
    if (selected === correctOptionId) {
      setResult({ ok: true, msg: "Correct — those lines build a SQL query with user input!" });
    } else {
      setResult({ ok: false, msg: "Not correct. Try examining how user input is used in the query." });
    }
  }

  // prepare lines with numbers for rendering
  const lines = CODE_SNIPPET.trim().split("\n").map((ln) => ln);

  return (
    <div className="page-root">
      <nav className="top-links">
        <a href="/">Home</a> <span> | </span> <a href="/game">Play Game</a>
      </nav>

      <h1 className="title">Vulnerability Challenge 1</h1>

      <div className="instructions">
        <strong>Vulnerability description:</strong> The server parses JSON sent by the client and then directly inserts a field from that JSON into a SQL statement without validation or parameterization. This allows an attacker to inject SQL content through the userId field.
      </div>

      {/* <div className="godot-window" role="region" aria-label="Godot preview window">
        <pre className="code-block" aria-hidden="false">
          {lines.map((ln, idx) => {
            // show line text with preserved spaces after the leading number in the sample
            return (
              <div key={idx} className="code-line">
                <span className="ln-number">{ln.split(" ")[0]}</span>
                <span className="ln-text">{ln.replace(/^\d+\s+/, "")}</span>
              </div>
            );
          })}
        </pre>
      </div> */}

      {/* Godot window */}

      <div className="godot-window">
        <iframe
          src="/godot-build/index.html"
          title="Godot Game"
          width="100%"
          height="100%"
          frameBorder="0"
        ></iframe>
      </div>

      <form className="options-form" onSubmit={handleSubmit}>
        <div className="options-list">
          {OPTIONS.map((o) => (
            <label key={o.id} className="option">
              <input
                type="radio"
                name="vuln"
                value={o.id}
                checked={selected === o.id}
                onChange={() => {
                  setSelected(o.id);
                  setResult(null);
                }}
              />
              <span className="option-label">{o.label}</span>
            </label>
          ))}
        </div>

        <div className="form-actions">
          <button type="submit" className="submit-btn">
            Submit
          </button>
          {result && (
            <div className={`result ${result.ok ? "ok" : "bad"}`}>
              {result.msg}
            </div>
          )}
        </div>
      </form>
    </div>
  );
}
