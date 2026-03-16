import { useState, useEffect, useRef, useCallback } from "react";

// ── WebSocket Hook ────────────────────────────────────────────────────────────
function useGestureSocket(url) {
  const [state, setState] = useState({
    gesture: "none", active: false, fps: 5,
    cursor_x: 0, cursor_y: 0, scroll_delta: 0,
    engineConnected: false,
  });
  const [log, setLog] = useState([]);
  const wsRef = useRef(null);

  const addLog = useCallback((msg, type = "info") => {
    const entry = { id: Date.now() + Math.random(), msg, type, time: new Date().toLocaleTimeString() };
    setLog(prev => [entry, ...prev].slice(0, 40));
  }, []);

  const sendCommand = useCallback((action) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action }));
    }
  }, []);

  useEffect(() => {
    function connect() {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => addLog("Connected to GestureOS backend", "success");

      ws.onmessage = (e) => {
        const data = JSON.parse(e.data);

        if (data.type === "init") {
          setState(prev => ({ ...prev, engineConnected: data.engineConnected, ...data.state }));
          addLog(`Engine ${data.engineConnected ? "online ✓" : "offline"}`, data.engineConnected ? "success" : "warn");
        } else if (data.type === "gesture_state") {
          setState(prev => ({ ...prev, ...data, engineConnected: true }));
          if (data.gesture && data.gesture !== "none") {
            addLog(`Gesture: ${data.gesture}`, "gesture");
          }
        } else if (data.type === "engine_connected") {
          setState(prev => ({ ...prev, engineConnected: true }));
          addLog("Python engine connected", "success");
        } else if (data.type === "engine_disconnected") {
          setState(prev => ({ ...prev, engineConnected: false, active: false }));
          addLog("Python engine disconnected", "error");
        } else if (data.type === "control") {
          setState(prev => ({ ...prev, active: data.active }));
          addLog(`Gesture control ${data.active ? "ENABLED" : "DISABLED"}`, data.active ? "success" : "warn");
        }
      };

      ws.onclose = () => {
        addLog("Disconnected — retrying...", "error");
        setTimeout(connect, 3000);
      };
    }

    connect();
    return () => wsRef.current?.close();
  }, [url, addLog]);

  return { state, log, sendCommand };
}

// ── Gesture Icons ─────────────────────────────────────────────────────────────
const GESTURE_MAP = {
  none:        { icon: "✋", label: "Idle",        color: "#4a5568" },
  move:        { icon: "☝️",  label: "Move Cursor", color: "#38bdf8" },
  left_click:  { icon: "🤌", label: "Left Click",  color: "#34d399" },
  right_click: { icon: "🤏", label: "Right Click", color: "#f59e0b" },
  scroll:      { icon: "🤞", label: "Scroll",      color: "#a78bfa" },
};

// ── Components ────────────────────────────────────────────────────────────────
function StatusPill({ connected }) {
  return (
    <div style={{
      display: "inline-flex", alignItems: "center", gap: "6px",
      padding: "4px 12px", borderRadius: "99px",
      background: connected ? "rgba(52,211,153,0.12)" : "rgba(248,113,113,0.12)",
      border: `1px solid ${connected ? "#34d399" : "#f87171"}`,
      fontSize: "11px", fontWeight: 600, letterSpacing: "0.08em",
      color: connected ? "#34d399" : "#f87171",
      textTransform: "uppercase",
    }}>
      <span style={{
        width: "6px", height: "6px", borderRadius: "50%",
        background: connected ? "#34d399" : "#f87171",
        boxShadow: connected ? "0 0 8px #34d399" : "none",
        animation: connected ? "pulse 2s infinite" : "none",
      }} />
      {connected ? "Engine Online" : "Engine Offline"}
    </div>
  );
}

function GestureCard({ gesture, active }) {
  const info = GESTURE_MAP[gesture] || GESTURE_MAP["none"];
  return (
    <div style={{
      background: "rgba(255,255,255,0.04)",
      border: `1px solid ${active && gesture !== "none" ? info.color + "44" : "rgba(255,255,255,0.08)"}`,
      borderRadius: "16px",
      padding: "24px",
      display: "flex", flexDirection: "column", alignItems: "center", gap: "10px",
      transition: "all 0.2s ease",
      boxShadow: active && gesture !== "none" ? `0 0 24px ${info.color}22` : "none",
    }}>
      <span style={{ fontSize: "40px", lineHeight: 1 }}>{info.icon}</span>
      <div style={{ fontSize: "11px", letterSpacing: "0.1em", textTransform: "uppercase", color: "#64748b" }}>Active Gesture</div>
      <div style={{ fontSize: "18px", fontWeight: 700, color: info.color, fontFamily: "'Space Mono', monospace" }}>
        {info.label}
      </div>
    </div>
  );
}

function MetricBox({ label, value, unit = "", accent = "#38bdf8" }) {
  return (
    <div style={{
      background: "rgba(255,255,255,0.03)",
      border: "1px solid rgba(255,255,255,0.07)",
      borderRadius: "12px",
      padding: "16px 20px",
    }}>
      <div style={{ fontSize: "10px", letterSpacing: "0.12em", textTransform: "uppercase", color: "#475569", marginBottom: "6px" }}>{label}</div>
      <div style={{ fontSize: "22px", fontWeight: 700, color: accent, fontFamily: "'Space Mono', monospace" }}>
        {value}<span style={{ fontSize: "12px", color: "#64748b", marginLeft: "4px" }}>{unit}</span>
      </div>
    </div>
  );
}

function LogPanel({ log }) {
  const typeColors = { info: "#94a3b8", success: "#34d399", error: "#f87171", warn: "#f59e0b", gesture: "#a78bfa" };
  return (
    <div style={{
      background: "rgba(0,0,0,0.3)",
      border: "1px solid rgba(255,255,255,0.06)",
      borderRadius: "16px",
      padding: "16px",
      height: "220px",
      overflowY: "auto",
      fontFamily: "'Space Mono', monospace",
      fontSize: "12px",
    }}>
      <div style={{ color: "#475569", fontSize: "10px", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: "10px" }}>
        ▸ System Log
      </div>
      {log.length === 0 && <div style={{ color: "#334155" }}>Waiting for events...</div>}
      {log.map(entry => (
        <div key={entry.id} style={{ display: "flex", gap: "10px", marginBottom: "4px", lineHeight: "1.6" }}>
          <span style={{ color: "#334155", flexShrink: 0 }}>{entry.time}</span>
          <span style={{ color: typeColors[entry.type] || "#94a3b8" }}>{entry.msg}</span>
        </div>
      ))}
    </div>
  );
}

function GestureLegend() {
  const gestures = [
    { gesture: "move",        desc: "Raise only index finger — moves cursor" },
    { gesture: "left_click",  desc: "Pinch thumb + index together" },
    { gesture: "right_click", desc: "Pinch thumb + middle finger" },
    { gesture: "scroll",      desc: "Index + middle close, move up/down" },
  ];
  return (
    <div style={{
      background: "rgba(255,255,255,0.02)",
      border: "1px solid rgba(255,255,255,0.06)",
      borderRadius: "16px",
      padding: "20px",
    }}>
      <div style={{ color: "#475569", fontSize: "10px", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: "14px" }}>
        ▸ Gesture Reference
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        {gestures.map(({ gesture, desc }) => {
          const info = GESTURE_MAP[gesture];
          return (
            <div key={gesture} style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <span style={{ fontSize: "20px", width: "28px", textAlign: "center" }}>{info.icon}</span>
              <div>
                <div style={{ fontSize: "12px", fontWeight: 600, color: info.color }}>{info.label}</div>
                <div style={{ fontSize: "11px", color: "#475569" }}>{desc}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const WS_URL = "ws://localhost:5000/ws";
  const { state, log, sendCommand } = useGestureSocket(WS_URL);
  const [inactiveCountdown, setInactiveCountdown] = useState(60);

  // Countdown to inactive
  useEffect(() => {
    if (!state.active) { setInactiveCountdown(60); return; }
    const iv = setInterval(() => setInactiveCountdown(p => Math.max(0, p - 1)), 1000);
    return () => clearInterval(iv);
  }, [state.active, state.gesture]);

  // Reset countdown on gesture
  useEffect(() => {
    if (state.gesture !== "none") setInactiveCountdown(60);
  }, [state.gesture]);

  const handleToggle = () => {
    sendCommand(state.active ? "disable" : "enable");
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "#080c14",
      color: "#e2e8f0",
      fontFamily: "'DM Sans', sans-serif",
      padding: "32px",
      backgroundImage: `
        radial-gradient(ellipse 80% 40% at 50% -10%, rgba(56,189,248,0.08) 0%, transparent 70%),
        radial-gradient(ellipse 40% 30% at 80% 80%, rgba(167,139,250,0.06) 0%, transparent 60%)
      `,
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 4px; }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        @keyframes fadeIn { from{opacity:0;transform:translateY(6px)} to{opacity:1;transform:translateY(0)} }
        .toggle-btn:hover { filter: brightness(1.15); transform: scale(1.02); }
        .toggle-btn:active { transform: scale(0.98); }
      `}</style>

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "32px" }}>
        <div>
          <div style={{ fontSize: "11px", letterSpacing: "0.2em", textTransform: "uppercase", color: "#38bdf8", marginBottom: "6px" }}>
            GestureOS
          </div>
          <h1 style={{ fontSize: "28px", fontWeight: 700, letterSpacing: "-0.02em", lineHeight: 1.1 }}>
            Gesture Control<br />
            <span style={{ color: "#334155" }}>Dashboard</span>
          </h1>
        </div>
        <StatusPill connected={state.engineConnected} />
      </div>

      {/* Main Toggle */}
      <div style={{
        background: state.active
          ? "linear-gradient(135deg, rgba(56,189,248,0.12), rgba(52,211,153,0.08))"
          : "rgba(255,255,255,0.03)",
        border: `1px solid ${state.active ? "rgba(56,189,248,0.3)" : "rgba(255,255,255,0.08)"}`,
        borderRadius: "20px",
        padding: "28px",
        marginBottom: "20px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        transition: "all 0.4s ease",
        boxShadow: state.active ? "0 0 40px rgba(56,189,248,0.08)" : "none",
      }}>
        <div>
          <div style={{ fontSize: "20px", fontWeight: 700, marginBottom: "4px" }}>
            {state.active ? "🟢 Control Active" : "⚫ Control Inactive"}
          </div>
          <div style={{ fontSize: "13px", color: "#475569" }}>
            {state.active
              ? `Auto-sleeps in ${inactiveCountdown}s without gesture`
              : "Tap enable or raise your hand to activate"}
          </div>
        </div>
        <button
          className="toggle-btn"
          onClick={handleToggle}
          disabled={!state.engineConnected}
          style={{
            padding: "12px 28px",
            borderRadius: "12px",
            border: "none",
            cursor: state.engineConnected ? "pointer" : "not-allowed",
            fontFamily: "'DM Sans', sans-serif",
            fontSize: "14px",
            fontWeight: 700,
            letterSpacing: "0.04em",
            transition: "all 0.2s ease",
            background: state.active
              ? "linear-gradient(135deg, #f87171, #fb923c)"
              : "linear-gradient(135deg, #38bdf8, #34d399)",
            color: "#0f172a",
            opacity: state.engineConnected ? 1 : 0.4,
          }}
        >
          {state.active ? "DISABLE" : "ENABLE"}
        </button>
      </div>

      {/* Metrics Row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: "12px", marginBottom: "20px" }}>
        <GestureCard gesture={state.gesture} active={state.active} />
        <MetricBox label="FPS Mode" value={state.fps} unit="fps" accent="#38bdf8" />
        <MetricBox label="Cursor X" value={Math.round(state.cursor_x)} unit="px" accent="#a78bfa" />
        <MetricBox label="Cursor Y" value={Math.round(state.cursor_y)} unit="px" accent="#f59e0b" />
      </div>

      {/* Inactive Progress Bar */}
      {state.active && (
        <div style={{
          background: "rgba(255,255,255,0.04)", borderRadius: "8px",
          height: "4px", marginBottom: "20px", overflow: "hidden",
        }}>
          <div style={{
            height: "100%", borderRadius: "8px",
            width: `${(inactiveCountdown / 60) * 100}%`,
            background: inactiveCountdown > 20
              ? "linear-gradient(90deg, #38bdf8, #34d399)"
              : "linear-gradient(90deg, #f59e0b, #f87171)",
            transition: "width 1s linear, background 0.5s ease",
          }} />
        </div>
      )}

      {/* Bottom Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
        <LogPanel log={log} />
        <GestureLegend />
      </div>
    </div>
  );
}