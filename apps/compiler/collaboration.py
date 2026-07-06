"""
Real-time Code Collaboration
WebSocket-based live code sharing and pair programming
"""

from typing import Dict, List, Set, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class CursorPosition:
    """User cursor position in editor"""
    user_id: int
    username: str
    line: int
    column: int
    timestamp: datetime
    color: str  # Hex color for cursor
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'line': self.line,
            'column': self.column,
            'color': self.color,
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class CodeChange:
    """A code change event"""
    user_id: int
    username: str
    timestamp: datetime
    content: str
    operation: str  # 'insert' or 'delete'
    position: Dict  # {line, column}
    text: str  # Text inserted/deleted
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'timestamp': self.timestamp.isoformat(),
            'content': self.content,
            'operation': self.operation,
            'position': self.position,
            'text': self.text,
        }


@dataclass
class SessionUser:
    """User in a collaboration session"""
    user_id: int
    username: str
    cursor: Optional[CursorPosition] = None
    selection: Optional[Dict] = None  # {start, end}
    is_active: bool = True
    joined_at: datetime = None
    
    def __post_init__(self):
        if self.joined_at is None:
            self.joined_at = datetime.now()
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'cursor': self.cursor.to_dict() if self.cursor else None,
            'selection': self.selection,
            'is_active': self.is_active,
            'joined_at': self.joined_at.isoformat(),
        }


class CollaborationSession:
    """Manages a code collaboration session"""
    
    def __init__(self, session_id: str, creator_id: int, creator_name: str):
        self.session_id = session_id
        self.creator_id = creator_id
        self.created_at = datetime.now()
        
        # Code and history
        self.code = ""
        self.change_history: List[CodeChange] = []
        
        # Users in session
        self.users: Dict[int, SessionUser] = {
            creator_id: SessionUser(
                user_id=creator_id,
                username=creator_name,
            )
        }
        
        # Session settings
        self.is_public = False
        self.allow_read_only = False
        self.max_participants = 5
        
        # WebSocket connections
        self.connections: Dict[int, List] = {}  # user_id -> list of connections
    
    def add_user(self, user_id: int, username: str) -> bool:
        """Add user to session"""
        if user_id in self.users:
            self.users[user_id].is_active = True
            return True
        
        if len(self.users) >= self.max_participants:
            return False
        
        self.users[user_id] = SessionUser(
            user_id=user_id,
            username=username,
        )
        return True
    
    def remove_user(self, user_id: int):
        """Remove user from session"""
        if user_id in self.users:
            self.users[user_id].is_active = False
            # Keep history, but mark as inactive
    
    def update_cursor(self, user_id: int, line: int, column: int, color: str = None):
        """Update user cursor position"""
        if user_id not in self.users:
            return
        
        if color is None:
            color = self._generate_color(user_id)
        
        self.users[user_id].cursor = CursorPosition(
            user_id=user_id,
            username=self.users[user_id].username,
            line=line,
            column=column,
            timestamp=datetime.now(),
            color=color,
        )
    
    def update_selection(self, user_id: int, start: Dict, end: Dict):
        """Update user selection"""
        if user_id not in self.users:
            return
        
        self.users[user_id].selection = {
            'start': start,
            'end': end,
        }
    
    def record_change(self, user_id: int, operation: str, position: Dict, 
                     text: str, content: str):
        """Record a code change"""
        if user_id not in self.users:
            return
        
        username = self.users[user_id].username
        
        change = CodeChange(
            user_id=user_id,
            username=username,
            timestamp=datetime.now(),
            content=content,
            operation=operation,
            position=position,
            text=text,
        )
        
        self.change_history.append(change)
        self.code = content
        
        # Keep history to max 1000 changes
        if len(self.change_history) > 1000:
            self.change_history = self.change_history[-1000:]
    
    def get_active_users(self) -> List[SessionUser]:
        """Get list of active users"""
        return [u for u in self.users.values() if u.is_active]
    
    def get_user_count(self) -> int:
        """Get active user count"""
        return len(self.get_active_users())
    
    def get_state(self) -> Dict:
        """Get complete session state"""
        return {
            'session_id': self.session_id,
            'code': self.code,
            'users': [u.to_dict() for u in self.get_active_users()],
            'user_count': self.get_user_count(),
            'created_at': self.created_at.isoformat(),
            'is_public': self.is_public,
        }
    
    def get_changes_since(self, timestamp: datetime) -> List[Dict]:
        """Get changes since a given timestamp"""
        return [
            c.to_dict() for c in self.change_history
            if c.timestamp > timestamp
        ]
    
    def _generate_color(self, user_id: int) -> str:
        """Generate a unique color for user"""
        colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
            '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B88B', '#A2D5C6'
        ]
        return colors[user_id % len(colors)]


class CollaborationManager:
    """Manages multiple collaboration sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, CollaborationSession] = {}
        self.user_sessions: Dict[int, Set[str]] = {}  # user_id -> set of session_ids
    
    def create_session(self, session_id: str, creator_id: int, 
                      creator_name: str) -> CollaborationSession:
        """Create a new collaboration session"""
        session = CollaborationSession(session_id, creator_id, creator_name)
        self.sessions[session_id] = session
        
        if creator_id not in self.user_sessions:
            self.user_sessions[creator_id] = set()
        self.user_sessions[creator_id].add(session_id)
        
        logger.info(f"Created session {session_id} by {creator_name}")
        return session
    
    def get_session(self, session_id: str) -> Optional[CollaborationSession]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def join_session(self, session_id: str, user_id: int, username: str) -> bool:
        """Join a session"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        if session.add_user(user_id, username):
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = set()
            self.user_sessions[user_id].add(session_id)
            logger.info(f"User {username} joined session {session_id}")
            return True
        
        return False
    
    def leave_session(self, session_id: str, user_id: int):
        """Leave a session"""
        session = self.get_session(session_id)
        if session:
            session.remove_user(user_id)
            
            if user_id in self.user_sessions:
                self.user_sessions[user_id].discard(session_id)
            
            # Delete session if empty
            if session.get_user_count() == 0:
                del self.sessions[session_id]
                logger.info(f"Deleted empty session {session_id}")
    
    def get_user_sessions(self, user_id: int) -> List[CollaborationSession]:
        """Get all sessions a user is in"""
        session_ids = self.user_sessions.get(user_id, set())
        return [self.sessions[sid] for sid in session_ids if sid in self.sessions]
    
    def broadcast_change(self, session_id: str, change_data: Dict) -> Dict:
        """Broadcast a change to all users in session"""
        session = self.get_session(session_id)
        if not session:
            return {'error': 'Session not found'}
        
        return {
            'type': 'change',
            'change': change_data,
            'session_state': session.get_state(),
        }
    
    def broadcast_cursor(self, session_id: str, cursor_data: Dict) -> Dict:
        """Broadcast cursor position"""
        session = self.get_session(session_id)
        if not session:
            return {'error': 'Session not found'}
        
        return {
            'type': 'cursor',
            'cursor': cursor_data,
            'users': [u.to_dict() for u in session.get_active_users()],
        }


# Global manager instance
collaboration_manager = CollaborationManager()


def get_collaboration_manager() -> CollaborationManager:
    """Get collaboration manager instance"""
    return collaboration_manager
