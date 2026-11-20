# -*- coding: utf-8 -*-
"""
Índice (verb, timestamp) sobre actstream_action para las consultas de estadísticas
(todas filtran por verbo y rango de fechas).

- CONCURRENTLY: no bloquea las escrituras en producción mientras se crea.
- IF NOT EXISTS / IF EXISTS: idempotente (se puede haber creado a mano antes).
- atomic = False: CREATE INDEX CONCURRENTLY no puede ejecutarse en una transacción.
"""
from django.db import migrations

INDEX_NAME = 'gol_stats_action_verb_ts'


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('actstream', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql='CREATE INDEX CONCURRENTLY IF NOT EXISTS %s ON actstream_action (verb, "timestamp")' % INDEX_NAME,
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS %s' % INDEX_NAME,
        ),
    ]
