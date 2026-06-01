# nudity-filter-camera
This project is a lightweight, responsive Python desktop application that integrates a live camera workspace with an automated local media gallery system. Designed to provide a streamlined, hands-free user experience, the application features a graphical user interface drawn directly onto the live feed using OpenCV. Users can capture high-resolution snapshots, record continuous video streams, and switch dynamically between front-facing and rear-facing webcams with a single click.

A core focus of the software is its integrated real-time safety filter, built to ensure content integrity. Operating on a dedicated background execution thread, the safety module continuously scans active camera frames. If any form of nudity or explicit content is introduced in front of the lens, the application executes an instant lockdown sequence. The live stream is immediately terminated, any active video recording caches are safely discarded to prevent policy violations, and the application closes itself cleanly.

Beyond live monitoring, the application manages data through two automated systems:

Automated Gallery Storage: Every successful photo snapshot (.jpg) and video recording (.avi) is routed automatically to a dedicated gallery folder on the host computer. Files are encoded instantly using unique, non-overwriting timestamp configurations, completely removing the need for tedious manual "Save As" prompts.

Relational Database Logging: The application establishes a local transaction pipeline with a MySQL database. Every operational event—including standard photo captures, normal video saves, camera hardware flips, and high-priority safety blocks—is logged with its exact, untampered calendar timestamp and status type for secure tracking.

To maximize usability, the entire project workspace is packaged into a standalone, single-file Windows executable (.exe) via PyInstaller. This configuration safely encapsulates all required deep learning models and environment packages internally. As a result, the final application can be deployed on any compatible Windows computer and connect seamlessly to its local hardware and database resources without requiring Python or PyCharm to be installed.
