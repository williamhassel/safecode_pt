import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./GamePage.css";

import { postWithAuth } from "../api/client";

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
  { id: "opt2", label: "Lines 6-8", lines: [6, 7, 8] }, // CORRECT in this example?
  { id: "opt3", label: "Lines 9-11", lines: [9, 10, 11] },
  { id: "opt4", label: "Lines 12-16", lines: [12, 13, 14, 15, 16] },
];

const API_BASE = "http://localhost:8000/api";
const CHALLENGE_ID = 1; // TODO: replace with real challenge id from backend later

export default function GamePage() {
  const navigate = useNavigate();
  const [selected, setSelected] = useState("");
  const [result, setResult] = useState(null);
  const [stats, setStats] = useState(null); // to show total/correct/accuracy from backend

  // choose which option you actually want to be correct
  const correctOptionId = "opt4";

  async function handleSubmit(e) {
    e.preventDefault();

    if (!selected) {
      setResult({ ok: false, msg: "Please select an option." });
      return;
    }

    const isCorrect = selected === correctOptionId;

    // Local feedback first
    if (isCorrect) {
      setResult({
        ok: true,
        msg: "Correct — those lines build a SQL query with user input!",
      });
    } else {
      setResult({
        ok: false,
        msg: "Not correct. Try examining how user input is used in the query.",
      });
    }

    // Now send result to backend (protected endpoint)
    const accessToken = localStorage.getItem("accessToken");
    if (!accessToken) {
      console.warn("No access token found. User is probably not logged in.");
      return;
    }

  try {
    const response = await postWithAuth("/results/", {
      challenge: CHALLENGE_ID,
      is_correct: isCorrect,
      score: isCorrect ? 1 : 0,
    });

    if (!response.ok) {
      const text = await response.text();
      console.error("Failed to send result:", text);
      return;
    }

    const data = await response.json();
    setStats(data.stats);

    if (data.certificate_issued) {
      alert(
        "Congratulations! You have earned a certificate. You can view/download it on your profile page."
      );
    }
  } catch (err) {
    console.error("Error while sending result:", err);
  }
}

  const lines = CODE_SNIPPET.trim().split("\n").map((ln) => ln);

  const handleLogout = () => {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    window.location.reload(); // Reload to trigger auth check
  };

  const handleHomeClick = (e) => {
    e.preventDefault();
    navigate("/");
  };

  return (
    <div className="page-root">
      <nav className="top-links">
        <a href="/" onClick={handleHomeClick}>Home</a>
        <span className="separator"> | </span>
        <span>Play Game</span>
        <span className="separator"> | </span>
        <button
          onClick={handleLogout}
          style={{
            background: 'none',
            border: 'none',
            color: 'white',
            cursor: 'pointer',
            textDecoration: 'underline',
            font: 'inherit',
            padding: 0
          }}
        >
          Logout
        </button>
      </nav>

      <h1 className="title">Vulnerability Challenge 1</h1>

      <div className="instructions">
        <strong>Vulnerability description:</strong> The server parses JSON sent
        by the client and then directly inserts a field from that JSON into a
        SQL statement without validation or parameterization. This allows an
        attacker to inject SQL content through the userId field.
      </div>

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

      {stats && (
        <div className="stats-panel">
          <h2>Your progress</h2>
          <p>Total answered: {stats.total_answered}</p>
          <p>Correct answers: {stats.correct_answers}</p>
          <p>
            Accuracy: {(stats.accuracy * 100).toFixed(1)}
            %
          </p>
        </div>
      )}
    </div>
  );
}