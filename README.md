# Slideshow Manager - PyQt5 Version

A modern, feature-rich slideshow manager built with PyQt5. Create, manage, and preview slideshows from your image collection with a clean, intuitive interface.

## 🎬 Applications

### 1. Main Slideshow Manager (`slideshow_manager_pyqt.py`)
Create video slideshows from selected images with real-time progress tracking, video playlist management, and FFmpeg export capabilities.

### 2. JSON Editor & Preview (`slideshow_json_editor.py`)
Create and edit slideshow configurations in JSON format with live preview.

## ✨ Key Features (v2.2)

### Main Application

#### Drag-and-Drop Timeline (NEW in v2.2) 🎞️
- **Visual Timeline Editor**: Drag thumbnails from gallery or video grid to timeline
- **Reorder by Dragging**: Rearrange timeline items by dragging within timeline
- **Bidirectional Sync**: Timeline automatically syncs with playlist
- **Timeline Controls**: Play, Export, and Clear buttons for timeline
- **Visual Feedback**: Green border when populated, dashed border when empty
- **Right-Click to Remove**: Context menu to remove items from timeline
- **Horizontal Scrolling**: Scrollable layout for long timelines
- **Thumbnail Preview**: Shows video/image thumbnails in timeline
- **Drag from Multiple Sources**: Works with both main gallery and video grid

#### Image Management
- **Selective Image Processing**: Checkbox on each thumbnail to choose which images to include
- **Background Processing**: FFmpeg runs in background (no UI lockup)
- **Real-time Progress Logging**: Detailed event log showing each step
- **Editable FFmpeg Commands**: Customize video encoding settings
- **Modern UI**: Dark theme, rounded buttons, resizable panels
- **Image Statistics**: Total, selected, visible, hidden, and size information

#### Video Player Integration (ENHANCED in v2.2)
- **Embedded VLC Player**: Play videos directly in the app
- **Video Thumbnail Grid**: When stopped, displays clickable video thumbnails in player area
- **Smart Playback Controls**: Single Play/Pause toggle button that changes based on state
- **Click to Play**: Click any video thumbnail to play instantly
- **Ctrl+Click to Select**: Select videos for playlist without playing
- **Drag to Timeline**: Drag video thumbnails directly to timeline (NEW in v2.2)
- **Multiple Players**: VLC, MPV, Celluloid, Shotcut, FFplay, or Totem
- **Platform Support**: Linux, Windows, macOS
- **Background Thumbnail Loading**: Video frames extracted asynchronously

#### Video Playlist Manager (ENHANCED in v2.2)
- **Build Custom Playlists**: Add videos in any order from available slideshows
- **Multiple Selection Methods**:
  - Click "Add Selected" button to add from dropdown
  - Ctrl+Click video thumbnails in player grid
  - Ctrl+Click video thumbnails in main gallery
  - Drag thumbnails to timeline (NEW in v2.2)
- **Reorder Videos**: Move items up/down with buttons, keyboard shortcuts, or drag-and-drop (NEW)
- **Duplicate Detection**: Warns when adding duplicate videos
- **File Validation**: Checks if video files exist before adding
- **Playlist Count**: Shows item count and estimated duration
- **Save/Load Playlists**: Store playlists in SQLite database for reuse
- **VLC Playback**: Play entire playlists sequentially
- **Keyboard Shortcuts**: Delete, Ctrl+Up, Ctrl+Down for quick operations
- **Timeline Sync**: Playlist automatically syncs with visual timeline (NEW in v2.2)

#### FFmpeg Export (v2.0)
- **3 Concatenation Methods**:
  - **Concat Demuxer** (fast, no re-encode, 1-2 seconds)
  - **Concat Filter** (re-encode, compatible with mixed formats)
  - **Concat Protocol** (simple, re-encode)
- **Live Command Preview**: See FFmpeg command before running
- **Progress Estimation**: Shows estimated time for each method
- **Script Database**: Save and reuse export scripts
- **Usage Tracking**: Track how many times each script is used
- **Export Options**: Run immediately or save to shell file
- **Output Validation**: Checks for filename conflicts

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

## 📁 Database & Storage

- **Database**: `~/.slideshow_scripts.db` (SQLite)
  - Stores FFmpeg export scripts
  - Stores video playlists
  - Tracks usage statistics
- **Videos**: `~/Pictures/Screenshots/slideshow_*.mp4`
- **Config**: `~/.slideshow_config.json`
- **Logs**: `./slideshow_manager.log`

## 🎯 UI Layout

### Tab 1: Image Gallery
```
┌─────────────────────────────────────────────────────┐
│ Control Panel: Add | Refresh | Create | Settings   │
├─────────────────────────────────────────────────────┤
│ 📸 Image Thumbnails (with checkboxes)               │
│    [✓] image1.png  [✓] image2.png  [ ] image3.png  │
├─────────────────────────────────────────────────────┤
│ ⚙️ FFmpeg Command (editable)                        │
└─────────────────────────────────────────────────────┘
```

### Tab 2: Video Player & Playlist (ENHANCED in v2.1)
```
┌──────────────────────────────┬──────────────────────┐
│ 🎬 Video Player              │ 📋 Playlist (3 items)│
│ ┌──────────────────────────┐ │ 1. slideshow_01.mp4  │
│ │  When Playing:           │ │ 2. slideshow_02.mp4  │
│ │  VLC Player Widget       │ │ 3. slideshow_03.mp4  │
│ │                          │ │                      │
│ │  When Stopped:           │ │ ➕ Add Selected      │
│ │  📹 📹 📹 📹              │ ➖ Remove            │
│ │  📹 📹 📹 📹              │ ⬆️ Move Up           │
│ │  (Video Thumbnails)      │ │ ⬇️ Move Down         │
│ │  Click to play           │ │ 🗑️ Clear All         │
│ │  Ctrl+Click to select    │ │ ▶️ Play Playlist     │
│ └──────────────────────────┘ │ 💾 Save Playlist     │
│ ▶️/⏸️ Play/Pause | ⏹️ Stop   │ 📂 Load Playlist     │
│ 📁 Open Folder               │ 📤 Export FFmpeg     │
└──────────────────────────────┴──────────────────────┘
```

### Tab 3: Settings
```
┌─────────────────────────────────────────────────────┐
│ ⚙️ Application Settings                             │
│ - Image directory                                   │
│ - Video player selection                            │
│ - FFmpeg parameters                                 │
└─────────────────────────────────────────────────────┘
```

### Tab 4: Logs
```
┌─────────────────────────────────────────────────────┐
│ 📋 Event Log (real-time progress)                   │
│ [2025-10-28 09:30:00] ✅ Slideshow created          │
│ [2025-10-28 09:30:15] ➕ Added to playlist          │
│ [2025-10-28 09:30:20] 📤 FFmpeg export started      │
└─────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Create a Slideshow
1. Launch: `python3 slideshow_manager_pyqt.py`
2. Go to **Image Gallery** tab
3. Select images with checkboxes
4. Click **Create Slideshow**
5. Wait for FFmpeg to finish (~30 seconds)

### Build a Playlist
1. Go to **Video Player & Playlist** tab
2. Add videos using one of these methods:
   - Select from dropdown and click **➕ Add Selected**
   - **Ctrl+Click** video thumbnails in player grid (when stopped)
   - **Ctrl+Click** video thumbnails in main gallery
3. Use **⬆️ Move Up** / **⬇️ Move Down** to reorder
4. Click **💾 Save Playlist** to store for later

### Export Concatenated Video
1. Build your playlist (or load saved one)
2. Click **📤 Export FFmpeg**
3. Choose concatenation method:
   - **Concat Demuxer** (recommended, fast)
   - **Concat Filter** (compatible)
   - **Concat Protocol** (simple)
4. Enter output filename
5. Click **📤 Export & Run**
6. Check logs for progress

## 📚 Documentation

- **PLAYLIST_FEATURES.md** - Complete guide to playlist features
- **QUICK_START_GUIDE.md** - Step-by-step tutorial
- **IMPLEMENTATION_SUMMARY.md** - Technical details

## 🎉 Recent Updates

### v2.1 (2025-10-28)
✅ **Video Thumbnail Grid** - Clickable video thumbnails display in player when stopped
✅ **Smart Playback Controls** - Single Play/Pause toggle button
✅ **Click to Play** - Click any video thumbnail to play instantly
✅ **Ctrl+Click Selection** - Select videos for playlist without playing
✅ **Background Thumbnail Loading** - Video frames extracted asynchronously
✅ **Improved UX** - Seamless transition between player and thumbnail grid

### v2.0 (2025-10-28)
✅ **Video Playlist Manager** - Build, reorder, save, and load playlists
✅ **FFmpeg Export Dialog** - 3 concatenation methods with live preview
✅ **SQLite Database** - Store scripts and playlists for reuse
✅ **Duplicate Detection** - Warns when adding duplicate videos
✅ **File Validation** - Checks if files exist before operations
✅ **Playlist Count** - Shows item count and estimated duration
✅ **Keyboard Shortcuts** - Delete, Ctrl+Up, Ctrl+Down
✅ **Progress Estimation** - Shows estimated time for FFmpeg operations
✅ **Confirmation Dialogs** - Prevents accidental data loss
✅ **Usage Tracking** - Track which scripts are used most
✅ **Fixed VLC Player** - Platform-specific window binding
✅ Added output filename validation
✅ Improved error handling and user feedback
✅ Better logging for debugging
✅ Comprehensive documentation

## 📖 Version History

### v2.0 - Video Playlist & FFmpeg Export (2025-10-28)
- **NEW**: Video playlist manager with full CRUD operations
- **NEW**: FFmpeg export dialog with 3 concatenation methods
- **NEW**: SQLite database for scripts and playlists
- **NEW**: Duplicate detection and file validation
- **NEW**: Playlist count with duration estimate
- **NEW**: Keyboard shortcuts for playlist operations
- **NEW**: Progress estimation for FFmpeg exports
- **NEW**: Confirmation dialogs for destructive actions
- **NEW**: Usage tracking for saved scripts
- **FIXED**: VLC player embedding on all platforms
- **IMPROVED**: Error handling and user feedback
- **DOCS**: Added 3 comprehensive documentation files

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

## 🔧 Troubleshooting

### Video Player Not Appearing
- **Solution**: Ensure VLC is installed (`vlc --version`)
- **Note**: Fixed in v2.0 with platform-specific window binding

### Playlist Won't Play
- Check video files exist in `~/Pictures/Screenshots/`
- Verify VLC is installed and working
- Check `slideshow_manager.log` for errors

### FFmpeg Export Fails
- Ensure FFmpeg is installed: `ffmpeg -version`
- Check disk space available
- Verify output directory permissions
- Try different concatenation method

### Database Errors
- Database auto-creates on first run at `~/.slideshow_scripts.db`
- Delete database file to reset (loses saved data)
- Check file permissions

## 💡 Tips & Best Practices

### For Best Performance
- Use **Concat Demuxer** when all videos have same codec/resolution
- Save frequently used playlists to database
- Name scripts descriptively for easy identification
- Check logs regularly for errors

### Keyboard Shortcuts
- **Delete** - Remove selected playlist item
- **Ctrl+Up** - Move playlist item up
- **Ctrl+Down** - Move playlist item down
- **Ctrl+A** - Select all images (Image Gallery)

### Workflow Recommendations
1. Create multiple slideshows from different image sets
2. Build playlist with best slideshows
3. Preview with "Play Playlist"
4. Export with Concat Demuxer for fast, lossless merge
5. Save playlist and script for future use

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Drag-and-drop playlist reordering
- Video trimming before concatenation
- Transition effects between videos
- Audio normalization
- Batch export multiple playlists
- Cloud backup of playlists

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- **PyQt5** - GUI framework
- **VLC** - Video playback
- **FFmpeg** - Video processing
- **Pillow** - Image processing

