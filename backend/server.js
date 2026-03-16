/**
 * GestureOS Backend — Node.js / Express / WebSocket bridge
 * Connects Python gesture engine → React frontend
 */

const express = require("express");
const http = require("http");
const { WebSocketServer, WebSocket } = require("ws");
const cors = require("cors");
require("dotenv").config();

const app = express();
const server = http.createServer(app);

app.use(cors());
app.use(express.json());

// ── WebSocket: Python Engine Client ──────────────────────────────────────────
let engineSocket = null;
let lastEngineState = {
  gesture: "none", active: false, fps: 5,
  cursor_x: 0, cursor_y: 0, scroll_delta: 0, timestamp: 0,
};

function connectToEngine() {
  const ENGINE_WS = process.env.ENGINE_WS || "ws://localhost:8765";
  console.log(`[Bridge] Connecting to Python engine at ${ENGINE_WS}...`);

  engineSocket = new WebSocket(ENGINE_WS);

  engineSocket.on("open", () => {
    console.log("[Bridge] Connected to Python engine ✓");
    broadcastToClients({ type: "engine_connected" });
  });

  engineSocket.on("message", (data) => {
    try {
      const state = JSON.parse(data.toString());
      lastEngineState = { ...state };
      broadcastToClients({ type: "gesture_state", ...state });
    } catch (e) {
      console.error("[Bridge] Parse error:", e.message);
    }
  });

  engineSocket.on("close", () => {
    console.log("[Bridge] Engine disconnected. Retrying in 3s...");
    broadcastToClients({ type: "engine_disconnected" });
    setTimeout(connectToEngine, 3000);
  });

  engineSocket.on("error", (err) => {
    console.error("[Bridge] Engine error:", err.message);
  });
}

function sendToEngine(command) {
  if (engineSocket && engineSocket.readyState === WebSocket.OPEN) {
    engineSocket.send(JSON.stringify(command));
    return true;
  }
  return false;
}

// ── WebSocket: React Frontend Clients ────────────────────────────────────────
const wss = new WebSocketServer({ server, path: "/ws" });
const frontendClients = new Set();

wss.on("connection", (ws) => {
  frontendClients.add(ws);
  console.log(`[WS] Frontend client connected (total: ${frontendClients.size})`);

  // Send current state immediately on connect
  ws.send(JSON.stringify({
    type: "init",
    engineConnected: engineSocket?.readyState === WebSocket.OPEN,
    state: lastEngineState,
  }));

  ws.on("message", (data) => {
    try {
      const cmd = JSON.parse(data.toString());

      if (cmd.action === "enable") {
        sendToEngine({ action: "enable" });
        broadcastToClients({ type: "control", active: true });
      } else if (cmd.action === "disable") {
        sendToEngine({ action: "disable" });
        broadcastToClients({ type: "control", active: false });
      }
    } catch (e) {
      console.error("[WS] Client message error:", e.message);
    }
  });

  ws.on("close", () => {
    frontendClients.delete(ws);
    console.log(`[WS] Frontend client disconnected (total: ${frontendClients.size})`);
  });
});

function broadcastToClients(message) {
  const data = JSON.stringify(message);
  frontendClients.forEach((ws) => {
    if (ws.readyState === WebSocket.OPEN) ws.send(data);
  });
}

// ── REST API ─────────────────────────────────────────────────────────────────
app.get("/api/status", (req, res) => {
  res.json({
    engineConnected: engineSocket?.readyState === WebSocket.OPEN,
    gestureControlActive: lastEngineState.active,
    fps: lastEngineState.fps,
  });
});

app.post("/api/control", (req, res) => {
  const { action } = req.body;
  if (!["enable", "disable"].includes(action)) {
    return res.status(400).json({ error: "action must be enable or disable" });
  }
  const sent = sendToEngine({ action });
  res.json({ success: sent, action });
});

// ── Start Server ─────────────────────────────────────────────────────────────
const PORT = process.env.PORT || 5000;
server.listen(PORT, () => {
  console.log(`[Server] Running on http://localhost:${PORT}`);
  connectToEngine();
});