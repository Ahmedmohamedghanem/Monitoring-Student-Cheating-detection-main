import cv2
import time
from datetime import datetime
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from main.detection.Cheating_detection import CheatDetector
from main.integrated_modules.face_recognition import FaceClassifier
from main.integrated_modules.database_manager import DatabaseManager
from main.detection.phone_detection import process_mobile_detection
from main.state import should_stop, cheating_stats


class IntegratedCheatingSystem:
    def __init__(self, camera, cheating_model_path, face_db_path, exam_location):
        self.camera = camera
        self.video_path = camera.stream if camera.is_live else camera.video_path
        self.cheat_detector = CheatDetector(model_path=cheating_model_path)
        self.db_manager = DatabaseManager()
        self.face_classifier = FaceClassifier(face_db_path)
        self.exam_location = exam_location
        self.last_summary_time = time.time()

        self.cheating_results = []
        self.phone_detections = []

        self.cap = cv2.VideoCapture(self.video_path)

    def format_timestamp(self, timestamp):
        minutes = int(timestamp // 60)
        seconds = int(timestamp % 60)
        milliseconds = int((timestamp % 1) * 1000)
        return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

    def process_cheating_alert(self, alert_info):
        track_id = alert_info['track_id']
        timestamp = alert_info['timestamp']
        reason = alert_info['reason']
        cropped_image = alert_info['crop']

        academic_id, confidence = self.face_classifier.classify_cropped_image(cropped_image)
        student_name = self.db_manager.get_student_name(academic_id)

        try:
            confidence = float(confidence) if confidence is not None else 0.0
        except (ValueError, TypeError):
            confidence = 0.0

        if student_name == "Unknown Student":
            known_students = {
                "41210033": "Soliman Mustafa",
                "41210081": "Mohamed ElShafey",
            }
            student_name = known_students.get(academic_id, student_name)

        result = {
            'track_id': track_id,
            'academic_id': academic_id,
            'student_name': student_name,
            'timestamp': timestamp,
            'formatted_time': self.format_timestamp(timestamp),
            'reason': reason,
            'confidence': float(confidence),
            'filepath': alert_info['filepath'],
            'location': self.exam_location,
            'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        recent_alerts = cheating_stats[self.camera.id]["violations"]
        result_time = datetime.strptime(result["datetime"], "%Y-%m-%d %H:%M:%S")

        for r in recent_alerts:
            if r["academic_id"] == academic_id:
                existing_time = datetime.strptime(r["datetime"], "%Y-%m-%d %H:%M:%S")
                if abs((result_time - existing_time).total_seconds()) < 10:
                    print(f"⏳ Ignoring repeated cheating alert for {academic_id} within 10 seconds")
                    return

        self.cheating_results.append(result)
        cheating_stats[self.camera.id]["count"] += 1
        cheating_stats[self.camera.id]["violations"].insert(0, result)
        cheating_stats[self.camera.id]["violations"] = cheating_stats[self.camera.id]["violations"][:30]

        self.db_manager.record_cheating_event(
            academic_id=academic_id,
            timestamp=timestamp,
            formatted_time=self.format_timestamp(timestamp),
            details=reason,
            confidence=confidence,
            image_path=alert_info['filepath'],
            location=self.exam_location
        )

        print(f"\n🚨 Processing cheating alert for person ID: {track_id}")
        print(f"⏰ Time: {self.format_timestamp(timestamp)}")
        print(f"📋 Reason: {reason}")
        print(f"📍 Location: {self.exam_location}")
        print(f"👤 Student: {student_name}")
        print(f"🆔 Academic ID: {academic_id}")
        print(f"🎯 Recognition confidence: {confidence:.2f}")
        print(f"💾 Image saved: {alert_info['filepath']}")
        print(f"📝 Recorded in database with location: {self.exam_location}")
        print("-" * 50)

        return result

    def process_phone_detection(self, timestamp):
        formatted_time = self.format_timestamp(timestamp)

        print(f"\n📱 Phone detected!")
        print(f"⏰ Time: {formatted_time}")
        print(f"📍 Location: {self.exam_location}")

        phone_record = {
            'timestamp': timestamp,
            'formatted_time': formatted_time,
            'location': self.exam_location,
            'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        self.phone_detections.append(phone_record)

        self.db_manager.record_phone_detection(
            timestamp=timestamp,
            formatted_time=formatted_time,
            location=self.exam_location
        )

        print(f"📝 Phone detection recorded in database with location: {self.exam_location}")
        print("-" * 50)

        return phone_record

    def display_results_on_frame(self, frame):
        return frame  # 🛑 لا يتم عرض أي شيء على الفريم نفسه

    def run(self):
        print(f"[🚀] Detection started on camera {self.camera.id} in {self.exam_location}")
        
        frame_count = 0

        while not should_stop.get(self.camera.id, False):
            ret, frame = self.cap.read()
            if not ret:
                print(f"[⛔] Failed to read frame from camera {self.camera.id}")
                break

            # ✅ تحليل فريم واحد فقط
            processed_frame, cheating_alerts = self.cheat_detector.process_frame(frame, frame_count)

            for alert in cheating_alerts:
                self.process_cheating_alert(alert)

            # ✅ كشف الهاتف من نفس الفريم
            phone_frame, phone_detected = process_mobile_detection(processed_frame)
            if phone_detected:
                timestamp = self.cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                self.process_phone_detection(timestamp)

            frame_count += 1
            time.sleep(0.05)

        self.cap.release()
        print(f"[🛑] Detection stopped for camera {self.camera.id}")
        self.generate_final_report()

    def generate_final_report(self):
        report_lines = []
        report_lines.append("\n🎯 Generating comprehensive report (Database + PDF)...")

        if self.cheating_results or self.phone_detections:
            report_lines.append(f"\n📊 SESSION SUMMARY:")
            report_lines.append(f"   • Total cheating alerts processed: {len(self.cheating_results)}")
            report_lines.append(f"   • Total phone detections: {len(self.phone_detections)}")
            report_lines.append(f"   • Images saved in: {self.cheat_detector.screenshots_dir}")

            if self.cheating_results:
                unique_students = set()
                for result in self.cheating_results:
                    unique_students.add(f"{result['student_name']} ({result['academic_id']})")

                report_lines.append(f"   • Students involved in cheating: {len(unique_students)}")
                for student in sorted(unique_students):
                    student_events = [
                        r for r in self.cheating_results
                        if f"{r['student_name']} ({r['academic_id']})" == student
                    ]
                    report_lines.append(f"     - {student}: {len(student_events)} incident(s)")
                    for ev in student_events:
                        report_lines.append(f"         - {ev['formatted_time']} → {ev['reason']}")

            if self.phone_detections:
                report_lines.append(f"\n📱 Phone Detections:")
                for phone in self.phone_detections:
                    report_lines.append(f"   - {phone['formatted_time']} → Phone detected in {phone['location']}")
        else:
            report_lines.append("No events recorded.")

        final_report = "\n".join(report_lines)
        print(final_report)

        try:
            hall_id = self.exam_location.replace("hall_", "")
            base_dir = os.path.join("media", "results", f"{hall_id}")
            os.makedirs(base_dir, exist_ok=True)

            now = datetime.now().strftime("%Y-%m-%d__%H-%M-%S")
            pdf_filename = f"hall_{hall_id}__{now}.pdf"
            pdf_path = os.path.join(base_dir, pdf_filename)

            c = canvas.Canvas(pdf_path, pagesize=A4)
            width, height = A4

            text_object = c.beginText(40, height - 50)
            text_object.setFont("Helvetica", 12)

            for line in report_lines:
                if text_object.getY() < 50:
                    c.drawText(text_object)
                    c.showPage()
                    text_object = c.beginText(40, height - 50)
                    text_object.setFont("Helvetica", 12)
                text_object.textLine(line)

            c.drawText(text_object)
            c.save()

            print(f"[✅] PDF report saved to {pdf_path}")

        except Exception as e:
            print(f"[⚠️] Failed to save PDF report: {e}")
