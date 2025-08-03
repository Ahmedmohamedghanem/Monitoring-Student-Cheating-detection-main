from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from main import views  # تأكد إنك مستورد views من app main

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),  # عشان اللوجن واللوج آوت يشتغلوا
    path('', RedirectView.as_view(url='/accounts/login/')),  # الصفحة الأساسية توديك للوجن
    path('camera/', include('main.urls')),  # مسارات التطبيق
    # path('activate/<str:model_name>/', views.activate_model, name='activate_model'),
]
