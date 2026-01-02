import React, { useState, useEffect } from "react";
import { postWithAuth } from "../api/client";
import "./HomePage.css";

const API_BASE = "http://localhost:8000/api";

export default function HomePage() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const accessToken = localStorage.getItem("accessToken");
      if (!accessToken) {
        setError("Not authenticated");
        setLoading(false);
        return;
      }

      const response = await fetch(`${API_BASE}/stats/`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch stats");
      }

      const data = await response.json();
      setStats(data);
    } catch (err) {
      console.error("Error fetching stats:", err);
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

  const progressPercentage = stats
    ? Math.min((stats.correct_answers / 8) * 100, 100)
    : 0;

  const questionsRemaining = stats ? Math.max(8 - stats.correct_answers, 0) : 8;

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
                {stats?.correct_answers || 0} / 8 correct
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
                {questionsRemaining > 0 ? (
                  <p>
                    Get {questionsRemaining} more correct answer
                    {questionsRemaining !== 1 ? "s" : ""} to earn your certificate!
                  </p>
                ) : (
                  <p>
                    You have {stats?.correct_answers || 0} correct answers. Keep
                    practicing to maintain 80% accuracy over 10 questions!
                  </p>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="action-section">
          <button onClick={handlePlayGame} className="play-btn">
            Continue Training
          </button>
        </div>
      </div>
    </div>
  );
}