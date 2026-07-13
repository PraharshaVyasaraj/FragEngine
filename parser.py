import cv2
import numpy as np
import os
import easyocr

class FeedParser:
    def __init__(self, icons_dir):
        self.icons_dir = icons_dir
        self.templates = {}
        self.reader = easyocr.Reader(['en'], gpu=False) # Default to CPU as it's small crop
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
        # Load States
        states_dir = os.path.join(self.icons_dir, "STATES")
        for name in ["KNOCK", "FINISH", "FALL", "DROWN"]:
            p = os.path.join(states_dir, f"{name}.png")
            if os.path.exists(p):
                self.templates[name] = self.load_template(p)

        # Load Zone
        zone_path = os.path.join(self.icons_dir, "ZONE", "ZONE.png")
        if os.path.exists(zone_path):
            self.templates["ZONE"] = self.load_template(zone_path)

    def match_icon(self, crop_binary, candidate_names):
        best_score = -1
        best_name = "UNKNOWN"
        ch, cw = crop_binary.shape
        
        for name in candidate_names:
            tpl_tight = self.templates.get(name)
            if tpl_tight is None:
                continue
            
            # Resize template to crop shape
            tpl_resized = cv2.resize(tpl_tight, (cw, ch))
            _, tpl_binary = cv2.threshold(tpl_resized, 127, 255, cv2.THRESH_BINARY)
                
            res = cv2.matchTemplate(crop_binary, tpl_binary, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            
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
        # Run EasyOCR text detection
        results = self.reader.readtext(img)
        t_ocr_end = time.perf_counter()
        ocr_ms = (t_ocr_end - t_ocr_start) * 1000
        
        text_blocks = []
        for res in results:
            bbox, text, prob = res
            x1 = int(bbox[0][0])
            x2 = int(bbox[2][0])
            y1 = int(bbox[0][1])
            y2 = int(bbox[2][1])
            # Only keep reliable text blocks that are wide enough
            if (x2 - x1) > 10 and prob > 0.2:
                text_blocks.append({"text": text.strip(), "x1": x1, "x2": x2, "y1": y1, "y2": y2})
                
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
            return None # Skip empty/noisy frames
            
        t_match_start = time.perf_counter()
        # Isolate the horizontal band containing the icons
        icon_band_gray = gray[:, icon_x1:icon_x2]
        _, thresh = cv2.threshold(icon_band_gray, 180, 255, cv2.THRESH_BINARY)
        
        # Locate individual icon shapes
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        icon_crops = []
        for c in contours:
            x, y, cw, ch = cv2.boundingRect(c)
            if cw > 5 and ch > 5:
                crop = thresh[y:y+ch, x:x+cw]
                icon_crops.append((x, crop))
                
        # Sort left-to-right
        icon_crops = sorted(icon_crops, key=lambda ic: ic[0])
        extracted_icons = [ic[1] for ic in icon_crops]
        
        i1 = "UNKNOWN"
        i2 = "UNKNOWN"
        
        if layout == "2T2I":
            i1 = "Weapon"
            if len(extracted_icons) >= 1:
                state_crop = extracted_icons[-1]
                i2, _ = self.match_icon(state_crop, ["KNOCK", "FINISH"])
        elif layout == "1T2I":
            if len(extracted_icons) >= 2:
                i1, _ = self.match_icon(extracted_icons[0], ["ZONE", "FALL", "DROWN"])
                i2, _ = self.match_icon(extracted_icons[1], ["KNOCK", "FINISH"])
            elif len(extracted_icons) == 1:
                # Fallback if both merged
                i2, _ = self.match_icon(extracted_icons[0], ["KNOCK", "FINISH"])
        t_match_end = time.perf_counter()
        match_ms = (t_match_end - t_match_start) * 1000
                
        return {
            "layout": layout,
            "t1": t1,
            "i1": i1,
            "i2": i2,
            "t2": t2,
            "_timings": {
                "ocr": ocr_ms,
                "icon_match": match_ms
            }
        }
