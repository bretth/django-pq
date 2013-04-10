# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Job'
        db.create_table(u'pq_job', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('uuid', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')()),
            ('origin', self.gf('django.db.models.fields.CharField')(max_length=254, null=True, blank=True)),
            ('queue', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['pq.Queue'], null=True, blank=True)),
            ('instance', self.gf('picklefield.fields.PickledObjectField')(null=True, blank=True)),
            ('func_name', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('args', self.gf('picklefield.fields.PickledObjectField')(blank=True)),
            ('kwargs', self.gf('picklefield.fields.PickledObjectField')(blank=True)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=254)),
            ('result_ttl', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('status', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('enqueued_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('scheduled_for', self.gf('django.db.models.fields.DateTimeField')()),
            ('repeat', self.gf('picklefield.fields.PickledObjectField')(null=True, blank=True)),
            ('interval', self.gf('picklefield.fields.PickledObjectField')(null=True, blank=True)),
            ('between', self.gf('django.db.models.fields.CharField')(max_length=5, null=True, blank=True)),
            ('weekdays', self.gf('picklefield.fields.PickledObjectField')(null=True, blank=True)),
            ('ended_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('expired_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('result', self.gf('picklefield.fields.PickledObjectField')(null=True, blank=True)),
            ('exc_info', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('timeout', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('meta', self.gf('picklefield.fields.PickledObjectField')(blank=True)),
            ('flow', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['pq.FlowStore'], null=True, blank=True)),
            ('if_failed', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('if_result', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
        ))
        db.send_create_signal(u'pq', ['Job'])

        # Adding model 'Queue'
        db.create_table(u'pq_queue', (
            ('name', self.gf('django.db.models.fields.CharField')(default='default', max_length=100, primary_key=True)),
            ('default_timeout', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('cleaned', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('scheduled', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('lock_expires', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 4, 10, 0, 0))),
            ('serial', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'pq', ['Queue'])

        # Adding model 'FlowStore'
        db.create_table(u'pq_flowstore', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(default='', max_length=100)),
            ('queue', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['pq.Queue'], null=True, blank=True)),
            ('enqueued_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('ended_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('expired_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('status', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('jobs', self.gf('picklefield.fields.PickledObjectField')(blank=True)),
        ))
        db.send_create_signal(u'pq', ['FlowStore'])

        # Adding model 'Worker'
        db.create_table(u'pq_worker', (
            ('name', self.gf('django.db.models.fields.CharField')(max_length=254, primary_key=True)),
            ('birth', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('expire', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('queue_names', self.gf('django.db.models.fields.CharField')(max_length=254, null=True, blank=True)),
        ))
        db.send_create_signal(u'pq', ['Worker'])


    def backwards(self, orm):
        # Deleting model 'Job'
        db.delete_table(u'pq_job')

        # Deleting model 'Queue'
        db.delete_table(u'pq_queue')

        # Deleting model 'FlowStore'
        db.delete_table(u'pq_flowstore')

        # Deleting model 'Worker'
        db.delete_table(u'pq_worker')


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
            'lock_expires': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 4, 10, 0, 0)'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '100', 'primary_key': 'True'}),
            'scheduled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'serial': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'pq.worker': {
            'Meta': {'object_name': 'Worker'},
            'birth': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'expire': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '254', 'primary_key': 'True'}),
            'queue_names': ('django.db.models.fields.CharField', [], {'max_length': '254', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['pq']