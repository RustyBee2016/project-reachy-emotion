"""
Session state management for Streamlit application.
Handles WebSocket connections, API client initialization, and shared state.
"""
import streamlit as st
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
    def initialize():
        """Initialize session state with default values."""
        session = SessionManager._get_session()
        
        # API Client
        if not hasattr(session, 'api_client'):
            config = APIConfig(
                base_url=os.getenv('REACHY_API_BASE', 'http://10.0.4.130/api/media'),
                gateway_url=os.getenv('REACHY_GATEWAY_BASE', 'http://10.0.4.140:8000'),
                api_token=os.getenv('REACHY_API_TOKEN'),
                timeout=30,
                max_retries=3
            )
            session.api_client = ReachyAPIClient(config)
            logger.info("API client initialized")
        
        # WebSocket Client (lazy initialization)
        if not hasattr(session, 'ws_client'):
            session.ws_client = None
            session.ws_connected = False
        
        # UI State
        if not hasattr(session, 'current_page'):
            session.current_page = 'home'
        
        if not hasattr(session, 'selected_videos'):
            session.selected_videos = []
        
        if not hasattr(session, 'filter_split'):
            session.filter_split = 'temp'
        
        if not hasattr(session, 'filter_label'):
            session.filter_label = None
        
        # Real-time Events
        if not hasattr(session, 'latest_emotion'):
            session.latest_emotion = None
        
        if not hasattr(session, 'recent_promotions'):
            session.recent_promotions = []
        
        if not hasattr(session, 'training_status'):
            session.training_status = None
        
        # Notifications
        if not hasattr(session, 'notifications'):
            session.notifications = []
        
        # Stats
        if not hasattr(session, 'last_refresh'):
            session.last_refresh = None
    
    @staticmethod
    def get_api_client() -> ReachyAPIClient:
        """Get API client from session state."""
        SessionManager.initialize()
        return st.session_state.api_client
    
    @staticmethod
    def get_ws_client() -> Optional[WebSocketClient]:
        """Get WebSocket client from session state."""
        SessionManager.initialize()
        return st.session_state.ws_client
    
    @staticmethod
    def connect_websocket():
        """Initialize and connect WebSocket client."""
        if st.session_state.ws_client is None:
            gateway_url = os.getenv('REACHY_GATEWAY_BASE', 'http://10.0.4.140:8000')
            st.session_state.ws_client = WebSocketClient(
                server_url=gateway_url,
                device_id='web-ui',
                heartbeat_interval=30
            )
            
            # Subscribe to events
            st.session_state.ws_client.subscribe(
                EventType.EMOTION,
                SessionManager._on_emotion_event
            )
            st.session_state.ws_client.subscribe(
                EventType.PROMOTION,
                SessionManager._on_promotion_event
            )
            st.session_state.ws_client.subscribe(
                EventType.TRAINING,
                SessionManager._on_training_event
            )
            
            # Connect (async)
            try:
                asyncio.run(st.session_state.ws_client.connect())
                st.session_state.ws_connected = True
                logger.info("WebSocket connected")
            except Exception as e:
                logger.error(f"WebSocket connection failed: {e}")
                st.session_state.ws_connected = False
    
    @staticmethod
    async def _on_emotion_event(event):
        """Handle emotion detection event."""
        st.session_state.latest_emotion = event
        SessionManager.add_notification(
            f"Emotion detected: {event.emotion} ({event.confidence:.2%})",
            "info"
        )
    
    @staticmethod
    async def _on_promotion_event(event):
        """Handle promotion completion event."""
        st.session_state.recent_promotions.insert(0, event)
        # Keep only last 10
        st.session_state.recent_promotions = st.session_state.recent_promotions[:10]
        
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
        st.session_state.training_status = event
        SessionManager.add_notification(
            f"Training {event.run_id[:8]}...: {event.status}",
            "info"
        )
    
    @staticmethod
    def poll_websocket_messages():
        """Poll WebSocket for new messages and update session state."""
        ws_client = SessionManager.get_ws_client()
        if ws_client and st.session_state.ws_connected:
            messages = ws_client.get_messages(max_count=50)
            
            for msg_type, data in messages:
                if msg_type == 'emotion':
                    st.session_state.latest_emotion = data
                elif msg_type == 'promotion':
                    st.session_state.recent_promotions.insert(0, data)
                    st.session_state.recent_promotions = st.session_state.recent_promotions[:10]
                elif msg_type == 'training':
                    st.session_state.training_status = data
    
    @staticmethod
    def add_notification(message: str, level: str = "info"):
        """Add notification to queue."""
        notification = {
            'message': message,
            'level': level,
            'timestamp': datetime.now()
        }
        st.session_state.notifications.append(notification)
        # Keep only last 20
        st.session_state.notifications = st.session_state.notifications[-20:]
    
    @staticmethod
    def clear_notifications():
        """Clear all notifications."""
        st.session_state.notifications = []
    
    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """Get session statistics."""
        api_client = SessionManager.get_api_client()
        ws_client = SessionManager.get_ws_client()
        
        stats = {
            'api_requests': api_client.request_count,
            'api_errors': api_client.error_count,
            'api_retries': api_client.retry_count,
            'ws_connected': st.session_state.ws_connected,
            'ws_events': 0,
            'notifications': len(st.session_state.notifications),
            'selected_videos': len(st.session_state.selected_videos)
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
