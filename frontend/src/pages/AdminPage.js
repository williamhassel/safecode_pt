import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { getWithAuth, postWithAuth } from "../api/client";
import "./AdminPage.css";

// ---- Helpers ----------------------------------------------------------------

function vulnLabel(type) {
  const map = {
    sqli: "SQL Injection",
    xss: "XSS",
    path_traversal: "Path Traversal",
    cmdi: "Command Injection",
    xxe: "XXE",
    insecure_deser: "Insecure Deserialization",
    ssrf: "SSRF",
    weak_crypto: "Weak Crypto",
    hardcoded_creds: "Hardcoded Creds",
    auth_bypass: "Auth Bypass",
  };
  return map[type] || type;
}

function diffClass(d) {
  if (d === "easy") return "diff-easy";
  if (d === "medium") return "diff-medium";
  return "diff-hard";
}

// ---- Code display with highlighted vulnerable lines -------------------------

function AdminCodeBlock({ code, vulnerableLines = [] }) {
  if (!code) return null;
  const vulnSet = new Set(vulnerableLines);
  const lines = code.split("\n");
  return (
    <div className="admin-code-wrap">
      <pre className="admin-code-block">
        {lines.map((line, i) => {
          const lineNum = i + 1;
          const isVuln = vulnSet.has(lineNum);
          return (
            <div key={i} className={`admin-code-line${isVuln ? " vuln-line" : ""}`}>
              <span className="admin-ln-number">{lineNum}</span>
              <span className="admin-ln-text">{line}</span>
            </div>
          );
        })}
      </pre>
    </div>
  );
}

// ---- Single expandable challenge card --------------------------------------

function ChallengeCard({ challenge, onApprove, onDiscard, busy }) {
  const [expanded, setExpanded] = useState(false);

  const ver = challenge.verification || {};
  const securePass =
    ver.secure?.ok && ver.secure?.tests?.returncode === 0;
  const insecurePass =
    ver.insecure?.ok && ver.insecure?.tests?.returncode !== 0;

  const shortDesc =
    challenge.explanation?.short || challenge.description || "";

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

          {/* Insecure code with vuln lines highlighted */}
          <div className="card-section-title">
            Insecure code — vulnerable lines highlighted
          </div>
          <AdminCodeBlock
            code={challenge.insecure_code}
            vulnerableLines={challenge.vulnerable_lines || []}
          />

          {/* Secure code */}
          <div className="card-section-title">Secure code (reference)</div>
          <AdminCodeBlock code={challenge.secure_code} vulnerableLines={[]} />

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

      // If queue is still filling, keep polling
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

    // Poll every 8 seconds while generating
    pollRef.current = setInterval(() => {
      fetchQueue();
    }, 8000);

    return () => clearInterval(pollRef.current);
  }, [user, fetchQueue]);

  // Stop polling when queue is full
  useEffect(() => {
    if (!generating && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = setInterval(fetchQueue, 30000); // slow poll
    }
  }, [generating, fetchQueue]);

  // --- Trigger manual generation ------------------------------------------
  const handleGenerateMore = async () => {
    setGenerating(true);
    try {
      await postWithAuth("/admin/review-queue/", {});
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
        setGenerating(true); // generation was likely triggered server-side
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
            {pendingCount > 10 ? `+` : ""})
          </h2>
          <button
            className="btn-generate"
            disabled={generating || actionBusy}
            onClick={handleGenerateMore}
          >
            {generating ? "Generating..." : "Generate More"}
          </button>
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
                <button
                  className="btn-generate"
                  style={{ marginTop: "0.75rem" }}
                  onClick={handleGenerateMore}
                >
                  Generate Challenges
                </button>
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
