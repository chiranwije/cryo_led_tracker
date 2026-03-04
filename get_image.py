import cv2
import numpy as np
import pandas as pd
import neoapi
import time
import matplotlib.pyplot as plt
import argparse
import os

def main():
    parser = argparse.ArgumentParser(description='Capture frames from camera.')
    parser.add_argument('--frames', type=int, default=100, help='Number of frames to capture')
    parser.add_argument('--folder', type=str, default='output_images', help='Folder name to save images')
    args = parser.parse_args()
    time_list=[1000,10000,20000,30000,40000,50000,60000,70000,80000,90000,100000,1000000]

    save_dir = os.path.join('/home/laserlab/data/ecqd/spatial_data/sep25_unpol/', args.folder)
    os.makedirs(save_dir, exist_ok=True)

    # Initialize and connect to camera
    camera = neoapi.Cam()
    try:
        camera.Connect('700006260959')
        if camera.IsConnected():
            print("Camera connected successfully.")
            
            
            # Set camera parameters
            camera.f.Width.value = 640
            camera.f.Height.value = 480
            camera.f.OffsetY.value = 0
            camera.f.Gain.value = 1
              # in microseconds
            camera.f.AcquisitionFrameRateEnable.value = True
            camera.f.AcquisitionFrameRate.value = 50000  # fps

            # Capture frames
            for i in range(len(time_list)):
                camera.f.ExposureTime.Set(time_list[i])
                image = camera.GetImage().GetNPArray()
                filename = os.path.join(save_dir, f'image{i}.npy')
                np.save(filename, image)

            print(f"Captured and saved {args.frames} frames to {save_dir}")
        else:
            print("Failed to connect to the camera.")
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        if camera.IsConnected():
            camera.Disconnect()
            print("Camera disconnected.")

if __name__ == '__main__':
    main()
