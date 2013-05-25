# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Worker.heartbeat'
        db.add_column(u'pq_worker', 'heartbeat',
                      self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Worker.heartbeat'
        db.delete_column(u'pq_worker', 'heartbeat')


    models = {
        u'pq.flowstore': {
            'Meta': {'object_name': 'FlowStore'},
            'ended_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'enqueued_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'expired_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jobs': ('picklefield.fields.PickledObjectField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'queue': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['pq.Queue']", 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'pq.job': {
            'Meta': {'object_name': 'Job'},
            'args': ('picklefield.fields.PickledObjectField', [], {'blank': 'True'}),
            'between': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'ended_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'enqueued_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'exc_info': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'expired_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'flow': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['pq.FlowStore']", 'null': 'True', 'blank': 'True'}),
            'func_name': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'if_failed': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'if_result': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'instance': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'interval': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'kwargs': ('picklefield.fields.PickledObjectField', [], {'blank': 'True'}),
            'meta': ('picklefield.fields.PickledObjectField', [], {'blank': 'True'}),
            'origin': ('django.db.models.fields.CharField', [], {'max_length': '254', 'null': 'True', 'blank': 'True'}),
            'queue': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['pq.Queue']", 'null': 'True', 'blank': 'True'}),
            'repeat': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'result': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'}),
            'result_ttl': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'scheduled_for': ('django.db.models.fields.DateTimeField', [], {}),
            'status': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timeout': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'weekdays': ('picklefield.fields.PickledObjectField', [], {'null': 'True', 'blank': 'True'})
        },
        u'pq.queue': {
            'Meta': {'object_name': 'Queue'},
            'cleaned': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_timeout': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'idempotent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'lock_expires': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 5, 24, 0, 0)'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '100', 'primary_key': 'True'}),
            'scheduled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'serial': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'pq.worker': {
            'Meta': {'object_name': 'Worker'},
            'birth': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'expire': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'heartbeat': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '254', 'primary_key': 'True'}),
            'queue_names': ('django.db.models.fields.CharField', [], {'max_length': '254', 'null': 'True', 'blank': 'True'}),
            'stop': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        }
    }

    complete_apps = ['pq']