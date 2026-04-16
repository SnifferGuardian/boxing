# import sys
# import os

# # Force Python to look in your new 'libs' folder first
# lib_path = r"C:\Users\Matt\Desktop\yolopose\libs"
# sys.path.insert(0, lib_path)

# from ultralytics import YOLO

# def build_engine():
#     try:
#         print("--- Loading YOLO11-Pose ---")
#         model = YOLO("yolo11n-pose.pt")

#         print("--- Starting TensorRT Export (this uses your 194 TOPS) ---")
#         # half=True is key for your RTX 4050's Tensor Cores
#         model.export(
#             format="engine", 
#             device=0, 
#             half=True, 
#             workspace=4, 
#             imgsz=640
#         )
        
#         print("\nSUCCESS! Check your folder for 'yolo11n-pose.engine'")
#     except Exception as e:
#         print(f"\nExport failed: {e}")

# if __name__ == "__main__":
#     build_engine()
from ultralytics import YOLO
model = YOLO("yolo11n-pose.pt")
model.export(format="coreml", nms=True)