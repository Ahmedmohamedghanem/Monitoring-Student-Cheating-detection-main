import cv2
import numpy as np
from ultralytics import YOLO
from boxmot import ByteTrack
import time
import os
from datetime import datetime
import torch
class CheatDetector:
    def __init__(self, model_path="main/modelss/best.pt"):
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.objectModel = YOLO(model_path).to(device)
        print("Class names:", self.objectModel.names)
        
        
        self.tracker = ByteTrack(
            track_thresh=0.35,
            match_thresh=0.75,
            frame_rate=30
        )
        
       
        self.screenshots_dir = "cheating_screenshots"
        if not os.path.exists(self.screenshots_dir):
            os.makedirs(self.screenshots_dir)
        
       
        self.current_tracks_info = {}
        self.track_states = {}  
        self.fps = 30  
        
    def get_box_color(self, cls_id):
        return (0, 0, 255) if cls_id == 0 else (0, 255, 0)  
    
    def update_track_state(self, track_id, cls_id, timestamp):
        """Update track state and detect cheating"""
        
        if track_id not in self.track_states:
            self.track_states[track_id] = {
                'last_class': cls_id,
                'cheating_start': None,
                'cheating_count': 0,
                'last_cheating_time': None,
                'continuous_cheating_duration': 0,
                'cheating_events': [], 
                'screenshot_taken': False,
                'is_cheating_now': False
            }
        
        state = self.track_states[track_id]
        current_is_cheating = (cls_id == 0) 
        
        
        if current_is_cheating and not state['is_cheating_now']:
            
            state['is_cheating_now'] = True
            state['cheating_start'] = timestamp
            state['cheating_count'] += 1
            state['last_cheating_time'] = timestamp
            
            
            state['cheating_events'].append(timestamp)
            
    
            
        elif not current_is_cheating and state['is_cheating_now']:
           
            if state['cheating_start']:
                duration = timestamp - state['cheating_start']
                state['continuous_cheating_duration'] = duration
   
            
            state['is_cheating_now'] = False
            state['cheating_start'] = None
        
        elif current_is_cheating and state['is_cheating_now']:
            
            if state['cheating_start']:
                state['continuous_cheating_duration'] = timestamp - state['cheating_start']
        
       
        state['cheating_events'] = [event for event in state['cheating_events'] 
                                   if timestamp - event <= 10.0]
        
        
        state['last_class'] = cls_id
        
        return self.check_cheating_rules(track_id, timestamp)
    
    def check_cheating_rules(self, track_id, timestamp):
        """Check cheating rules"""
        state = self.track_states[track_id]
        
        
        if state['screenshot_taken']:
            return False, None
        
       
        recent_events = len(state['cheating_events'])
        
       
        continuous_duration = state['continuous_cheating_duration']
        
        reason = None
        
        if recent_events > 3:
            reason = f"Looked around {recent_events} times in 10 seconds"
            print(f"🚨 Alert! Track {track_id}: {reason}")
            state['screenshot_taken'] = True
            return True, reason
        
        if continuous_duration >= 3.0:
            reason = f"Continuous looking around for {continuous_duration:.1f} seconds"
            print(f"🚨 Alert! Track {track_id}: {reason}")
            state['screenshot_taken'] = True
            return True, reason
        
        return False, None
    
    def take_screenshot(self, frame, x1, y1, x2, y2, track_id, timestamp, reason):
        """Take screenshot of person looking around"""
        
       
        padding = 20
        height, width = frame.shape[:2]
        
        x1_expanded = max(0, x1 - padding)
        y1_expanded = max(0, y1 - padding)
        x2_expanded = min(width, x2 + padding)
        y2_expanded = min(height, y2 + padding)
        
        person_crop = frame[y1_expanded:y2_expanded, x1_expanded:x2_expanded]
        
        
        timestamp_str = datetime.fromtimestamp(timestamp).strftime("%Y%m%d_%H%M%S_%f")[:-3]  
        filename = f"cheat_ID{track_id}_{timestamp_str}.jpg"
        filepath = os.path.join(self.screenshots_dir, filename)
        
        
        cv2.imwrite(filepath, person_crop)
        print(f"📸 Screenshot saved: {filename}")
        
        
        return {
            'filepath': filepath,
            'track_id': track_id,
            'timestamp': timestamp,
            'reason': reason,
            'crop': person_crop
        }
    
    def cleanup_inactive_tracks(self, active_track_ids):
        """Cleanup inactive tracks"""
        self.track_states = {tid: state for tid, state in self.track_states.items() 
                           if tid in active_track_ids}
        self.current_tracks_info = {tid: info for tid, info in self.current_tracks_info.items() 
                                  if tid in active_track_ids}
    
    def process_frame(self, frame, frame_count):
        """Process single frame and return detections and cheating alerts"""
        
        
        current_timestamp = frame_count / 30.0  
        
       
        original_frame = frame.copy()
        
        
        results = self.objectModel(frame, 
                                 verbose=False, 
                                 imgsz=640,
                                 conf=0.35,
                                 iou=0.5)[0]
        
        detections = []
        detection_classes = {}
        cheating_alerts = []
        
       
        if results.boxes is not None:
            boxes = results.boxes.xyxy.cpu().numpy()
            confs = results.boxes.conf.cpu().numpy()
            classes = results.boxes.cls.cpu().numpy().astype(int)
            
            valid_indices = confs >= 0.40
            
            for i, (box, conf, cls_id) in enumerate(zip(boxes[valid_indices], 
                                                       confs[valid_indices], 
                                                       classes[valid_indices])):
                x1, y1, x2, y2 = map(int, box)
                label = "Looking Around" if cls_id == 0 else "Normal"
                
                detections.append([x1, y1, x2, y2, conf, cls_id])
                detection_classes[i] = {'cls_id': cls_id, 'label': label, 'conf': conf}

        if detections:
            tracks = self.tracker.update(np.array(detections), frame)
            
            active_track_ids = set()
            
            for track in tracks:
                x1, y1, x2, y2 = map(int, track[:4])
                track_id = int(track[4])
                active_track_ids.add(track_id)
                
                
                current_cls_id = 1  
                current_label = "Normal"
                
                if detections:
                    track_center = np.array([(x1 + x2) / 2, (y1 + y2) / 2])
                    det_centers = np.array([[(d[0] + d[2]) / 2, (d[1] + d[3]) / 2] 
                                          for d in detections])
                    distances = np.linalg.norm(det_centers - track_center, axis=1)
                    best_match = np.argmin(distances)
                    
                    if best_match < len(detection_classes) and best_match in detection_classes:
                        current_cls_id = detection_classes[best_match]['cls_id']
                        current_label = detection_classes[best_match]['label']
                
                self.current_tracks_info[track_id] = {
                    'cls_id': current_cls_id,
                    'label': current_label,
                    'bbox': (x1, y1, x2, y2)
                }
                
                should_screenshot, reason = self.update_track_state(track_id, current_cls_id, current_timestamp)
                
               
                if should_screenshot:
                    alert_info = self.take_screenshot(original_frame, x1, y1, x2, y2, track_id, current_timestamp, reason)
                    cheating_alerts.append(alert_info)
                
               
                box_color = self.get_box_color(current_cls_id)
                cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
                
                display_text = f"{current_label} ID:{track_id}"
                
               
                cv2.rectangle(frame, (x1, y1-20), (x1+120, y1), box_color, -1)
                cv2.putText(frame, display_text, (x1, y1-5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            
            self.cleanup_inactive_tracks(active_track_ids)
        
        return frame, cheating_alerts
    
    def get_final_report(self):
        """Get final statistics report"""
        report = []
        for track_id, state in self.track_states.items():
            report.append({
                'track_id': track_id,
                'cheating_count': state['cheating_count'],
                'max_continuous_duration': state['continuous_cheating_duration'],
                'screenshot_taken': state['screenshot_taken']
            })
        return report

