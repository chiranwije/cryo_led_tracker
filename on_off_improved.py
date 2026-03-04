import numpy as np
import os
import time
import sys
import cv2
import neoapi
import threading
import queue
from concurrent.futures import ThreadPoolExecutor

# --- Global Variables ---
# Threading and Queue Management
processing_finished = threading.Event()
recording_active = threading.Event()
# The queue size acts as a buffer. If the consumer falls behind, this queue
# will hold raw frames. A larger size can handle longer processing spikes.
frame_queue = queue.Queue(maxsize=10000)
# A new queue to hold processed data ready for saving
save_queue = queue.Queue()

# Camera and Data
camera = None
camera_connected = False
framerate = 1000
output_folder = "/home/laserlab/git/sampletrack/pico/oct6/pulse/8hrs20ns8ns8nsleft/"
os.makedirs(output_folder, exist_ok=True)

# Live Location Tracking
live_location = 1
p_press_count = 0

# --- Camera Management ---

def connect_camera():
    """Connects and configures the camera."""
    global camera, camera_connected
    if camera_connected:
        print("Camera is already connected.")
        return
    try:
        camera = neoapi.Cam()
        camera.Connect('700006383766')
        camera.SetImageBufferCount(1000)  # Allocate host-side buffers for driver was 1000

        # --- Settings ---
        camera.f.ExposureTime.Set(250)  # Min exposure 20 for max framerate
        camera.f.Width.value = 160
        camera.f.Height.value = 160
        camera.f.OffsetY.value = 256
        camera.f.OffsetX.value = 224
        camera.f.Gain.value = 1

        # --- Framerate Control ---
        camera.f.AcquisitionFrameRateEnable.value = True
        camera.f.AcquisitionFrameRate.value = framerate

        # --- Digital I/O ---
        camera.f.LineSelector.value = neoapi.LineSelector_Line2
        camera.f.LineMode.value = neoapi.LineMode_Output
        camera.f.LineSource.value = neoapi.LineSource_ExposureActive
        camera.f.LineInverter.value = False

        camera_connected = True
        print("✅ Camera connected successfully.")
    except neoapi.NeoException as e:
        print(f"❌ Error connecting to camera: {e}")
        camera = None
        camera_connected = False

def disconnect_camera():
    """Stops streaming and disconnects the camera."""
    global camera, camera_connected
    if camera_connected and camera:
        if camera.IsStreaming():
            camera.StopStreaming()
        camera.Disconnect()
        camera = None
        camera_connected = False
        print("Camera TURNED OFF.")

# --- Threading Tasks (Producer-Consumer-Saver) ---

def producer_task():
    """
    PRODUCER: Acquires images from camera and puts them in a queue.
    This thread does no processing to ensure it can run as fast as the camera.
    """
    print("🚀 Producer thread started.")
    try:
        camera.StartStreaming()
        while recording_active.is_set():
            try:
                img = camera.GetImage()
                if not img.IsEmpty():
                    # Put raw image data and current metadata into the queue
                    frame_queue.put((img.GetNPArray(), img.GetTimestamp(), live_location), block=False)
            except neoapi.NeoException as e:
                print(f"⚠️ Producer error: {e}")
                time.sleep(0.01)  # Wait briefly on hardware error
            except queue.Full:
                # This is a critical warning: the consumer is too slow and the buffer is full.
                # Frames are now being dropped by the camera hardware.
                print("⚠️ CRITICAL: Frame queue is full! Consumer cannot keep up.")
                time.sleep(0.01) # Give consumer a moment to catch up
    finally:
        if camera and camera.IsStreaming():
            camera.StopStreaming()
        print("🛑 Producer thread stopped.")

'''
def consumer_task():
    """
    CONSUMER (PROCESSOR): Processes images from the queue, puts results in save_queue.
    Uses a thread pool for parallel image processing.
    """
    print("🛠️ Consumer thread started.")
    
    SAVE_CHUNK_SIZE = 100000
    positions_chunk = np.empty((SAVE_CHUNK_SIZE, 4), dtype=np.int64)
    chunk_index = 0

    def process_frame(np_img, timestamp, location_val):
        """Helper function to process a single frame."""
        _, thresh = cv2.threshold(np_img, 50, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            return timestamp, x + w // 2, y + h // 2, location_val
        return None

    # Using a ThreadPoolExecutor to parallelize the contour finding
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as pool:
        # Loop continues as long as the recording is active OR there are frames left to process
        while not (processing_finished.is_set() and frame_queue.empty()):
            try:
                # Get a frame from the queue, waiting up to 1 second
                np_img, timestamp, location_val = frame_queue.get(timeout=1)
                
                # Submit processing to the thread pool
                future = pool.submit(process_frame, np_img, timestamp, location_val)
                result = future.result()

                if result:
                    positions_chunk[chunk_index] = result
                    chunk_index += 1

                # If the chunk is full, pass it to the saver thread
                if chunk_index == SAVE_CHUNK_SIZE:
                    save_queue.put(positions_chunk.copy())
                    # Start a new chunk
                    positions_chunk = np.empty((SAVE_CHUNK_SIZE, 4), dtype=np.int64)
                    chunk_index = 0

                frame_queue.task_done()
            except queue.Empty:
                # This is expected when the producer has stopped but the consumer is finishing up
                continue

    # After the main loop, there might be a partially filled chunk left. Save it.
    if processing_finished.is_set():
        save_queue.put(positions_chunk[:chunk_index].copy())
    
    print("🛑 Consumer thread stopped.")

def saver_task():
    """
    SAVER: Gets processed data from the save_queue and saves it to disk.
    """
    print("💾 Saver thread started.")
    file_chunk_index = 0
    total_frame_count = 0

    # Loop continues as long as processing is active OR there are items left to save
    while not (processing_finished.is_set() and save_queue.empty()):
        try:
            # Wait for a chunk of data to save
            positions_chunk = save_queue.get(timeout=1)
            
            chunk_path = os.path.join(output_folder, f'positions_chunk_{file_chunk_index}.npy')
            print(f"\n📈 Saving chunk {file_chunk_index} with {len(positions_chunk)} positions...")
            np.save(chunk_path, positions_chunk)
            print(f"✅ Chunk saved to {chunk_path}")

            total_frame_count += len(positions_chunk)
            file_chunk_index += 1
            save_queue.task_done()

        except queue.Empty:
            # This is expected when the consumer is finished and the queue is empty.
            continue
    
    print(f"\n🛑 Saver thread stopped. Saved a total of {total_frame_count} frames.")

'''

# --- Corrected Consumer Task ---
def consumer_task():
    """
    CONSUMER (PROCESSOR): Processes images, puts results in save_queue.
    """
    print("🛠️ Consumer thread started.")
    
    SAVE_CHUNK_SIZE = 100000
    positions_chunk = np.empty((SAVE_CHUNK_SIZE, 4), dtype=np.int64)
    chunk_index = 0

    def process_frame(np_img, timestamp, location_val):
        # ... (processing logic is the same)
        _, thresh = cv2.threshold(np_img, 50, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            return timestamp, x + w // 2, y + h // 2, location_val
        return None

    try:
        # ... (main processing loop is the same)
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as pool:
            while not (processing_finished.is_set() and frame_queue.empty()):
                try:
                    np_img, timestamp, location_val = frame_queue.get(timeout=1)
                    
                    future = pool.submit(process_frame, np_img, timestamp, location_val)
                    result = future.result()

                    if result:
                        positions_chunk[chunk_index] = result
                        chunk_index += 1

                    if chunk_index == SAVE_CHUNK_SIZE:
                        save_queue.put(positions_chunk.copy())
                        positions_chunk = np.empty((SAVE_CHUNK_SIZE, 4), dtype=np.int64)
                        chunk_index = 0

                    frame_queue.task_done()
                except queue.Empty:
                    continue
    finally:
        # CHANGE #1: This 'finally' block GUARANTEES this code runs.
        # It sends the last partial chunk of data.
        if chunk_index > 0:
            print(f"CONSUMER: Putting final partial chunk of size {chunk_index} into save queue.")
            save_queue.put(positions_chunk[:chunk_index].copy())
        
        # CHANGE #2: The consumer sends a 'None' sentinel to signal it's finished.
        print("CONSUMER: Putting sentinel (None) to signal end of data stream.")
        save_queue.put(None) 
        print("🛑 Consumer thread stopped.")

# --- Corrected Saver Task ---
def saver_task():
    """
    SAVER: Gets processed data from the save_queue and saves it to disk.
    """
    print("💾 Saver thread started.")
    file_chunk_index = 0
    total_frame_count = 0

    # CHANGE #3: The loop is now simpler and more robust. It runs
    # indefinitely until it receives the specific 'None' signal.
    while True:
        try:
            # This blocks and waits until an item is available.
            positions_chunk = save_queue.get() 
            
            # CHANGE #4: Check for the sentinel value. This is the only
            # safe way for this loop to terminate.
            if positions_chunk is None:
                print("SAVER: Sentinel received. Shutting down.")
                save_queue.task_done()
                break # Exit the loop

            # ... (saving logic is the same)
            chunk_path = os.path.join(output_folder, f'positions_chunk_{file_chunk_index}.npy')
            print(f"\n📈 Saving chunk {file_chunk_index} with {len(positions_chunk)} positions...")
            np.save(chunk_path, positions_chunk)
            print(f"✅ Chunk saved to {chunk_path}")

            total_frame_count += len(positions_chunk)
            file_chunk_index += 1
            save_queue.task_done()

        except queue.Empty:
            continue
    
    print(f"\n🛑 Saver thread stopped. Saved a total of {total_frame_count} frames.")

# --- Main Control Functions ---

def start_recording():
    """Clears state and starts all threads."""
    if not camera_connected:
        print("Cannot start, camera is not connected.")
        return None, None, None

    # Clear flags and queues from any previous runs
    recording_active.set()
    processing_finished.clear()
    while not frame_queue.empty():
        try: frame_queue.get_nowait()
        except queue.Empty: break
    while not save_queue.empty():
        try: save_queue.get_nowait()
        except queue.Empty: break

    # Create and start threads
    producer = threading.Thread(target=producer_task)
    consumer = threading.Thread(target=consumer_task)
    saver = threading.Thread(target=saver_task)

    producer.start()
    consumer.start()
    saver.start()

    print("🟢 Recording started...")
    return producer, consumer, saver

def stop_recording(producer_thread, consumer_thread, saver_thread):
    """Signals threads to stop and waits for them to finish cleanly."""
    if not recording_active.is_set() and not processing_finished.is_set():
        print("Recording is already stopped or stopping.")
        return

    print("\n🟡 Stopping recording... Please wait for data to be saved.")
    
    # 1. Signal producer to stop acquiring new frames
    recording_active.clear()
    if producer_thread and producer_thread.is_alive():
        producer_thread.join()
        
    # 2. Signal consumer that no more frames are coming, so it can process the queue and finish
    processing_finished.set()
    if consumer_thread and consumer_thread.is_alive():
        consumer_thread.join()
        
    # 3. The saver will automatically finish after the consumer puts the last chunk in the save_queue
    if saver_thread and saver_thread.is_alive():
        saver_thread.join()
    
    print("🔴 Recording stopped completely. All data saved.")


# --- Main Execution Block ---

if __name__ == "__main__":
    connect_camera()

    producer_thread, consumer_thread, saver_thread = None, None, None
    if camera_connected:
        producer_thread, consumer_thread, saver_thread = start_recording()

    try:
        # Only loop for user input if recording actually started
        if producer_thread:
            while producer_thread.is_alive():
                prompt = (f"Live (p-value: {live_location}) | "
                          f"Frame Queue: {frame_queue.qsize()}/{frame_queue.maxsize} | "
                          f"Save Queue: {save_queue.qsize()} | "
                          f"Press 'p' to toggle, 'q' to quit: ")
                user_input = input(prompt)

                if user_input.lower() == 'q':
                    # Break the input loop; the 'finally' block will handle the shutdown

                    break
                elif user_input.lower() == 'p':
                    p_press_count += 1
                    # This logic correctly alternates between 0 and an incrementing number
                    live_location = 0 if p_press_count % 2 != 0 else (p_press_count // 2) + 1

    except (KeyboardInterrupt, EOFError):
        print("\nInterrupted by user.")
    finally:
        # This block executes whether the loop breaks ('q') or an interrupt occurs.
        # It ensures that the cleanup and saving process is always called.
        if camera_connected:
            stop_recording(producer_thread, consumer_thread, saver_thread)
            disconnect_camera()

    print("\nProgram exited.")
    sys.exit(0)