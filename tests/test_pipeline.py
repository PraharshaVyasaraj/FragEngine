import cv2
import os
import pytest
import sys

# Skip in CI since it depends on local gitignored assets
if os.environ.get("GITHUB_ACTIONS") == "true":
    pytest.skip("Skipping local integration tests in CI environment", allow_module_level=True)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from parser import FeedParser

# Setup paths
base_dir = r"C:\FragEngine"
samples_dir = os.path.join(base_dir, "TRANING_FEED_SAMPLE")
icons_dir = r"C:\FragEngine\icons"

def test_feed_parser():
    parser = FeedParser(icons_dir)
    
    images = ["SAMPLE_ZONE_FINISH_1T2I.png", "SAMPLE_WEAPON_KNOCK_2T2I.png", "SAMPLE_FIST_FINISH_2T2I.png"]
    for img_name in images:
        p = os.path.join(samples_dir, img_name)
        img = cv2.imread(p)
        assert img is not None
        
        res = parser.process_frame(img)
        assert res is not None
        assert "layout" in res
        print(f"\n--- {img_name} ---")
        print(f"Parsed layout: {res['layout']}")
        print(f"T1: {res['t1']} | I1: {res['i1']} ({res['i1_confidence']:.2f}) | I2: {res['i2']} ({res['i2_confidence']:.2f}) | T2: {res['t2']}")
        
        if img_name == "SAMPLE_ZONE_FINISH_1T2I.png":
            assert res["layout"] == "T1I2"
            assert res["i1"] == "ZONE"
            assert res["i2"] == "FINISH"
        elif img_name == "SAMPLE_WEAPON_KNOCK_2T2I.png":
            assert res["layout"] == "T2I2"
            assert res["i1"] == "Weapon"
            assert res["i2"] == "KNOCK"
        elif img_name == "SAMPLE_FIST_FINISH_2T2I.png":
            assert res["layout"] == "T2I2"
            assert res["i1"] == "FIST"
            assert res["i2"] == "FINISH"

if __name__ == "__main__":
    test_feed_parser()
