import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import "./GamePage.css";

import { postWithAuth } from "../api/client";

const SET_SIZE = 10;
const REQUIRED_SETS = 10;

function transformApiChallenge(apiData) {
  const correctOptionIndex = apiData.options.findIndex((opt) =>
    JSON.stringify([...opt.lines].sort()) === JSON.stringify([...apiData.vulnerable_lines].sort())
  );
  return {
    apiId: apiData.id,
    insecure_code: apiData.insecure_code,
    vulnerable_lines: apiData.vulnerable_lines || [],
    options: apiData.options.map((opt, idx) => ({
      id: `opt${idx + 1}`,
      label: opt.label,
      lines: opt.lines,
    })),
    correct_option: correctOptionIndex !== -1 ? `opt${correctOptionIndex + 1}` : "opt1",
    description: apiData.explanation?.short || apiData.description || "Identify the vulnerable line in the code.",
    language: apiData.language || "python",
    vuln_type: apiData.vuln_type || "sqli",
    explanation: apiData.explanation || {},
  };
}

function CodeBlock({ code }) {
  if (!code) return null;
  const lines = code.split("\n");
  return (
    <pre className="code-block">
      {lines.map((line, i) => (
        <div key={i} className="code-line">
          <span className="ln-number">{i + 1}</span>
          <span className="ln-text">{line}</span>
        </div>
      ))}
    </pre>
  );
}

export default function GamePage() {
  const navigate = useNavigate();

  // phase: 'loading' | 'playing' | 'feedback' | 'summary' | 'error'
  const [phase, setPhase] = useState("loading");
  const [setId, setSetId] = useState(null);
  const [challenges, setChallenges] = useState([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [selected, setSelected] = useState("");
  const [answers, setAnswers] = useState([]);
  const [summaryData, setSummaryData] = useState(null);

  const loadSet = useCallback(async () => {
    setPhase("loading");
    setCurrentIdx(0);
    setAnswers([]);
    setSelected("");
    setSummaryData(null);
    try {
      const response = await postWithAuth("/sets/new/", {});
      if (response.status === 404) {
        setPhase("error");
        return;
      }
      if (!response.ok) throw new Error("Failed to start set");
      const data = await response.json();
      setSetId(data.set_id);
      setChallenges(data.challenges.map(transformApiChallenge));
      setPhase("playing");
    } catch (err) {
      console.error("Error loading set:", err);
      setPhase("error");
    }
  }, []);

  useEffect(() => {
    loadSet();
  }, [loadSet]);

  const challenge = challenges[currentIdx];

  function handleSubmit(e) {
    e.preventDefault();
    if (!selected || !challenge) return;

    const isCorrect = selected === challenge.correct_option;
    setAnswers((prev) => [
      ...prev,
      {
        challengeId: challenge.apiId,
        isCorrect,
        selectedOption: selected,
        correctOption: challenge.correct_option,
      },
    ]);
    setPhase("feedback");
  }

  // submitSet is called with the complete answers array to avoid stale-closure
  // issues on the final challenge: we pass the array explicitly rather than
  // reading `answers` state inside the async callback.
  async function submitSet(allAnswers) {
    setPhase("loading");
    try {
      const payload = {
        answers: allAnswers.map((a) => ({
          challenge_id: a.challengeId,
          is_correct: a.isCorrect,
        })),
      };
      const response = await postWithAuth(`/sets/${setId}/submit/`, payload);
      if (!response.ok) throw new Error("Failed to submit set");
      const data = await response.json();
      setSummaryData(data);
      setPhase("summary");
    } catch (err) {
      console.error("Error submitting set:", err);
      setPhase("error");
    }
  }

  function handleNext() {
    if (currentIdx < SET_SIZE - 1) {
      setCurrentIdx((idx) => idx + 1);
      setSelected("");
      setPhase("playing");
    } else {
      // answers state contains all SET_SIZE answers at this point (set during handleSubmit)
      submitSet(answers);
    }
  }

  const handleLogout = () => {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    window.location.reload();
  };

  const handleHomeClick = (e) => {
    e.preventDefault();
    navigate("/");
  };

  // ── Loading ──────────────────────────────────────────────────────────────
  if (phase === "loading") {
    return (
      <div className="page-root">
        <div style={{ padding: "2rem", color: "white" }}>Loading...</div>
      </div>
    );
  }

  // ── Error / no pool ───────────────────────────────────────────────────────
  if (phase === "error") {
    return (
      <div className="page-root">
        <nav className="top-links">
          <a href="/" onClick={handleHomeClick}>Home</a>
        </nav>
        <div style={{ padding: "2rem", color: "white", textAlign: "center" }}>
          <h2>No challenges available yet.</h2>
          <p>The challenge pool is being generated. Please check back in a few minutes.</p>
          <button
            onClick={loadSet}
            style={{
              padding: "0.75rem 1.5rem",
              borderRadius: "8px",
              border: "none",
              cursor: "pointer",
              fontWeight: "600",
              background: "linear-gradient(135deg, #667eea, #764ba2)",
              color: "white",
            }}
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // ── Summary ───────────────────────────────────────────────────────────────
  if (phase === "summary" && summaryData) {
    const { score, total, is_passed, completed_sets, certificate_issued } = summaryData;
    const pct = Math.round((score / total) * 100);

    return (
      <div className="page-root">
        <nav className="top-links">
          <a href="/" onClick={handleHomeClick}>Home</a>
          <span className="separator"> | </span>
          <button
            onClick={handleLogout}
            style={{ background: "none", border: "none", color: "white", cursor: "pointer", textDecoration: "underline", font: "inherit", padding: 0 }}
          >
            Logout
          </button>
        </nav>

        <div className="summary-container">
          <h1 className="title">{is_passed ? "Set Complete!" : "Set Results"}</h1>

          <div className={`summary-score ${is_passed ? "passed" : "failed"}`}>
            {score} / {total}
          </div>
          <p className="summary-pct">{pct}% correct</p>

          {is_passed ? (
            <p className="summary-message passed-msg">You passed! Onwards to the next set.</p>
          ) : (
            <p className="summary-message failed-msg">You need 80% to pass. Keep at it!</p>
          )}

          {/* Per-challenge breakdown */}
          <div className="summary-results-list">
            {challenges.map((ch, idx) => {
              const answer = answers[idx];
              const correct = answer?.isCorrect;
              return (
                <div key={idx} className={`summary-result-item ${correct ? "correct" : "incorrect"}`}>
                  <span className="summary-result-num">{idx + 1}</span>
                  <span className="summary-result-icon">{correct ? "✓" : "✗"}</span>
                  <span className="summary-result-type">{ch.vuln_type.replace(/_/g, " ")}</span>
                </div>
              );
            })}
          </div>

          {/* Set progress toward certificate */}
          <div className="summary-progress">
            <p>
              Completed sets: <strong>{completed_sets} / {REQUIRED_SETS}</strong>
            </p>
            <div className="progress-bar-track">
              <div
                className="progress-bar-fill"
                style={{ width: `${Math.min((completed_sets / REQUIRED_SETS) * 100, 100)}%` }}
              />
            </div>
          </div>

          {certificate_issued && (
            <div className="summary-cert">
              Congratulations — you have earned a certificate!
            </div>
          )}

          <div className="summary-actions">
            <button onClick={loadSet} className="submit-btn">
              {is_passed ? "New Set" : "Try Again"}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Playing / Feedback ────────────────────────────────────────────────────
  const lastAnswer = answers[answers.length - 1];
  const isLastChallenge = currentIdx === SET_SIZE - 1;

  return (
    <div className="page-root">
      <nav className="top-links">
        <a href="/" onClick={handleHomeClick}>Home</a>
        <span className="separator"> | </span>
        <span>Play Game</span>
        <span className="separator"> | </span>
        <button
          onClick={handleLogout}
          style={{ background: "none", border: "none", color: "white", cursor: "pointer", textDecoration: "underline", font: "inherit", padding: 0 }}
        >
          Logout
        </button>
      </nav>

      {/* Progress dots */}
      <div className="set-progress-bar">
        <div className="set-progress-text">
          Challenge {currentIdx + 1} of {SET_SIZE}
        </div>
        <div className="set-progress-track">
          {Array.from({ length: SET_SIZE }).map((_, i) => {
            let cls = "set-progress-dot";
            if (i < answers.length) {
              cls += answers[i].isCorrect ? " dot-correct" : " dot-incorrect";
            } else if (i === currentIdx) {
              cls += " dot-current";
            }
            return <div key={i} className={cls} />;
          })}
        </div>
      </div>

      <div style={{ maxWidth: "800px", margin: "0 auto 1rem" }}>
        <h1 className="title" style={{ margin: 0 }}>Vulnerability Challenge</h1>
        {challenge?.vuln_type && (
          <span style={{ fontSize: "13px", color: "#ddd", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            {challenge.vuln_type.replace(/_/g, " ")}
          </span>
        )}
      </div>

      <div className="instructions">
        <strong>Vulnerability description:</strong> {challenge?.description || "Loading..."}
      </div>

      <div className="godot-window">
        <CodeBlock code={challenge?.insecure_code} />
      </div>

      <form className="options-form" onSubmit={handleSubmit}>
        <div className="options-grid">
          {challenge?.options?.map((o) => {
            const lineDisplay =
              o.lines?.length > 0
                ? o.lines.length === 1
                  ? `Line ${o.lines[0]}`
                  : `Lines ${Math.min(...o.lines)}–${Math.max(...o.lines)}`
                : "";
            const isSelected = selected === o.id;
            const submitted = phase === "feedback";
            const isCorrectOpt = o.id === challenge.correct_option;
            const isWrongChoice = isSelected && !isCorrectOpt;

            let cardClass = "option-card";
            if (isSelected) cardClass += " selected";
            if (submitted) {
              cardClass += " disabled";
              if (isCorrectOpt) cardClass += " correct-answer";
              else if (isWrongChoice) cardClass += " wrong-answer";
            }

            return (
              <button
                key={o.id}
                type="button"
                className={cardClass}
                onClick={() => {
                  if (!submitted) setSelected(o.id);
                }}
              >
                {lineDisplay && <span className="option-card-line">{lineDisplay}</span>}
                <span className="option-card-label">{o.label}</span>
              </button>
            );
          })}
        </div>

        <div className="form-actions">
          {phase === "playing" && (
            <button type="submit" className="submit-btn" disabled={!selected}>
              Submit
            </button>
          )}

          {phase === "feedback" && (
            <>
              <div className={`result ${lastAnswer?.isCorrect ? "ok" : "bad"}`}>
                {lastAnswer?.isCorrect
                  ? challenge.explanation?.correct_hint || "Correct!"
                  : challenge.explanation?.wrong_hint || "Not quite — the correct answer is highlighted."}
              </div>
              <button type="button" onClick={handleNext} className="submit-btn next-btn">
                {isLastChallenge ? "Finish →" : "Next →"}
              </button>
            </>
          )}
        </div>
      </form>
    </div>
  );
}
