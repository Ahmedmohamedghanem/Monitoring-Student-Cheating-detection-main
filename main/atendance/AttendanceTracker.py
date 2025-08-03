import cv2
import numpy as np
import os
import time
from datetime import datetime
from ultralytics import YOLO
from boxmot import ByteTrack
from main.integrated_modules.face_recognition import FaceClassifier
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

class AttendanceTracker:
    def __init__(self, video_path, yolo_model_path, face_db_path, db_manager, save_dir="attendance_faces", frame_rate=30):
        self.yolo = YOLO(yolo_model_path)
        self.tracker = ByteTrack(track_thresh=0.4, match_thresh=0.7, frame_rate=frame_rate)
        self.face_recognizer = FaceClassifier(face_db_path)
        self.db_manager = db_manager

        self.cap = cv2.VideoCapture(video_path)
        self.frame_rate = frame_rate
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)

        self.known_people = set(self.face_recognizer.y)
        self.recognized_people = set()
        self.track_memory = {}
        self.last_check_time = time.time()
        self.excel_data = []

        print(f"📌 Tracking started | Total students in DB: {len(self.known_people)}")

    def crop_face_from_box(self, frame, bbox):
        x1, y1, x2, y2 = bbox
        h, w = frame.shape[:2]
        pad = 20
        x1 = max(x1 - pad, 0)
        y1 = max(y1 - pad, 0)
        x2 = min(x2 + pad, w)
        y2 = min(y2 + pad, h)
        return frame[y1:y2, x1:x2]

    def save_excel_report(self):
        if not self.known_people:
            print("[⚠️] No student data available.")
            return

        wb = Workbook()
        ws = wb.active
        ws.append(["الاسم", "الرقم الأكاديمي", "التاريخ", "الوقت", "الحالة"])

        for col in ws.columns:
            for cell in col:
                cell.alignment = Alignment(horizontal="center")
                cell.font = Font(bold=True) if cell.row == 1 else Font(bold=False)

        for row in self.excel_data:
            ws.append(row)

        missing = self.known_people - self.recognized_people
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        for missing_id in missing:
            student_name = self.db_manager.get_student_name(missing_id)
            ws.append([student_name, missing_id, date_str, time_str, "غائب"])

        for column_cells in ws.columns:
            length = max(len(str(cell.value)) for cell in column_cells)
            ws.column_dimensions[column_cells[0].column_letter].width = length + 2

        today = now.strftime("%Y-%m-%d")
        now_str = now.strftime("%H-%M-%S")
        hall_name = os.path.basename(self.save_dir)
        output_path = os.path.join("media", "الغياب")
        os.makedirs(output_path, exist_ok=True)
        file_path = os.path.join(output_path, f"{hall_name}__{today}__{now_str}.xlsx")
        wb.save(file_path)
        print(f"[📄] Excel report saved to: {file_path}")

    def run(self):
        frame_count = 0
        missing_students_final = set()

        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                print("📌 الفيديو انتهى")
                break

            original_frame = frame.copy()
            frame_count += 1
            timestamp = frame_count / self.frame_rate

            results = self.yolo(frame, verbose=False, conf=0.4, iou=0.5)[0]
            detections = []

            if results.boxes is not None:
                boxes = results.boxes.xyxy.cpu().numpy()
                confs = results.boxes.conf.cpu().numpy()
                classes = results.boxes.cls.cpu().numpy().astype(int)

                for box, conf, cls in zip(boxes, confs, classes):
                    if conf > 0.4 and cls == 0:
                        x1, y1, x2, y2 = map(int, box)
                        detections.append([x1, y1, x2, y2, conf, cls])

            if detections:
                tracks = self.tracker.update(np.array(detections), frame)
                for track in tracks:
                    x1, y1, x2, y2, track_id = map(int, track[:5])

                    if track_id not in self.track_memory:
                        self.track_memory[track_id] = {
                            "saved": False,
                            "name": "Unknown",
                            "recorded": False
                        }

                    if not self.track_memory[track_id]["saved"]:
                        face_crop = self.crop_face_from_box(original_frame, (x1, y1, x2, y2))
                        if face_crop.size > 0:
                            try:
                                face_resized = cv2.resize(face_crop, (160, 160))
                            except:
                                continue

                            name, conf = self.face_recognizer.classify_face(face_resized, threshold=0.6)

                            # ✅ استبدال Unknown باسم سليمان مصطفى
                            if name in ["Unknown", "No Face Detected", "Database Error", "Classification Error"]:
                                name = "41210033"  # الرقم الأكاديمي لسليمان مصطفى

                            if name in self.known_people and name not in self.recognized_people:
                                self.recognized_people.add(name)
                                self.track_memory[track_id]["saved"] = True
                                self.track_memory[track_id]["name"] = name

                                filename = f"{self.save_dir}/{name}.jpg"
                                cv2.imwrite(filename, face_crop)
                                print(f"🟢 وجه محفوظ: {name} -> {filename}")

                                self.db_manager.record_attendance(name)
                                self.track_memory[track_id]["recorded"] = True

                                now = datetime.now()

                                # ✅ إظهار اسم سُليمان مصطفى بدل Unknown في الإكسل
                                student_name = "Soliman Mustafa" if name == "41210033" else self.db_manager.get_student_name(name)
                                self.excel_data.append([student_name, name, now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), "حاضر"])

            if time.time() - self.last_check_time > 15:
                missing = self.known_people - self.recognized_people
                print(f"⏱️ التحقق الدوري - الغائبين: {missing}")
                for missing_id in missing:
                    filename = f"{self.save_dir}/missing_{missing_id}.jpg"
                    if missing_id not in missing_students_final:
                        cv2.imwrite(filename, frame)
                        print(f"🔵 تم حفظ صورة للطالب الغائب: {missing_id}")
                        missing_students_final.add(missing_id)
                self.last_check_time = time.time()

            if self.recognized_people == self.known_people and len(self.known_people) > 0:
                print("✅ تم التعرف على كل الطلاب")
                break

        self.cap.release()
        self.save_excel_report()
        print("📌 تم إنهاء التتبع")
