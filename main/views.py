import os
import json
import threading
import logging
import cv2
import requests
import ollama 
from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse, FileResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.gzip import gzip_page
from django.views.decorators.http import require_GET,require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.core.files.storage import FileSystemStorage
from main.integrated_detection import IntegratedCheatingSystem
from collections import defaultdict
from main.models import Hall, Camera

from main.camera import gen
from datetime import datetime
from main.detection.Cheating_detection import CheatDetector
from main.atendance.AttendanceTracker import AttendanceTracker
from main.integrated_modules.database_manager import DatabaseManager
from main.state import should_stop, detectors, threads,cheating_stats ,hall_active_models,active_models, cheating_live_count
from django.template.loader import render_to_string
from main.Ai_assistant.Rag import (
    load_documents_from_db,
    build_vectorstore,
    create_rag_chain,
)
from langchain_ollama import OllamaLLM
import threading



logger = logging.getLogger(__name__)


@login_required(login_url='login')
def hall_list(request):
    grouped_halls = defaultdict(list)
    for hall in Hall.objects.all():
        grouped_halls[hall.floor].append(hall)
    return render(request, 'hall_list.html', {'grouped_halls': dict(grouped_halls)})

@login_required(login_url='login')
def camera_view(request, hall_id):
    hall = get_object_or_404(Hall, id=hall_id)
    cameras = hall.cameras.all()
    return render(request, 'camera_grid.html', {'hall': hall, 'cameras': cameras})


@gzip_page
@login_required(login_url='login')
def livefe(request, cam_id):
    try:
        camera_obj = Camera.objects.get(id=cam_id)
        if camera_obj.is_live and camera_obj.stream:
            source = int(camera_obj.stream) if camera_obj.stream.isdigit() else camera_obj.stream
        elif camera_obj.video_path:
            source = os.path.join(settings.BASE_DIR, camera_obj.video_path.replace('/', os.sep))
        else:
            return render(request, 'error.html', {'message': 'لا يوجد مصدر متاح لهذه الكاميرا.'})

        return StreamingHttpResponse(
            gen(source, cam_id=camera_obj.id),
            content_type="multipart/x-mixed-replace;boundary=frame"
        )
    except Camera.DoesNotExist:
        return render(request, 'error.html', {'message': 'الكاميرا غير موجودة.'})




@csrf_exempt
def toggle_anti_cheating_for_all(request):
    activate = request.GET.get("activate") == "true"
    hall_id = request.GET.get("hall_id")
    hall_name = request.GET.get("hall_name")

    try:
        if hall_id:
            hall = Hall.objects.get(id=hall_id)
        elif hall_name:
            hall = Hall.objects.get(name__iexact=hall_name)
        else:
            return JsonResponse({'status': False, 'error': 'No hall specified'})
    except Hall.DoesNotExist:
        return JsonResponse({'status': False, 'error': 'Hall not found'})

    cameras = Camera.objects.filter(hall=hall)
    hall_active_models[hall.id] = activate

    if activate:
        for cam in cameras:
            source = cam.get_stream_url

            if cam.id in threads and threads[cam.id].is_alive():
                print(f"[⏳] Thread already running for camera {cam.id}")
                continue

            integrated_detector = IntegratedCheatingSystem(
                cam,
                "main/modelss/best.pt",
                "main/modelss/face_db_clean.npz",
                hall.name
            )

            detectors[cam.id] = integrated_detector
            should_stop[cam.id] = False

            def run(cam_id=cam.id, detector=integrated_detector):
                detector.run()
                print(f"[✅] Model finished on camera {cam_id}")

            thread = threading.Thread(target=run)

            threads[cam.id] = thread
            thread.start()

            print(f"[✅] Started integrated detection on camera {cam.id} in hall {hall.name}")

    else:
        for cam in cameras:
            should_stop[cam.id] = True

        
            cheating_stats[cam.id] = {
                "count": 0,
                "violations": []
            }

        print(f"[⛔] Integrated detection DISABLED and stats cleared for hall: {hall.name}")

    return JsonResponse({'status': activate})



attendance_threads = {}

@csrf_exempt
def toggle_attendance_tracking(request):
    activate = request.GET.get("activate") == "true"
    hall_id = request.GET.get("hall_id")

    if not hall_id:
        return JsonResponse({"status": False, "error": "Missing hall_id"})

    key = f"attendance_{hall_id}"

    if activate:
        if key in attendance_threads:
            return JsonResponse({"status": True, "message": "Attendance already running"})

        def run_attendance():
            db_manager = DatabaseManager("cheating_system.db")
            cameras = Camera.objects.filter(hall_id=hall_id)

            for camera in cameras:
                print(f"[🎞️] Starting Attendance for camera: {camera.id}")
                video_source = camera.video_path or camera.stream
                if not video_source:
                    print(f"[⚠️] الكاميرا {camera.id} لا تحتوي على مصدر فيديو")
                    continue

                system = AttendanceTracker(
                    video_path=video_source,
                    yolo_model_path="main/modelss/yolov8n.pt",  # تأكد من المسار
                    face_db_path="main/modelss/face_db_clean.npz",
                    db_manager=db_manager,
                    save_dir=f"attendance_faces/hall_{hall_id}/camera_{camera.id}"
                )
                system.run()

            db_manager.close()
            print(f"[✅] Attendance finished for hall {hall_id}")
            if key in attendance_threads:
                del attendance_threads[key]

        thread = threading.Thread(target=run_attendance)
        thread.daemon = True
        thread.start()

        attendance_threads[key] = thread
        return JsonResponse({"status": True, "message": "Attendance tracking started"})

    else:
        if key in attendance_threads:
            return JsonResponse({"status": False, "message": "Can't stop attendance thread safely yet"})
        return JsonResponse({"status": False, "message": "Attendance not running"})


def latest_anti_cheat_frame(request, cam_id):
    img_path = os.path.join(settings.MEDIA_ROOT, f"cheat_frame_{cam_id}.jpg")
    if os.path.exists(img_path):
        return FileResponse(open(img_path, 'rb'), content_type='image/jpeg')
    return JsonResponse({'error': 'No frame found'}, status=404)





def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        role = request.POST.get('role')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/camera/hall_list/')
        else:
            return render(request, 'registration/login.html', {'error': 'اسم المستخدم أو كلمة المرور خطأ'})

    return render(request, 'registration/login.html', {'error': ''})
@require_GET
def logout_view(request):
    logout(request)
    return redirect('login')



@csrf_exempt
def update_camera_stream(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        camera_id = data.get('camera_id')
        new_stream = data.get('new_stream')
        try:
            camera = Camera.objects.get(id=camera_id)
            camera.stream = new_stream
            camera.save()
            return JsonResponse({'status': 'success', 'message': 'تم تحديث الرابط بنجاح'})
        except Camera.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'الكاميرا غير موجودة'}, status=404)
    return JsonResponse({'status': 'error', 'message': 'مسموح فقط بـ POST'}, status=405)





@login_required(login_url='login')
def video_feed(request, cam_id):
    camera = get_object_or_404(Camera, id=cam_id)
    hall_id = camera.hall.id  

    source = os.path.join(settings.BASE_DIR, camera.video_path.replace('/', os.sep)) \
        if camera.video_path else (int(camera.stream) if camera.stream.isdigit() else camera.stream)

    return StreamingHttpResponse(
        gen(source, cam_id=camera.id, hall_id=hall_id),  
        content_type='multipart/x-mixed-replace;boundary=frame'
    )


documents = load_documents_from_db()
vectorstore = build_vectorstore(documents)
rag_chain = create_rag_chain(vectorstore)

def query_documents(rag_chain, question: str):
    try:
        answer = rag_chain.invoke(question)
        if "no relevant data" in answer.lower() or not answer.strip():
            
            response = ollama.chat(
                model='llama3:3b',
                messages=[
                    {"role": "system", "content": "أنت مساعد ذكي للإجابة على أسئلة عن نظام كشف الغش والغياب."},
                    {"role": "user", "content": question}
                ]
            )
            return response.get("message", {}).get("content", "").strip()
        return answer
    except requests.exceptions.ConnectionError:
        return "⚠️ تأكد إن خدمة Ollama شغالة."
    except Exception as e:
        return f"🚫 حصل خطأ: {str(e)}"


@csrf_exempt
@require_http_methods(["GET", "POST"])
def rag_assistant(request):
    if "chat_history" not in request.session:
        request.session["chat_history"] = []

    if request.method == "GET":
        # عرض الشات السابق من session
        return render(request, "rag_response.html", {
            "chat_history": request.session["chat_history"]
        })

    question = request.POST.get('question', '').strip()

    if not question:
        return JsonResponse({'error': 'لم يتم إرسال سؤال.'}, status=400)

    try:
        # استخدام chain وfallback تلقائيًا
        answer = query_documents(rag_chain, question)

        # ✅ حفظ السؤال والإجابة في الجلسة
        history = request.session.get("chat_history", [])
        history.append({"question": question, "answer": answer})
        request.session["chat_history"] = history
        request.session.modified = True

        return JsonResponse({'answer': answer})

    except Exception as e:
        print("❌ خطأ في الاتصال بـ Ollama:", e)
        return JsonResponse({'error': 'حدث خطأ أثناء الاتصال بنموذج الذكاء الاصطناعي.'}, status=500)

# ✅ إعادة تعيين المحادثة
def reset_chat(request):
    request.session["chat_history"] = []
    return redirect("rag_assistant")




def cheating_stats_view(request):
    hall_id = request.GET.get('hall_id')
    if not hall_id:
        return JsonResponse({"status": "error", "message": "Missing hall_id"}, status=400)

    try:
        hall = Hall.objects.get(id=hall_id)
    except Hall.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Hall not found"}, status=404)

    cameras = hall.cameras.all()

    per_camera_data = {}
    all_violations = []

    for cam in cameras:
        stats = cheating_stats.get(cam.id, {"count": 0, "violations": []})
        per_camera_data[cam.id] = {
            "count": stats["count"]
        }
        all_violations += stats["violations"]

    return JsonResponse({
        "status": "active",
        "per_camera": per_camera_data,
        "violations": sorted(
            all_violations,
            key=lambda x: datetime.strptime(x['datetime'], "%Y-%m-%d %H:%M:%S"),
            reverse=True
        )[:30]
    })


# حافظ على كل طالب وعدد مرات التكرار اللي تم إبلاغه بها
# مثال: reported["12345"] = [3, 6]
reported_violations = defaultdict(set)

def global_cheating_stats(request):
    repeated_students = []

    for hall in Hall.objects.prefetch_related('cameras'):
        for cam in hall.cameras.all():
            stats = cheating_stats.get(cam.id, {"count": 0, "violations": []})

            # نحسب كم مرة تكرر كل أكاديمي ID داخل violations
            id_counts = defaultdict(int)
            student_info = {}

            for v in stats["violations"]:
                key = v["academic_id"]
                id_counts[key] += 1
                student_info[key] = {
                    "student_name": v["student_name"],
                    "hall_name": hall.name,
                    # "floor_name": hall.floor 
                }

            for academic_id, count in id_counts.items():
                if count >= 3 and count % 3 == 0:
                    if count not in reported_violations[academic_id]:
                        reported_violations[academic_id].add(count)
                        repeated_students.append({
                            "academic_id": academic_id,
                            "student_name": student_info[academic_id]["student_name"],
                            "hall_name": student_info[academic_id]["hall_name"],
                            # "floor_name": student_info[academic_id]["floor_name"], 
                            # "violation_count": count
                            
                        })

    return JsonResponse({"repeated_students": repeated_students})





def privacy_policy(request):
    return render(request, 'privacy.html')


def About(request):
    return render(request, 'about.html')


def Support(request):
    return render(request, 'support.html')
