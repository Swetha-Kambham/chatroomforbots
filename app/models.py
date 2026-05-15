from datetime import datetime
from app import db


class Bot(db.Model):
    __tablename__ = "bots"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    role = db.Column(db.String(100), nullable=False)
    system_prompt = db.Column(db.Text, nullable=False)
    model_name = db.Column(db.String(100), nullable=False, default="tinyllama")
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    conversation_bots = db.relationship("ConversationBot", back_populates="bot", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "system_prompt": self.system_prompt,
            "model_name": self.model_name,
            "is_default": self.is_default,
        }


class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    messages = db.relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    conversation_bots = db.relationship("ConversationBot", back_populates="conversation", cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": self.id, "name": self.name}


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), nullable=False)
    sender_name = db.Column(db.String(100), nullable=False)
    sender_type = db.Column(db.String(20), nullable=False)  # "user", "bot", "system"
    content = db.Column(db.Text, nullable=False)
    routed_to = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    conversation = db.relationship("Conversation", back_populates="messages")

    def to_dict(self):
        return {
            "id": self.id,
            "sender_name": self.sender_name,
            "sender_type": self.sender_type,
            "content": self.content,
            "routed_to": self.routed_to,
            "created_at": self.created_at.strftime("%H:%M"),
        }


class ConversationBot(db.Model):
    __tablename__ = "conversation_bots"

    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), primary_key=True)
    bot_id = db.Column(db.Integer, db.ForeignKey("bots.id"), primary_key=True)

    conversation = db.relationship("Conversation", back_populates="conversation_bots")
    bot = db.relationship("Bot", back_populates="conversation_bots")
