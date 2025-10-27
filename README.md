# Slideshow Manager - PyQt5 Version

A modern, feature-rich slideshow manager built with PyQt5. Create, manage, and preview slideshows from your image collection with a clean, intuitive interface.

## Applications

### 1. Main Slideshow Manager (`slideshow_manager_pyqt.py`)
Create video slideshows from selected images with real-time progress tracking.

### 2. JSON Editor & Preview (`slideshow_json_editor.py`)
Create and edit slideshow configurations in JSON format with live preview.

## Key Features

### Main Application
- **Selective Image Processing**: Checkbox on each thumbnail to choose which images to include
- **Background Processing**: FFmpeg runs in background (no UI lockup)
- **Real-time Progress Logging**: Detailed event log showing each step
- **Editable FFmpeg Commands**: Customize video encoding settings
- **Video Player Integration**: Play slideshows with VLC, MPV, Celluloid, Shotcut, FFplay, or Totem
- **Modern UI**: Dark theme, rounded buttons, resizable panels
- **Image Statistics**: Total, selected, visible, hidden, and size information

### JSON Editor
- **JSON Configuration Editor**: Create slideshow configs with syntax highlighting
- **Live Preview**: Browse images from configuration
- **Playback Controls**: Play/Stop/Previous/Next for preview
- **Validation**: Check JSON structure and required fields
- **Load/Save**: Import/export configurations
- **Auto-timestamps**: Track creation and modification dates

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Main Application
```bash
python3 slideshow_manager_pyqt.py
```

### JSON Editor
```bash
python3 slideshow_json_editor.py
```

## UI Layout

```
┌─────────────────────────────────────────────────────┐
│ Control Panel: Add | Refresh | Create | Settings   │
├─────────────────────────────────────────────────────┤
│ 📸 Image Thumbnails (with checkboxes)               │
├─────────────────────────────────────────────────────┤
│ ⚙️ FFmpeg Command (editable)                        │
├─────────────────────────────────────────────────────┤
│ 📹 Select Video to Play                             │
├─────────────────────────────────────────────────────┤
│ 📋 Event Log (real-time progress)                   │
└─────────────────────────────────────────────────────┘
```

## Recent Updates (v1.4)

✅ Checkbox selection for each thumbnail  
✅ Only selected images used in slideshow  
✅ Fixed button text centering  
✅ Added JSON-based preview player/editor  
✅ Detailed progress logging to event log  

## Version History

### v1.4 - Selective Processing & JSON Editor
- Added checkbox selection for each thumbnail
- Only selected images used in slideshow creation
- Fixed button text centering with CSS
- Added JSON-based preview player/editor
- Detailed progress logging to event log

### v1.3 - UI Reorganization & Progress Logging
- Reorganized section order (Thumbnails → FFmpeg → Video → Log)
- Added detailed progress logging for each step
- Better process control with Popen

### v1.2 - Background Threading
- FFmpeg runs in background thread (no UI lockup)
- Responsive UI during slideshow creation

### v1.1 - FFmpeg Command Fixes
- Fixed "height not divisible by 2" error
- Added proper video filters for odd dimensions
- Automatic padding and scaling

### v1.0 - Initial Release
- Modern PyQt5 UI with dark theme
- Rounded buttons with proper styling
- Thumbnail grid layout
- FFmpeg slideshow creation
- Video player integration

