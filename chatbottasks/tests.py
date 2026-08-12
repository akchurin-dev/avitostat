from django.test import TestCase

from chatbottasks.models import TestTaskModel
from utils.logging import TraceLogger


class AIChatBotTaskUtilsTest(TestCase):
    def test_interrupt_task_decorator(self):
        @TestTaskModel.interrupt_task_if_error
        def f(*, task_id, tlogger):
            raise Exception()

        task = TestTaskModel.objects.create(object_id="123", status=TestTaskModel.Status.PENDING)

        try:
            f(task_id=task.pk, tlogger=TraceLogger())
        except:
            pass

        task.refresh_from_db()
        assert task.status == TestTaskModel.Status.INTERRUPTED, f"Task has status '{task.status}'"

    def test_interrupt_task_decorator_without_exception_with_tlogger(self):
        @TestTaskModel.interrupt_task_if_error
        def f(*, task_id, tlogger):
            pass

        task = TestTaskModel.objects.create(object_id="123", status=TestTaskModel.Status.PENDING)

        f(task_id=task.pk, tlogger=TraceLogger())

        task.refresh_from_db()
        assert task.status == TestTaskModel.Status.PENDING, f"Task has status '{task.status}'"

    def test_interrupt_task_decorator_without_exception_with_trace_id(self):
        @TestTaskModel.interrupt_task_if_error
        def f(*, task_id, trace_id):
            pass

        task = TestTaskModel.objects.create(object_id="123", status=TestTaskModel.Status.PENDING)

        f(task_id=task.pk, trace_id=None)

        task.refresh_from_db()
        assert task.status == TestTaskModel.Status.PENDING, f"Task has status '{task.status}'"

    def test_cancel_tasks(self):
        object_id = "123"

        t1 = TestTaskModel.objects.create(object_id=object_id)
        t2 = TestTaskModel.objects.create(object_id=object_id)

        TestTaskModel.cancel_tasks(except_task_id=t2.pk, tlogger=TraceLogger())

        t1.refresh_from_db()
        assert t1.status == TestTaskModel.Status.CANCELED, f"Task has status '{t1.status}', expected CANCELED"

    def test_cancel_tasks_when_current_task_canceled(self):
        object_id = "123"

        t1 = TestTaskModel.objects.create(object_id=object_id)
        t2 = TestTaskModel.objects.create(object_id=object_id)

        TestTaskModel.cancel_tasks(except_task_id=t2.pk, tlogger=TraceLogger())
        success_cancel = TestTaskModel.cancel_tasks(except_task_id=t1.pk, tlogger=TraceLogger())

        t2.refresh_from_db()

        assert t2.status == TestTaskModel.Status.PENDING, f"Task has status '{t1.status}', expected PENDING"
        assert success_cancel is False, f"Ok flag is {success_cancel}, expected False"

    def test_change_status(self):
        t = TestTaskModel.objects.create(object_id="123")
        success_changed = TestTaskModel.change_task_status(
            task_id=t.pk,
            new_status=TestTaskModel.Status.ANSWER_GENERATION,
            tlogger=TraceLogger(),
        )

        t.refresh_from_db()

        assert t.status == TestTaskModel.Status.ANSWER_GENERATION, f"Task has status '{t.status}', expected ANSWER_GENERATION"
        assert success_changed is True, f"Ok flag is {success_changed}, expected True"

    def test_change_status_when_current_task_canceled(self):
        t = TestTaskModel.objects.create(object_id="123")
        TestTaskModel.objects.filter(pk=t.pk).update(status=TestTaskModel.Status.CANCELED)
        success_changed = TestTaskModel.change_task_status(
            task_id=t.pk,
            new_status=TestTaskModel.Status.ANSWER_GENERATION,
            tlogger=TraceLogger(),
        )

        t.refresh_from_db()

        assert t.status == TestTaskModel.Status.CANCELED, f"Task has status '{t.status}', expected CANCELED"
        assert success_changed is False, f"Ok flag is {success_changed}, expected False"
