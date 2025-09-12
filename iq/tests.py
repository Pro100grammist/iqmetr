# iq/tests.py
from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from .models import Question, Answer, TestSession, Response
from django.urls import reverse
from datetime import timedelta


class ScoringTests(TestCase):
    def setUp(self):
        q1 = Question.objects.create(
            number=1, text="Q1", difficulty="easy", score=Decimal("1.22")
        )
        q2 = Question.objects.create(
            number=2, text="Q2", difficulty="hard", score=Decimal("2.16")
        )
        a11 = Answer.objects.create(question=q1, text="A1", is_correct=True)
        Answer.objects.create(question=q1, text="A2")
        Answer.objects.create(question=q1, text="A3")
        Answer.objects.create(question=q1, text="A4")
        a21 = Answer.objects.create(question=q2, text="B1", is_correct=True)
        Answer.objects.create(question=q2, text="B2")
        Answer.objects.create(question=q2, text="B3")
        Answer.objects.create(question=q2, text="B4")
        self.session = TestSession.objects.create(
            name="T", age=20, question_ids=[q1.id, q2.id]
        )

    def test_sum_scores(self):
        s = self.session
        q_ids = s.question_ids
        for qid in q_ids:
            q = Question.objects.get(id=qid)
            a = q.answers.get(is_correct=True)
            Response.objects.create(
                session=s,
                question=q,
                selected_answer=a,
                is_correct=True,
                score_awarded=q.score,
            )
        total = sum(r.score_awarded for r in s.responses.all())
        self.assertEqual(total, Decimal("3.38"))


class TimeoutTests(TestCase):
    def test_timeout_finish(self):
        q = Question.objects.create(
            number=1, text="Q", difficulty="easy", score=Decimal("1.22")
        )
        for i in range(4):
            Answer.objects.create(question=q, text=f"A{i}", is_correct=(i == 0))
        s = TestSession.objects.create(name="T", age=30, question_ids=[q.id])
        # Застеримо сесію як прострочену
        s.started_at = timezone.now() - timedelta(minutes=21)
        s.save(update_fields=["started_at"])
        url = reverse("test", kwargs={"session_uuid": s.uuid})
        resp = self.client.get(url, follow=False)
        self.assertEqual(resp.status_code, 302)  # редирект
        self.assertIn("/finish/", resp["Location"])  # на finish
