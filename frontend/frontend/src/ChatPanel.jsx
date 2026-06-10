import { useState, useRef, useEffect } from "react"

const API = "http://localhost:8000"

const SUGGESTED = [
  "Where is authentication handled?",
  "What should a new developer read first?",
  "What are the main modules?",
  "Explain the data flow from input to output",
  "Which files are most complex?",
  "How does the database connect?",
]

export default function ChatPanel({ repoLoaded }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const bottomRef = useRef()
  const inputRef = useRef()

  // Scroll to bottom on new message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Clear chat when repo changes
  useEffect(() => {
    if (!repoLoaded) {
      setMessages([])
    }
  }, [repoLoaded])

  async function sendQuestion(question) {
    if (!question.trim() || loading) return
    setInput("")
    setError("")

    // Add user message immediately
    setMessages(prev => [...prev, {
      role: "user",
      content: question,
      id: Date.now()
    }])

    setLoading(true)

    try {
      const res = await fetch(`${API}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || "Something went wrong")

      // Add assistant message
      setMessages(prev => [...prev, {
        role: "assistant",
        content: data,
        id: Date.now() + 1
      }])

    } catch (e) {
      setError(e.message)
      // Remove the user message if request failed
      setMessages(prev => prev.slice(0, -1))
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  async function clearHistory() {
    await fetch(`${API}/history`, { method: "DELETE" })
    setMessages([])
  }

  const hasMessages = messages.length > 0

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>

      {/* Chat messages area */}
      <div style={{
        flex: 1,
        overflowY: "auto",
        padding: hasMessages ? "1rem" : "0",
        display: "flex",
        flexDirection: "column",
        gap: "1.25rem",
        minHeight: hasMessages ? 300 : 0,
        maxHeight: 600,
      }}>

        {/* Empty state — suggested questions */}
        {!hasMessages && (
          <div>
            <p style={{ fontSize: 13, color: "#475569", marginBottom: 10 }}>
              Suggested questions:
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {SUGGESTED.map(q => (
                <button
                  key={q}
                  onClick={() => sendQuestion(q)}
                  disabled={!repoLoaded}
                  style={{
                    fontSize: 12, padding: "6px 12px", borderRadius: 20,
                    border: "1px solid rgba(255,255,255,0.1)",
                    background: "rgba(255,255,255,0.04)",
                    cursor: repoLoaded ? "pointer" : "not-allowed",
                    color: repoLoaded ? "#94a3b8" : "#334155",
                    transition: "all 0.15s"
                  }}
                  onMouseOver={e => {
                    if (repoLoaded) {
                      e.currentTarget.style.borderColor = "#818cf8"
                      e.currentTarget.style.color = "#c7d2fe"
                    }
                  }}
                  onMouseOut={e => {
                    e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)"
                    e.currentTarget.style.color = repoLoaded ? "#94a3b8" : "#334155"
                  }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Message list */}
        {messages.map((msg) => (
          <div key={msg.id}>
            {msg.role === "user" ? (
              <UserMessage content={msg.content} />
            ) : (
              <AssistantMessage
                data={msg.content}
                onFollowUp={sendQuestion}
              />
            )}
          </div>
        ))}

        {/* Loading indicator */}
        {loading && (
          <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
            <BotAvatar />
            <div style={{
              padding: "10px 14px",
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: "4px 12px 12px 12px",
              display: "flex", gap: 4, alignItems: "center"
            }}>
              <ThinkingDots />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Error */}
      {error && (
        <div style={{
          margin: "0.5rem 0",
          padding: "8px 12px",
          background: "rgba(239,68,68,0.1)",
          border: "1px solid rgba(239,68,68,0.2)",
          borderRadius: 8,
          fontSize: 13,
          color: "#f87171"
        }}>
          {error}
        </div>
      )}

      {/* Input area */}
      <div style={{
        borderTop: hasMessages ? "1px solid rgba(255,255,255,0.06)" : "none",
        paddingTop: hasMessages ? "1rem" : 0,
        marginTop: hasMessages ? "0.5rem" : 0
      }}>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && !e.shiftKey && sendQuestion(input)}
            placeholder={repoLoaded ? "Ask anything about this codebase..." : "Upload a repo first"}
            disabled={!repoLoaded || loading}
            style={{
              flex: 1, padding: "10px 14px", borderRadius: 10,
              border: "1px solid rgba(255,255,255,0.1)",
              background: repoLoaded ? "rgba(255,255,255,0.05)" : "rgba(255,255,255,0.02)",
              color: "#f1f5f9", fontSize: 14, outline: "none",
              transition: "border-color 0.15s"
            }}
            onFocus={e => e.target.style.borderColor = "#6366f1"}
            onBlur={e => e.target.style.borderColor = "rgba(255,255,255,0.1)"}
          />
          <button
            onClick={() => sendQuestion(input)}
            disabled={!repoLoaded || loading || !input.trim()}
            style={{
              padding: "10px 18px", borderRadius: 10, border: "none",
              background: (!repoLoaded || loading || !input.trim())
                ? "rgba(99,102,241,0.2)" : "#6366f1",
              color: (!repoLoaded || loading || !input.trim()) ? "#475569" : "#fff",
              fontWeight: 600, fontSize: 14,
              cursor: (!repoLoaded || loading || !input.trim()) ? "not-allowed" : "pointer",
              transition: "all 0.15s", minWidth: 70
            }}
          >
            {loading ? "..." : "Ask"}
          </button>
        </div>

        {/* Clear history button */}
        {hasMessages && (
          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 6 }}>
            <button
              onClick={clearHistory}
              style={{
                fontSize: 11, color: "#334155", background: "none",
                border: "none", cursor: "pointer", padding: "2px 4px"
              }}
              onMouseOver={e => e.target.style.color = "#64748b"}
              onMouseOut={e => e.target.style.color = "#334155"}
            >
              Clear conversation
            </button>
          </div>
        )}
      </div>
    </div>
  )
}


function UserMessage({ content }) {
  return (
    <div style={{ display: "flex", justifyContent: "flex-end" }}>
      <div style={{
        maxWidth: "80%",
        padding: "10px 14px",
        background: "rgba(99,102,241,0.2)",
        border: "1px solid rgba(99,102,241,0.3)",
        borderRadius: "12px 4px 12px 12px",
        fontSize: 14, color: "#c7d2fe", lineHeight: 1.6
      }}>
        {content}
      </div>
    </div>
  )
}


function AssistantMessage({ data, onFollowUp }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
      <BotAvatar />

      <div style={{ flex: 1, minWidth: 0 }}>

        {/* Direct answer — always visible */}
        {data.direct_answer && (
          <div style={{
            fontSize: 14, fontWeight: 600, color: "#c7d2fe",
            marginBottom: 8, lineHeight: 1.5
          }}>
            {data.direct_answer}
          </div>
        )}

        {/* Main explanation */}
        <div style={{
          fontSize: 13, color: "#94a3b8", lineHeight: 1.8,
          whiteSpace: "pre-wrap",
          maxHeight: expanded ? "none" : 200,
          overflow: expanded ? "visible" : "hidden",
          position: "relative"
        }}>
          {data.answer}
          {!expanded && data.answer?.length > 400 && (
            <div style={{
              position: "absolute", bottom: 0, left: 0, right: 0,
              height: 60,
              background: "linear-gradient(transparent, #080810)"
            }} />
          )}
        </div>

        {/* Show more/less */}
        {data.answer?.length > 400 && (
          <button
            onClick={() => setExpanded(!expanded)}
            style={{
              fontSize: 12, color: "#6366f1", background: "none",
              border: "none", cursor: "pointer", padding: "4px 0",
              marginTop: 4
            }}
          >
            {expanded ? "Show less ▲" : "Show more ▼"}
          </button>
        )}

        {/* Code evidence */}
        {data.code_evidence && data.code_evidence.length > 0 && (
          <div style={{ marginTop: 10 }}>
            {data.code_evidence.slice(0, 2).map((ev, i) => (
              <pre key={i} style={{
                margin: "0 0 6px",
                padding: "8px 12px",
                background: "rgba(0,0,0,0.4)",
                border: "1px solid rgba(255,255,255,0.06)",
                borderRadius: 8,
                fontSize: 11, color: "#64748b",
                overflowX: "auto",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word"
              }}>
                {ev}
              </pre>
            ))}
          </div>
        )}

        {/* Files used */}
        {data.files_used && data.files_used.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 8 }}>
            {data.files_used.map(f => (
              <span key={f} style={{
                fontSize: 11, padding: "2px 7px", borderRadius: 4,
                background: "rgba(99,102,241,0.12)",
                color: "#818cf8", fontFamily: "monospace"
              }}>
                {f.split("\\").pop().split("/").pop()}
              </span>
            ))}
          </div>
        )}

        {/* Confidence badge */}
        {data.confidence && (
          <div style={{ marginTop: 8 }}>
            <span style={{
              fontSize: 10, fontWeight: 600, letterSpacing: "0.08em",
              padding: "2px 7px", borderRadius: 4,
              background: data.confidence === "high"
                ? "rgba(16,185,129,0.1)"
                : data.confidence === "medium"
                  ? "rgba(245,158,11,0.1)"
                  : "rgba(239,68,68,0.1)",
              color: data.confidence === "high"
                ? "#10b981"
                : data.confidence === "medium"
                  ? "#f59e0b"
                  : "#ef4444"
            }}>
              {data.confidence.toUpperCase()} CONFIDENCE
            </span>
          </div>
        )}

        {/* Follow-up questions */}
        {data.follow_up_questions && data.follow_up_questions.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <div style={{
              fontSize: 10, color: "#334155", fontWeight: 600,
              letterSpacing: "0.08em", marginBottom: 6
            }}>
              EXPLORE FURTHER
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {data.follow_up_questions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => onFollowUp(q)}
                  style={{
                    fontSize: 12, padding: "6px 10px",
                    borderRadius: 6, textAlign: "left",
                    border: "1px solid rgba(255,255,255,0.06)",
                    background: "rgba(255,255,255,0.02)",
                    color: "#64748b", cursor: "pointer",
                    transition: "all 0.15s"
                  }}
                  onMouseOver={e => {
                    e.currentTarget.style.borderColor = "#6366f1"
                    e.currentTarget.style.color = "#818cf8"
                    e.currentTarget.style.background = "rgba(99,102,241,0.06)"
                  }}
                  onMouseOut={e => {
                    e.currentTarget.style.borderColor = "rgba(255,255,255,0.06)"
                    e.currentTarget.style.color = "#64748b"
                    e.currentTarget.style.background = "rgba(255,255,255,0.02)"
                  }}
                >
                  → {q}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}


function BotAvatar() {
  return (
    <div style={{
      width: 28, height: 28, borderRadius: 8, flexShrink: 0,
      background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: 13, color: "#fff", fontWeight: 700, marginTop: 2
    }}>
      ◈
    </div>
  )
}


function ThinkingDots() {
  return (
    <div style={{ display: "flex", gap: 4, alignItems: "center", padding: "4px 2px" }}>
      {[0, 1, 2].map(i => (
        <div key={i} style={{
          width: 6, height: 6, borderRadius: "50%",
          background: "#475569",
          animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`
        }} />
      ))}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.3; transform: scale(0.8); }
          50% { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </div>
  )
}
