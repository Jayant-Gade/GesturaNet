# Gesture Engine Fix - MediaPipe Python 3.13 Compatibility

## Progress

- [ ] 1. Update requirements.txt (pin mediapipe==0.10.14)
- [ ] 2. Refactor gestureEngine.py to legacy `mp.solutions.Hands` API
- [ ] 3. Test `python gestureEngine.py` - confirm no AttributeError, camera starts
- [ ] 4. Test gestures: move cursor (index), left click (thumb+index pinch), right click (thumb+middle), scroll (index+middle)
- [ ] 5. Verify WebSocket broadcast to backend/frontend
- [ ] 6. Mark complete ✓

Current status: Starting refactor...
