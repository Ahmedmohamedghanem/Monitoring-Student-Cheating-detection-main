from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.hall_list, name='hall_list'),
    path('hall/<int:hall_id>/cameras/', views.camera_view, name='camera_view'),
    path('live/<int:cam_id>/', views.livefe, name='live'),
    path('camera/livefe/<int:cam_id>/', views.livefe, name='livefe'),
    path('video_feed/<int:cam_id>/', views.video_feed, name='video_feed'),
    path('toggle_anti_cheating_all/', views.toggle_anti_cheating_for_all, name='toggle_anti_cheating_for_all'),
    path('camera/latest_cheat_frame/<int:cam_id>/', views.latest_anti_cheat_frame, name='latest_anti_cheat_frame'),
    path('ai-assistant/', views.rag_assistant, name='rag_assistant'),
    path('cheating_stats/', views.cheating_stats_view, name='cheating_stats'),
    path("ai-assistant/reset/", views.reset_chat, name="reset_chat"),
    path("toggle_attendance_tracking/", views.toggle_attendance_tracking, name="toggle_attendance_tracking"),
    path('global_cheating_stats/', views.global_cheating_stats, name='global_cheating_stats'),
    path('privacy/', views.privacy_policy, name='privacy'),
    path('about/', views.About, name='about'),
    path('support/', views.Support, name='support'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
