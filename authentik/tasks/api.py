from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.mixins import (
    ListModelMixin,
    RetrieveModelMixin,
)
from rest_framework.viewsets import GenericViewSet

from authentik.core.api.utils import ModelSerializer
from authentik.events.logs import LogEventSerializer
from authentik.tasks.models import Task
from authentik.tasks.schedules.models import Schedule
from authentik.tenants.utils import get_current_tenant


class TaskSerializer(ModelSerializer):
    messages = LogEventSerializer(many=True, source="_messages")

    class Meta:
        model = Task
        fields = [
            "message_id",
            "queue_name",
            "actor_name",
            "state",
            "mtime",
            "rel_obj_content_type",
            "rel_obj_id",
            "uid",
            "messages",
        ]


class TaskViewSet(
    RetrieveModelMixin,
    ListModelMixin,
    GenericViewSet,
):
    queryset = Task.objects.none()
    serializer_class = TaskSerializer
    search_fields = (
        "message_id",
        "queue_name",
        "actor_name",
        "state",
    )
    filterset_fields = (
        "queue_name",
        "actor_name",
        "state",
    )
    ordering = (
        "actor_name",
        "-mtime",
    )

    def get_queryset(self):
        qs = Task.objects.filter(tenant=get_current_tenant())
        if self.request.query_params.get("exclude_scheduled", "false").lower() == "true":
            qs = qs.exclude(schedule_uid__in=Schedule.objects.all().values_list("uid", flat=True))
        return qs

    @extend_schema(
        parameters=[
            OpenApiParameter("exclude_scheduled", bool, default=False),
        ]
    )
    def list(self, *args, **kwargs):
        return super().list(*args, **kwargs)
