from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from app import db
from app.models import Bot
from app.services import ollama

bots_bp = Blueprint("bots", __name__)


@bots_bp.route("/bots", methods=["POST"])
def create():
    conv_id = request.form.get("conv_id", type=int)
    name = request.form.get("name", "").strip()
    role = request.form.get("role", "Custom Bot").strip()
    system_prompt = request.form.get("system_prompt", "").strip()
    model_name = request.form.get("model_name", "tinyllama").strip()

    if not name or not system_prompt:
        return redirect(url_for("conversations.index", conv_id=conv_id))

    if not Bot.query.filter_by(name=name).first():
        bot = Bot(name=name, role=role, system_prompt=system_prompt, model_name=model_name, is_default=False)
        db.session.add(bot)
        db.session.commit()

        if conv_id:
            from app.models import ConversationBot
            db.session.add(ConversationBot(conversation_id=conv_id, bot_id=bot.id))
            db.session.commit()

    return redirect(url_for("conversations.index", conv_id=conv_id))


@bots_bp.route("/bots/<int:bot_id>", methods=["POST"])
def update(bot_id):
    conv_id = request.form.get("conv_id", type=int)
    bot = Bot.query.get_or_404(bot_id)

    bot.role = request.form.get("role", bot.role).strip()
    bot.system_prompt = request.form.get("system_prompt", bot.system_prompt).strip()
    bot.model_name = request.form.get("model_name", bot.model_name).strip()
    if not bot.is_default:
        bot.name = request.form.get("name", bot.name).strip()

    db.session.commit()
    return redirect(url_for("conversations.index", conv_id=conv_id))


@bots_bp.route("/bots/<int:bot_id>/delete", methods=["POST"])
def delete(bot_id):
    conv_id = request.form.get("conv_id", type=int)
    bot = Bot.query.get_or_404(bot_id)
    if not bot.is_default:
        db.session.delete(bot)
        db.session.commit()
    return redirect(url_for("conversations.index", conv_id=conv_id))


@bots_bp.route("/ollama/models")
def models():
    return jsonify(ollama.list_models())
