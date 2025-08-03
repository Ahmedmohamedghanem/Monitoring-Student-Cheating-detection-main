from main.state import cheating_model, detectors, should_stop, cheating_live_count, hall_active_models
from main.integrated_detection import IntegratedCheatingSystem
from main.models import Camera as CameraModel
from main.detection.phone_detection import process_mobile_detection
import cv2
import time

def gen(source, cam_id, hall_id, delay=0.03):
    cap = cv2.VideoCapture(source)
    frame_count = 0
    warmup_frames = 0

    
    if not cap.isOpened():
        print(f"[❌] لم يتم فتح الفيديو: {source}")
        return

    
    try:
        camera_obj = CameraModel.objects.get(id=cam_id)
        if camera_obj.hall.id != hall_id:
            print(f"[⚠️] الكاميرا {cam_id} لا تنتمي للقاعة {hall_id}")
            return
    except CameraModel.DoesNotExist:
        print(f"[❌] لم يتم العثور على الكاميرا ذات المعرف {cam_id}")
        return

   
    if cam_id not in detectors:
        detectors[cam_id] = IntegratedCheatingSystem(
            camera=camera_obj,
            cheating_model_path="main/modelss/best.pt",
            face_db_path="main/modelss/face_db_clean.npz",
            exam_location=f"hall_{hall_id}"
        )
        should_stop[cam_id] = False

    if cam_id not in cheating_live_count:
        cheating_live_count[cam_id] = 0

    detector = detectors[cam_id]

  
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print(f"[⚠️] لم يتم قراءة الفريم من الكاميرا {cam_id}")
            break

        frame_count += 1

      
        if hall_active_models.get(hall_id, False) and not should_stop.get(cam_id, True):
            try:
               
                processed_frame, cheating_alerts = detector.cheat_detector.process_frame(frame, frame_count)

               
                phone_frame, mobile_detected = process_mobile_detection(processed_frame)

                
                for alert in cheating_alerts:
                    detector.process_cheating_alert(alert)

               
                if mobile_detected:
                    detector.process_phone_detection(frame_count / 30.0)

                
                display_frame = detector.display_results_on_frame(phone_frame)

                
                frame = display_frame

                
            except Exception as e:
                print(f"[❌] خطأ أثناء تحليل الفريم: {e}")

        else:
            
            frame = cv2.putText(frame, "Anti-Cheating Disabled", (30, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

       
        if warmup_frames < 5:
            warmup_frames += 1
            continue

       
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue

        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n\r\n')

        
        time.sleep(delay)

   
    cap.release()

    
    try:
        detector.generate_final_report()
    except Exception as e:
        print(f"[⚠️] فشل توليد التقرير النهائي: {e}")
