from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0016_extractedfunddata_audit_fee_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='rag_status',
            field=models.CharField(
                choices=[
                    ('not_started', 'Not Started'),
                    ('queued', 'Queued'),
                    ('running', 'Running'),
                    ('completed', 'Completed'),
                    ('failed', 'Failed'),
                ],
                default='not_started',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='rag_progress',
            field=models.PositiveSmallIntegerField(default=0, help_text='0-100'),
        ),
        migrations.AddField(
            model_name='document',
            name='rag_error_message',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='document',
            name='rag_started_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='document',
            name='rag_completed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name='document',
            index=models.Index(fields=['rag_status'], name='api_documen_rag_sta_8b10ec_idx'),
        ),
    ]
