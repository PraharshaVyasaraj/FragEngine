import os
import logging

class DataQualityValidator:
    def __init__(self, log_path=None):
        if log_path is None:
            log_path = r"C:\FragEngine\data\data_quality.log"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        
        self.logger = logging.getLogger("DataQuality")
        self.logger.setLevel(logging.WARNING)
        if not self.logger.handlers:
            handler = logging.FileHandler(log_path, encoding="utf-8")
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def validate_telemetry_row(self, row_dict):
        """
        Validates telemetry data records.
        Returns (is_valid, list_of_warnings)
        """
        warnings = []
        
        # Validate CPU_Percent
        cpu = row_dict.get("CPU_Percent", 0.0)
        if not (0.0 <= cpu <= 100.0):
            warnings.append(f"CPU_Percent ({cpu}) out of bounds [0, 100]")
            
        # Validate RAM_MB
        ram = row_dict.get("RAM_MB", 0.0)
        if ram < 0:
            warnings.append(f"RAM_MB ({ram}) is negative")
            
        # Validate GPU_Percent
        gpu = row_dict.get("GPU_Percent", 0.0)
        if not (0.0 <= gpu <= 100.0):
            warnings.append(f"GPU_Percent ({gpu}) out of bounds [0, 100]")
            
        # Validate Latencies
        for k in ["Decode_ms", "Preprocess_ms", "OCR_ms", "IconMatch_ms", "DictCorrection_ms", "Total_Latency_ms"]:
            val = row_dict.get(k, 0.0)
            if val < 0:
                warnings.append(f"{k} ({val}) is negative")
                
        # Validate OCR Confidence
        conf = row_dict.get("OCR_Confidence_Avg", 0.0)
        if not (0.0 <= conf <= 1.0):
            warnings.append(f"OCR_Confidence_Avg ({conf}) out of bounds [0.0, 1.0]")
            
        # Validate Levenshtein Distance
        lev = row_dict.get("Avg_Levenshtein_Dist", 0.0)
        if lev < 0:
            warnings.append(f"Avg_Levenshtein_Dist ({lev}) is negative")
            
        # Validate Row_Index
        row_idx = row_dict.get("Row_Index", 0)
        if not (0 <= row_idx <= 3):
            warnings.append(f"Row_Index ({row_idx}) out of bounds [0, 3]")
            
        if warnings:
            self.logger.warning(f"Telemetry Validation Warning: {'; '.join(warnings)}")
            return False, warnings
        return True, []

    def validate_parsed_event(self, event_dict):
        """
        Validates OCR-parsed game events.
        """
        warnings = []
        layout = event_dict.get("layout")
        if layout not in ["T1I2", "T2I2"]:
            warnings.append(f"Unexpected layout type: {layout}")
            
        t1 = event_dict.get("t1", "")
        t2 = event_dict.get("t2", "")
        
        if layout == "T2I2":
            if not t1 or t1 == "None":
                warnings.append("Parsed player T1 name is empty or None in T2I2")
            if not t2 or t2 == "None":
                warnings.append("Parsed player T2 name is empty or None in T2I2")
        elif layout == "T1I2":
            if not t1 or t1 == "None":
                warnings.append("Parsed player T1 name is empty or None in T1I2")
            
        i1 = event_dict.get("i1", "")
        if not i1:
            warnings.append("Primary icon category I1 is empty")
            
        if warnings:
            self.logger.warning(f"Event Validation Warning: {'; '.join(warnings)}")
            return False, warnings
        return True, []
