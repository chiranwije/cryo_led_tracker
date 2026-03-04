import numpy as np
import os
import time
import sys
import cv2
import neoapi
import threading


# Global Variables
frame_count = 0  # Track the number of captured frames
positions = []
framerate = 1000 
camera = None
camera_connected = False  
recording = threading.Event()  # Use an Event to control recording
output_folder = "/home/laserlab/git/sampletrack/data"
os.makedirs(output_folder, exist_ok=True)  # Ensure output directory exists

# Function to connect the camera
def connect_camera():
    global camera, camera_connected
    if not camera_connected:
        camera = neoapi.Cam()
        camera.ClearImages()
        #camera.StartStreaming()

        camera.Connect('700006383766')
        camera.f.ExposureTime.Set(250)  # Set exposure time
        camera.SetImageBufferCount(1000)
        camera.SetImageBufferCycleCount(1000)
        #camera.SetUserBufferMode()
        camera.f.Width.value = 160
        camera.f.Height.value = 160
        camera.f.OffsetY.value = 256
        camera.f.OffsetX.value = 224
        camera.f.Gain.value = 1
        camera.f.AcquisitionFrameRateEnable.value = True
        camera.f.AcquisitionFrameRate.value = framerate
        camera_connected = True
        # Digital I/O
        camera.f.LineSelector.value = neoapi.LineSelector_Line2 # Select Line2
        camera.f.LineMode.value = neoapi.LineMode_Output # Set Line2 as output
        camera.f.LineSource.value = neoapi.LineSource_ExposureActive # Use ExposureActive signal
        camera.f.LineInverter.value = True  # Invert the signal
        print("Camera TURNED ON.")

# Function to disconnect the camera
def disconnect_camera():
    global camera, camera_connected
    if camera_connected and camera is not None:
        camera.Disconnect()
        camera = None  
        camera_connected = False
        print("Camera TURNED OFF.")

# Function to capture data
def capture_data():
    global positions, frame_count

    while recording.is_set():
        if camera_connected and camera is not None:
            
            img = camera.GetImage()
            if not img.IsEmpty():
                _, thresh = cv2.threshold(img.GetNPArray(), 50, 255, cv2.THRESH_BINARY)
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    largest_contour = max(contours, key=cv2.contourArea)
                    x, y, w, h = cv2.boundingRect(largest_contour)
                    center_x, center_y = x + w // 2, y + h // 2
                    timestamp = img.GetTimestamp()
                    positions.append((timestamp, center_x, center_y))



# skip the issue of saving every 1000 frames and causing huge time delays
                    # Save in batches
                    #if frame_count % 1000 == 0:
                      #np.save(f'positions_live.npy', np.array(positions))
                
                    #frame_count += 1

                    # Periodic buffer clearing
                    if frame_count % 10000 == 0:
                      camera.ClearImages()
                      
                    #positions.append((timestamp, center_x, center_y))
                    #np.save(f'positions_live.npy', np.array(positions))  # Save continuously
                    # Periodic buffer clearing
                    #if frame_count % 1000 == 0:
                    #    camera.ClearImages()
                        
                    #frame_count += 1  # Increment frame count
                    #print(f"Frame {frame_count}: Position ({center_x}, {center_y})")
                    
                    # Stop and restart after 1000 frames
                    #if frame_count >= 1000:
                    #    print("\nStopping recording after 1000 frames...")
                    #    stop_recording()
                    #    frame_count = 0  # Reset frame count
                    #    start_recording()
                    #    continue  # Skip further processing in this loop
                    #clear images
                    #camera.ClearImages()
                    del img
                    np.save(f'positions_live.npy', np.array(positions))

                else:
                    print("No contours detected! Stopping recording...")
                    stop_recording()
                    break  # Exit loop if no object detected

# Function to start recording in a separate thread
def start_recording():
    global frame_count
    frame_count = 0  # Reset frame count
    recording.set()  # Set event flag to True
    thread = threading.Thread(target=capture_data, daemon=True)
    thread.start()
    print("Recording started... Type 'q' and press Enter to stop.")

# Function to stop recording
def stop_recording():
    recording.clear()  # Clear event flag to stop loop
    print("\nRecording stopped.")

# Start with the camera connected
connect_camera()
start_recording()

# Main loop to listen for 'Q' press
try:
    while recording.is_set():
        user_input = input()  # Wait for user input
        if user_input.lower() == 'q':  # If 'q' or 'Q' is entered
            stop_recording()
            break
except KeyboardInterrupt:
    stop_recording()

disconnect_camera()
sys.exit(0)