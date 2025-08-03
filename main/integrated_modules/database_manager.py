import sqlite3
from datetime import datetime
import os
import csv

class DatabaseManager:
    def __init__(self, db_path="cheating_system.db"):
        self.db_path = db_path
        self.init_database()
        self.populate_initial_data()

    def init_database(self):
        """Create all necessary tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # students table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                academic_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                committee TEXT NOT NULL,
                cheat_count INTEGER DEFAULT 0
            )
        ''')

        # cheating_events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cheating_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                academic_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                formatted_time TEXT NOT NULL,
                location TEXT DEFAULT 'Exam Hall',
                details TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                image_path TEXT,
                datetime_recorded TEXT NOT NULL,
                FOREIGN KEY (academic_id) REFERENCES students (academic_id)
            )
        ''')

        # attendance_log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                academic_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                formatted_time TEXT NOT NULL,
                location TEXT DEFAULT 'Exam Hall',
                datetime_recorded TEXT NOT NULL,
                FOREIGN KEY (academic_id) REFERENCES students (academic_id)
            )
        ''')

        # phone_detection table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS phone_detection (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                formatted_time TEXT NOT NULL,
                location TEXT DEFAULT 'Exam Hall',
                datetime_recorded TEXT NOT NULL
            )
        ''')

        conn.commit()
        conn.close()
        print("✅ Database initialized.")

    def populate_initial_data(self):
        """Insert initial student records"""
        students_data = [
            ('41210069', 'Amr Mohamed', 'Committee 1'),
            ('41210112', 'Menna Allah Ayman', 'Committee 1'),
            ('41210006', 'Ahmed ElSayed', 'Committee 1'),
            ('41210021', 'Ahmed Ghanem', 'Committee 1'),
            ('41210091', 'Mohamed Fawzy', 'Committee 2'),
            ('41210081', 'Mohamed ElShafey', 'Committee 2'),
            ('41210108', 'Mustafa Nabih', 'Committee 2'),
            ('41210136', 'Rayan Hassan', 'Committee 2'),
            ('41210033', 'Soliman Mustafa', 'Committee 1')
        ]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for academic_id, name, committee in students_data:
            cursor.execute('''
                INSERT OR IGNORE INTO students (academic_id, name, committee, cheat_count)
                VALUES (?, ?, ?, 0)
            ''', (academic_id, name, committee))

        conn.commit()
        conn.close()
        print("✅ Initial student data added.")

    def get_student_name(self, academic_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM students WHERE academic_id = ?', (academic_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else "Unknown Student"

    def record_cheating_event(self, academic_id, timestamp, formatted_time, details,
                              confidence=0.0, image_path=None, location="Exam Hall"):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            confidence = float(confidence) if confidence else 0.0
        except:
            confidence = 0.0

        cursor.execute('''
            INSERT INTO cheating_events
            (academic_id, timestamp, formatted_time, location, details, confidence, image_path, datetime_recorded)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (academic_id, timestamp, formatted_time, location, details, confidence,
              image_path, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        cursor.execute('''
            UPDATE students SET cheat_count = cheat_count + 1 WHERE academic_id = ?
        ''', (academic_id,))

        conn.commit()
        conn.close()
        print(f"📝 Cheating recorded for {academic_id} | {details}")

    def record_phone_detection(self, timestamp, formatted_time, location="Exam Hall"):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO phone_detection (timestamp, formatted_time, location, datetime_recorded)
            VALUES (?, ?, ?, ?)
        ''', (timestamp, formatted_time, location, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        conn.commit()
        conn.close()
        print(f"📱 Phone detection recorded at {formatted_time} in {location}")

    def record_attendance(self, academic_id, location="Exam Hall"):
        now = datetime.now()
        today_date = now.strftime("%Y-%m-%d")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if attendance already recorded today for this student
        cursor.execute('''
            SELECT COUNT(*) FROM attendance_log 
            WHERE academic_id = ? AND DATE(datetime_recorded) = ?
        ''', (academic_id, today_date))
        
        count = cursor.fetchone()[0]
        
        if count > 0:
            print(f"⚠️  Attendance already recorded today for: {academic_id}")
            conn.close()
            return

        cursor.execute('''
            INSERT INTO attendance_log (academic_id, timestamp, formatted_time, location, datetime_recorded)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            academic_id,
            now.timestamp(),
            now.strftime("%H:%M:%S"),
            location,
            now.strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()
        conn.close()
        print(f"🟢 Attendance recorded for: {academic_id}")

    def get_student_statistics(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT academic_id, name, committee, cheat_count FROM students
            ORDER BY cheat_count DESC, name
        ''')
        students = cursor.fetchall()
        conn.close()
        return students

    def get_all_cheating_events(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.name, s.academic_id, s.committee, ce.formatted_time,
                   ce.details, ce.confidence, ce.image_path, ce.datetime_recorded
            FROM cheating_events ce
            JOIN students s ON ce.academic_id = s.academic_id
            ORDER BY ce.timestamp
        ''')
        result = cursor.fetchall()
        conn.close()
        return result

    def get_all_phone_detections(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, formatted_time, location, datetime_recorded
            FROM phone_detection
            ORDER BY timestamp
        ''')
        result = cursor.fetchall()
        conn.close()
        return result

    def get_committee_statistics(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT committee,
                   COUNT(*) as total_students,
                   SUM(cheat_count) as total_cheating_events,
                   AVG(CAST(cheat_count AS FLOAT)) as avg_cheating_per_student,
                   COUNT(CASE WHEN cheat_count > 0 THEN 1 END) as students_with_cheating
            FROM students
            GROUP BY committee
        ''')
        stats = cursor.fetchall()
        conn.close()
        return stats

    def export_to_csv(self, filename="cheating_report.csv"):
        data = self.get_all_cheating_events()
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Student Name', 'Academic ID', 'Committee', 'Time', 'Details',
                             'Confidence', 'Image Path', 'Recorded Time'])
            for row in data:
                writer.writerow(row)
        print(f"📤 Report exported to {filename}")

    def close(self):
        pass  # You can add cleanup here if needed later