import logging
from datetime import datetime
from typing import Dict, List
from schemas import ChatSession, ChatMessage

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
    
    def create_session(self, session_id: str) -> ChatSession:
        """Create a new chat session"""
        session = ChatSession(
            messages=[],
            created_at=datetime.now().isoformat(),
            last_activity=datetime.now().isoformat()
        )
        self.sessions[session_id] = session
        logger.info(f"Created new chat session: {session_id}")
        return session
    
    def get_session(self, session_id: str) -> ChatSession:
        """Get existing session or create new one"""
        if session_id not in self.sessions:
            return self.create_session(session_id)
        return self.sessions[session_id]
    
    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Add a message to the session"""
        session = self.get_session(session_id)
        
        message = ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat()
        )
        
        session.messages.append(message)
        session.last_activity = datetime.now().isoformat()
        
        logger.info(f"Added {role} message to session {session_id}: {content[:50]}...")
    
    def get_conversation_context(self, session_id: str, max_messages: int = 10) -> str:
        """Get conversation context for LLM"""
        session = self.get_session(session_id)
        
        context_messages = []
        for msg in session.messages[-max_messages:]:
            role_title = msg.role.title()
            context_messages.append(f"{role_title}: {msg.content}")
        
        return "\n".join(context_messages)
    
    def get_message_count(self, session_id: str) -> int:
        """Get total message count for session"""
        session = self.get_session(session_id)
        return len(session.messages)
    
    def session_exists(self, session_id: str) -> bool:
        """Check if session exists"""
        return session_id in self.sessions
    
    def get_session_info(self, session_id: str) -> Dict:
        """Get session information"""
        if not self.session_exists(session_id):
            return {
                "session_id": session_id,
                "messages": [],
                "message_count": 0,
                "status": "new_session"
            }
        
        session = self.sessions[session_id]
        return {
            "session_id": session_id,
            "messages": [msg.dict() for msg in session.messages],
            "message_count": len(session.messages),
            "created_at": session.created_at,
            "last_activity": session.last_activity,
            "status": "active"
        }