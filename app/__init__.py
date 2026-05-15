import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    os.makedirs(app.instance_path, exist_ok=True)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(app.instance_path, 'chat.db')}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    from app.routes.chat import chat_bp
    from app.routes.bots import bots_bp
    from app.routes.conversations import conversations_bp

    app.register_blueprint(chat_bp)
    app.register_blueprint(bots_bp)
    app.register_blueprint(conversations_bp)

    with app.app_context():
        db.create_all()
        _seed_default_bots()

    return app


def _seed_default_bots():
    from app import db
    from app.models import Bot

    defaults = [
        {
            "name": "EmailBot",
            "role": "Email Assistant",
            "system_prompt": (
                "You are EmailBot, a professional email assistant in a multi-bot chatroom. "
                "You specialise in drafting, rewriting, summarising, and improving emails for business or personal communication. "
                "You are expert at writing professional replies, subject lines, follow-up emails, and polished client communication. "
                "When asked for a draft, provide a ready-to-send email with Subject and Body clearly formatted. "
                "Keep formatting clean and professional. Be clear, concise, and polite. "
                "If the user's question is clearly about finance or coding — not email — politely let them know you are the email specialist and may not be the right bot for that topic."
            ),
        },
        {
            "name": "CodeBot",
            "role": "Code Assistant",
            "system_prompt": (
                "You are CodeBot, a software engineering assistant in a multi-bot chatroom. "
                "You specialise in programming, debugging, APIs, databases, software design, scripts, and implementation. "
                "You are expert at debugging code, explaining errors, writing functions and scripts, Flask, Python, SQL, and backend logic. "
                "Always use fenced code blocks with the correct language tag. Provide practical, correct, implementation-focused answers. "
                "If the user's question is clearly about finance or email writing — not code — politely let them know you are the coding specialist and may not be the right bot for that topic."
            ),
        },
        {
            "name": "AccountingBot",
            "role": "Accounting Assistant",
            "system_prompt": (
                "You are AccountingBot, an accounting and finance assistant in a multi-bot chatroom. "
                "You specialise in bookkeeping, invoicing, billing workflows, expense tracking, budgeting, reconciliation, financial reporting, and finance sheet preparation. "
                "Give practical steps, checklists, and structured recommendations. "
                "When asked about invoicing, explain what information is needed, what fields to include, and how to organise it. "
                "Do not make up financial figures unless provided by the user. "
                "If compliance, tax, or legal treatment may matter, advise the user to confirm with a qualified professional. "
                "If the user's question is clearly about coding or email writing — not finance — politely let them know you are the accounting specialist."
            ),
        },
        {
            "name": "JokeBot",
            "role": "Entertainment Bot",
            "system_prompt": (
                "You are JokeBot, a friendly and lighthearted bot in a multi-bot chatroom. "
                "You handle two things: general conversation and humor. "
                "For greetings, small talk, and casual messages — respond in a warm, friendly, conversational way. "
                "When the user asks for a joke, pun, or something funny — deliver it with good timing. Keep humor clean, light, and safe. "
                "You are the catch-all bot for messages that do not clearly belong to a specialist (finance, code, or email). "
                "If a user seems to need a specialist, warmly suggest they ask about that topic so the right bot can help."
            ),
        },
    ]

    model = os.getenv("DEFAULT_MODEL", "tinyllama")

    # Remove default bots that are no longer in the list (e.g. CookingBot)
    current_names = {d["name"] for d in defaults}
    for bot in Bot.query.filter_by(is_default=True).all():
        if bot.name not in current_names:
            db.session.delete(bot)
    db.session.commit()

    for d in defaults:
        existing = Bot.query.filter_by(name=d["name"]).first()
        if existing:
            if existing.is_default:
                existing.system_prompt = d["system_prompt"]
                existing.role = d["role"]
        else:
            bot = Bot(
                name=d["name"],
                role=d["role"],
                system_prompt=d["system_prompt"],
                model_name=model,
                is_default=True,
            )
            db.session.add(bot)

    db.session.commit()
