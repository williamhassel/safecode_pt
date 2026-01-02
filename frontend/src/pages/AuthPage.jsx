// src/AuthPage.jsx
import { useState } from "react";

const API_BASE = "http://localhost:8000/api"; // change if your backend is hosted elsewhere

export default function AuthPage({ onAuthenticated }) {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState(""); // used only in register mode
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const resetErrors = () => {
    setError("");
  };

  const handleLogin = async () => {
    const res = await fetch(`${API_BASE}/auth/login/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, password }),
    });

    if (!res.ok) {
      const text = await res.text();
      console.error("Login failed:", text);
      throw new Error("Login failed");
    }

    const data = await res.json();
    const { access, refresh } = data;

    localStorage.setItem("accessToken", access);
    localStorage.setItem("refreshToken", refresh);

    if (onAuthenticated) {
      onAuthenticated();
    }
  };

  const handleRegister = async () => {
    // 1) Create user
    const res = await fetch(`${API_BASE}/auth/register/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, email, password }),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      console.error("Register failed:", body);
      const detail =
        body?.username?.[0] ||
        body?.password?.[0] ||
        body?.detail ||
        "Registration failed";
      throw new Error(detail);
    }

    // 2) Immediately log in with same credentials
    await handleLogin();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    resetErrors();
    setLoading(true);

    try {
      if (mode === "login") {
        await handleLogin();
      } else {
        await handleRegister();
      }
    } catch (err) {
      setError(err.message || "Something went wrong");
      setLoading(false);
      return;
    }

    setLoading(false);
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        color: "#ffffff",
        fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 420,
          padding: "2.5rem",
          borderRadius: "1.5rem",
          background: "white",
          boxShadow: "0 24px 70px rgba(0,0,0,0.3)",
          border: "none",
        }}
      >
        <div style={{ marginBottom: "1.5rem", textAlign: "center" }}>
          <h1 style={{ fontSize: "1.8rem", margin: 0, fontWeight: 700, color: "#667eea" }}>
            SafeCode
          </h1>
          <p style={{ marginTop: "0.5rem", color: "#666", fontSize: "0.9rem" }}>
            Log in or create an account to track your secure coding progress
            and certificates.
          </p>
        </div>

        {/* Mode toggle */}
        <div
          style={{
            display: "flex",
            background: "#f8f9fa",
            borderRadius: "999px",
            padding: "0.25rem",
            border: "1px solid #e9ecef",
            marginBottom: "1.5rem",
          }}
        >
          <button
            type="button"
            onClick={() => {
              resetErrors();
              setMode("login");
            }}
            style={{
              flex: 1,
              padding: "0.6rem 0.75rem",
              borderRadius: "999px",
              border: "none",
              cursor: "pointer",
              fontSize: "0.9rem",
              fontWeight: 500,
              background: mode === "login" ? "linear-gradient(135deg, #667eea 0%, #764ba2 100%)" : "transparent",
              color: mode === "login" ? "#ffffff" : "#666",
              transition: "all 0.15s ease-out",
            }}
          >
            Log in
          </button>
          <button
            type="button"
            onClick={() => {
              resetErrors();
              setMode("register");
            }}
            style={{
              flex: 1,
              padding: "0.6rem 0.75rem",
              borderRadius: "999px",
              border: "none",
              cursor: "pointer",
              fontSize: "0.9rem",
              fontWeight: 500,
              background: mode === "register" ? "linear-gradient(135deg, #667eea 0%, #764ba2 100%)" : "transparent",
              color: mode === "register" ? "#ffffff" : "#666",
              transition: "all 0.15s ease-out",
            }}
          >
            Create account
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Username */}
          <div style={{ marginBottom: "0.9rem" }}>
            <label
              style={{
                display: "block",
                marginBottom: "0.25rem",
                fontSize: "0.8rem",
                color: "#333",
                fontWeight: 500,
              }}
            >
              Username
            </label>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              style={{
                width: "100%",
                padding: "0.55rem 0.7rem",
                borderRadius: "0.75rem",
                border: "1px solid #e9ecef",
                background: "#f8f9fa",
                color: "#333",
                fontSize: "0.9rem",
              }}
            />
          </div>

          {/* Email only in register mode */}
          {mode === "register" && (
            <div style={{ marginBottom: "0.9rem" }}>
              <label
                style={{
                  display: "block",
                  marginBottom: "0.25rem",
                  fontSize: "0.8rem",
                  color: "#333",
                  fontWeight: 500,
                }}
              >
                Email (optional)
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={{
                  width: "100%",
                  padding: "0.55rem 0.7rem",
                  borderRadius: "0.75rem",
                  border: "1px solid #e9ecef",
                  background: "#f8f9fa",
                  color: "#333",
                  fontSize: "0.9rem",
                }}
              />
            </div>
          )}

          {/* Password */}
          <div style={{ marginBottom: "0.9rem" }}>
            <label
              style={{
                display: "block",
                marginBottom: "0.25rem",
                fontSize: "0.8rem",
                color: "#333",
                fontWeight: 500,
              }}
            >
              Password
            </label>
            <input
              type="password"
              value={password}
              minLength={8}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={{
                width: "100%",
                padding: "0.55rem 0.7rem",
                borderRadius: "0.75rem",
                border: "1px solid #e9ecef",
                background: "#f8f9fa",
                color: "#333",
                fontSize: "0.9rem",
              }}
            />
            <p
              style={{
                marginTop: "0.25rem",
                fontSize: "0.75rem",
                color: "#666",
              }}
            >
              Minimum 8 characters. Use a strong password if this is used in
              teaching.
            </p>
          </div>

          {/* Error */}
          {error && (
            <div
              style={{
                marginBottom: "0.9rem",
                padding: "0.6rem 0.75rem",
                borderRadius: "0.75rem",
                background: "#f8d7da",
                color: "#721c24",
                fontSize: "0.8rem",
                border: "1px solid #f5c6cb",
              }}
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              padding: "0.7rem 0.75rem",
              borderRadius: "0.9rem",
              border: "none",
              cursor: loading ? "default" : "pointer",
              background: loading ? "linear-gradient(135deg, #5568d3 0%, #63408b 100%)" : "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
              color: "#ffffff",
              fontWeight: 600,
              fontSize: "0.95rem",
              marginTop: "0.3rem",
              boxShadow: "0 4px 15px rgba(102, 126, 234, 0.4)",
              transition: "all 0.3s ease",
            }}
            onMouseEnter={(e) => {
              if (!loading) {
                e.target.style.transform = "translateY(-2px)";
                e.target.style.boxShadow = "0 6px 20px rgba(102, 126, 234, 0.5)";
              }
            }}
            onMouseLeave={(e) => {
              e.target.style.transform = "translateY(0)";
              e.target.style.boxShadow = "0 4px 15px rgba(102, 126, 234, 0.4)";
            }}
          >
            {loading
              ? "Please wait..."
              : mode === "login"
              ? "Log in"
              : "Create account"}
          </button>
        </form>

        <p
          style={{
            marginTop: "1rem",
            fontSize: "0.75rem",
            color: "#666",
            textAlign: "center",
          }}
        >
          This account is only for this training platform – it is not your NTNU
          login.
        </p>
      </div>
    </div>
  );
}
