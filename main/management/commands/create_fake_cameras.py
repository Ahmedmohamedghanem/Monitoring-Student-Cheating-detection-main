from django.core.management.base import BaseCommand
from main.models import Camera

class Command(BaseCommand):
    help = 'Create fake cameras for testing'

    def handle(self, *args, **kwargs):
        fake_cameras = [
            {'name': 'كاميرا 1', 'stream_url': 'videos/cam_2.mp4'},
            {'name': 'كاميرا 2', 'stream_url': 'camera/static/videos/cam_2.mp4'},
            {'name': 'كاميرا 3', 'stream_url': 'camera/static/videos/cam_2.mp4'},
            {'name': 'كاميرا 4', 'stream_url': 'camera/static/videos/cam_2.mp4'},
        ]

        for cam in fake_cameras:
            Camera.objects.get_or_create(
                name=cam['name'],
                defaults={'stream': cam['stream_url']}  # 🛠️ هنا غيرنا stream_url الى stream
            )

        self.stdout.write(self.style.SUCCESS('✅ تم إنشاء الكاميرات الوهمية بنجاح!'))
