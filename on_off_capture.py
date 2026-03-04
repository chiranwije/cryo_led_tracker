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
framerate = 1000 #was 1000 for 250us mightve been a limiting factor looking into it 
camera = None
camera_connected = False
recording = threading.Event()  # Use an Event to control recording
output_folder = "/home/laserlab/git/sampletrack/test/"
os.makedirs(output_folder, exist_ok=True)  # Ensure output directory exists

# --- New Global Variables for Live Location ---
live_location = 1
p_press_count = 0
# ---------------------------------------------

# Function to connect the camera
def connect_camera():
    global camera, camera_connected
    if not camera_connected:
        try:
            camera = neoapi.Cam()
            camera.Connect('700006383766')
            camera.f.ExposureTime.Set(250)  # Set exposure time was 250, 20 is the min
            camera.SetImageBufferCount(1000)
            # camera.SetImageBufferCycleCount(1000) # This feature might not be available or needed
            camera.f.Width.value = 160
            camera.f.Height.value = 160
            camera.f.OffsetY.value = 256
            camera.f.OffsetX.value = 224
            camera.f.Gain.value = 1
            camera.f.AcquisitionFrameRateEnable.value = True
            camera.f.AcquisitionFrameRate.value = framerate
            
            # Digital I/O
            camera.f.LineSelector.value = neoapi.LineSelector_Line2 # Select Line2
            camera.f.LineMode.value = neoapi.LineMode_Output # Set Line2 as output
            camera.f.LineSource.value = neoapi.LineSource_ExposureActive # Use ExposureActive signal
            camera.f.LineInverter.value = True  # Invert the signal
            
            camera_connected = True
            print("Camera TURNED ON.")
        except neoapi.NeoException as e:
            print(f"Error connecting to camera: {e}")
            camera = None
            camera_connected = False


# Function to disconnect the camera
def disconnect_camera():
    global camera, camera_connected
    if camera_connected and camera is not None:
        if camera.IsStreaming():
            camera.StopStreaming()
        camera.Disconnect()
        camera = None
        camera_connected = False
        print("Camera TURNED OFF.")

# Function to capture data
def capture_data():
    global positions, frame_count, live_location

    if camera_connected and camera is not None:
      camera.StartStreaming()

    while recording.is_set():
        if camera_connected and camera is not None:
            try:
                img = camera.GetImage()
                if not img.IsEmpty():
                    np_img = img.GetNPArray()
                    _, thresh = cv2.threshold(np_img, 50, 255, cv2.THRESH_BINARY)
                    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                    if contours:
                        largest_contour = max(contours, key=cv2.contourArea)
                        x, y, w, h = cv2.boundingRect(largest_contour)
                        center_x, center_y = x + w // 2, y + h // 2
                        timestamp = img.GetTimestamp()

                        # --- Append live_location to the positions data ---
                        positions.append((timestamp, center_x, center_y, live_location))
                        # ----------------------------------------------------

                        # Save in batches is a feature was problamatic for now
                        #if len(positions) % 1000 == 0:
                        #    np.save(os.path.join(output_folder, 'positions_live.npy'), np.array(positions))
                        frame_count += 1
                    else:
                        # If no contours are found, you might want to append a placeholder
                        # or handle it as an invalid frame, depending on your needs.
                        pass
                    
                    # It's important to release the image buffer
                    del img

                else:
                    # This case might indicate a buffer underrun or a problem with image acquisition
                    print("error") # Small sleep to prevent a tight loop on error

            except neoapi.NeoException as e:
                print(f"An error occurred during image acquisition: {e}")
                time.sleep(0.1) # Wait a bit before trying again
                
    if camera_connected and camera is not None and camera.IsStreaming():
        camera.StopStreaming()


# Function to start recording in a separate thread
def start_recording():
    global frame_count, positions
    frame_count = 0  # Reset frame count
    positions = [] # Clear previous recording data
    recording.set()  # Set event flag to True
    thread = threading.Thread(target=capture_data, daemon=True)
    thread.start()
    print("Recording started...")

# Function to stop recording
def stop_recording():
    if recording.is_set():
        recording.clear()  # Clear event flag to stop loop
        #print("\nStopping recording ... waiting for no reason for 1 second")
        # Give the thread a moment to finish processing the last frame
        #time.sleep(1)
        # Save any remaining data
        if positions:
            np.save(os.path.join(output_folder, 'positions_live_final.npy'), np.array(positions))
            print(f"Final data saved to {os.path.join(output_folder, 'positions_live_final.npy')}")
        print("Recording stopped.")

# --- Main execution block ---
if __name__ == "__main__":
    connect_camera()

    if camera_connected:
        start_recording()

        try:
            while recording.is_set():
                # --- MODIFIED LINE: Show current p-value in the input prompt ---
                prompt = f"Current p-value: {live_location} | Press 'p' to toggle, 'q' to quit: "
                user_input = input(prompt)
                # ----------------------------------------------------------------

                if user_input.lower() == 'q':
                    stop_recording()
                    break
                
                elif user_input.lower() == 'p':
                    p_press_count += 1
                    if p_press_count % 2 != 0: # Odd number of presses
                        live_location = 0
                    else: # Even number of presses
                        live_location = (p_press_count // 2) + 1
                    # The new value will be shown in the next prompt automatically

        except (KeyboardInterrupt, EOFError):
            # Added EOFError for cases where input stream is closed (e.g., piping)
            stop_recording()

    disconnect_camera()
    print("Program exited.")
    sys.exit(0)