from django.test import TestCase

from aichatbottasks import models
from aichatbottasks import utils
from utils.logging import TraceLogger


class AIChatBotTaskUtilsTest(TestCase):
    def test_interrupt_task_decorator(self):
        @utils.interrupt_task_if_error
        def f(*, aichatbottask_id: int):
            raise Exception()

        task = models.Task.objects.create(object_id="123", status=models.Task.Status.PENDING)

        try:
            f(aichatbottask_id=task.pk)
        except:
            pass

        task.refresh_from_db()
        assert task.status == models.Task.Status.INTERRUPTED, f"Task has status '{task.status}'"

    def test_interrupt_task_decorator_without_exception(self):
        @utils.interrupt_task_if_error
        def f(*, aichatbottask_id: int):
            pass

        task = models.Task.objects.create(object_id="123", status=models.Task.Status.PENDING)

        try:
            f(aichatbottask_id=task.pk)
        except:
            pass

        task.refresh_from_db()
        assert task.status == models.Task.Status.PENDING, f"Task has status '{task.status}'"

    def test_cancel_tasks(self):
        object_id = "123"

        t1 = models.Task.objects.create(object_id=object_id)
        t2 = models.Task.objects.create(object_id=object_id)

        utils.cancel_tasks(except_task_id=t2.pk, tlogger=TraceLogger())

        t1.refresh_from_db()
        assert t1.status == models.Task.Status.CANCELED, f"Task has status '{t1.status}', expected CANCELED"

    def test_cancel_tasks_when_current_task_canceled(self):
        object_id = "123"

        t1 = models.Task.objects.create(object_id=object_id)
        t2 = models.Task.objects.create(object_id=object_id)

        utils.cancel_tasks(except_task_id=t2.pk, tlogger=TraceLogger())
        success_cancel = utils.cancel_tasks(except_task_id=t1.pk, tlogger=TraceLogger())

        t2.refresh_from_db()

        assert t2.status == models.Task.Status.PENDING, f"Task has status '{t1.status}', expected PENDING"
        assert success_cancel is False, f"Ok flag is {success_cancel}, expected False"

    def test_change_status(self):
        t = models.Task.objects.create(object_id="123")
        success_changed = utils.change_task_status(
            task_id=t.pk,
            new_status=models.Task.Status.ANSWER_GENERATION,
            tlogger=TraceLogger(),
        )

        t.refresh_from_db()

        assert t.status == models.Task.Status.ANSWER_GENERATION, f"Task has status '{t.status}', expected ANSWER_GENERATION"
        assert success_changed is True, f"Ok flag is {success_changed}, expected True"

    def test_change_status_when_current_task_canceled(self):
        t = models.Task.objects.create(object_id="123")
        models.Task.objects.filter(pk=t.pk).update(status=models.Task.Status.CANCELED)
        success_changed = utils.change_task_status(
            task_id=t.pk,
            new_status=models.Task.Status.ANSWER_GENERATION,
            tlogger=TraceLogger(),
        )

        t.refresh_from_db()

        assert t.status == models.Task.Status.CANCELED, f"Task has status '{t.status}', expected CANCELED"
        assert success_changed is False, f"Ok flag is {success_changed}, expected False"
