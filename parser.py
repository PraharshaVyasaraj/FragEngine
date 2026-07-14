import os
# Direct OpenVINO execution target to GPU (Intel iGPU UHD 770)
os.environ["OPENVINO_DEVICE"] = "GPU"

import cv2
import numpy as np
from paddleocr import PaddleOCR

class FeedParser:
    def __init__(self, icons_dir):
        self.icons_dir = icons_dir
        self.templates = {}
        self.last_trace = {}
        # PP-OCRv5 Mobile — fastest stable model for short game text on Windows
        # use_angle_cls=False: kill feed text is always horizontal, skip rotation model
        # use_gpu=False:       run on CPU; OpenVINO handles iGPU acceleration separately
        # rec_model_dir=None:  auto-select PP-OCRv5 Mobile rec weights from PaddleOCR 2.7.x
        # Try OpenVINO GPU -> OpenVINO CPU -> Standard CPU
        try:
            self.ocr = PaddleOCR(
                use_angle_cls=False,
                lang='en',
                use_gpu=False,
                show_log=False,
                rec_algorithm='SVTR_LCNet',
                use_openvino=True,
                openvino_device='GPU',
                det_limit_side_len=600,
                rec_image_shape='3, 32, 160',
                rec_batch_num=2
            )
        except Exception as e:
            try:
                self.ocr = PaddleOCR(
                    use_angle_cls=False,
                    lang='en',
                    use_gpu=False,
                    show_log=False,
                    rec_algorithm='SVTR_LCNet',
                    use_openvino=True,
                    openvino_device='CPU',
                    det_limit_side_len=600,
                    rec_image_shape='3, 32, 160',
                    rec_batch_num=2
                )
            except Exception as e2:
                self.ocr = PaddleOCR(
                    use_angle_cls=False,
                    lang='en',
                    use_gpu=False,
                    show_log=False,
                    rec_algorithm='SVTR_LCNet',
                    det_limit_side_len=600,
                    rec_image_shape='3, 32, 160',
                    rec_batch_num=2
                )
        self.load_all_templates()
        
    def load_template(self, path):
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is None:
            return None
        
        # Extract template silhouette mask
        if img.shape[-1] == 4:
            alpha = img[:, :, 3]
            if alpha.min() < 255:
                gray = alpha
            else:
                gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        x, y, w, h = cv2.boundingRect(binary)
        if w > 0 and h > 0:
            return binary[y:y+h, x:x+w]
        return binary

    def load_all_templates(self):
        self.templates = {}
        
        # Helper to load template into a list (maps a single key to multiple visual shapes)
        def add_template(category, path):
            tpl = self.load_template(path)
            if tpl is not None:
                if category not in self.templates:
                    self.templates[category] = []
                self.templates[category].append(tpl)
                
        # Load States (KNOCK, FINISH, FALL, DROWN)
        states_dir = os.path.join(self.icons_dir, "STATES")
        for name in ["KNOCK", "FINISH", "FALL", "DROWN"]:
            p = os.path.join(states_dir, f"{name}.png")
            add_template(name, p)

        # Load Zone (ZONE)
        zone_path = os.path.join(self.icons_dir, "ZONE", "ZONE.png")
        add_template("ZONE", zone_path)
            
        # Load Grenade (THROWABLES/NADE.png)
        nade_path = os.path.join(self.icons_dir, "THROWABLES", "NADE.png")
        add_template("THROWABLE", nade_path)
            
        # Load Vehicles (EV, Taxi, Ferry, Helicopter)
        vehicles_dir = os.path.join(self.icons_dir, "VEHICLES")
        if os.path.exists(vehicles_dir):
            for filename in os.listdir(vehicles_dir):
                if filename.endswith(".png"):
                    add_template("VEHICLE", os.path.join(vehicles_dir, filename))
                    
        # Load Fist (MELEE/MELEE INGAME SS/FIST.png)
        fist_path = os.path.join(self.icons_dir, "MELEE", "MELEE INGAME SS", "FIST.png")
        add_template("FIST", fist_path)

    def match_icon(self, crop_gray, candidate_names, trace_list=None):
        best_score = -1
        best_name = "UNKNOWN"
        ch, cw = crop_gray.shape
        
        # Test thresholds to handle glowing text or background bleed
        thresholds = [160, 180, 200]
        # Test scale bounds to handle sizing discrepancies
        scales = [0.9, 1.0, 1.1]
        
        for thresh_val in thresholds:
            _, crop_binary = cv2.threshold(crop_gray, thresh_val, 255, cv2.THRESH_BINARY)
            
            for name in candidate_names:
                tpl_list = self.templates.get(name, [])
                for tpl_tight in tpl_list:
                    th, tw = tpl_tight.shape
                    
                    for scale_val in scales:
                        # Scale coordinates
                        target_w = max(1, int(cw * scale_val))
                        target_h = max(1, int(ch * scale_val))
                        
                        # Preserve template aspect ratio inside scaled target bounds
                        scale = min(target_w / tw, target_h / th)
                        new_w = max(1, int(tw * scale))
                        new_h = max(1, int(th * scale))
                        
                        tpl_resized = cv2.resize(tpl_tight, (new_w, new_h))
                        _, tpl_binary = cv2.threshold(tpl_resized, 127, 255, cv2.THRESH_BINARY)
                        
                        # Pad resized template to exactly match target bounds
                        pad_y = (target_h - new_h) // 2
                        pad_bottom = target_h - new_h - pad_y
                        pad_x = (target_w - new_w) // 2
                        pad_right = target_w - new_w - pad_x
                        
                        tpl_padded = cv2.copyMakeBorder(
                            tpl_binary, 
                            pad_y, pad_bottom, pad_x, pad_right, 
                            cv2.BORDER_CONSTANT, 
                            value=0
                        )
                        
                        # Resize crop to match padded template exactly if scaled
                        if scale_val != 1.0:
                            crop_evaluated = cv2.resize(crop_binary, (target_w, target_h))
                        else:
                            crop_evaluated = crop_binary
                            
                        res = cv2.matchTemplate(crop_evaluated, tpl_padded, cv2.TM_CCOEFF_NORMED)
                        _, max_val, _, _ = cv2.minMaxLoc(res)
                        
                        if trace_list is not None:
                            trace_list.append({
                                "category": name,
                                "threshold": thresh_val,
                                "scale": scale_val,
                                "score": float(max_val)
                            })
                        
                        if max_val > best_score:
                            best_score = max_val
                            best_name = name
                            
        return best_name, best_score

    def process_frame(self, img):
        """
        Processes a single screenshot frame (cropped to the feed ROI).
        Returns a dict with layout, t1, i1, i2, t2, and confidence metrics,
        or None if layout is unrecognizable.
        """
        if img is None:
            return None
            
        h, w, _ = img.shape
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        import time
        t_ocr_start = time.perf_counter()
        
        # Run PP-OCRv5 Mobile text extraction (PaddleOCR 2.7.x API)
        # Returns: [ [ [ [x,y]x4 ], (text, prob) ], ... ] per page
        results = self.ocr.ocr(img, cls=False)
        t_ocr_end = time.perf_counter()
        ocr_ms = (t_ocr_end - t_ocr_start) * 1000
        
        text_blocks = []
        ocr_confidences = []
        
        debug_trace = {
            "raw_ocr": [],
            "filtered_ocr": [],
            "layout": "unrecognizable",
            "icon_band": {},
            "contours": [],
            "template_evaluations": []
        }

        # PaddleOCR 2.x: results[0] is the list of detections for the first (and only) image
        page_results = results[0] if results and results[0] else []
        for line in page_results:
            bbox, (text, prob) = line
            debug_trace["raw_ocr"].append({
                "text": text,
                "confidence": float(prob),
                "bbox": [[float(pt[0]), float(pt[1])] for pt in bbox]
            })
            x1 = int(bbox[0][0])
            x2 = int(bbox[2][0])
            y1 = int(bbox[0][1])
            y2 = int(bbox[2][1])
            # Only keep reliable text blocks that are wide enough
            if (x2 - x1) > 10 and prob > 0.2:
                text_blocks.append({"text": text.strip(), "x1": x1, "x2": x2, "y1": y1, "y2": y2})
                ocr_confidences.append(prob)
                debug_trace["filtered_ocr"].append({
                    "text": text.strip(),
                    "x1": x1, "x2": x2, "y1": y1, "y2": y2,
                    "confidence": float(prob)
                })
                
        ocr_confidence_avg = float(np.mean(ocr_confidences)) if ocr_confidences else 0.0
                
        # Sort left-to-right
        text_blocks = sorted(text_blocks, key=lambda b: b["x1"])
        
        if len(text_blocks) == 2:
            layout = "2T2I"
            t1 = text_blocks[0]["text"]
            t2 = text_blocks[1]["text"]
            icon_x1 = text_blocks[0]["x2"]
            icon_x2 = text_blocks[1]["x1"]
        elif len(text_blocks) == 1:
            layout = "1T2I"
            t1 = text_blocks[0]["text"]
            t2 = "None"
            icon_x1 = text_blocks[0]["x2"]
            icon_x2 = w
        else:
            debug_trace["layout"] = "unrecognizable"
            self.last_trace = debug_trace
            return {
                "status": "unrecognizable",
                "_timings": {
                    "ocr": ocr_ms,
                    "icon_match": 0.0
                },
                "debug_trace": debug_trace
            }
            
        debug_trace["layout"] = layout
        debug_trace["icon_band"] = {"x1": icon_x1, "x2": icon_x2}
        t_match_start = time.perf_counter()
        # Isolate the horizontal band containing the icons
        icon_band_gray = gray[:, icon_x1:icon_x2]
        _, thresh = cv2.threshold(icon_band_gray, 180, 255, cv2.THRESH_BINARY)
        
        # Locate individual icon shapes
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        icon_crops = []
        for c in contours:
            x, y, cw, ch = cv2.boundingRect(c)
            # Standard game HUD icons (weapons, states, zone) are at least 12x12 pixels.
            # Discard smaller background noise contours.
            if cw >= 12 and ch >= 12:
                crop = icon_band_gray[y:y+ch, x:x+cw]
                icon_crops.append((x, crop))
                
        # Sort left-to-right
        icon_crops = sorted(icon_crops, key=lambda ic: ic[0])
        extracted_icons = [ic[1] for ic in icon_crops]
        
        i1 = "UNKNOWN"
        i2 = "UNKNOWN"
        i1_score = 0.0
        i2_score = 0.0
        
        if layout == "2T2I":
            if len(extracted_icons) >= 2:
                action_crop = extracted_icons[0]
                state_crop = extracted_icons[1]
                
                # Match action icon against special categories (GRENADE maps to THROWABLE)
        # Trace contour extraction
        for c in contours:
            x, y, cw, ch = cv2.boundingRect(c)
            debug_trace["contours"].append({
                "x": x, "y": y, "width": cw, "height": ch,
                "status": "accepted" if (cw >= 12 and ch >= 12) else "rejected"
            })

        if layout == "2T2I":
            if len(extracted_icons) >= 2:
                action_crop = extracted_icons[0]
                state_crop = extracted_icons[1]
                
                # Match action icon against special categories (GRENADE maps to THROWABLE)
                match_name, match_score = self.match_icon(action_crop, ["THROWABLE", "VEHICLE", "FIST"], debug_trace["template_evaluations"])
                i1_score = float(match_score)
                if (match_name == "FIST" and match_score >= 0.40) or (match_name != "FIST" and match_score >= 0.60):
                    i1 = match_name
                else:
                    i1 = "Weapon"
                    
                # Match state icon
                match_name2, match_score2 = self.match_icon(state_crop, ["KNOCK", "FINISH"], debug_trace["template_evaluations"])
                i2_score = float(match_score2)
                i2 = match_name2
            elif len(extracted_icons) == 1:
                # Fallback if both merged or one missed
                single_crop = extracted_icons[0]
                state_name, state_score = self.match_icon(single_crop, ["KNOCK", "FINISH"], debug_trace["template_evaluations"])
                if state_score >= 0.50:
                    i2 = state_name
                    i2_score = float(state_score)
                    i1 = "Weapon"
                else:
                    action_name, action_score = self.match_icon(single_crop, ["THROWABLE", "VEHICLE", "FIST"], debug_trace["template_evaluations"])
                    i1_score = float(action_score)
                    if (action_name == "FIST" and action_score >= 0.40) or (action_name != "FIST" and action_score >= 0.60):
                        i1 = action_name
                    else:
                        i1 = "Weapon"
                    i2 = "UNKNOWN"
            else:
                i1 = "Weapon"
                i2 = "UNKNOWN"
        elif layout == "1T2I":
            if len(extracted_icons) >= 2:
                match_name, match_score = self.match_icon(extracted_icons[0], ["ZONE", "FALL", "DROWN"], debug_trace["template_evaluations"])
                i1 = match_name
                i1_score = float(match_score)
                
                match_name2, match_score2 = self.match_icon(extracted_icons[1], ["KNOCK", "FINISH"], debug_trace["template_evaluations"])
                i2 = match_name2
                i2_score = float(match_score2)
            elif len(extracted_icons) == 1:
                # Fallback if both merged
                match_name2, match_score2 = self.match_icon(extracted_icons[0], ["KNOCK", "FINISH"], debug_trace["template_evaluations"])
                i2 = match_name2
                i2_score = float(match_score2)
                
        t_match_end = time.perf_counter()
        match_ms = (t_match_end - t_match_start) * 1000
        
        self.last_trace = debug_trace
                
        return {
            "layout": layout,
            "t1": t1,
            "i1": i1,
            "i1_confidence": i1_score,
            "i2": i2,
            "i2_confidence": i2_score,
            "t2": t2,
            "ocr_confidence": ocr_confidence_avg,
            "_timings": {
                "ocr": ocr_ms,
                "icon_match": match_ms
            },
            "debug_trace": debug_trace
        }
