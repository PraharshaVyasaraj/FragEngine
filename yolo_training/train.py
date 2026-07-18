import os
import sys

def check_dependencies():
    try:
        import ultralytics
        print("[INFO] ultralytics package is installed.")
    except ImportError:
        print("[INFO] ultralytics package is missing. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "ultralytics"])

def start_training():
    check_dependencies()
    from ultralytics import YOLO

    # 1. Initialize a lightweight YOLO model
    print("[INFO] Initializing yolov8n.pt...")
    model = YOLO("yolov8n.pt")

    # 2. Run model training on the custom dataset
    yaml_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "dataset.yaml"))
    print(f"[INFO] Starting training with config: {yaml_path}")
    
    # Check if dataset directories contain files
    train_images_dir = os.path.join(os.path.dirname(__file__), "dataset", "images", "train")
    has_files = False
    if os.path.exists(train_images_dir):
        files = [f for f in os.listdir(train_images_dir) if f != ".gitkeep"]
        if files:
            has_files = True
            
    if not has_files:
        print(f"\n[WARNING] The training directory '{train_images_dir}' is empty.")
        print("[WARNING] Please place your labeled training images and annotation files into:")
        print("  - images/train/ (images)")
        print("  - labels/train/ (YOLO txt labels)")
        print("\nAborting training. Populate dataset folders first.")
        return

    results = model.train(
        data=yaml_path,
        epochs=50,
        imgsz=256,
        batch=16,
        device="cpu", # Change to "0" or "cuda" if a CUDA-enabled GPU is available
        workers=2
    )

    # 3. Export model to ONNX for fast inference integration
    print("[INFO] Training complete. Exporting model to ONNX...")
    model.export(format="onnx")
    print("[INFO] YOLO custom model training workflow finished successfully!")

if __name__ == "__main__":
    start_training()
