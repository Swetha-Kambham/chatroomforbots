import os
import re
from app.services import ollama

THRESHOLD = int(os.getenv("ROUTER_CONFIDENCE_THRESHOLD", "1"))
ROUTER_MODEL = os.getenv("ROUTER_MODEL", os.getenv("DEFAULT_MODEL", "tinyllama"))

KEYWORD_MAP = {
    "EmailBot": [
        "email", "inbox", "send", "reply", "forward", "subject",
        "draft", "attachment", "compose", "newsletter", "recipient",
        "unsubscribe", "mail",
    ],
    "CodeBot": [
        "code", "function", "bug", "script", "debug", "python",
        "javascript", "error", "fix", "syntax", "class", "import",
        "variable", "loop", "algorithm", "api", "database", "sql",
        "html", "css", "git", "compile", "runtime", "exception",
    ],
    "AccountingBot": [
        "invoice", "budget", "tax", "expense", "payment", "cost",
        "finance", "money", "receipt", "profit", "loss", "revenue",
        "salary", "accounting", "account", "accounts", "balance",
        "sheet", "audit", "debit", "credit", "cash", "spend", "income",
    ],
    "JokeBot": [
        "joke", "funny", "laugh", "humor", "pun", "comedy",
        "entertain", "hilarious", "witty", "riddle", "lol",
    ],
}

_ROUTER_RULES_AND_EXAMPLES = (
    "Rules:\n"
    "1. If the message clearly belongs to a specialist bot, choose that bot.\n"
    "2. If the message is a follow-up, reply, or continuation (e.g. 'okay', 'thanks', 'what else?', 'can you explain more?'), stay with the last active bot.\n"
    "3. If the message is ambiguous and there is a last active bot, prefer that bot over the catch-all bot.\n"
    "4. Only choose the catch-all bot for explicit greetings, jokes, or messages with no connection to any specialist topic.\n\n"
    "Examples:\n"
    "Message: help me write an email → EmailBot\n"
    "Message: I have a bug in my Python code → CodeBot\n"
    "Message: I need help with my invoice → AccountingBot\n"
    "Message: tell me a joke → JokeBot\n"
    "Message: hi → JokeBot\n"
    "Message: okay thanks [Last bot: AccountingBot] → AccountingBot\n"
    "Message: what should I do next? [Last bot: CodeBot] → CodeBot\n"
    "Message: can you help me? [Last bot: EmailBot] → EmailBot\n\n"
    "Reply with ONLY the bot name. No explanation. No punctuation."
)


def _build_system_prompt(bot_info: list[dict]) -> str:
    """Build router system prompt dynamically from active bots and their roles/system prompts."""
    lines = ["You are a message router for a multi-bot chatroom. Decide which bot should respond.\n"]
    lines.append("Bots and what they handle:")
    for bot in bot_info:
        # Use role as label + first 150 chars of system_prompt for richer routing context
        snippet = (bot.get("system_prompt") or "")[:150].replace("\n", " ").strip()
        description = f"{bot['role']} — {snippet}" if snippet else bot["role"]
        lines.append(f"- {bot['name']}: {description}")
    lines.append("")
    lines.append(_ROUTER_RULES_AND_EXAMPLES)
    return "\n".join(lines)


HIGH_CONFIDENCE = 2  # keyword matches needed to skip LLM entirely

def route(message: str, bot_info: list[dict], last_bot: str | None = None, history: list[dict] | None = None) -> tuple[str, str]:
    """
    Returns (bot_name, method) where method is 'keyword', 'llm', 'context', or 'fallback'.
    bot_info: list of {"name": str, "role": str} for all active bots.
    Fast path: 2+ keyword matches → instant route, no LLM call.
    Semantic path: LLM with conversation history for ambiguous messages.
    Context fallback: stay with last active bot rather than jumping to JokeBot.
    """
    available_bot_names = [b["name"] for b in bot_info]

    scores = _keyword_scores(message.lower())
    top_score = max(scores.values())
    top_bots = [bot for bot, score in scores.items() if score == top_score and bot in available_bot_names]
    top_bots_any = [bot for bot, score in scores.items() if score == top_score and score > 0]

    # Fast path — high confidence keyword match, skip LLM
    if top_score >= HIGH_CONFIDENCE and len(top_bots) == 1:
        return top_bots[0], "keyword"

    # If keyword clearly points to a specialist not in this conversation, don't let LLM guess wrong
    if top_score >= THRESHOLD and len(top_bots_any) == 1 and top_bots_any[0] not in available_bot_names:
        fallback = "JokeBot" if "JokeBot" in available_bot_names else available_bot_names[0]
        return fallback, f"unavailable:{top_bots_any[0]}"

    # Semantic path — LLM with conversation context
    llm_result = _llm_route(message, bot_info, last_bot, history)
    if llm_result:
        return llm_result, "llm"

    # Low confidence keyword fallback
    if top_score >= THRESHOLD and len(top_bots) == 1:
        return top_bots[0], "keyword"

    # Stay with last active bot rather than jumping to JokeBot
    if last_bot and last_bot in available_bot_names and last_bot != "JokeBot":
        return last_bot, "context"

    fallback = "JokeBot" if "JokeBot" in available_bot_names else available_bot_names[0]
    return fallback, "fallback"


def _keyword_scores(message: str) -> dict[str, int]:
    scores = {bot: 0 for bot in KEYWORD_MAP}
    for bot, keywords in KEYWORD_MAP.items():
        for kw in keywords:
            # prefix match: \bfinance matches finance, finances, financial, etc.
            if re.search(r'\b' + re.escape(kw), message):
                scores[bot] += 1
    return scores


def _llm_route(message: str, bot_info: list[dict], last_bot: str | None = None, history: list[dict] | None = None) -> str | None:
    available_bot_names = [b["name"] for b in bot_info]
    try:
        context = ""
        if history:
            recent = history[-3:]
            lines = "\n".join(f"  {m['sender_name']}: {m['content'][:120]}" for m in recent)
            context += f"Recent conversation:\n{lines}\n"
        if last_bot:
            context += f"Last bot active: {last_bot}\n"
        prompt = f"{context}New message: {message}\nBot:"
        response = ollama.chat(
            model=ROUTER_MODEL,
            system_prompt=_build_system_prompt(bot_info),
            messages=[],
            user_message=prompt,
        )
        for word in response.strip().split():
            candidate = word.strip(".,!?:\"'")
            if candidate in available_bot_names:
                return candidate
    except Exception:
        pass
    return None
