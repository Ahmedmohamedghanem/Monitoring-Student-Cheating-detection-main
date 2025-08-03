# main/state.py
from collections import defaultdict
import time
from ultralytics import YOLO
from collections import defaultdict

cheating_stats = defaultdict(lambda: {"count": 0, "violations": []})

cheating_model = YOLO("main/Modelss/best.pt").to("cuda")


hall_active_models = {}  


cheating_live_count = defaultdict(int)       
cheating_temp_counter = defaultdict(int)     
cheating_last_reset = defaultdict(float)     
shared_frame_storage = {}                    


active_models = {}   
detectors = {}       
should_stop = {}     
threads = {}         
