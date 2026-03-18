import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { getWithAuth, postWithAuth } from "../api/client";
import "./AdminPage.css";

// ---- Helpers ----------------------------------------------------------------

const VULN_TYPES = [
  { value: "sqli",            label: "SQL Injection" },
  { value: "xss",             label: "XSS" },
  { value: "path_traversal",  label: "Path Traversal" },
  { value: "cmdi",            label: "Command Injection" },
  { value: "xxe",             label: "XXE" },
  { value: "insecure_deser",  label: "Insecure Deserialization" },
  { value: "ssrf",            label: "SSRF" },
  { value: "weak_crypto",     label: "Weak Crypto" },
  { value: "hardcoded_creds", label: "Hardcoded Creds" },
  { value: "auth_bypass",     label: "Auth Bypass" },
];

function vulnLabel(type) {
  const found = VULN_TYPES.find((v) => v.value === type);
  return found ? found.label : type;
}

function diffClass(d) {
  if (d === "easy") return "diff-easy";
  if (d === "medium") return "diff-medium";
  return "diff-hard";
}

// ---- Code display with highlighted lines ------------------------------------

function AdminCodeBlock({ code, highlightLines = [], highlightClass = "vuln-line" }) {
  if (!code) return null;
  const highlightSet = new Set(highlightLines);
  const lines = code.split("\n");
  return (
    <div className="admin-code-wrap">
      <pre className="admin-code-block">
        {lines.map((line, i) => {
          const lineNum = i + 1;
          const isHighlighted = highlightSet.has(lineNum);
          return (
            <div
              key={i}
              className={`admin-code-line${isHighlighted ? ` ${highlightClass}` : ""}`}
            >
              <span className="admin-ln-number">{lineNum}</span>
              <span className="admin-ln-text">{line}</span>
            </div>
          );
        })}
      </pre>
    </div>
  );
}

// ---- Multiple-choice options display ----------------------------------------

function OptionsDisplay({ options, vulnerableLines }) {
  if (!options || options.length === 0) return null;

  const vulnSet = new Set(vulnerableLines || []);

  function isCorrectOption(opt) {
    const optSet = new Set(opt.lines || []);
    if (optSet.size !== vulnSet.size) return false;
    for (const ln of vulnSet) {
      if (!optSet.has(ln)) return false;
    }
    return true;
  }

  function formatLines(lines) {
    if (!lines || lines.length === 0) return "—";
    if (lines.length === 1) return `Line ${lines[0]}`;
    const sorted = [...lines].sort((a, b) => a - b);
    // Check if contiguous
    const isRange = sorted.every((v, i) => i === 0 || v === sorted[i - 1] + 1);
    if (isRange) return `Lines ${sorted[0]}–${sorted[sorted.length - 1]}`;
    return `Lines ${sorted.join(", ")}`;
  }

  return (
    <div className="options-list">
      {options.map((opt, idx) => {
        const correct = isCorrectOption(opt);
        return (
          <div key={idx} className={`option-row${correct ? " option-correct" : " option-distractor"}`}>
            <span className="option-letter">{String.fromCharCode(65 + idx)}</span>
            <span className="option-lines">{formatLines(opt.lines)}</span>
            {correct && <span className="option-badge correct-badge">Correct answer</span>}
          </div>
        );
      })}
    </div>
  );
}

// ---- Single expandable challenge card --------------------------------------

function ChallengeCard({ challenge, onApprove, onDiscard, busy }) {
  const [expanded, setExpanded] = useState(false);
  const [optionHighlight, setOptionHighlight] = useState(null); // lines to highlight in code

  const ver = challenge.verification || {};
  const securePass =
    ver.secure?.ok && ver.secure?.tests?.returncode === 0;
  const insecurePass =
    ver.insecure?.ok && ver.insecure?.tests?.returncode !== 0;

  const shortDesc =
    challenge.explanation?.short || challenge.description || "";

  const options = challenge.options || [];
  const vulnerableLines = challenge.vulnerable_lines || [];

  return (
    <div className={`challenge-card${expanded ? " expanded" : ""}`}>
      {/* Header row – always visible */}
      <div className="card-header" onClick={() => setExpanded((v) => !v)}>
        <span className="card-chevron">&#9654;</span>
        <div className="card-badges">
          <span className="badge vuln">{vulnLabel(challenge.vuln_type)}</span>
          <span className={`badge ${diffClass(challenge.difficulty)}`}>
            {challenge.difficulty}
          </span>
          <span className="badge lang">{challenge.language}</span>
        </div>
        {shortDesc && (
          <span className="card-description" title={shortDesc}>
            {shortDesc}
          </span>
        )}
      </div>

      {/* Expanded body */}
      {expanded && (
        <div className="card-body">
          {/* Explanation */}
          {shortDesc && (
            <>
              <div className="card-section-title">Description</div>
              <div className="explanation-box">{shortDesc}</div>
            </>
          )}

          {/* Multiple-choice options */}
          {options.length > 0 && (
            <>
              <div className="card-section-title">
                Multiple-choice options
                <span className="card-section-hint">
                  &nbsp;— hover an option to highlight those lines in the code below
                </span>
              </div>
              <div className="options-list">
                {options.map((opt, idx) => {
                  const correct = (() => {
                    const vulnSet = new Set(vulnerableLines);
                    const optSet = new Set(opt.lines || []);
                    if (optSet.size !== vulnSet.size) return false;
                    for (const ln of vulnSet) if (!optSet.has(ln)) return false;
                    return true;
                  })();
                  const lines = opt.lines || [];
                  const sorted = [...lines].sort((a, b) => a - b);
                  const isRange = sorted.every(
                    (v, i) => i === 0 || v === sorted[i - 1] + 1
                  );
                  const linesLabel =
                    lines.length === 0
                      ? "—"
                      : lines.length === 1
                      ? `Line ${lines[0]}`
                      : isRange
                      ? `Lines ${sorted[0]}–${sorted[sorted.length - 1]}`
                      : `Lines ${sorted.join(", ")}`;
                  return (
                    <div
                      key={idx}
                      className={`option-row${correct ? " option-correct" : " option-distractor"}`}
                      onMouseEnter={() => setOptionHighlight(lines)}
                      onMouseLeave={() => setOptionHighlight(null)}
                    >
                      <span className="option-letter">
                        {String.fromCharCode(65 + idx)}
                      </span>
                      <span className="option-lines">{linesLabel}</span>
                      {correct && (
                        <span className="option-badge correct-badge">
                          Correct answer
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </>
          )}

          {/* Insecure code */}
          <div className="card-section-title">
            Insecure code
            {optionHighlight
              ? " — highlighted: hovered option"
              : " — highlighted: vulnerable lines"}
          </div>
          <AdminCodeBlock
            code={challenge.insecure_code}
            highlightLines={optionHighlight ?? vulnerableLines}
            highlightClass={optionHighlight ? "option-line" : "vuln-line"}
          />

          {/* Secure code */}
          <div className="card-section-title">Secure code (reference)</div>
          <AdminCodeBlock code={challenge.secure_code} highlightLines={[]} />

          {/* Test verification results */}
          <div className="card-section-title">Test verification</div>
          <div className="verification-row">
            <span className={`ver-pill ${securePass ? "pass" : "fail"}`}>
              {securePass ? "Secure code: PASS" : "Secure code: FAIL"}
            </span>
            <span className={`ver-pill ${insecurePass ? "pass" : "fail"}`}>
              {insecurePass
                ? "Insecure code: tests correctly fail"
                : "Insecure code: tests did NOT fail (problem!)"}
            </span>
          </div>

          {/* Actions */}
          <div className="card-actions">
            <button
              className="btn-approve"
              disabled={busy}
              onClick={() => onApprove(challenge.id)}
            >
              Approve — add to pool
            </button>
            <button
              className="btn-discard"
              disabled={busy}
              onClick={() => onDiscard(challenge.id)}
            >
              Discard
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ---- Main admin page -------------------------------------------------------

export default function AdminPage() {
  const navigate = useNavigate();

  const [user, setUser] = useState(null);
  const [userLoading, setUserLoading] = useState(true);

  const [challenges, setChallenges] = useState([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [approvedCount, setApprovedCount] = useState(0);
  const [queueLoading, setQueueLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [actionBusy, setActionBusy] = useState(false);

  // Vuln-type selector for targeted batch generation
  const [selectedVulnType, setSelectedVulnType] = useState("");

  const pollRef = useRef(null);

  // --- Load current user first to check is_staff --------------------------
  useEffect(() => {
    async function loadUser() {
      try {
        const res = await getWithAuth("/auth/me/");
        if (!res.ok) throw new Error("Not authenticated");
        const data = await res.json();
        setUser(data);
      } catch {
        setUser(null);
      } finally {
        setUserLoading(false);
      }
    }
    loadUser();
  }, []);

  // --- Fetch review queue --------------------------------------------------
  const fetchQueue = useCallback(async () => {
    try {
      const res = await getWithAuth("/admin/review-queue/");
      if (!res.ok) return;
      const data = await res.json();
      setChallenges(data.challenges || []);
      setPendingCount(data.pending_count || 0);
      setApprovedCount(data.approved_count || 0);

      if ((data.pending_count || 0) < 10) {
        setGenerating(true);
      } else {
        setGenerating(false);
      }
    } catch (err) {
      console.error("Failed to fetch review queue:", err);
    } finally {
      setQueueLoading(false);
    }
  }, []);

  // Start polling once we know the user is staff
  useEffect(() => {
    if (!user?.is_staff) return;

    fetchQueue();

    pollRef.current = setInterval(() => {
      fetchQueue();
    }, 8000);

    return () => clearInterval(pollRef.current);
  }, [user, fetchQueue]);

  // Slow poll when queue is full
  useEffect(() => {
    if (!generating && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = setInterval(fetchQueue, 30000);
    }
  }, [generating, fetchQueue]);

  // --- Trigger generation --------------------------------------------------
  const handleGenerateMore = async () => {
    setGenerating(true);
    try {
      if (selectedVulnType) {
        await postWithAuth("/admin/generate-batch/", {
          vuln_type: selectedVulnType,
          count: 10,
        });
      } else {
        await postWithAuth("/admin/review-queue/", {});
      }
    } catch (err) {
      console.error("Failed to trigger generation:", err);
    }
  };

  // --- Approve challenge ---------------------------------------------------
  const handleApprove = async (id) => {
    setActionBusy(true);
    try {
      const res = await postWithAuth(`/admin/challenges/${id}/approve/`, {});
      if (res.ok) {
        setChallenges((prev) => prev.filter((c) => c.id !== id));
        setPendingCount((n) => Math.max(0, n - 1));
        setApprovedCount((n) => n + 1);
        setGenerating(true);
      }
    } catch (err) {
      console.error("Failed to approve challenge:", err);
    } finally {
      setActionBusy(false);
    }
  };

  // --- Discard challenge ---------------------------------------------------
  const handleDiscard = async (id) => {
    setActionBusy(true);
    try {
      const res = await postWithAuth(`/admin/challenges/${id}/discard/`, {});
      if (res.ok) {
        setChallenges((prev) => prev.filter((c) => c.id !== id));
        setPendingCount((n) => Math.max(0, n - 1));
        setGenerating(true);
      }
    } catch (err) {
      console.error("Failed to discard challenge:", err);
    } finally {
      setActionBusy(false);
    }
  };

  // --- Loading / access denied states -------------------------------------
  if (userLoading) {
    return (
      <div className="admin-root">
        <div className="admin-denied">
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  if (!user || !user.is_staff) {
    return (
      <div className="admin-root">
        <div className="admin-denied">
          <h2>Access Denied</h2>
          <p>This page is only available to staff/admin accounts.</p>
          <button
            className="btn-generate"
            style={{ marginTop: "1rem" }}
            onClick={() => navigate("/")}
          >
            Go Home
          </button>
        </div>
      </div>
    );
  }

  const generateLabel = selectedVulnType
    ? `Generate 10 \u00d7 ${vulnLabel(selectedVulnType)}`
    : generating
    ? "Generating..."
    : "Generate 10 (any type)";

  return (
    <div className="admin-root">
      {/* Navigation */}
      <nav className="admin-nav">
        <button className="admin-nav-link" onClick={() => navigate("/")}>
          Home
        </button>
        <span className="admin-nav-sep">|</span>
        <span className="admin-nav-title">Challenge Review Queue</span>
        <span className="admin-nav-sep">|</span>
        <button
          className="admin-nav-link"
          onClick={() => {
            localStorage.removeItem("accessToken");
            localStorage.removeItem("refreshToken");
            window.location.reload();
          }}
        >
          Logout
        </button>
      </nav>

      <div className="admin-content">
        {/* Header */}
        <div className="admin-header">
          <h1>Challenge Review Queue</h1>
          <p>
            Review AI-generated security challenges before they go live in the
            student pool. Approve quality challenges or discard poor ones.
          </p>
        </div>

        {/* Stats chips */}
        <div className="admin-stats-bar">
          <span className="stat-chip pending">
            {pendingCount} pending review
          </span>
          <span className="stat-chip approved">
            {approvedCount} approved in pool
          </span>
          {generating && (
            <span className="stat-chip generating">
              <span className="spinning">&#9696;</span> Generating more...
            </span>
          )}
        </div>

        {/* Toolbar */}
        <div className="admin-toolbar">
          <h2>
            Pending Challenges ({challenges.length}
            {pendingCount > 10 ? "+" : ""})
          </h2>
          <div className="toolbar-actions">
            <select
              className="vuln-type-select"
              value={selectedVulnType}
              onChange={(e) => setSelectedVulnType(e.target.value)}
              disabled={actionBusy}
            >
              <option value="">Any vulnerability type</option>
              {VULN_TYPES.map((v) => (
                <option key={v.value} value={v.value}>
                  {v.label}
                </option>
              ))}
            </select>
            <button
              className="btn-generate"
              disabled={actionBusy}
              onClick={handleGenerateMore}
            >
              {generateLabel}
            </button>
          </div>
        </div>

        {/* Challenge list */}
        {queueLoading ? (
          <div className="admin-empty">
            <div className="spinner">&#9696;</div>
            <p>Loading review queue...</p>
          </div>
        ) : challenges.length === 0 ? (
          <div className="admin-empty">
            {generating ? (
              <>
                <div className="spinner spinning" style={{ fontSize: "2rem" }}>
                  &#9696;
                </div>
                <p style={{ marginTop: "0.75rem" }}>
                  Challenges are being generated. This usually takes 1–2 minutes
                  per challenge. The page will refresh automatically.
                </p>
              </>
            ) : (
              <>
                <p>No challenges pending review.</p>
                <div style={{ marginTop: "0.75rem", display: "flex", gap: "0.75rem", justifyContent: "center", flexWrap: "wrap" }}>
                  <select
                    className="vuln-type-select"
                    value={selectedVulnType}
                    onChange={(e) => setSelectedVulnType(e.target.value)}
                  >
                    <option value="">Any vulnerability type</option>
                    {VULN_TYPES.map((v) => (
                      <option key={v.value} value={v.value}>
                        {v.label}
                      </option>
                    ))}
                  </select>
                  <button className="btn-generate" onClick={handleGenerateMore}>
                    Generate Challenges
                  </button>
                </div>
              </>
            )}
          </div>
        ) : (
          <div className="challenge-list">
            {challenges.map((ch) => (
              <ChallengeCard
                key={ch.id}
                challenge={ch}
                onApprove={handleApprove}
                onDiscard={handleDiscard}
                busy={actionBusy}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
