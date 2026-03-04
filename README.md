# Cryo LED Tracker
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green.svg)](https://opencv.org/)
[![Baumer NeoAPI](https://img.shields.io/badge/Baumer-NeoAPI-orange.svg)](https://www.baumer.com/int/en/product-overview/industrial-cameras-image-processing/software/baumer-neoapi/c/42528)

Real-time LED position tracking system for quantum dot characterization in cryogenic environments using computer vision and high-speed image processing.

## Overview

This project enables **location-resolved photon counting** in a mechanically noisy cryogenic environment by synchronizing high-speed camera data with photon correlation measurements. The system tracks LED position fluctuations caused by vibrations and mechanical noise, allowing precise spatial correlation with single/multi-photon detection events. 

## Problem Statement

When scanning electrically excited quantum dots inside a closed-loop helium cryostat, the mechanical vibrations inherent to the system create significant positioning uncertainty. To get time and space resolved data we use the periodic osccilation to our advantage to scan a larger area of the ensemble. To achieve meaningful location-resolved photon counting, we needed to:

- **Track real-time sample position** despite mechanical vibrations (make it a feature not a problem)
- **Synchronize photon correlation measurements** with spatial data
- **Process high-throughput camera data** (~1 kHz) without data loss
- **Correlate single-photon events** with precise sample locations
Technical Justification
This approach is viable due to two critical hardware characteristics:

Picosecond-Scale Time Resolution: The photon correlation hardware operates at picosecond temporal resolution, enabling precise time-stamping of individual photon events. This allows post-hoc synchronization with position data acquired at millisecond scales.
Periodic Mechanical Motion: The cryostat's cold finger exhibits robust, deterministic periodic oscillations. These vibrations couple identically to both the quantum dot ensemble and the tracking LED, ensuring faithful position correspondence.
## Solution Architecture
To exploit these properties, we attached a miniature LED (SMD0805 package) to the opposite side of the quantum dot sample. The high-speed camera tracks this LED's motion in real time, providing a direct measure of quantum dot position since the LED vibration is mechanically coupled identically to the sample motion.
The workflow is:

1. **Image Acquisition**: High-speed camera captures LED position at ~1 kHz via USB 3.0
2. **Computer Vision Processing**: OpenCV-based centroid detection calculates LED position in real time
3. **Signal Generation**: Emit reference signal (LVTTL) to photon correlation board
4. **Data Synchronization**: Save position data synchronized with time-tagged photon events
5. **Post-Processing**: Correlate position history with photon correlation data for location-resolved analysis

## Key Features

- **Real-time position tracking** using OpenCV centroid detection algorithms
- **High-throughput data handling** optimized for ~1 kHz acquisition rates
- **USB 3.0 integration** for bandwidth-intensive camera streaming
- **Memory-efficient numpy arrays** for large-scale data storage and retrieval
- **Hardware synchronization** with external photon correlation boards via LVTTL signals
- **Data fidelity preservation** through intelligent buffering strategies

## Project Structure

- **Image Acquisition Module** (`w/o_tracking`): Low-level camera interface and image streaming without position analysis
- **Position Tracking Module**: OpenCV-based real-time LED centroid detection and position calculation
- **Data Management**: Synchronized storage of position and timing metadata in optimized numpy arrays
- **Sanity Check Tools**: Camera frame rate validation and data quality monitoring utilities
- **Legacy Components**: Earlier implementation for multi-file correlation board systems with asynchronous position marking

## Technical Highlights

### Performance Optimization
- Leveraged USB 3.0 for high-bandwidth image streaming
- Implemented parallel processing pipelines for concurrent image capture and analysis
- Optimized memory allocation and array operations for sustainable 1 kHz operation
- Eliminated bottlenecks in I/O-bound camera communication

### Synchronization Strategy
- Developed robust time-stamping protocol for correlating spatial and spectral data
- Implemented buffering mechanisms to handle variable save latencies on external systems
- Created position tracking log independent of downstream data processing

### Adaptability
- Modular design supporting both real-time and legacy hardware configurations
- Graceful degradation enabling continued operation during temporary latencies
- Backward compatibility with earlier multi-file correlation board architectures

## Technologies Used

- **Computer Vision**: OpenCV (image processing, feature detection)
- **Data Processing**: NumPy (array operations, memory optimization)
- **Hardware Communication**: USB 3.0, LVTTL signal generation
- **System Integration**: Real-time embedded programming, hardware synchronization

## Use Case

This system was instrumental in enabling time-sensitive quantum dot photoluminescence experiments, providing reliable spatial correlation data despite challenging environmental conditions. The flexible architecture supports both current and legacy experimental setups.

## Requirements

- Python 3.8+
- OpenCV 4.x
- Neoapi
- NumPy
- High-speed USB 3.0 camera with appropriate SDK (Baumer Camera + neoapi)
- LVTTL signal generation hardware
- Time tagger (correlation board)
- SPADs 

---

*Designed for quantum optics research in cryogenic environments. Optimized for production-grade data acquisition and real-time processing.*
---

## 🤝 Acknowledgments

Special thanks to **Yasmin Sarhan** for her contributions and collaborative efforts during the development and testing of this tracking system.
