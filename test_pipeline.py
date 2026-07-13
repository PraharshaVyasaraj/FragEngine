import cv2
import numpy as np
import os
import easyocr

# Setup paths
base_dir = r"E:\Games Data\SAMPLE_IMAGESET_FEED"
samples_dir = os.path.join(base_dir, "TRANING_FEED_SAMPLE")
icons_dir = r"E:\Games Data\SF FEED ICONS"

def load_template(path):
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        return None
    
    # Extract raw mask from alpha or grayscale
    if img.shape[-1] == 4:
        alpha = img[:, :, 3]
        if alpha.min() < 255:
            gray = alpha
        else:
            gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
    else:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
    # Binarize template
    _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    
    # Crop to tight bounding box of non-zero (white) pixels
    x, y, w, h = cv2.boundingRect(binary)
    if w > 0 and h > 0:
        tight = binary[y:y+h, x:x+w]
        return tight
    return binary

# Load templates
templates = {}

# Load States
states_dir = os.path.join(icons_dir, "STATES")
for name in ["KNOCK", "FINISH", "FALL", "DROWN"]:
    p = os.path.join(states_dir, f"{name}.png")
    if os.path.exists(p):
        templates[name] = load_template(p)

# Load Zone
zone_path = os.path.join(icons_dir, "ZONE", "ZONE.png")
if os.path.exists(zone_path):
    templates["ZONE"] = load_template(zone_path)

print("Loaded templates (after tight cropping):")
for k, v in templates.items():
    print(f"  {k}: shape {v.shape}")

reader = easyocr.Reader(['en'])

def match_icon(crop_binary, candidate_names, debug=False):
    best_score = -1
    best_name = "UNKNOWN"
    
    ch, cw = crop_binary.shape
    if debug:
        print(f"  Debugging matching for crop shape: {crop_binary.shape}")
        
    for name in candidate_names:
        tpl_tight = templates.get(name)
        if tpl_tight is None:
            continue
        
        # Resize the pre-cropped binary template to exactly match the crop shape
        tpl_resized = cv2.resize(tpl_tight, (cw, ch))
        
        # Ensure strict binary (0 or 255)
        _, tpl_binary = cv2.threshold(tpl_resized, 127, 255, cv2.THRESH_BINARY)
            
        res = cv2.matchTemplate(crop_binary, tpl_binary, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        
        if debug:
            print(f"    Template '{name}': Match Score = {max_val:.4f}")
            
        if max_val > best_score:
            best_score = max_val
            best_name = name
            
    return best_name, best_score

def process_image(img_path):
    img = cv2.imread(img_path)
    if img is None:
        return "FAILED TO LOAD IMAGE"
    
    h, w, _ = img.shape
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Run EasyOCR
    results = reader.readtext(img)
    
    # Filter and sort text results left-to-right
    text_blocks = []
    for res in results:
        bbox, text, prob = res
        x1 = int(bbox[0][0])
        x2 = int(bbox[2][0])
        y1 = int(bbox[0][1])
        y2 = int(bbox[2][1])
        if (x2 - x1) > 10 and prob > 0.2:
            text_blocks.append({"text": text, "x1": x1, "x2": x2, "y1": y1, "y2": y2})
            
    text_blocks = sorted(text_blocks, key=lambda b: b["x1"])
    
    if len(text_blocks) == 2:
        layout = "2T2I"
        t1_name = text_blocks[0]["text"]
        t2_name = text_blocks[1]["text"]
        icon_x1 = text_blocks[0]["x2"]
        icon_x2 = text_blocks[1]["x1"]
    elif len(text_blocks) == 1:
        layout = "1T2I"
        t1_name = text_blocks[0]["text"]
        t2_name = "None"
        icon_x1 = text_blocks[0]["x2"]
        icon_x2 = w
    else:
        return f"UNKNOWN LAYOUT (Found {len(text_blocks)} text blocks)"
        
    icon_band_gray = gray[:, icon_x1:icon_x2]
    # We binarize the horizontal band
    _, thresh = cv2.threshold(icon_band_gray, 180, 255, cv2.THRESH_BINARY)
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    icon_crops = []
    for c in contours:
        x, y, cw, ch = cv2.boundingRect(c)
        if cw > 5 and ch > 5:
            # Crop from the binarized image (thresh)
            crop = thresh[y:y+ch, x:x+cw]
            icon_crops.append((x, crop))
            
    icon_crops = sorted(icon_crops, key=lambda ic: ic[0])
    extracted_icons = [ic[1] for ic in icon_crops]
    
    i1_name = "UNKNOWN"
    i2_name = "UNKNOWN"
    
    print(f"\n--- Diagnostic for {os.path.basename(img_path)} ({layout}) ---")
    print(f"Detected {len(extracted_icons)} icon crops in horizontal band.")
    
    if layout == "2T2I":
        i1_name = "Weapon"
        if len(extracted_icons) >= 1:
            state_crop = extracted_icons[-1]
            i2_name, _ = match_icon(state_crop, ["KNOCK", "FINISH"], debug=True)
    elif layout == "1T2I":
        if len(extracted_icons) >= 2:
            print("Matching Icon 1 (Hazard):")
            i1_name, _ = match_icon(extracted_icons[0], ["ZONE", "FALL", "DROWN"], debug=True)
            print("Matching Icon 2 (State):")
            i2_name, _ = match_icon(extracted_icons[1], ["KNOCK", "FINISH"], debug=True)
        elif len(extracted_icons) == 1:
            i2_name, _ = match_icon(extracted_icons[0], ["KNOCK", "FINISH"], debug=True)
            
    return f"RESULT: {layout} | T1: {t1_name} | I1: {i1_name} | I2: {i2_name} | T2: {t2_name}"

images = ["SAMPLE_ZONE_FINISH_1T2I.png", "SAMPLE_WEAPON_KNOCK_2T2I.png", "SAMPLE_FIST_FINISH_2T2I.png"]
for img_name in images:
    p = os.path.join(samples_dir, img_name)
    res = process_image(p)
    print(res)
