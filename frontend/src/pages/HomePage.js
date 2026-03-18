import React, { useState, useEffect } from "react";
import { getWithAuth } from "../api/client";
import "./HomePage.css";

export default function HomePage() {
  const [stats, setStats] = useState(null);
  const [isStaff, setIsStaff] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [statsRes, meRes] = await Promise.all([
        getWithAuth("/stats/"),
        getWithAuth("/auth/me/"),
      ]);

      if (!statsRes.ok) throw new Error("Failed to fetch stats");
      const data = await statsRes.json();
      setStats(data);

      if (meRes.ok) {
        const me = await meRes.json();
        setIsStaff(!!me.is_staff);
      }
    } catch (err) {
      console.error("Error fetching data:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    window.location.reload();
  };

  const handlePlayGame = () => {
    window.location.href = "/game";
  };

  if (loading) {
    return (
      <div className="home-page">
        <div className="loading">Loading your progress...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="home-page">
        <div className="error">Error: {error}</div>
      </div>
    );
  }

  const REQUIRED_SETS = 10;
  const completedSets = stats?.completed_sets || 0;
  const setsRemaining = Math.max(REQUIRED_SETS - completedSets, 0);
  const progressPercentage = Math.min((completedSets / REQUIRED_SETS) * 100, 100);

  return (
    <div className="home-page">
      <nav className="top-nav">
        <h1 className="app-title">SafeCode Training</h1>
        <button onClick={handleLogout} className="logout-btn">
          Logout
        </button>
      </nav>

      <div className="home-content">
        <div className="welcome-section">
          <h2>Welcome Back!</h2>
          <p>Track your progress towards earning your security training certificate.</p>
        </div>

        <div className="progress-card">
          <h3>Your Progress</h3>

          <div className="stats-grid">
            <div className="stat-item">
              <div className="stat-value">{stats?.total_answered || 0}</div>
              <div className="stat-label">Total Answered</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{stats?.correct_answers || 0}</div>
              <div className="stat-label">Correct Answers</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">
                {stats?.accuracy ? (stats.accuracy * 100).toFixed(1) : 0}%
              </div>
              <div className="stat-label">Accuracy</div>
            </div>
          </div>

          <div className="progress-section">
            <div className="progress-header">
              <h4>Certificate Progress</h4>
              <span className="progress-text">
                {completedSets} / {REQUIRED_SETS} sets completed
              </span>
            </div>
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${progressPercentage}%` }}
              ></div>
            </div>
            {stats?.has_certificate ? (
              <div className="certificate-badge">
                <span className="badge-icon">🎓</span>
                <span className="badge-text">Certificate Earned!</span>
              </div>
            ) : (
              <div className="progress-info">
                <p>
                  {setsRemaining > 0
                    ? `Complete ${setsRemaining} more set${setsRemaining !== 1 ? "s" : ""} (80%+ correct each) to earn your certificate!`
                    : "You've completed all required sets — your certificate should be issued!"}
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="action-section">
          <button onClick={handlePlayGame} className="play-btn">
            Continue Training
          </button>
          {isStaff && (
            <button
              onClick={() => { window.location.href = "/admin-review"; }}
              className="play-btn"
              style={{ marginTop: "0.75rem", background: "linear-gradient(135deg, #1a1a2e, #0f3460)" }}
            >
              Review Challenge Queue (Admin)
            </button>
          )}
        </div>
      </div>
    </div>
  );
}