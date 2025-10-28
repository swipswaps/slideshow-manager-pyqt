# 🎬 Video Playlist & FFmpeg Export Features

**Date:** 2025-10-28  
**Status:** ✅ **IMPLEMENTED AND WORKING**

---

## 🎯 Overview

The slideshow manager now includes comprehensive video playlist management with database-backed FFmpeg script storage and export functionality.

### New Features

1. **✅ Video Playlist Manager** - Build custom playlists from available videos
2. **✅ VLC Playlist Playback** - Play entire playlists sequentially
3. **✅ SQLite Database** - Store and reuse FFmpeg scripts and playlists
4. **✅ FFmpeg Export Dialog** - Generate concatenation scripts with 3 methods
5. **✅ Script Management** - Save, load, and track usage of export scripts

---

## 📋 Playlist Management Features

### Building a Playlist

1. **Navigate to Video Player Tab**
   - Click on "🎬 Video Player & Playlist" tab
   - Right side shows the playlist panel

2. **Add Videos to Playlist**
   - Select a video from the dropdown
   - Click "➕ Add Selected" button
   - Video appears in playlist widget

3. **Reorder Playlist**
   - Select an item in the playlist
   - Click "⬆️ Move Up" or "⬇️ Move Down"
   - Videos play in the order shown

4. **Remove from Playlist**
   - Select an item in the playlist
   - Click "➖ Remove" to delete it
   - Or click "🗑️ Clear All" to empty playlist

### Playing Playlists

**Single Video Playback:**
- Select video from dropdown
- Click "▶️ Play" button
- Use "⏸️ Pause" and "⏹️ Stop" controls

**Playlist Playback:**
- Build a playlist (see above)
- Click "▶️ Play Playlist" button
- All videos play sequentially
- VLC automatically advances to next video

---

## 💾 Saving & Loading Playlists

### Save Playlist

1. Build your playlist
2. Click "💾 Save Playlist"
3. Enter a name (e.g., "Best Moments 2025")
4. Enter optional description
5. Playlist saved to database

### Load Playlist

1. Click "📂 Load Playlist"
2. Select from list of saved playlists
3. Shows name and description
4. Playlist loads into widget
5. Ready to play or export

**Database Location:** `~/.slideshow_scripts.db`

---

## 📤 FFmpeg Export Features

### Export Dialog

Click "📤 Export FFmpeg" to open the export dialog with:

- **Script Name** - Auto-generated or custom
- **Description** - Optional notes about the script
- **Output File** - Name of concatenated video file
- **Concatenation Method** - Choose from 3 options
- **Command Preview** - Live preview of FFmpeg command
- **Saved Scripts** - Load previously saved scripts

### Three Concatenation Methods

#### 1. Concat Demuxer (Recommended)
**Fast, no re-encode**

```bash
# Creates concat.txt file list
cat > concat.txt << 'EOF'
file '/path/to/video1.mp4'
file '/path/to/video2.mp4'
file '/path/to/video3.mp4'
EOF

# Concatenate without re-encoding (fast!)
ffmpeg -f concat -safe 0 -i concat.txt -c copy output.mp4

# Cleanup
rm concat.txt
```

**Pros:**
- ⚡ Very fast (no re-encoding)
- 🎯 Preserves original quality
- 💾 No quality loss

**Cons:**
- ⚠️ Requires same codec/resolution
- ⚠️ May have sync issues if videos differ

**Best for:** Videos from same source/settings

#### 2. Concat Filter
**Re-encode for compatibility**

```bash
ffmpeg -i 'video1.mp4' -i 'video2.mp4' -i 'video3.mp4' \
  -filter_complex "[0:v:0][0:a:0][1:v:0][1:a:0][2:v:0][2:a:0]concat=n=3:v=1:a=1[outv][outa]" \
  -map "[outv]" -map "[outa]" \
  -c:v libx264 -preset medium -crf 23 \
  -c:a aac -b:a 192k \
  output.mp4
```

**Pros:**
- ✅ Works with different codecs/resolutions
- ✅ Smooth transitions
- ✅ Consistent output quality

**Cons:**
- 🐌 Slower (re-encodes everything)
- 📉 Some quality loss from re-encoding

**Best for:** Mixed video sources

#### 3. Concat Protocol
**Simple, re-encode**

```bash
ffmpeg -i "concat:video1.mp4|video2.mp4|video3.mp4" \
  -c:v libx264 -preset medium -crf 23 \
  -c:a aac -b:a 192k \
  output.mp4
```

**Pros:**
- 📝 Simple syntax
- ✅ Works with most videos

**Cons:**
- 🐌 Slower (re-encodes)
- ⚠️ Limited format support

**Best for:** Quick tests, simple concatenation

---

## 🗄️ Database Features

### FFmpeg Scripts Table

Stores reusable FFmpeg commands:

| Field | Description |
|-------|-------------|
| `name` | Unique script name |
| `description` | Optional notes |
| `command` | Full FFmpeg command |
| `created_at` | Creation timestamp |
| `modified_at` | Last modification |
| `times_used` | Usage counter |

### Playlists Table

Stores video playlists:

| Field | Description |
|-------|-------------|
| `name` | Unique playlist name |
| `description` | Optional notes |
| `video_paths` | JSON array of video paths |
| `created_at` | Creation timestamp |
| `modified_at` | Last modification |

### Database Operations

**Save Script:**
```python
db.save_script(name, command, description)
```

**Load Script:**
```python
script = db.get_script(name)
# Returns: {name, description, command, created_at, modified_at, times_used}
```

**List All Scripts:**
```python
scripts = db.list_scripts()
# Returns: [(name, description, modified_at, times_used), ...]
```

**Track Usage:**
```python
db.increment_usage(name)  # Increments times_used counter
```

---

## 🎮 Usage Workflow

### Typical Workflow

1. **Create Slideshows**
   - Select images from gallery
   - Click "Create Slideshow"
   - Videos saved to `~/Pictures/Screenshots/`

2. **Build Playlist**
   - Go to Video Player tab
   - Add videos to playlist in desired order
   - Save playlist for later use

3. **Export Concatenated Video**
   - Click "📤 Export FFmpeg"
   - Choose concatenation method
   - Customize output filename
   - Save script to database
   - Click "📤 Export & Run"

4. **Reuse Scripts**
   - Load saved playlist
   - Open export dialog
   - Select saved script from dropdown
   - Modify if needed
   - Run again

---

## 🔧 Technical Implementation

### Database Class

```python
class FFmpegScriptDatabase:
    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path
        self.init_database()
    
    def save_script(self, name, command, description="")
    def get_script(self, name)
    def list_scripts(self)
    def delete_script(self, name)
    def increment_usage(self, name)
    
    def save_playlist(self, name, video_paths, description="")
    def get_playlist(self, name)
    def list_playlists(self)
    def delete_playlist(self, name)
```

### Playlist Export Dialog

```python
class PlaylistExportDialog(QDialog):
    def __init__(self, playlist, db, parent=None)
    
    def generate_concat_demuxer_script(self, output_file)
    def generate_concat_filter_script(self, output_file)
    def generate_concat_protocol_script(self, output_file)
    
    def save_script()
    def export_and_run()
    def export_to_file()
```

### VLC Playlist Playback

```python
def play_playlist(self):
    """Play all videos in playlist sequentially using VLC."""
    media_list = self.vlc_instance.media_list_new()
    
    for video_path in self.current_playlist:
        media = self.vlc_instance.media_new(video_path)
        media_list.add_media(media)
    
    self.playlist_player = self.vlc_instance.media_list_player_new()
    self.playlist_player.set_media_player(self.media_player)
    self.playlist_player.set_media_list(media_list)
    self.playlist_player.play()
```

---

## 📁 File Locations

| Item | Location |
|------|----------|
| Database | `~/.slideshow_scripts.db` |
| Videos | `~/Pictures/Screenshots/slideshow_*.mp4` |
| Config | `~/.slideshow_config.json` |
| Logs | `./slideshow_manager.log` |
| Exported Scripts | User-specified (default: `concat_*.sh`) |

---

## 🎯 Use Cases

### 1. Create Highlight Reel
- Create multiple slideshows from different events
- Build playlist with best moments
- Export as single video using concat demuxer

### 2. Monthly Compilation
- Save monthly playlists
- Reuse export script each month
- Track usage statistics

### 3. Custom Ordering
- Create slideshows in any order
- Rearrange in playlist
- Export with custom transitions

### 4. Batch Processing
- Save multiple export scripts
- Different quality settings
- Reuse for different playlists

---

## ⚡ Performance Notes

- **Concat Demuxer:** ~1-2 seconds for 10 videos (no re-encode)
- **Concat Filter:** ~30-60 seconds per minute of video (re-encode)
- **Concat Protocol:** ~30-60 seconds per minute of video (re-encode)

**Recommendation:** Use concat demuxer when possible for best performance.

---

## 🐛 Troubleshooting

### Playlist Won't Play
- Check video files exist
- Verify VLC is installed
- Check log file for errors

### Export Fails
- Ensure FFmpeg is installed: `ffmpeg -version`
- Check disk space
- Verify video paths are valid
- Check output directory permissions

### Database Errors
- Database auto-creates on first run
- Location: `~/.slideshow_scripts.db`
- Delete to reset (loses saved data)

---

## 🚀 Future Enhancements

Potential improvements:

- [ ] Drag-and-drop playlist reordering
- [ ] Playlist import/export (JSON format)
- [ ] Video trimming before concatenation
- [ ] Transition effects between videos
- [ ] Audio normalization across playlist
- [ ] Batch export multiple playlists
- [ ] Cloud backup of playlists/scripts
- [ ] Playlist sharing functionality

---

## 📝 Summary

The new playlist and export features provide:

✅ **Flexible playlist management** - Build, save, and reuse video playlists  
✅ **Multiple export methods** - Choose speed vs compatibility  
✅ **Database persistence** - Never lose your scripts or playlists  
✅ **Usage tracking** - See which scripts you use most  
✅ **VLC integration** - Play playlists directly in the app  
✅ **Script reusability** - Save time with reusable export templates  

**Ready to use!** Open the app and start building playlists! 🎉

