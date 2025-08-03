from django.db import models

class Hall(models.Model):
    name = models.CharField(max_length=100)
    floor = models.CharField(max_length=50, default='Unknown')  # ← أضف هذا السطر

    def __str__(self):
        return f"{self.name} - {self.floor}"


class Camera(models.Model):
    name = models.CharField(max_length=100)
    stream = models.CharField(max_length=255)  # رابط مباشر أو مسار داخل static
    hall = models.ForeignKey(Hall, related_name='cameras', on_delete=models.CASCADE, null=True, blank=True)
    video_path = models.CharField(max_length=255, null=True, blank=True)  # مسار فيديو إضافي (اختياري)
    is_live = models.BooleanField(default=False)  # هل الكاميرا لايف أم فيديو ثابت

    def __str__(self):
        if self.hall:
            return f"{self.name} ({self.hall.name})"
        return self.name

    def save(self, *args, **kwargs):
        if self.stream and 'static/' in self.stream:
            parts = self.stream.split('static/')
            self.stream = parts[-1]  # نحافظ على المسار بعد كلمة static فقط
        super().save(*args, **kwargs)

    @property
    def get_stream_url(self):
        """يرجع رابط الفيديو كامل ليشتغل مباشرة"""
        if self.stream.startswith('http'):
            return self.stream
        return f'/static/{self.stream}'

