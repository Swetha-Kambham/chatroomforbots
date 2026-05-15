import os
from flask import Blueprint, render_template, request, redirect, url_for
from app import db
from app.models import Conversation, Bot, ConversationBot, Message

conversations_bp = Blueprint("conversations", __name__)


@conversations_bp.route("/")
def index():
    conversations = Conversation.query.order_by(Conversation.created_at.desc()).all()
    if not conversations:
        default = Conversation(name="General Chat")
        db.session.add(default)
        db.session.commit()
        _add_all_bots(default.id)
        conversations = [default]

    active_id = request.args.get("conv_id", conversations[0].id, type=int)
    active_conv = Conversation.query.get_or_404(active_id)
    all_bots = Bot.query.order_by(Bot.created_at).all()
    conv_bot_ids = {cb.bot_id for cb in active_conv.conversation_bots}

    return render_template(
        "index.html",
        conversations=conversations,
        active_conv=active_conv,
        all_bots=all_bots,
        conv_bot_ids=conv_bot_ids,
        messages=active_conv.messages[-50:],
    )


@conversations_bp.route("/conversations", methods=["POST"])
def create():
    name = request.form.get("name", "").strip() or "New Chat"
    conv = Conversation(name=name)
    db.session.add(conv)
    db.session.commit()
    _add_all_bots(conv.id)
    return redirect(url_for("conversations.index", conv_id=conv.id))


@conversations_bp.route("/conversations/<int:conv_id>", methods=["DELETE"])
def delete(conv_id):
    conv = Conversation.query.get_or_404(conv_id)
    db.session.delete(conv)
    db.session.commit()
    return "", 200


@conversations_bp.route("/conversations/<int:conv_id>/bots", methods=["POST"])
def add_bot(conv_id):
    bot_id = request.form.get("bot_id", type=int)
    if not ConversationBot.query.filter_by(conversation_id=conv_id, bot_id=bot_id).first():
        db.session.add(ConversationBot(conversation_id=conv_id, bot_id=bot_id))
        db.session.commit()
    return redirect(url_for("conversations.index", conv_id=conv_id))


@conversations_bp.route("/conversations/<int:conv_id>/bots/<int:bot_id>", methods=["DELETE"])
def remove_bot(conv_id, bot_id):
    cb = ConversationBot.query.filter_by(conversation_id=conv_id, bot_id=bot_id).first_or_404()
    bot_name = cb.bot.name
    db.session.delete(cb)
    db.session.add(Message(
        conversation_id=conv_id,
        sender_name="RouterBot",
        sender_type="system",
        content=f"{bot_name} removed from chat",
    ))
    db.session.commit()
    return "", 200


def _add_all_bots(conv_id):
    for bot in Bot.query.all():
        if not ConversationBot.query.filter_by(conversation_id=conv_id, bot_id=bot.id).first():
            db.session.add(ConversationBot(conversation_id=conv_id, bot_id=bot.id))
    db.session.commit()
