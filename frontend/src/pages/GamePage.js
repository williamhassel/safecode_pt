import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import "./GamePage.css";

import { postWithAuth, getWithAuth } from "../api/client";

export default function GamePage() {
  const navigate = useNavigate();
  const [selected, setSelected] = useState("");
  const [result, setResult] = useState(null);
  const [stats, setStats] = useState(null);
  const [challengeData, setChallengeData] = useState(null);
  const [currentChallengeId, setCurrentChallengeId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const iframeRef = useRef(null);

  // Fetch challenge data from backend on component mount
  useEffect(() => {
    async function fetchChallenge() {
      try {
        // Try to fetch latest challenge from API first
        let challengeData = null;

        try {
          const response = await getWithAuth('/generator/latest/');
          console.log('Latest challenge API response status:', response.status);

          if (response.ok) {
            const apiData = await response.json();
            console.log('Latest challenge API data:', apiData);

            // Store the challenge ID
            setCurrentChallengeId(apiData.id);

            // Transform API response to match our component structure
            // Find the correct option by matching vulnerable_lines with option lines
            const correctOptionIndex = apiData.options.findIndex((opt) =>
              JSON.stringify(opt.lines.sort()) === JSON.stringify(apiData.vulnerable_lines.sort())
            );

            challengeData = {
              insecure_code: apiData.insecure_code,
              vulnerable_lines: apiData.vulnerable_lines || [],
              options: apiData.options.map((opt, idx) => ({
                id: `opt${idx + 1}`,
                label: opt.label,
                lines: opt.lines
              })),
              correct_option: correctOptionIndex !== -1 ? `opt${correctOptionIndex + 1}` : 'opt1',
              description: apiData.explanation?.short || apiData.description || "Identify the vulnerable line in the code.",
              language: apiData.language || "python",
              vuln_type: apiData.vuln_type || "sqli"
            };
            console.log('Transformed challenge data:', challengeData);
          } else {
            console.error('API response not OK:', response.status, await response.text());
          }
        } catch (apiErr) {
          console.error("Could not fetch from API, using fallback:", apiErr);
        }

        // Fallback challenge if API fails
        if (!challengeData) {
          challengeData = {
            insecure_code: `# views.py (insecure example)
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import connection

@csrf_exempt
def get_user_vulnerable(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    data = json.loads(request.body)
    user_id = data.get("user_id")

    # Dangerous: building SQL by inserting raw user input
    query = f"SELECT id, username, email FROM auth_user WHERE id = {user_id}"

    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    return JsonResponse({"rows": rows})`,
            vulnerable_lines: [16],
            options: [
              { id: "opt1", label: "Lines 12-13 (JSON parsing)", lines: [12, 13] },
              { id: "opt2", label: "Line 16 (SQL query construction)", lines: [16] },
              { id: "opt3", label: "Lines 18-20 (Query execution)", lines: [18, 19, 20] },
              { id: "opt4", label: "Line 8 (Function definition)", lines: [8] },
            ],
            correct_option: "opt2",
            description: "The server parses JSON sent by the client and then directly inserts a field from that JSON into a SQL statement without validation or parameterization. This allows an attacker to inject SQL content through the user_id field."
          };
        }

        setChallengeData(challengeData);
        setLoading(false);

        // Send code to Godot iframe once it's loaded
        // We need to wait a bit for the iframe to be ready
        setTimeout(() => {
          sendCodeToGodot(challengeData.insecure_code);
        }, 1000);

      } catch (err) {
        console.error("Error fetching challenge:", err);
        setLoading(false);
      }
    }

    fetchChallenge();
  }, []);

  // Send code snippet to Godot iframe via postMessage
  const sendCodeToGodot = (code) => {
    console.log('Sending code to Godot:', code?.substring(0, 100) + '...');
    if (iframeRef.current && iframeRef.current.contentWindow) {
      iframeRef.current.contentWindow.postMessage(
        { type: "SET_CODE", code: code },
        "*" // In production, specify the exact origin
      );
      console.log('Code sent to Godot iframe');
    } else {
      console.error('Godot iframe not ready yet');
    }
  };

  // Generate a new challenge using the backend API
  const handleGenerateChallenge = async () => {
    setGenerating(true);
    try {
      // Step 1: Request generation
      const generateResponse = await postWithAuth("/generator/generate/", {});
      if (!generateResponse.ok) {
        throw new Error("Failed to start generation");
      }

      const { generation_id } = await generateResponse.json();
      console.log("Generation started:", generation_id);

      // Step 2: Poll for completion
      let attempts = 0;
      const maxAttempts = 60; // 60 attempts * 2 seconds = 2 minutes max

      while (attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds

        const statusResponse = await getWithAuth(`/generator/generation/${generation_id}/`);
        if (!statusResponse.ok) {
          throw new Error("Failed to check generation status");
        }

        const statusData = await statusResponse.json();
        console.log("Generation status:", statusData.status);

        if (statusData.status === "done" && statusData.challenge_id) {
          // Step 3: Fetch the generated challenge
          const challengeResponse = await getWithAuth(`/generator/challenge/${statusData.challenge_id}/`);
          if (!challengeResponse.ok) {
            throw new Error("Failed to fetch generated challenge");
          }

          const apiData = await challengeResponse.json();

          // Store the new challenge ID
          setCurrentChallengeId(statusData.challenge_id);

          // Transform and set the challenge data
          const correctOptionIndex = apiData.options.findIndex((opt) =>
            JSON.stringify(opt.lines.sort()) === JSON.stringify(apiData.vulnerable_lines.sort())
          );

          const newChallengeData = {
            insecure_code: apiData.insecure_code,
            vulnerable_lines: apiData.vulnerable_lines || [],
            options: apiData.options.map((opt, idx) => ({
              id: `opt${idx + 1}`,
              label: opt.label,
              lines: opt.lines
            })),
            correct_option: correctOptionIndex !== -1 ? `opt${correctOptionIndex + 1}` : 'opt1',
            description: apiData.explanation?.short || apiData.description || "Identify the vulnerable line in the code.",
            language: apiData.language || "python",
            vuln_type: apiData.vuln_type || "sqli"
          };

          setChallengeData(newChallengeData);
          sendCodeToGodot(newChallengeData.insecure_code);
          setGenerating(false);
          alert("New challenge generated successfully!");
          return;
        } else if (statusData.status === "failed") {
          throw new Error(`Generation failed: ${statusData.error || "Unknown error"}`);
        }

        attempts++;
      }

      throw new Error("Generation timed out after 2 minutes");
    } catch (err) {
      console.error("Error generating challenge:", err);
      alert(`Failed to generate challenge: ${err.message}`);
      setGenerating(false);
    }
  };

  async function handleSubmit(e) {
    e.preventDefault();

    if (!selected) {
      setResult({ ok: false, msg: "Please select an option." });
      return;
    }

    if (!challengeData) {
      setResult({ ok: false, msg: "Challenge data not loaded yet." });
      return;
    }

    const isCorrect = selected === challengeData.correct_option;

    // Local feedback first
    if (isCorrect) {
      setResult({
        ok: true,
        msg: "Correct — that's the vulnerable line!",
      });
    } else {
      setResult({
        ok: false,
        msg: "Not correct. Try examining how user input is used in the code.",
      });
    }

    // Now send result to backend (protected endpoint)
    const accessToken = localStorage.getItem("accessToken");
    if (!accessToken) {
      console.warn("No access token found. User is probably not logged in.");
      return;
    }

    try {
      // Determine if this is a generated challenge or a static challenge
      // Generated challenges have IDs, static challenges would use the old system
      const payload = {
        is_correct: isCorrect,
        score: isCorrect ? 1 : 0,
      };

      if (currentChallengeId) {
        // This is a generated challenge
        payload.generated_challenge = currentChallengeId;
      } else {
        // Fallback for static challenges (if any exist)
        payload.challenge = 1;
      }

      const response = await postWithAuth("/results/", payload);

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

  const handleLogout = () => {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    window.location.reload(); // Reload to trigger auth check
  };

  const handleHomeClick = (e) => {
    e.preventDefault();
    navigate("/");
  };

  if (loading) {
    return (
      <div className="page-root">
        <div style={{ padding: "2rem", color: "white" }}>Loading challenge...</div>
      </div>
    );
  }

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

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', maxWidth: '800px', margin: '0 auto 1rem' }}>
        <h1 className="title" style={{ margin: 0 }}>Vulnerability Challenge</h1>
        <button
          onClick={handleGenerateChallenge}
          disabled={generating}
          style={{
            padding: '0.5rem 1rem',
            borderRadius: '8px',
            border: 'none',
            cursor: generating ? 'not-allowed' : 'pointer',
            fontWeight: '600',
            fontSize: '14px',
            background: generating ? '#ccc' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            boxShadow: '0 4px 15px rgba(102, 126, 234, 0.4)',
            opacity: generating ? 0.6 : 1
          }}
        >
          {generating ? 'Generating...' : 'Generate New Challenge'}
        </button>
      </div>

      <div className="instructions">
        <strong>Vulnerability description:</strong> {challengeData?.description || "Loading..."}
      </div>

      {/* Godot window */}
      <div className="godot-window">
        <iframe
          ref={iframeRef}
          src="/godot-build/index.html"
          title="Godot Game"
          width="100%"
          height="100%"
          frameBorder="0"
          style={{ pointerEvents: 'auto' }}
        ></iframe>
      </div>

      <form className="options-form" onSubmit={handleSubmit}>
        <div className="options-list">
          {challengeData?.options?.map((o) => {
            // Format line numbers for display
            const lineDisplay = o.lines && o.lines.length > 0
              ? o.lines.length === 1
                ? `Line ${o.lines[0]}`
                : `Lines ${Math.min(...o.lines)}-${Math.max(...o.lines)}`
              : '';

            return (
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
                <span className="option-label">
                  {lineDisplay && <strong>{lineDisplay}:</strong>} {o.label}
                </span>
              </label>
            );
          })}
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
