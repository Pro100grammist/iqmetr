import os
import json
from decimal import Decimal
from typing import Dict, Any, List

import requests
from django.utils import timezone

from practice.utils import compile_final_document
from practice.services.decisions import load_txt
from django.conf import settings


def _first_non_empty(*vals: str) -> str:
    for v in vals:
        if isinstance(v, str) and v.strip():
            return v
    return ""


def _ensure_decisions_cache(task) -> Dict[str, Dict[str, str]]:
    """
    Guarantee we have decision texts in cache. If cache is empty, attempt to
    read from files specified in task.decisions_json.
    """
    cache = task.decisions_cache or {}
    links = task.decisions_json or {}
    if cache:
        return cache
    out = {}
    for key in ("first", "appeal", "cassation"):
        src = links.get(key)
        if not src:
            continue
        try:
            txt = load_txt(src, settings.BASE_DIR)
            out[key] = {"type": "file-txt", "text": txt, "source": src}
        except Exception:
            # ignore if missing; evaluator can still operate
            pass
    return out


def _truncate(s: str, max_chars: int = 16000) -> str:
    if not isinstance(s, str):
        return ""
    if len(s) <= max_chars:
        return s
    head = s[: max_chars - 200]
    return head + "\n\n[... truncated ...]"


def _build_messages(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    rubric = payload["rubric"] or {}
    spec = payload.get("spec", "")
    task = payload.get("task", {})
    candidate = payload.get("candidate", {})

    # Compose compact decisions text bundle
    dec = task.get("decisions", {}) or {}
    ref_bundle = []
    for k in ("first", "appeal", "cassation"):
        t = (dec.get(k) or {}).get("text", "")
        if t:
            ref_bundle.append(f"== {k.upper()} DECISION ==\n{_truncate(t)}")
    ref_text = "\n\n".join(ref_bundle) if ref_bundle else "(no reference decisions available)"

    compiled = payload.get("compiled_document") or (
        _truncate("\n\n".join([_first_non_empty(candidate.get("motivation_text"), ""), _first_non_empty(candidate.get("resolution_text"), "")])))

    system = (
        "Ти — експерт-оцінювач судових рішень. Оціни фіналізований документ за методикою "
        "(розбивка на групи та критерії з максимальними балами). Поверни строго JSON."
    )

    schema_hint = {
        "total": "number (sum of group scores, <= rubric.total_max)",
        "groups": [
            {
                "key": "group key",
                "title": "group title",
                "max": "number",
                "score": "number (0..max)",
                "criteria": [
                    {
                        "key": "criterion key",
                        "title": "criterion title",
                        "max": "number",
                        "score": "number (0..max)",
                        "deductions": "short explanation what is missing/incorrect",
                    }
                ],
            }
        ],
        "feedback": "overall summary of deductions and suggestions",
    }

    user_parts = [
        f"СПЕЦІАЛІЗАЦІЯ: {spec}",
        "\nРУБРИКА (JSON):\n" + json.dumps(rubric, ensure_ascii=False),
        "\nЕТАЛОННІ РІШЕННЯ:\n" + ref_text,
        "\n\nДОКУМЕНТ КАНДИДАТА:\n" + compiled,
        "\nВИМОГИ ДО ВИХОДУ: поверни JSON згідно схеми нижче, числа — десяткові; дотримуйся max.",
        "СХЕМА JSON:\n" + json.dumps(schema_hint, ensure_ascii=False),
    ]

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]


def _parse_json_content(text: str) -> Dict[str, Any]:
    s = (text or "").strip()
    # strip ```json ... ``` if present
    if s.startswith("```"):
        s = s.strip("`\n ")
        # remove possible leading 'json' word
        if s.lower().startswith("json"):
            s = s[4:].lstrip()
    try:
        return json.loads(s)
    except Exception:
        # Attempt to find the first {...} block
        try:
            start = s.find("{")
            end = s.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(s[start : end + 1])
        except Exception:
            pass
    return {}


def _postprocess_scores(rubric: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    groups = data.get("groups") or []
    # Ensure numeric and clamped
    total = Decimal("0")
    for g in groups:
        g_max = Decimal(str(g.get("max") or 0))
        g_score = Decimal(str(g.get("score") or 0))
        crits = g.get("criteria") or []
        csum = Decimal("0")
        for c in crits:
            c_max = Decimal(str(c.get("max") or 0))
            c_score = Decimal(str(c.get("score") or 0))
            if c_score < 0:
                c_score = Decimal("0")
            if c_score > c_max:
                c_score = c_max
            c["score"] = float(c_score)
            csum += c_score
        # if model omitted group score, sum criteria
        if not g.get("score"):
            g_score = csum
        # clamp to group max
        if g_score > g_max:
            g_score = g_max
        if g_score < 0:
            g_score = Decimal("0")
        g["score"] = float(g_score)
        total += g_score

    # Clamp to rubric total_max
    rubric_total = Decimal(str(rubric.get("total_max") or 75))
    if total > rubric_total:
        total = rubric_total

    out = {
        "groups": groups,
        "rubric": {
            "name": rubric.get("name"),
            "version": rubric.get("version"),
            "total_max": rubric.get("total_max"),
        },
    }
    return out, total


def _call_openai(messages: List[Dict[str, str]], model: str, timeout: int) -> Dict[str, Any]:
    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        base_url = base_url.rstrip("/")
        url = f"{base_url}/chat/completions"
    else:
        url = "https://api.openai.com/v1/chat/completions"
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": messages,
        "max_tokens": 1800,
    }
    r = requests.post(url, headers=headers, json=body, timeout=timeout)
    r.raise_for_status()
    js = r.json()
    content = js.get("choices", [{}])[0].get("message", {}).get("content", "")
    parsed = _parse_json_content(content)
    return {"raw": js, "parsed": parsed}


def call_ai_evaluator(session, ev, timeout=120):
    """
    Оцінює фінальний документ за рубрикою.
    Джерела:
    - Рубрика береться з session.task.rubric (civil_v1.json / criminal_v1.json через apply_rubric)
    - Еталонні рішення — з decisions_cache або decisions_json (TXT файли)
    Використання AI:
    - Якщо задано AI_EVAL_ENDPOINT/AI_EVAL_API_KEY — викликаємо зовнішній сервіс.
    - Інакше, якщо OPENAI_API_KEY — викликаємо OpenAI Chat Completions і просимо JSON.
    - Інакше повертаємо заглушку-демо результат.
    """
    endpoint = os.getenv("AI_EVAL_ENDPOINT")
    api_key = os.getenv("AI_EVAL_API_KEY")

    rubric = session.task.rubric or {}
    if not rubric:
        # Fallback: load rubric from repo JSON by spec
        try:
            from pathlib import Path
            base = Path(settings.BASE_DIR)
            if session.spec == "civil":
                rp = base / "data/practice/rubrics/civil_v1.json"
            else:
                rp = base / "data/practice/rubrics/criminal_v1.json"
            if rp.exists():
                rubric = json.loads(rp.read_text(encoding="utf-8"))
        except Exception:
            rubric = {}
    decisions = _ensure_decisions_cache(session.task)
    compiled = compile_final_document(session)

    payload = {
        "spec": session.spec,
        "rubric": rubric,
        "max_score": str(session.task.max_score),
        "task": {
            "intro_text": session.task.intro_text,
            "descriptive_text": session.task.descriptive_text,
            "partial_motivation_text": session.task.partial_motivation_text,
            "facts_text": session.task.facts_text,
            "model_intro_text": session.task.model_intro_text,
            "decisions": decisions,
        },
        "candidate": {
            "motivation_text": session.motivation_text,
            "resolution_text": session.resolution_text,
        },
        "compiled_document": _truncate(compiled, 24000),
        "meta": {
            "duration_sec": int(
                ((session.finished_at or timezone.now()) - session.started_at).total_seconds()
            ),
            "keypress_count": session.keypress_count,
            "paste_blocked": session.paste_blocked,
        },
    }

    data: Dict[str, Any]
    model_name = ""

    if endpoint and api_key:
        try:
            r = requests.post(
                endpoint,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=timeout,
            )
            r.raise_for_status()
            data = r.json()
            model_name = os.getenv("AI_EVAL_MODEL", "external")
        except Exception:
            data = None
    if not locals().get("data") and os.getenv("OPENAI_API_KEY"):
        try:
            # Build and call OpenAI directly
            messages = _build_messages(payload)
            result = _call_openai(messages, os.getenv("OPENAI_MODEL", "gpt-4o-mini"), timeout)
            parsed = result.get("parsed") or {}
            post, total = _postprocess_scores(rubric, parsed)
            data = {
                "total": float(total),
                "scores": post,
                "feedback": parsed.get("feedback", ""),
                "raw": result.get("raw"),
            }
            model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        except Exception:
            data = None
    else:
        # Заглушка (локально/якщо API не налаштоване)
        # побудуємо просте flat оцінювання від рубрики: усі групи = 70% від макс.
        groups = []
        total = Decimal("0")
        for g in (rubric.get("groups") or []):
            gmax = Decimal(str(g.get("max") or 0))
            gscore = (gmax * Decimal("0.7")).quantize(Decimal("0.1"))
            crits = []
            for c in (g.get("criteria") or []):
                cmax = Decimal(str(c.get("max") or 0))
                cscore = (cmax * Decimal("0.7")).quantize(Decimal("0.1"))
                crits.append(
                    {
                        "key": c.get("key"),
                        "title": c.get("title"),
                        "max": float(cmax),
                        "score": float(cscore),
                        "deductions": "Демо: приблизно 30% знято як приклад.",
                    }
                )
            total += gscore
            groups.append(
                {
                    "key": g.get("key"),
                    "title": g.get("title"),
                    "max": float(gmax),
                    "score": float(gscore),
                    "criteria": crits,
                }
            )
        data = {
            "total": float(total),
            "scores": {
                "groups": groups,
                "rubric": {
                    "name": rubric.get("name"),
                    "version": rubric.get("version"),
                    "total_max": rubric.get("total_max"),
                },
            },
            "feedback": "Демонстраційна оцінка: структура виконана загалом коректно; зверніть увагу на чіткість висновків і посилання на практику ВС.",
        }
        model_name = "stub"

    if not locals().get("data"):
        # final safety fallback to stub if previous branches failed
        groups = []
        total = Decimal("0")
        for g in (rubric.get("groups") or []):
            gmax = Decimal(str(g.get("max") or 0))
            gscore = (gmax * Decimal("0.7")).quantize(Decimal("0.1"))
            crits = []
            for c in (g.get("criteria") or []):
                cmax = Decimal(str(c.get("max") or 0))
                cscore = (cmax * Decimal("0.7")).quantize(Decimal("0.1"))
                crits.append(
                    {
                        "key": c.get("key"),
                        "title": c.get("title"),
                        "max": float(cmax),
                        "score": float(cscore),
                        "deductions": "Демо: приблизно 30% знято як приклад.",
                    }
                )
            total += gscore
            groups.append(
                {
                    "key": g.get("key"),
                    "title": g.get("title"),
                    "max": float(gmax),
                    "score": float(gscore),
                    "criteria": crits,
                }
            )
        data = {
            "total": float(total),
            "scores": {
                "groups": groups,
                "rubric": {
                    "name": rubric.get("name"),
                    "version": rubric.get("version"),
                    "total_max": rubric.get("total_max"),
                },
            },
            "feedback": "Оцінювання виконано у демонстраційному режимі (мережевий виклик недоступний).",
        }
        model_name = (model_name or "stub")

    # Persist
    scores = data.get("scores", {})
    total_val = Decimal(str(data.get("total", 0)))
    feedback = data.get("feedback", "")

    ev.scores = scores
    ev.total = total_val
    ev.feedback = feedback
    ev.status = "done"
    ev.completed_at = timezone.now()
    ev.model_name = model_name
    # Store raw response if present
    raw = data.get("raw")
    if raw:
        ev.raw_response = raw
    ev.save(
        update_fields=[
            "scores",
            "total",
            "feedback",
            "status",
            "completed_at",
            "model_name",
            "raw_response",
        ]
    )
