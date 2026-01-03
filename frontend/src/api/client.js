// src/api/client.js
const API_BASE = "http://localhost:8000/api";
const REFRESH_ENDPOINT = "/auth/refresh/";

async function refreshAccessToken() {
  const refreshToken = localStorage.getItem("refreshToken");
  if (!refreshToken) throw new Error("No refresh token. Please log in again.");

  const res = await fetch(`${API_BASE}${REFRESH_ENDPOINT}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh: refreshToken }),
  });

  if (!res.ok) {
    // Refresh token expired/invalid → user must re-login
    throw new Error("Session expired. Please log in again.");
  }

  const data = await res.json(); // { access: "..." }
  localStorage.setItem("accessToken", data.access);
  return data.access;
}

export async function postWithAuth(endpoint, body) {
  let accessToken = localStorage.getItem("accessToken");
  if (!accessToken) throw new Error("Not authenticated (no access token).");

  // First attempt
  let res = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(body),
  });

  // If access token expired, refresh and retry once
  if (res.status === 401) {
    const text = await res.text();

    // Only attempt refresh for the token-expired case
    if (text.includes("token_not_valid") || text.includes("Token is expired")) {
      accessToken = await refreshAccessToken();

      res = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify(body),
      });
    } else {
      // Other 401 causes (permissions, user inactive, etc.)
      throw new Error(text);
    }
  }

  return res;
}

export async function getWithAuth(endpoint) {
  let accessToken = localStorage.getItem("accessToken");
  if (!accessToken) throw new Error("Not authenticated (no access token).");

  // First attempt
  let res = await fetch(`${API_BASE}${endpoint}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
  });

  // If access token expired, refresh and retry once
  if (res.status === 401) {
    const text = await res.text();

    if (text.includes("token_not_valid") || text.includes("Token is expired")) {
      accessToken = await refreshAccessToken();

      res = await fetch(`${API_BASE}${endpoint}`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
      });
    } else {
      throw new Error(text);
    }
  }

  return res;
}
