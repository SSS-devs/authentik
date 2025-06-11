import pickle  # nosec
from uuid import uuid4

import pgtrigger
from cron_converter import Cron
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.timezone import datetime
from django.utils.translation import gettext_lazy as _
from dramatiq.actor import Actor
from dramatiq.broker import Broker, get_broker
from dramatiq.message import Message

from authentik.lib.models import SerializerModel
from authentik.tasks.schedules.lib import ScheduleSpec


def validate_crontab(value):
    try:
        Cron(value)
    except ValueError as exc:
        raise ValidationError(
            _("%(value)s is not a valid crontab"),
            params={"value": value},
        ) from exc


class Schedule(SerializerModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    uid = models.TextField(unique=True, editable=False, help_text=_("Unique schedule identifier"))

    actor_name = models.TextField(editable=False, help_text=_("Dramatiq actor to call"))
    args = models.BinaryField(editable=False, help_text=_("Args to send to the actor"))
    kwargs = models.BinaryField(editable=False, help_text=_("Kwargs to send to the actor"))
    options = models.BinaryField(editable=False, help_text=_("Options to send to the actor"))

    rel_obj_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    rel_obj_id = models.TextField(null=True)
    rel_obj = GenericForeignKey("rel_obj_content_type", "rel_obj_id")

    crontab = models.TextField(validators=[validate_crontab], help_text=_("When to schedule tasks"))
    paused = models.BooleanField(default=False, help_text=_("Pause this schedule"))

    next_run = models.DateTimeField(auto_now_add=True, editable=False)

    class Meta:
        verbose_name = _("Schedule")
        verbose_name_plural = _("Schedules")
        default_permissions = (
            "change",
            "view",
        )
        permissions = [
            ("send_schedule", _("Manually trigger a schedule")),
        ]
        indexes = (models.Index(fields=("rel_obj_content_type", "rel_obj_id")),)
        triggers = (
            pgtrigger.Trigger(
                name="set_next_run_on_paused",
                operation=pgtrigger.Update,
                when=pgtrigger.Before,
                condition=pgtrigger.Q(new__paused=True) & pgtrigger.Q(old__paused=False),
                func="""
                    NEW.next_run = to_timestamp(0);
                    RETURN NEW;
                """,
            ),
        )

    def __str__(self):
        return self.uid

    @classmethod
    def dispatch_by_actor(cls, actor: Actor):
        """Dispatch a schedule by looking up its actor.
        Only available for schedules without custom arguments."""
        schedule = cls.objects.filter(actor_name=actor.actor_name, paused=False).first()
        if schedule:
            schedule.send()

    @property
    def serializer(self):
        from authentik.tasks.schedules.api import ScheduleSerializer

        return ScheduleSerializer

    def send(self, broker: Broker | None = None) -> Message:
        broker = broker or get_broker()
        actor: Actor = broker.get_actor(self.actor_name)
        return actor.send_with_options(
            args=pickle.loads(self.args),  # nosec
            kwargs=pickle.loads(self.kwargs),  # nosec
            rel_obj=self,
            **pickle.loads(self.options),  # nosec
        )

    # TODO: actually do loop here
    def calculate_next_run(self, next_run: datetime) -> datetime:
        return Cron(self.crontab).schedule(next_run).next()


class ScheduledModel(models.Model):
    schedules = GenericRelation(
        Schedule, content_type_field="rel_obj_content_type", object_id_field="rel_obj_id"
    )

    class Meta:
        abstract = True

    @property
    def schedule_specs(self) -> list[ScheduleSpec]:
        raise NotImplementedError
