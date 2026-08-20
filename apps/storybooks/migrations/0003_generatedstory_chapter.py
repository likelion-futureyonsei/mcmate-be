import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("storybooks", "0002_generatedstory"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 생성 단위를 스토리북 -> 챕터(권)로 변경. 테이블이 비어 있어 재생성한다.
        migrations.DeleteModel(name="GeneratedStory"),
        migrations.CreateModel(
            name="GeneratedStory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="생성 시각")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="수정 시각")),
                ("body", models.TextField(verbose_name="본문")),
                ("chapter", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="generated_stories", to="storybooks.chapter", verbose_name="챕터")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="generated_stories", to=settings.AUTH_USER_MODEL, verbose_name="유저")),
            ],
            options={
                "db_table": "generated_stories",
                "verbose_name": "생성 스토리",
                "verbose_name_plural": "생성 스토리",
            },
        ),
        migrations.AddConstraint(
            model_name="generatedstory",
            constraint=models.UniqueConstraint(fields=("user", "chapter"), name="uniq_generated_story_per_user_chapter"),
        ),
    ]
