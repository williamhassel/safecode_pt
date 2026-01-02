// src/api/auth.js
export async function getValidAccessToken() {
  const access = localStorage.getItem("accessToken");
  const refresh = localStorage.getItem("refreshToken");

  if (!access || !refresh) throw new Error("Not authenticated");
  return access;
}