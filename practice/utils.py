def _norm(s: str) -> str:
    if not s:
        return ""
    # перетворюємо можливі '\\n' у реальні переноси та прибираємо зайві \r
    return s.replace("\r\n", "\n").replace("\r", "\n").replace("\\n", "\n").strip()


def compile_final_document(session) -> str:
    """Повертає зведений текст рішення згідно вимог:
    civil: Intro + Descriptive + Partial motivation + user Motivation + user Resolution
    criminal: Model intro + user Motivation + user Resolution
    """
    t = session.task
    spec = session.spec
    parts = []
    if spec == "civil":
        parts = [
            _norm(getattr(t, "intro_text", "")),
            _norm(getattr(t, "descriptive_text", "")),
            _norm(getattr(t, "partial_motivation_text", "")),
            _norm(getattr(session, "motivation_text", "")),
            _norm(getattr(session, "resolution_text", "")),
        ]
    else:  # criminal
        parts = [
            _norm(getattr(t, "model_intro_text", "")),
            _norm(getattr(session, "motivation_text", "")),
            _norm(getattr(session, "resolution_text", "")),
        ]
    # з'єднуємо подвійним переносом
    return "\n\n".join([p for p in parts if p])
