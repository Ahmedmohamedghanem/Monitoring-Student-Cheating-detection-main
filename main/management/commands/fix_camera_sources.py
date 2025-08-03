from django.core.management.base import BaseCommand
from main.models import Camera

class Command(BaseCommand):
    help = 'تصحيح مسارات الفيديوهات للكاميرات'

    def handle(self, *args, **kwargs):
        cameras = Camera.objects.all()
        for camera in cameras:
            if 'static/' in camera.source:
                # نخلي المسار يبدأ من بعد static/
                parts = camera.source.split('static/')
                camera.source = parts[-1]  # اللي بعد static
                camera.save()
        self.stdout.write(self.style.SUCCESS('✅ تم تصحيح مسارات الكاميرات!'))
