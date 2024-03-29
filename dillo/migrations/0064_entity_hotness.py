# Generated by Django 2.2.14 on 2021-06-20 14:41

from django.db import migrations, models


def set_hotness(apps, schema_editor):
    """Set hotness for posts."""

    from dillo.models.posts import Post

    for post in Post.objects.all():
        post.update_hotness()
        print(f'Set hotness for post {post.id}')


class Migration(migrations.Migration):

    dependencies = [
        ('dillo', '0063_badge_drop_unique_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='event', name='hotness', field=models.FloatField(default=0),
        ),
        migrations.AddField(model_name='job', name='hotness', field=models.FloatField(default=0),),
        migrations.AddField(model_name='post', name='hotness', field=models.FloatField(default=0),),
        migrations.RunPython(set_hotness, migrations.RunPython.noop),
    ]
