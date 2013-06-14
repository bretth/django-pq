from django.contrib import admin
from django.conf import settings
from django.db.models import F
from .job import FailedJob, QueuedJob, DequeuedJob, ScheduledJob
from .queue import FailedQueue
from .flow import FlowStore
from .worker import Worker

CONN = getattr(settings, 'PQ_ADMIN_CONNECTION', 'default')

def requeue_failed_jobs(modeladmin, request, queryset):
    """Requeue selected failed jobs onto the origin queue"""
    fq = FailedQueue.create(CONN)
    for job in queryset:
        fq.requeue(job.id)
requeue_failed_jobs.short_description = "Requeue selected jobs"

class FailedJobAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'origin', 'exc_info', 'ended_at')
    list_filter = ('origin',)
    ordering = ('-id',)
    actions = [requeue_failed_jobs]

    def __init__(self, *args, **kwargs):
        super(FailedJobAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = (None, )

    def queryset(self, request):
        return self.model.objects.using(
            CONN).filter(queue__name='failed')

    def has_add_permission(self, request):
        return False


class QueuedJobAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'queue', 'timeout', 'enqueued_at',
                    'scheduled_for', 'get_schedule_options',)
    list_filter = ('origin',)
    ordering = ('id', 'scheduled_for')

    def __init__(self, *args, **kwargs):
        super(QueuedJobAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = (None, )


    def queryset(self, request):
        return self.model.objects.using(
            CONN).all().exclude(queue__name='failed').exclude(queue=None)

    def has_add_permission(self, request):
        return False


class ScheduledJobAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'queue', 'timeout', 'enqueued_at',
                    'scheduled_for', 'get_schedule_options',)
    list_filter = ('origin',)
    ordering = ('scheduled_for', )

    def __init__(self, *args, **kwargs):
        super(ScheduledJobAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = (None, )

    def queryset(self, request):
        return self.model.objects.using(
            CONN).filter(status=0).exclude(queue__name='failed').exclude(queue=None)

    def has_add_permission(self, request):
        return False

def requeue_jobs(modeladmin, request, queryset):
    """Requeue selected jobs onto the origin queue"""
    fq = FailedQueue.create(CONN)
    for job in queryset:
        fq.requeue(job.id)
requeue_jobs.short_description = "Requeue selected jobs"


class DequeuedJobAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'origin', 'status', 'enqueued_at', 'ended_at')
    list_filter = ('origin', 'status')
    ordering = ('-enqueued_at',)
    actions = [requeue_jobs]

    def __init__(self, *args, **kwargs):
        super(DequeuedJobAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = (None, )

    def queryset(self, request):
        return self.model.objects.using(CONN).filter(queue=None)

    def has_add_permission(self, request):
        return False


class FlowAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'queue', 'enqueued_at', 'ended_at', 'status' )
    list_filter = ('name', 'queue',)
    ordering = ('id',)

    def __init__(self, *args, **kwargs):
        super(FlowAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = (None, )

    def has_add_permission(self, request):
        return False


class WorkerAdmin(admin.ModelAdmin):
    list_display = ('name', 'birth', 'expire', 'heartbeat', 'queue_names', 'stop')
    list_editable = ('stop', )
    ordering = ('name',)

    def __init__(self, *args, **kwargs):
        super(WorkerAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = (None, )

    def has_add_permission(self, request):
        return False



admin.site.register(FailedJob, FailedJobAdmin)
admin.site.register(QueuedJob, QueuedJobAdmin)
admin.site.register(ScheduledJob, ScheduledJobAdmin)
admin.site.register(DequeuedJob, DequeuedJobAdmin)
admin.site.register(FlowStore, FlowAdmin)
admin.site.register(Worker, WorkerAdmin)

