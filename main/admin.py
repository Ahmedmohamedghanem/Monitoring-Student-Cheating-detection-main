from django.contrib import admin
from main.models import Hall, Camera

@admin.register(Hall)
class HallAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)        
    ordering = ('name',)          

@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'hall', 'stream','video_path','is_live')  
    list_filter = ('hall',)       
    search_fields = ('name', 'hall__name')  
    ordering = ('name',)
