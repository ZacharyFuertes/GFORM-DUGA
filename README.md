# GFORM DUGA

GFORM DUGA is an automated Google Form submission tool designed for rapid, intelligent form filling with randomized data and a professional management interface.

## Features

- Automated Submission Engine: Handles multi-page Google Forms using browser simulation.
- Intelligent Data Filling: Randomized ratings of 3, 4, or 5 with weighted distribution.
- Name Generation: Includes a pool of 50 non-repeating names.
- Gender Synchronization: Automatically selects the correct gender based on the generated name.
- Real-time Progress Tracking: Visual progress bar and status statistics.
- Live Logging: Color-coded event logging for every submission attempt.
- Automatic Setup: Built-in browser installer to handle first-time setup automatically.
- Standalone Interface: Custom GUI branded as GFORM DUGA by zekasf.

## Tech Stack

- Core Logic: Python 3
- Automation Framework: Playwright
- GUI Framework: Tkinter
- Image Support: Pillow (PIL)
- Packaging: PyInstaller

## How To Use

### Option 1: Using the Executable (Recommended)
1. Navigate to the dist folder.
2. Run GFORM_DUGA.exe.
3. If this is your first time, the app will automatically download the required browser components.
4. Enter the desired number of submissions.
5. Click Start Bot.

### Option 2: Running from Source
1. Ensure Python 3 is installed.
2. Open a terminal in the project directory.
3. Install dependencies:
   pip install -r requirements.txt
4. Run the launcher:
   run.bat gui
   (Alternative: python gui_launcher.py)
5. Use the GUI to configure and start the submission process.

## Notes
- The bot is configured to fill the name field approximately 50% of the time.
- Names are drawn from a pool without replacement to ensure no repeats until the entire list is exhausted.
- The app requires an active internet connection to download browsers and submit forms.
