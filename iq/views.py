# iq/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import random

from .forms import StartForm
from .models import Question, Answer, TestSession, Response

TEST_QUESTION_COUNT = 30
TEST_DURATION_SECONDS = 20 * 60  # 20 хвилин


def start(request):
    """Стартова сторінка: ім'я + вік -> redirect на правила."""
    if request.method == "POST":
        form = StartForm(request.POST)
        if form.is_valid():
            request.session["candidate"] = (
                form.cleaned_data
            )  # тимчасово у сесії браузера
            return redirect("rules")
    else:
        form = StartForm()
    return render(request, "iq/start.html", {"form": form})


def rules(request):
    """Сторінка з правилами і кнопкою 'Почати' -> створюємо TestSession і кидаємо на тест."""
    candidate = request.session.get("candidate")
    if not candidate:
        return redirect("start")
    if request.method == "POST":
        # вибираємо 30 активних питань випадково
        q_ids = list(
            Question.objects.filter(is_active=True).values_list("id", flat=True)
        )
        if len(q_ids) < TEST_QUESTION_COUNT:
            return render(
                request,
                "iq/rules.html",
                {
                    "error": "Недостатньо питань у базі.",
                    "duration": TEST_DURATION_SECONDS,
                },
            )

        random.shuffle(q_ids)
        selected = q_ids[:TEST_QUESTION_COUNT]

        with transaction.atomic():
            session = TestSession.objects.create(
                name=candidate["name"],
                age=candidate["age"],
                question_ids=selected,
            )
        return redirect("test", session_uuid=session.uuid)

    return render(request, "iq/rules.html", {"duration": TEST_DURATION_SECONDS})


def test_view(request, session_uuid):
    """Сторінка тесту: 30 запитань з 4 відповідями, таймер, прогрес."""
    session = get_object_or_404(TestSession, uuid=session_uuid, is_completed=False)
    # обчислити скільки часу лишилось
    elapsed = (timezone.now() - session.started_at).total_seconds()
    remaining = max(0, int(TEST_DURATION_SECONDS - elapsed))
    if remaining == 0:
        return redirect("finish", session_uuid=session.uuid)

    # тягнемо питання в зафіксованому порядку
    questions = list(
        Question.objects.filter(id__in=session.question_ids).prefetch_related("answers")
    )
    # порядок як у session.question_ids:
    q_map = {q.id: q for q in questions}
    ordered_questions = [q_map[qid] for qid in session.question_ids if qid in q_map]

    if request.method == "POST":
        # приймаємо відповіді формату answer_<question_id> = <answer_id>
        with transaction.atomic():
            total = Decimal("0.00")
            for q in ordered_questions:
                field = f"answer_{q.id}"
                ans_id = request.POST.get(field)
                selected = (
                    Answer.objects.filter(id=ans_id, question=q).first()
                    if ans_id
                    else None
                )
                correct = bool(selected and selected.is_correct)
                score = q.score if correct else Decimal("0.00")
                Response.objects.update_or_create(
                    session=session,
                    question=q,
                    defaults={
                        "selected_answer": selected,
                        "is_correct": correct,
                        "score_awarded": score,
                    },
                )
                total += score

            # Якщо натиснули "Завершити" — або авто-фініш
            if "finish_now" in request.POST:
                session.total_score = total
                session.finished_at = timezone.now()
                session.is_completed = True
                session.save(
                    update_fields=["total_score", "finished_at", "is_completed"]
                )
                return redirect("result", session_uuid=session.uuid)

        # Інакше залишаємося на сторінці (наприклад, авто-збереження відповідей)
        return redirect("test", session_uuid=session.uuid)

    return render(
        request,
        "iq/test.html",
        {
            "session": session,
            "questions": ordered_questions,
            "remaining": remaining,
            "total_questions": len(ordered_questions),
        },
    )


def finish(request, session_uuid):
    """Фініш по таймеру."""
    session = get_object_or_404(TestSession, uuid=session_uuid)
    if not session.is_completed:
        # підрахунок якщо хтось нічого не обрав — 0; суму беремо з responses
        total = sum((r.score_awarded for r in session.responses.all()), Decimal("0.00"))
        session.total_score = total
        session.finished_at = timezone.now()
        session.is_completed = True
        session.save(update_fields=["total_score", "finished_at", "is_completed"])
    return redirect("result", session_uuid=session.uuid)


def result(request, session_uuid):
    """Фінальна сторінка з протоколом (де правильно/помилка по кожному питанню)."""
    session = get_object_or_404(TestSession, uuid=session_uuid)
    # дістаємо питання в вихідному порядку
    questions = list(
        Question.objects.filter(id__in=session.question_ids).prefetch_related("answers")
    )
    q_map = {q.id: q for q in questions}
    ordered_questions = [q_map[qid] for qid in session.question_ids if qid in q_map]

    # responses у dict
    resp_map = {
        r.question_id: r
        for r in session.responses.select_related("selected_answer", "question")
    }
    rows = []
    for q in ordered_questions:
        r = resp_map.get(q.id)
        rows.append(
            {
                "q": q,
                "selected": r.selected_answer if r else None,
                "is_correct": r.is_correct if r else False,
                "score": r.score_awarded if r else Decimal("0.00"),
                "correct_answer": next(
                    (a for a in q.answers.all() if a.is_correct), None
                ),
            }
        )

    return render(
        request,
        "iq/result.html",
        {
            "session": session,
            "rows": rows,
            "total": session.total_score,
        },
    )
