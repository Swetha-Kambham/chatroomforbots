import os
from flask import Blueprint, render_template, request, jsonify
from app import db
from app.models import Conversation, Message, Bot, ConversationBot
from app.services import ollama, router

chat_bp = Blueprint("chat", __name__)

MEMORY = int(os.getenv("BOT_MEMORY_MESSAGES", "5"))


@chat_bp.route("/messages/<int:conv_id>")
def messages(conv_id):
    conv = Conversation.query.get_or_404(conv_id)
    msgs = conv.messages[-50:]
    return render_template("partials/messages.html", messages=msgs)


@chat_bp.route("/message", methods=["POST"])
def send_message():
    conv_id = request.form.get("conv_id", type=int)
    content = request.form.get("content", "").strip()

    if not content or not conv_id:
        return "", 400

    conv = Conversation.query.get_or_404(conv_id)

    user_msg = Message(
        conversation_id=conv_id,
        sender_name="You",
        sender_type="user",
        content=content,
    )
    db.session.add(user_msg)
    db.session.commit()

    active_bots = _get_active_bots(conv_id)
    if not active_bots:
        return render_template("partials/messages.html", messages=conv.messages[-50:])

    bot_info = [{"name": b.name, "role": b.role, "system_prompt": b.system_prompt} for b in active_bots]
    last_bot = _get_last_bot(conv_id)
    history = _get_memory(conv_id, exclude_last=1)
    chosen_name, method = router.route(content, bot_info, last_bot=last_bot, history=history)
    chosen_bot = next((b for b in active_bots if b.name == chosen_name), active_bots[0])

    if method.startswith("unavailable:"):
        missing_bot = method.split(":")[1]
        db.session.add(Message(
            conversation_id=conv_id,
            sender_name="RouterBot",
            sender_type="system",
            content=f"{missing_bot} is not in this chat — add it from the sidebar to handle this topic.",
        ))
        db.session.commit()
        return render_template("partials/messages.html", messages=conv.messages[-50:])

    jokebot_active = any(b["name"] == "JokeBot" for b in bot_info)
    if method == "fallback" and not jokebot_active:
        routing_note = f"No specialist matched — JokeBot not in chat, routing to {chosen_bot.name} as best available"
    else:
        routing_note = f"Routing to {chosen_bot.name} ({method} match)"

    system_msg = Message(
        conversation_id=conv_id,
        sender_name="RouterBot",
        sender_type="system",
        content=routing_note,
        routed_to=chosen_bot.name,
    )
    db.session.add(system_msg)
    db.session.commit()

    # Save placeholder so polling shows the bot is thinking even after a page refresh
    bot_msg = Message(
        conversation_id=conv_id,
        sender_name=chosen_bot.name,
        sender_type="bot",
        content="…",
        routed_to=chosen_bot.name,
    )
    db.session.add(bot_msg)
    db.session.commit()

    # Only pass this bot's own prior exchanges so it isn't confused by other bots' responses
    bot_history = _get_bot_memory(conv_id, chosen_bot.name, exclude_last=1)
    response_text = ollama.chat(
        model=chosen_bot.model_name,
        system_prompt=chosen_bot.system_prompt,
        messages=bot_history,
        user_message=content,
    )

    bot_msg.content = response_text
    db.session.commit()

    return render_template("partials/messages.html", messages=conv.messages[-50:])


def _get_last_bot(conv_id: int) -> str | None:
    last = (
        Message.query
        .filter_by(conversation_id=conv_id, sender_type="bot")
        .order_by(Message.created_at.desc())
        .first()
    )
    return last.sender_name if last else None


def _get_active_bots(conv_id: int) -> list[Bot]:
    rows = ConversationBot.query.filter_by(conversation_id=conv_id).all()
    return [row.bot for row in rows]


def _get_bot_memory(conv_id: int, bot_name: str, exclude_last: int = 0) -> list[dict]:
    """Returns only user messages + this specific bot's replies, so bots don't see each other's responses."""
    msgs = (
        Message.query
        .filter_by(conversation_id=conv_id)
        .filter(
            db.or_(
                Message.sender_type == "user",
                db.and_(Message.sender_type == "bot", Message.sender_name == bot_name)
            )
        )
        .filter(Message.content != "…")
        .order_by(Message.created_at.desc())
        .limit(MEMORY + exclude_last)
        .all()
    )
    msgs = list(reversed(msgs))
    if exclude_last:
        msgs = msgs[:-exclude_last] if len(msgs) > exclude_last else []
    return [m.to_dict() for m in msgs]


def _get_memory(conv_id: int, exclude_last: int = 0) -> list[dict]:
    msgs = (
        Message.query
        .filter_by(conversation_id=conv_id)
        .filter(Message.sender_type.in_(["user", "bot"]))
        .filter(Message.content != "…")
        .order_by(Message.created_at.desc())
        .limit(MEMORY + exclude_last)
        .all()
    )
    msgs = list(reversed(msgs))
    if exclude_last:
        msgs = msgs[:-exclude_last] if len(msgs) > exclude_last else []
    return [m.to_dict() for m in msgs]
