import { useState, useRef, useEffect } from "react"
import DiagramViewer from "./DiagramViewer"
import ChatPanel from "./ChatPanel"
import GitIntelPanel from "./GitPanel"
import AuthPage from "./AuthPage"

const API = "http://localhost:8000"

const FEATURES = [
  {
    id: "summary", icon: "◈", title: "Repository Summary",
    description: "Auto-detects tech stack, architecture patterns, main features, and entry points.",
    endpoint: "/summary", color: "#3b82f6", glow: "rgba(59,130,246,0.12)"
  },
  {
    id: "security", icon: "⬡", title: "Security Scanner",
    description: "Finds hardcoded secrets, SQL injection risks, missing .env files, weak hashing.",
    endpoint: "/security", color: "#ef4444", glow: "rgba(239,68,68,0.12)"
  },
  {
    id: "dependencies", icon: "⬢", title: "Dependency Detection",
    description: "Identifies 50+ frameworks across frontend, backend, database, auth, deployment.",
    endpoint: "/dependencies", color: "#10b981", glow: "rgba(16,185,129,0.12)"
  },
  {
    id: "onboard", icon: "◎", title: "Onboarding Assistant",
    description: "Day-by-day learning path for new developers — prerequisites, key files, first tasks.",
    endpoint: "/onboard", color: "#f59e0b", glow: "rgba(245,158,11,0.12)"
  },
  {
    id: "diagram", icon: "◇", title: "Architecture Diagram",
    description: "Generates Mermaid diagrams with actual filenames grouped by layer.",
    endpoint: "/diagram", color: "#8b5cf6", glow: "rgba(139,92,246,0.12)", isDiagram: true
  },
  {
    id: "qa", icon: "◉", title: "Codebase Q&A",
    description: "Semantic search with conversation memory. Ask in plain English, get cited answers.",
    color: "#06b6d4", glow: "rgba(6,182,212,0.12)", isQA: true
  },
  {
    id: "git", icon: "⌥", title: "Git Intelligence",
    description: "File churn, ownership, coupling, risk ranking — from actual commit history.",
    color: "#f97316", glow: "rgba(249,115,22,0.12)", isGit: true,
    badge: "V3"
  },
]
function AppWithAuth() {
  const [user, setUser] = useState(null)
  const [authChecked, setAuthChecked] = useState(false)

  useEffect(() => {
    const savedToken = localStorage.getItem("code_intel_token")
    const savedUser = localStorage.getItem("code_intel_user")
    if (savedToken && savedUser) {
      try { setUser(JSON.parse(savedUser)) }
      catch (e) { localStorage.removeItem("code_intel_user") }
    }
    setAuthChecked(true)
  }, [])

  if (!authChecked) return null
  if (!user) return <AuthPage onLogin={(u) => setUser(u)} />
  return <App user={user} onLogout={() => {
    localStorage.removeItem("code_intel_token")
    localStorage.removeItem("code_intel_user")
    setUser(null)
  }} />
}

function App({ user, onLogout })  {
  const [repoInfo, setRepoInfo] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState("")
  const [dragOver, setDragOver] = useState(false)
  const [githubUrl, setGithubUrl] = useState("")
  const [activeFeature, setActiveFeature] = useState(null)
  const [featureData, setFeatureData] = useState({})
  const [featureLoading, setFeatureLoading] = useState({})
  const [mounted, setMounted] = useState(false)
  const [gitAvailable, setGitAvailable] = useState(false)
  const fileRef = useRef()

  useEffect(() => { setTimeout(() => setMounted(true), 80) }, [])

  useEffect(() => {
    async function checkExistingSession() {
      try {
        const res = await fetch(`${API}/status`)
        const data = await res.json()
        if (data.repo_loaded && data.total_files > 0) {
          setRepoInfo({
            total_files: data.total_files,
            total_chunks: data.total_chunks,
            files: [],
            source: data.source || "restored"
          })
          setGitAvailable(data.git_available || false)
          console.log("Session restored from previous upload")
        }
      } catch (e) {
        console.log("No existing session")
      }
    }

    checkExistingSession()
  }, [])

  useEffect(() => {
    async function checkExistingSession() {
        try {
            const savedToken = localStorage.getItem("code_intel_token")
            const savedUser = localStorage.getItem("code_intel_user")
            
            if (savedToken && savedUser) {
                const userData = JSON.parse(savedUser)
                setToken(savedToken)
                setUser(userData)
                
                // Check if backend has data for THIS user
                const res = await fetch(`${API}/status`, {
                    headers: { "Authorization": `Bearer ${savedToken}` }
                })
                const data = await res.json()
                if (data.repo_loaded) {
                    setRepoInfo({
                        total_files: data.total_files,
                        total_chunks: data.total_chunks,
                        files: [],
                        source: data.source || "restored"
                    })
                }
            }
        } catch (e) {
            console.log("No existing session")
        }
    }
    checkExistingSession()
}, [])
  async function handleZipUpload(file) {
    if (!file || !file.name.endsWith(".zip")) {
      setUploadError("Please select a .zip file")
      return
    }
    setUploading(true)
    setUploadError("")
    setRepoInfo(null)
    setFeatureData({})
    setActiveFeature(null)
    setGitAvailable(false)

    const form = new FormData()
    form.append("file", file)

    try {
      const res = await fetch(`${API}/upload`, { method: "POST", body: form })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || "Upload failed")
      setRepoInfo({ ...data, source: "zip" })
    } catch (e) {
      setUploadError(e.message)
    } finally {
      setUploading(false)
    }
  }

  async function handleGithubUpload() {
    if (!githubUrl.trim()) return
    if (!githubUrl.startsWith("https://github.com/")) {
      setUploadError("Please enter a valid GitHub URL")
      return
    }
    setUploading(true)
    setUploadError("")
    setRepoInfo(null)
    setFeatureData({})
    setActiveFeature(null)
    setGitAvailable(false)

    try {
      const res = await fetch(`${API}/upload/github`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: githubUrl.trim() })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || "Clone failed")
      setRepoInfo({ ...data, source: "github" })
      setGitAvailable(data.git_available !== false)
    } catch (e) {
      setUploadError(e.message)
    } finally {
      setUploading(false)
    }
  }

  async function loadFeature(feature) {
    if (feature.isQA || feature.isDiagram || feature.isGit) {
      setActiveFeature(feature.id)
      return
    }
    setActiveFeature(feature.id)
    if (featureData[feature.id]) return
    setFeatureLoading(p => ({ ...p, [feature.id]: true }))
    try {
      const res = await fetch(`${API}${feature.endpoint}`)
      const data = await res.json()
      setFeatureData(p => ({ ...p, [feature.id]: data }))
    } catch (e) {
      setFeatureData(p => ({ ...p, [feature.id]: { error: e.message } }))
    } finally {
      setFeatureLoading(p => ({ ...p, [feature.id]: false }))
    }
  }

  function onDrop(e) {
    e.preventDefault()
    setDragOver(false)
    handleZipUpload(e.dataTransfer.files[0])
  }

  const isGitFeature = (f) => f.id === "git"

  return (
    <div style={{
      minHeight: "100vh", background: "#080810",
      color: "#e2e8f0", fontFamily: "'DM Sans','Segoe UI',sans-serif"
    }}>
      {/* Ambient glow */}
      <div style={{
        position: "fixed", inset: 0, pointerEvents: "none", zIndex: 0,
        background: "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99,102,241,0.1), transparent)"
      }} />

      <div style={{ position: "relative", zIndex: 1, maxWidth: 1100, margin: "0 auto", padding: "0 1.5rem" }}>

        {/* Header */}
        <header style={{
  padding: "1.75rem 0 1rem", display: "flex",
  alignItems: "center", justifyContent: "space-between",
  borderBottom: "1px solid rgba(255,255,255,0.05)"
}}>
  {/* Left — logo */}
  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
    <div style={{
      width: 34, height: 34, borderRadius: 9,
      background: "linear-gradient(135deg,#6366f1,#8b5cf6)",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: 16, color: "#fff", fontWeight: 700
    }}>◈</div>
    <div>
      <div style={{ fontSize: 16, fontWeight: 700, color: "#f1f5f9" }}>Code Intel</div>
      <div style={{ fontSize: 10, color: "#334155", letterSpacing: "0.06em" }}>REPOSITORY INTELLIGENCE</div>
    </div>
  </div>

  {/* Right — pill + user menu */}
  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
    <div style={{ fontSize: 11, color: "#334155", padding: "4px 12px", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 20 }}>
      Gemini · ChromaDB · GitPython
    </div>
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ fontSize: 12, color: "#475569" }}>{user?.name}</div>
      <div style={{
        width: 30, height: 30, borderRadius: "50%",
        background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 12, color: "#fff", fontWeight: 700
      }}>
        {user?.name?.[0]?.toUpperCase()}
      </div>
      <button onClick={onLogout} style={{
        fontSize: 12, color: "#475569", background: "none",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 6, padding: "4px 10px", cursor: "pointer"
      }}>
        Sign out
      </button>
    </div>
  </div>
</header>

        {/* Hero */}
        <section style={{
          padding: "3.5rem 0 2.5rem", textAlign: "center",
          opacity: mounted ? 1 : 0, transform: mounted ? "translateY(0)" : "translateY(16px)",
          transition: "all 0.5s ease"
        }}>
          <div style={{
            display: "inline-block", fontSize: 10, fontWeight: 700, letterSpacing: "0.15em",
            color: "#818cf8", padding: "4px 14px", borderRadius: 20,
            border: "1px solid rgba(129,140,248,0.25)", background: "rgba(99,102,241,0.07)",
            marginBottom: "1.25rem"
          }}>
            SEMANTIC RAG · GIT INTELLIGENCE · V3
          </div>

          <h1 style={{
            fontSize: "clamp(2rem,5vw,3.2rem)", fontWeight: 800,
            lineHeight: 1.1, margin: "0 0 1rem", letterSpacing: "-1.5px", color: "#f8fafc"
          }}>
            Chat with your{" "}
            <span style={{ background: "linear-gradient(135deg,#818cf8,#a78bfa,#c084fc)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              code.
            </span>
            <br />
            Understand your{" "}
            <span style={{ background: "linear-gradient(135deg,#38bdf8,#818cf8)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              history.
            </span>
          </h1>

          <p style={{ fontSize: 15, color: "#8b9aad", maxWidth: 500, margin: "0 auto 2.5rem", lineHeight: 1.7 }}>
            Upload any repo via ZIP or GitHub URL. Get instant Q&A, security scans, architecture diagrams, and git-powered intelligence.
          </p>

          {/* Upload zone */}
          <div style={{ maxWidth: 520, margin: "0 auto" }}>

            {/* GitHub URL input */}
            <div style={{
              display: "flex", gap: 8, marginBottom: 12,
              padding: "6px 6px 6px 14px",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 12, background: "rgba(255,255,255,0.03)"
            }}>
              <span style={{ fontSize: 16, display: "flex", alignItems: "center" }}>⌥</span>
              <input
                value={githubUrl}
                onChange={e => setGithubUrl(e.target.value)}
                onKeyDown={e => e.key === "Enter" && !uploading && handleGithubUpload()}
                placeholder="https://github.com/user/repo"
                style={{
                  flex: 1, background: "none", border: "none",
                  color: "#f1f5f9", fontSize: 14, outline: "none"
                }}
              />
              <button
                onClick={handleGithubUpload}
                disabled={uploading || !githubUrl.trim()}
                style={{
                  padding: "8px 16px", borderRadius: 8, border: "none",
                  background: (uploading || !githubUrl.trim()) ? "rgba(99,102,241,0.2)" : "#6366f1",
                  color: (uploading || !githubUrl.trim()) ? "#475569" : "#fff",
                  fontSize: 13, fontWeight: 600,
                  cursor: (uploading || !githubUrl.trim()) ? "not-allowed" : "pointer"
                }}
              >
                {uploading ? "..." : "Analyze →"}
              </button>
            </div>

            {/* Divider */}
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
              <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.06)" }} />
              <span style={{ fontSize: 12, color: "#a6b8d2" }}>or upload ZIP</span>
              <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.06)" }} />
            </div>

            {/* ZIP drop zone */}
            <div
              onClick={() => !uploading && fileRef.current.click()}
              onDragOver={e => { e.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
              style={{
                border: `1.5px dashed ${dragOver ? "#818cf8" : repoInfo ? "#10b981" : "rgba(255,255,255,0.1)"}`,
                borderRadius: 12, padding: "1.5rem",
                cursor: uploading ? "wait" : "pointer",
                background: dragOver ? "rgba(99,102,241,0.06)" : repoInfo ? "rgba(16,185,129,0.04)" : "rgba(255,255,255,0.01)",
                transition: "all 0.2s", textAlign: "center"
              }}
            >
              <input ref={fileRef} type="file" accept=".zip" style={{ display: "none" }}
                onChange={e => handleZipUpload(e.target.files[0])} />

              {uploading ? (
                <div>
                  <MiniSpinner color="#6366f1" size={24} />
                  <p style={{ color: "#818cf8", fontSize: 13, margin: "8px 0 0" }}>
                    {githubUrl ? "Cloning + indexing repo..." : "Indexing repository..."}
                  </p>
                </div>
              ) : repoInfo ? (
                <div>
                  <div style={{ fontSize: 20, marginBottom: 4 }}>✓</div>
                  <p style={{ color: "#10b981", fontWeight: 600, margin: "0 0 2px", fontSize: 14 }}>
                    {repoInfo.total_files} files · {repoInfo.total_chunks} chunks indexed
                    {gitAvailable && <span style={{ color: "#f97316", marginLeft: 8 }}>· Git ✓</span>}
                  </p>
                  <p style={{ color: "#334155", fontSize: 12, margin: 0 }}>
                    {repoInfo.source === "github" ? "📡 GitHub clone" : "📦 ZIP upload"} · Click to change
                  </p>
                </div>
              ) : (
                <div>
                  <div style={{ fontSize: 24, marginBottom: 6, opacity: 0.5 }}>⬆</div>
                  <p style={{ color: "#94a3b8", fontWeight: 500, margin: "0 0 2px", fontSize: 14 }}>Drop .zip here</p>
                  <p style={{ color: "#334155", fontSize: 12, margin: 0 }}>No git history (use URL above for V3)</p>
                </div>
              )}
            </div>
          </div>

          {uploadError && (
            <p style={{ color: "#f87171", fontSize: 13, marginTop: 10 }}>{uploadError}</p>
          )}
        </section>

        {/* Feature cards */}
        <section style={{ paddingBottom: "3rem" }}>
          <div style={{
            fontSize: 10, fontWeight: 700, letterSpacing: "0.12em",
            color: "#334155", marginBottom: "1rem", textTransform: "uppercase"
          }}>
            {repoInfo ? "Intelligence Features" : "What You Get"}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "0.875rem" }}>
            {FEATURES.map((feature, i) => {
              const isLocked = !repoInfo || (isGitFeature(feature) && !gitAvailable)
              const lockReason = isGitFeature(feature) && repoInfo && !gitAvailable
                ? "Requires GitHub URL" : null

              return (
                <FeatureCard
                  key={feature.id}
                  feature={feature}
                  active={activeFeature === feature.id}
                  locked={isLocked}
                  lockReason={lockReason}
                  loading={featureLoading[feature.id]}
                  onClick={() => !isLocked && loadFeature(feature)}
                  delay={i * 50}
                  mounted={mounted}
                />
              )
            })}
          </div>

          {/* Feature panel */}
          {activeFeature && repoInfo && (
            <div style={{
              marginTop: "1.25rem",
              border: "1px solid rgba(255,255,255,0.07)",
              borderRadius: 14, overflow: "hidden",
              background: "rgba(255,255,255,0.015)"
            }}>
              {/* Panel header */}
              <div style={{
                padding: "0.875rem 1.25rem",
                borderBottom: "1px solid rgba(255,255,255,0.05)",
                display: "flex", alignItems: "center", justifyContent: "space-between",
                background: "rgba(255,255,255,0.02)"
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontSize: 18, color: FEATURES.find(f => f.id === activeFeature)?.color }}>
                    {FEATURES.find(f => f.id === activeFeature)?.icon}
                  </span>
                  <span style={{ fontWeight: 600, fontSize: 14, color: "#f1f5f9" }}>
                    {FEATURES.find(f => f.id === activeFeature)?.title}
                  </span>
                  {activeFeature === "git" && (
                    <span style={{
                      fontSize: 10, fontWeight: 700, padding: "1px 6px", borderRadius: 4,
                      background: "rgba(249,115,22,0.15)", color: "#f97316"
                    }}>V3</span>
                  )}
                </div>
                <button onClick={() => setActiveFeature(null)} style={{
                  background: "none", border: "none", color: "#889ab5",
                  cursor: "pointer", fontSize: 18, lineHeight: 1, padding: 4
                }}>×</button>
              </div>

              <div style={{ padding: "1.5rem" }}>
                {activeFeature === "qa" && <ChatPanel repoLoaded={!!repoInfo} />}
                {activeFeature === "diagram" && <DiagramViewer apiBase={API} repoLoaded={!!repoInfo} />}
                {activeFeature === "git" && <GitIntelPanel apiBase={API} />}
                {!["qa", "diagram", "git"].includes(activeFeature) && (
                  <FeatureDataPanel
                    featureId={activeFeature}
                    data={featureData[activeFeature]}
                    loading={featureLoading[activeFeature]}
                  />
                )}
              </div>
            </div>
          )}
        </section>

        {/* File list */}
        {repoInfo && (
          <section style={{ marginBottom: "3rem" }}>
            <details>
              <summary style={{
                cursor: "pointer", fontSize: 11, color: "#889ab5", fontWeight: 600,
                letterSpacing: "0.08em", userSelect: "none", textTransform: "uppercase"
              }}>
                {repoInfo.files?.length} indexed files
              </summary>
              <div style={{
                marginTop: 8, maxHeight: 180, overflowY: "auto",
                background: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(255,255,255,0.05)",
                borderRadius: 10, padding: "0.75rem"
              }}>
                {repoInfo.files?.map(f => (
                  <div key={f} style={{ padding: "2px 0", fontSize: 11, fontFamily: "monospace", color: "#889ab5" }}>{f}</div>
                ))}
              </div>
            </details>
          </section>
        )}
      </div>
    </div>
  )
}

// ── Feature card ──────────────────────────────────────────────

function FeatureCard({ feature, active, locked, lockReason, loading, onClick, delay, mounted }) {
  const [hovered, setHovered] = useState(false)

  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        borderRadius: 12, padding: "1.1rem",
        border: `1px solid ${active ? feature.color + "35" : hovered && !locked ? "rgba(255,255,255,0.1)" : "rgba(255,255,255,0.05)"}`,
        background: active ? feature.glow : hovered && !locked ? "rgba(255,255,255,0.025)" : "rgba(255,255,255,0.015)",
        cursor: locked ? "not-allowed" : "pointer",
        opacity: mounted ? (locked && !lockReason ? 0.35 : locked ? 0.55 : 1) : 0,
        transform: mounted ? "translateY(0)" : "translateY(10px)",
        transition: `all 0.35s ease ${delay}ms`,
        position: "relative", overflow: "hidden"
      }}
    >
      {active && (
        <div style={{
          position: "absolute", top: 0, left: 0, right: 0, height: 2,
          background: `linear-gradient(90deg, transparent, ${feature.color}, transparent)`
        }} />
      )}

      <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
        <div style={{ fontSize: 20, color: feature.color, flexShrink: 0, marginTop: 1 }}>
          {loading ? <MiniSpinner color={feature.color} size={20} /> : feature.icon}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: "#f1f5f9", letterSpacing: "-0.2px" }}>
              {feature.title}
            </span>
            {feature.badge && (
              <span style={{
                fontSize: 9, fontWeight: 700, padding: "1px 5px", borderRadius: 3,
                background: feature.color + "20", color: feature.color
              }}>{feature.badge}</span>
            )}
          </div>
          <div style={{ fontSize: 12, color: "#abbbd2", lineHeight: 1.55 }}>
            {lockReason || feature.description}
          </div>
        </div>
      </div>

      {active && (
        <div style={{
          marginTop: 8, paddingTop: 8,
          borderTop: "1px solid rgba(255,255,255,0.05)",
          fontSize: 10, color: feature.color, fontWeight: 700, letterSpacing: "0.08em"
        }}>▼ OPEN BELOW</div>
      )}
    </div>
  )
}

// ── Feature data renderer ─────────────────────────────────────

function FeatureDataPanel({ featureId, data, loading }) {
  if (loading) return (
    <div style={{ textAlign: "center", padding: "2rem", color: "#bbc8da" }}>
      <MiniSpinner color="#6366f1" size={24} /> <span style={{ marginLeft: 8, fontSize: 13 }}>Loading...</span>
    </div>
  )
  if (!data) return null
  if (data.error) return <p style={{ color: "#f87171", fontSize: 13 }}>Error: {data.error}</p>

  if (featureId === "summary") return <SummaryPanel data={data} />
  if (featureId === "security") return <SecurityPanel data={data} />
  if (featureId === "dependencies") return <DepsPanel data={data} />
  if (featureId === "onboard") return <OnboardPanel data={data} />
  return <pre style={{ fontSize: 11, color: "#a7bad4" }}>{JSON.stringify(data, null, 2)}</pre>
}

function SummaryPanel({ data }) {
  return (
    <div>
      <h2 style={{ fontSize: 18, fontWeight: 700, color: "#f1f5f9", margin: "0 0 4px" }}>{data.project_name}</h2>
      <p style={{ color: "#abbbd2", fontSize: 13, margin: "0 0 1.25rem" }}>{data.one_liner}</p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", marginBottom: "1.25rem" }}>
        {Object.entries(data.tech_stack || {}).map(([cat, techs]) => techs?.length > 0 && (
          <div key={cat} style={{ padding: "0.75rem", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: 8 }}>
            <div style={{ fontSize: 10, color: "#acc0db", fontWeight: 700, letterSpacing: "0.08em", marginBottom: 6, textTransform: "uppercase" }}>{cat}</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
              {techs.map(t => (
                <span key={t} style={{ fontSize: 11, padding: "2px 7px", borderRadius: 4, background: "rgba(99,102,241,0.12)", color: "#818cf8" }}>{t}</span>
              ))}
            </div>
          </div>
        ))}
      </div>
      {data.main_features && (
        <div>
          <div style={{ fontSize: 10, color: "#889ab5", fontWeight: 700, letterSpacing: "0.08em", marginBottom: 8, textTransform: "uppercase" }}>Main Features</div>
          {data.main_features.map((f, i) => (
            <div key={i} style={{ fontSize: 13, color: "#94a3b8", padding: "3px 0", display: "flex", gap: 8 }}>
              <span style={{ color: "#334155" }}>•</span>{f}
            </div>
          ))}
        </div>
      )}
      {data.for_beginners && (
        <div style={{ marginTop: "1rem", padding: "0.75rem 1rem", background: "rgba(16,185,129,0.05)", border: "1px solid rgba(16,185,129,0.12)", borderRadius: 8, fontSize: 13, color: "#6ee7b7" }}>
          💡 {data.for_beginners}
        </div>
      )}
    </div>
  )
}

function SecurityPanel({ data }) {
  const sc = { HIGH: "#ef4444", MEDIUM: "#f59e0b", LOW: "#64748b" }
  const sb = { HIGH: "rgba(239,68,68,0.08)", MEDIUM: "rgba(245,158,11,0.08)", LOW: "rgba(100,116,139,0.08)" }
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1.25rem", flexWrap: "wrap" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 38, fontWeight: 800, color: data.score >= 8 ? "#10b981" : data.score >= 6 ? "#f59e0b" : "#ef4444" }}>{data.score}</div>
          <div style={{ fontSize: 10, color: "#334155" }}>/ 10</div>
        </div>
        <div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#f1f5f9" }}>Grade {data.grade}</div>
          <div style={{ fontSize: 13, color: "#abbbd2" }}>{data.recommendation}</div>
        </div>
        <div style={{ display: "flex", gap: 6, marginLeft: "auto" }}>
          {Object.entries(data.by_severity || {}).map(([sev, count]) => (
            <div key={sev} style={{ padding: "3px 10px", borderRadius: 5, background: sb[sev], color: sc[sev], fontSize: 12, fontWeight: 600 }}>
              {count} {sev}
            </div>
          ))}
        </div>
      </div>
      {data.ok_checks?.map((ok, i) => (
        <div key={i} style={{ fontSize: 13, color: "#10b981", padding: "2px 0", display: "flex", gap: 8 }}>✓ {ok}</div>
      ))}
      <div style={{ marginTop: "1rem", display: "flex", flexDirection: "column", gap: 6 }}>
        {data.issues?.map((issue, i) => (
          <div key={i} style={{ padding: "0.7rem 0.9rem", background: sb[issue.severity], border: `1px solid ${sc[issue.severity]}25`, borderLeft: `3px solid ${sc[issue.severity]}`, borderRadius: 7 }}>
            <div style={{ display: "flex", gap: 8, marginBottom: 3 }}>
              <span style={{ fontSize: 10, fontWeight: 700, color: sc[issue.severity] }}>{issue.severity}</span>
              <span style={{ fontSize: 13, color: "#e2e8f0", fontWeight: 500 }}>{issue.message}</span>
            </div>
            <div style={{ fontSize: 11, color: "#abbdd6", fontFamily: "monospace" }}>{issue.file}{issue.line > 0 ? ` · line ${issue.line}` : ""}</div>
            {issue.evidence && <code style={{ fontSize: 11, color: "#64748b", display: "block", margin: "3px 0" }}>{issue.evidence}</code>}
            <div style={{ fontSize: 11, color: "#334155" }}>Fix: {issue.fix}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function DepsPanel({ data }) {
  const cc = { frontend: "#3b82f6", backend: "#10b981", database: "#f59e0b", auth: "#ef4444", realtime: "#8b5cf6", deployment: "#06b6d4", testing: "#84cc16", devops: "#f97316", ai: "#ec4899", ui: "#a78bfa", config: "#64748b" }
  return (
    <div>
      <div style={{ fontSize: 13, color: "#abbbd2", marginBottom: "1rem" }}>{data.total_detected} dependencies · {data.categories_found?.length} categories</div>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
        {Object.entries(data.dependencies || {}).map(([cat, items]) => (
          <div key={cat}>
            <div style={{ fontSize: 10, color: "#334155", fontWeight: 700, letterSpacing: "0.08em", marginBottom: 5, textTransform: "uppercase" }}>{cat}</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
              {items.map(item => (
                <span key={item} style={{ fontSize: 12, padding: "3px 9px", borderRadius: 5, background: `${cc[cat] || "#475569"}15`, color: cc[cat] || "#94a3b8", border: `1px solid ${cc[cat] || "#475569"}25`, fontWeight: 500 }}>{item}</span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function OnboardPanel({ data }) {
  return (
    <div>
      <p style={{ fontSize: 14, color: "#94a3b8", marginBottom: "1.25rem", lineHeight: 1.7 }}>{data.welcome_message}</p>
      {data.prerequisites?.length > 0 && (
        <div style={{ marginBottom: "1.25rem" }}>
          <SLabel>Prerequisites</SLabel>
          {data.prerequisites.map((p, i) => (
            <div key={i} style={{ padding: "5px 0", fontSize: 13, display: "flex", gap: 8, borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
              <span style={{ color: "#f59e0b", fontWeight: 600 }}>{p.skill}</span>
              <span style={{ color: "#334155" }}>— {p.why}</span>
            </div>
          ))}
        </div>
      )}
      {data.learning_path?.map((day, i) => (
        <div key={i} style={{ marginBottom: 10, padding: "0.7rem 0.9rem", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)", borderLeft: "3px solid #6366f1", borderRadius: 7 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#818cf8", marginBottom: 5 }}>Day {day.day} — {day.title}</div>
          {day.tasks?.map((task, j) => (
            <div key={j} style={{ fontSize: 12, color: "#cfdbec", padding: "2px 0", display: "flex", gap: 6 }}>
              <span>→</span><span><span style={{ color: "#94a3b8" }}>{task.action}</span> — {task.reason}</span>
            </div>
          ))}
        </div>
      ))}
      {data.first_task_suggestion && (
        <div style={{ padding: "0.75rem 1rem", background: "rgba(99,102,241,0.07)", border: "1px solid rgba(99,102,241,0.18)", borderRadius: 9, fontSize: 13, color: "#c7d2fe" }}>
          🎯 <strong>First task:</strong> {data.first_task_suggestion}
        </div>
      )}
    </div>
  )
}

function SLabel({ children }) {
  return <div style={{ fontSize: 10, color: "#334155", fontWeight: 700, letterSpacing: "0.08em", marginBottom: 8, textTransform: "uppercase" }}>{children}</div>
}

function MiniSpinner({ size = 18, color = "#6366f1" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={{ display: "inline-block", verticalAlign: "middle" }}>
      <circle cx="12" cy="12" r="9" stroke={color} strokeWidth="2.5" strokeOpacity="0.2" />
      <path d="M12 3a9 9 0 0 1 9 9" stroke={color} strokeWidth="2.5" strokeLinecap="round">
        <animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="0.7s" repeatCount="indefinite" />
      </path>
    </svg>
  )
}

export default AppWithAuth