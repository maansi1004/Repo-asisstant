import { useState } from "react"

const API = "http://localhost:8000"

export default function AuthPage({ onLogin }) {
  const [mode, setMode] = useState("login") // login | register
  const [form, setForm] = useState({ email: "", password: "", name: "" })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function handleSubmit() {
    setError("")
    setLoading(true)

    const endpoint = mode === "login" ? "/auth/login" : "/auth/register"
    const body = mode === "login"
      ? { email: form.email, password: form.password }
      : { email: form.email, password: form.password, name: form.name }

    try {
      const res = await fetch(`${API}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || "Something went wrong")

      // Store token in localStorage
      localStorage.setItem("code_intel_token", data.token)
      localStorage.setItem("code_intel_user", JSON.stringify(data.user))
      onLogin(data.user, data.token)

    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: "100vh", background: "#080810",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: "'DM Sans','Segoe UI',sans-serif", padding: "1rem"
    }}>
      {/* Background glow */}
      <div style={{
        position: "fixed", inset: 0, pointerEvents: "none",
        background: "radial-gradient(ellipse 70% 50% at 50% 0%, rgba(99,102,241,0.12), transparent)"
      }} />

      <div style={{
        position: "relative", zIndex: 1,
        width: "100%", maxWidth: 420
      }}>
        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: "2rem" }}>
          <div style={{
            width: 48, height: 48, borderRadius: 14, margin: "0 auto 12px",
            background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 24, color: "#fff", fontWeight: 700
          }}>◈</div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "#f1f5f9", margin: 0, letterSpacing: "-0.5px" }}>
            Code Intel
          </h1>
          <p style={{ fontSize: 13, color: "#475569", margin: "4px 0 0" }}>
            Repository Intelligence Platform
          </p>
        </div>

        {/* Card */}
        <div style={{
          background: "rgba(255,255,255,0.03)",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: 16, padding: "2rem"
        }}>
          {/* Mode toggle */}
          <div style={{
            display: "flex", marginBottom: "1.5rem",
            background: "rgba(255,255,255,0.03)",
            borderRadius: 10, padding: 4
          }}>
            {["login", "register"].map(m => (
              <button
                key={m}
                onClick={() => { setMode(m); setError("") }}
                style={{
                  flex: 1, padding: "8px", borderRadius: 8, border: "none",
                  background: mode === m ? "rgba(99,102,241,0.3)" : "transparent",
                  color: mode === m ? "#c7d2fe" : "#475569",
                  cursor: "pointer", fontSize: 13, fontWeight: mode === m ? 600 : 400,
                  transition: "all 0.15s", textTransform: "capitalize"
                }}
              >{m === "login" ? "Sign In" : "Create Account"}</button>
            ))}
          </div>

          {/* Name field (register only) */}
          {mode === "register" && (
            <div style={{ marginBottom: "1rem" }}>
              <label style={{ fontSize: 12, color: "#475569", fontWeight: 600, letterSpacing: "0.06em", display: "block", marginBottom: 6 }}>
                FULL NAME
              </label>
              <input
                value={form.name}
                onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
                placeholder="Your name"
                style={inputStyle}
                onFocus={e => e.target.style.borderColor = "#6366f1"}
                onBlur={e => e.target.style.borderColor = "rgba(255,255,255,0.1)"}
              />
            </div>
          )}

          {/* Email */}
          <div style={{ marginBottom: "1rem" }}>
            <label style={{ fontSize: 12, color: "#475569", fontWeight: 600, letterSpacing: "0.06em", display: "block", marginBottom: 6 }}>
              EMAIL
            </label>
            <input
              type="email"
              value={form.email}
              onChange={e => setForm(p => ({ ...p, email: e.target.value }))}
              placeholder="you@example.com"
              style={inputStyle}
              onKeyDown={e => e.key === "Enter" && handleSubmit()}
              onFocus={e => e.target.style.borderColor = "#6366f1"}
              onBlur={e => e.target.style.borderColor = "rgba(255,255,255,0.1)"}
            />
          </div>

          {/* Password */}
          <div style={{ marginBottom: "1.5rem" }}>
            <label style={{ fontSize: 12, color: "#475569", fontWeight: 600, letterSpacing: "0.06em", display: "block", marginBottom: 6 }}>
              PASSWORD
            </label>
            <input
              type="password"
              value={form.password}
              onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
              placeholder={mode === "register" ? "Min 8 characters" : "Your password"}
              style={inputStyle}
              onKeyDown={e => e.key === "Enter" && handleSubmit()}
              onFocus={e => e.target.style.borderColor = "#6366f1"}
              onBlur={e => e.target.style.borderColor = "rgba(255,255,255,0.1)"}
            />
          </div>

          {/* Error */}
          {error && (
            <div style={{
              padding: "8px 12px", marginBottom: "1rem",
              background: "rgba(239,68,68,0.1)",
              border: "1px solid rgba(239,68,68,0.2)",
              borderRadius: 8, fontSize: 13, color: "#f87171"
            }}>
              {error}
            </div>
          )}

          {/* Submit */}
          <button
            onClick={handleSubmit}
            disabled={loading || !form.email || !form.password}
            style={{
              width: "100%", padding: "11px",
              borderRadius: 10, border: "none",
              background: (loading || !form.email || !form.password)
                ? "rgba(99,102,241,0.25)" : "#6366f1",
              color: (loading || !form.email || !form.password) ? "#475569" : "#fff",
              fontSize: 14, fontWeight: 600, cursor:
                (loading || !form.email || !form.password) ? "not-allowed" : "pointer",
              transition: "all 0.15s"
            }}
          >
            {loading ? "Please wait..." : mode === "login" ? "Sign In" : "Create Account"}
          </button>

          {/* Footer note */}
          <p style={{ fontSize: 12, color: "#334155", textAlign: "center", marginTop: "1rem", marginBottom: 0 }}>
            {mode === "login"
              ? "Don't have an account? "
              : "Already have an account? "}
            <button
              onClick={() => { setMode(mode === "login" ? "register" : "login"); setError("") }}
              style={{ background: "none", border: "none", color: "#6366f1", cursor: "pointer", fontSize: 12, fontWeight: 600 }}
            >
              {mode === "login" ? "Create one" : "Sign in"}
            </button>
          </p>
        </div>

        {/* Skip login note */}
        <p style={{ textAlign: "center", fontSize: 12, color: "#1e293b", marginTop: "1rem" }}>
          Authentication is optional — data stored locally
        </p>
      </div>
    </div>
  )
}

const inputStyle = {
  width: "100%", padding: "10px 12px", borderRadius: 8,
  border: "1px solid rgba(255,255,255,0.1)",
  background: "rgba(255,255,255,0.04)",
  color: "#f1f5f9", fontSize: 14, outline: "none",
  boxSizing: "border-box", transition: "border-color 0.15s"
}
