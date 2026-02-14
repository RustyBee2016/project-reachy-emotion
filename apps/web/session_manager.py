"""
Session state management for Streamlit application.
Handles WebSocket connections, API client initialization, and shared state.
"""
import sys
import types

try:
    import streamlit as st
except ImportError:  # pragma: no cover - test/runtime fallback
    streamlit_stub = types.ModuleType("streamlit")
    streamlit_stub.session_state = {}

    def _noop(*args, **kwargs):
        return None

    class _Ctx:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

    streamlit_stub.columns = lambda n: [_Ctx() for _ in range(n)]
    streamlit_stub.success = _noop
    streamlit_stub.error = _noop
    streamlit_stub.warning = _noop
    streamlit_stub.info = _noop
    streamlit_stub.metric = _noop
    streamlit_stub.expander = lambda *args, **kwargs: _Ctx()
    sys.modules["streamlit"] = streamlit_stub
    st = streamlit_stub
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import os

from apps.web.api_client_v2 import ReachyAPIClient, APIConfig
from apps.web.websocket_client import WebSocketClient, EventType

logger = logging.getLogger(__name__)


class SessionManager:
    """Manage Streamlit session state and connections."""
    
    @staticmethod
    def _get_session():
        """Get session state (allows mocking in tests)."""
        return st.session_state

    @staticmethod
    def _has(session, key: str) -> bool:
        if isinstance(session, dict):
            return key in session
        return hasattr(session, key)

    @staticmethod
    def _get(session, key: str, default=None):
        if isinstance(session, dict):
            return session.get(key, default)
        return getattr(session, key, default)

    @staticmethod
    def _set(session, key: str, value):
        if isinstance(session, dict):
            session[key] = value
        else:
            setattr(session, key, value)
    
    @staticmethod
    def initialize():
        """Initialize session state with default values."""
        session = SessionManager._get_session()
        
        # API Client
        if not SessionManager._has(session, 'api_client'):
            config = APIConfig(
                base_url=os.getenv('REACHY_API_BASE', 'http://10.0.4.130/api/media'),
                gateway_url=os.getenv('REACHY_GATEWAY_BASE', 'http://10.0.4.140:8000'),
                api_token=os.getenv('REACHY_API_TOKEN'),
                timeout=30,
                max_retries=3
            )
            SessionManager._set(session, 'api_client', ReachyAPIClient(config))
            logger.info("API client initialized")
        
        # WebSocket Client (lazy initialization)
        if not SessionManager._has(session, 'ws_client'):
            SessionManager._set(session, 'ws_client', None)
            SessionManager._set(session, 'ws_connected', False)
        
        # UI State
        if not SessionManager._has(session, 'current_page'):
            SessionManager._set(session, 'current_page', 'home')
        
        if not SessionManager._has(session, 'selected_videos'):
            SessionManager._set(session, 'selected_videos', [])
        
        if not SessionManager._has(session, 'filter_split'):
            SessionManager._set(session, 'filter_split', 'temp')
        
        if not SessionManager._has(session, 'filter_label'):
            SessionManager._set(session, 'filter_label', None)
        
        # Real-time Events
        if not SessionManager._has(session, 'latest_emotion'):
            SessionManager._set(session, 'latest_emotion', None)
        
        if not SessionManager._has(session, 'recent_promotions'):
            SessionManager._set(session, 'recent_promotions', [])
        
        if not SessionManager._has(session, 'training_status'):
            SessionManager._set(session, 'training_status', None)
        
        # Notifications
        if not SessionManager._has(session, 'notifications'):
            SessionManager._set(session, 'notifications', [])
        
        # Stats
        if not SessionManager._has(session, 'last_refresh'):
            SessionManager._set(session, 'last_refresh', None)
    
    @staticmethod
    def get_api_client() -> ReachyAPIClient:
        """Get API client from session state."""
        SessionManager.initialize()
        return SessionManager._get(st.session_state, 'api_client')
    
    @staticmethod
    def get_ws_client() -> Optional[WebSocketClient]:
        """Get WebSocket client from session state."""
        SessionManager.initialize()
        return SessionManager._get(st.session_state, 'ws_client')
    
    @staticmethod
    def connect_websocket():
        """Initialize and connect WebSocket client."""
        if SessionManager._get(st.session_state, 'ws_client') is None:
            gateway_url = os.getenv('REACHY_GATEWAY_BASE', 'http://10.0.4.140:8000')
            ws_client = WebSocketClient(
                server_url=gateway_url,
                device_id='web-ui',
                heartbeat_interval=30
            )
            SessionManager._set(st.session_state, 'ws_client', ws_client)
            
            # Subscribe to events
            ws_client.subscribe(
                EventType.EMOTION,
                SessionManager._on_emotion_event
            )
            ws_client.subscribe(
                EventType.PROMOTION,
                SessionManager._on_promotion_event
            )
            ws_client.subscribe(
                EventType.TRAINING,
                SessionManager._on_training_event
            )
            
            # Connect (async)
            try:
                asyncio.run(ws_client.connect())
                SessionManager._set(st.session_state, 'ws_connected', True)
                logger.info("WebSocket connected")
            except Exception as e:
                logger.error(f"WebSocket connection failed: {e}")
                SessionManager._set(st.session_state, 'ws_connected', False)
    
    @staticmethod
    async def _on_emotion_event(event):
        """Handle emotion detection event."""
        SessionManager._set(st.session_state, 'latest_emotion', event)
        SessionManager.add_notification(
            f"Emotion detected: {event.emotion} ({event.confidence:.2%})",
            "info"
        )
    
    @staticmethod
    async def _on_promotion_event(event):
        """Handle promotion completion event."""
        recent = SessionManager._get(st.session_state, 'recent_promotions', [])
        recent.insert(0, event)
        SessionManager._set(st.session_state, 'recent_promotions', recent[:10])
        
        if event.success:
            SessionManager.add_notification(
                f"Video promoted: {event.video_id[:8]}... → {event.to_split}",
                "success"
            )
        else:
            SessionManager.add_notification(
                f"Promotion failed: {event.error}",
                "error"
            )
    
    @staticmethod
    async def _on_training_event(event):
        """Handle training status event."""
        SessionManager._set(st.session_state, 'training_status', event)
        SessionManager.add_notification(
            f"Training {event.run_id[:8]}...: {event.status}",
            "info"
        )
    
    @staticmethod
    def poll_websocket_messages():
        """Poll WebSocket for new messages and update session state."""
        ws_client = SessionManager.get_ws_client()
        if ws_client and SessionManager._get(st.session_state, 'ws_connected', False):
            messages = ws_client.get_messages(max_count=50)
            
            for msg_type, data in messages:
                if msg_type == 'emotion':
                    SessionManager._set(st.session_state, 'latest_emotion', data)
                elif msg_type == 'promotion':
                    recent = SessionManager._get(st.session_state, 'recent_promotions', [])
                    recent.insert(0, data)
                    SessionManager._set(st.session_state, 'recent_promotions', recent[:10])
                elif msg_type == 'training':
                    SessionManager._set(st.session_state, 'training_status', data)
    
    @staticmethod
    def add_notification(message: str, level: str = "info"):
        """Add notification to queue."""
        notification = {
            'message': message,
            'level': level,
            'timestamp': datetime.now()
        }
        notifications = SessionManager._get(st.session_state, 'notifications', [])
        notifications.append(notification)
        SessionManager._set(st.session_state, 'notifications', notifications[-20:])
    
    @staticmethod
    def clear_notifications():
        """Clear all notifications."""
        SessionManager._set(st.session_state, 'notifications', [])
    
    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """Get session statistics."""
        api_client = SessionManager.get_api_client()
        ws_client = SessionManager.get_ws_client()
        
        stats = {
            'api_requests': api_client.request_count,
            'api_errors': api_client.error_count,
            'api_retries': api_client.retry_count,
            'ws_connected': SessionManager._get(st.session_state, 'ws_connected', False),
            'ws_events': 0,
            'notifications': len(SessionManager._get(st.session_state, 'notifications', [])),
            'selected_videos': len(SessionManager._get(st.session_state, 'selected_videos', []))
        }
        
        if ws_client:
            metrics = ws_client.get_metrics()
            stats['ws_events'] = metrics['events_received']
            stats['ws_healthy'] = metrics['is_healthy']
        
        return stats


def render_status_bar():
    """Render status bar with connection status and stats."""
    SessionManager.initialize()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        api_client = SessionManager.get_api_client()
        if api_client.health_check():
            st.success("✓ API Connected")
        else:
            st.error("✗ API Disconnected")
    
    with col2:
        if st.session_state.ws_connected:
            st.success("✓ WebSocket Connected")
        else:
            st.warning("○ WebSocket Disconnected")
    
    with col3:
        stats = SessionManager.get_stats()
        st.metric("API Requests", stats['api_requests'])
    
    with col4:
        st.metric("Notifications", stats['notifications'])


def render_notifications():
    """Render notification panel."""
    SessionManager.initialize()
    
    if st.session_state.notifications:
        with st.expander(f"📬 Notifications ({len(st.session_state.notifications)})", expanded=False):
            for notif in reversed(st.session_state.notifications[-5:]):
                timestamp = notif['timestamp'].strftime('%H:%M:%S')
                if notif['level'] == 'success':
                    st.success(f"[{timestamp}] {notif['message']}")
                elif notif['level'] == 'error':
                    st.error(f"[{timestamp}] {notif['message']}")
                elif notif['level'] == 'warning':
                    st.warning(f"[{timestamp}] {notif['message']}")
                else:
                    st.info(f"[{timestamp}] {notif['message']}")
            
            if st.button("Clear Notifications"):
                SessionManager.clear_notifications()
                st.rerun()


def render_sidebar_info():
    """Render sidebar information."""
    SessionManager.initialize()
    
    with st.sidebar:
        st.header("System Status")
        
        # Connection status
        api_client = SessionManager.get_api_client()
        ws_client = SessionManager.get_ws_client()
        
        st.subheader("Connections")
        api_status = "🟢 Connected" if api_client.health_check() else "🔴 Disconnected"
        st.text(f"API: {api_status}")
        
        ws_status = "🟢 Connected" if st.session_state.ws_connected else "⚪ Disconnected"
        st.text(f"WebSocket: {ws_status}")
        
        # Stats
        st.subheader("Statistics")
        stats = SessionManager.get_stats()
        st.text(f"API Requests: {stats['api_requests']}")
        st.text(f"API Errors: {stats['api_errors']}")
        st.text(f"WS Events: {stats['ws_events']}")
        
        # Latest emotion
        if st.session_state.latest_emotion:
            st.subheader("Latest Emotion")
            emotion = st.session_state.latest_emotion
            st.text(f"Emotion: {emotion.emotion}")
            st.text(f"Confidence: {emotion.confidence:.2%}")
            st.text(f"Device: {emotion.device_id}")
        
        # Training status
        if st.session_state.training_status:
            st.subheader("Training Status")
            training = st.session_state.training_status
            st.text(f"Run: {training.run_id[:8]}...")
            st.text(f"Status: {training.status}")
            if training.accuracy:
                st.text(f"Accuracy: {training.accuracy:.2%}")
