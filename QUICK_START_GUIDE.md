# 🚀 Quick Start Guide: Video Playlist & FFmpeg Export

**Get started in 5 minutes!**

---

## 📋 Prerequisites

Make sure you have:
- ✅ Python 3.x installed
- ✅ PyQt5 installed (`pip install PyQt5`)
- ✅ VLC installed (for video playback)
- ✅ FFmpeg installed (for video export)
- ✅ python-vlc installed (`pip install python-vlc`)

---

## 🎬 Step 1: Launch the Application

```bash
cd /path/to/slideshow-app-pyqt
python3 slideshow_manager_pyqt.py
```

The application window opens with 4 tabs:
- 📸 Image Gallery
- 🎬 Video Player & Playlist
- ⚙️ Settings
- 📊 Logs

---

## 🎥 Step 2: Navigate to Video Player Tab

Click on the **"🎬 Video Player & Playlist"** tab.

You'll see:
- **Left side (2/3):** VLC video player
- **Right side (1/3):** Playlist manager

---

## ➕ Step 3: Build Your Playlist

### Add Videos

1. **Select a video** from the dropdown at the top
   - Shows all available videos from `~/Pictures/Screenshots/`
   - Includes all `slideshow_*.mp4` files

2. **Click "➕ Add Selected"**
   - Video appears in the playlist widget below
   - Shows the video filename

3. **Repeat** to add more videos
   - Add as many as you want
   - No limit on playlist size

### Reorder Videos

1. **Select a video** in the playlist widget
2. **Click "⬆️ Move Up"** or **"⬇️ Move Down"**
3. Videos play in the order shown (top to bottom)

### Remove Videos

- **Remove one:** Select it, click "➖ Remove"
- **Remove all:** Click "🗑️ Clear All"

---

## ▶️ Step 4: Play Your Playlist

### Option A: Play Single Video
1. Select video from dropdown
2. Click "▶️ Play" button
3. Use "⏸️ Pause" and "⏹️ Stop" as needed

### Option B: Play Entire Playlist
1. Build your playlist (see Step 3)
2. Click "▶️ Play Playlist" button
3. All videos play sequentially
4. VLC automatically advances to next video

---

## 💾 Step 5: Save Your Playlist (Optional)

Want to reuse this playlist later?

1. **Click "💾 Save Playlist"**
2. **Enter a name** (e.g., "Best Moments 2025")
3. **Enter description** (optional)
4. **Click OK**

Playlist saved to database at `~/.slideshow_scripts.db`

### Load Saved Playlist

1. **Click "📂 Load Playlist"**
2. **Select from list** of saved playlists
3. Playlist loads into widget
4. Ready to play or export!

---

## 📤 Step 6: Export as Single Video

### Open Export Dialog

1. Build your playlist (or load saved one)
2. **Click "📤 Export FFmpeg"**
3. Export dialog opens

### Configure Export

**Script Name:**
- Auto-generated: `concat_playlist_20251028_093000`
- Or enter custom name

**Description:**
- Optional notes about this script
- Example: "Monthly highlights compilation"

**Output File:**
- Default: `concatenated_20251028_093000.mp4`
- Or enter custom filename

**Concatenation Method:**
Choose one of three options:

#### 🚀 Option 1: Concat Demuxer (Recommended)
- **Speed:** ⚡ Very fast (1-2 seconds)
- **Quality:** 🎯 Perfect (no quality loss)
- **Best for:** Videos from same source
- **Note:** Requires same codec/resolution

#### 🔧 Option 2: Concat Filter
- **Speed:** 🐌 Slower (re-encodes)
- **Quality:** ✅ Good (configurable)
- **Best for:** Mixed video sources
- **Note:** Works with different formats

#### 📝 Option 3: Concat Protocol
- **Speed:** 🐌 Slower (re-encodes)
- **Quality:** ✅ Good (configurable)
- **Best for:** Simple concatenation
- **Note:** Limited format support

### Preview Command

The **Command Preview** box shows the exact FFmpeg command that will run.

Example for concat demuxer:
```bash
# Step 1: Create concat.txt file with video list
cat > concat.txt << 'EOF'
file '/home/user/Pictures/Screenshots/slideshow_20251026_142125.mp4'
file '/home/user/Pictures/Screenshots/slideshow_20251027_093437.mp4'
file '/home/user/Pictures/Screenshots/slideshow_20251028_075459.mp4'
EOF

# Step 2: Run FFmpeg concat demuxer (fast, no re-encode)
ffmpeg -f concat -safe 0 -i concat.txt -c copy concatenated_output.mp4

# Step 3: Cleanup
rm concat.txt
```

### Execute Export

Choose one of three options:

#### 💾 Save Script to Database
- Saves the script for later use
- Can load and modify later
- Tracks usage statistics

#### 📤 Export & Run
- Saves script to database
- Runs FFmpeg immediately
- Background thread (non-blocking)
- Check logs for progress

#### 💾 Export to File
- Saves as executable shell script (`.sh`)
- Can run manually later
- Useful for batch processing

---

## 🔄 Step 7: Reuse Saved Scripts

### Load Previous Script

1. Open export dialog
2. **"Load Saved Script"** dropdown shows all saved scripts
3. Select one: `my_script (used 5x)`
4. Script loads into preview
5. Modify if needed
6. Run again!

### Benefits

- ✅ Save time with templates
- ✅ Consistent quality settings
- ✅ Track which scripts you use most
- ✅ Modify and re-save

---

## 🎯 Common Workflows

### Workflow 1: Quick Concatenation

```
1. Add videos to playlist
2. Click "📤 Export FFmpeg"
3. Choose "concat demuxer"
4. Click "📤 Export & Run"
5. Done! (1-2 seconds)
```

### Workflow 2: Monthly Compilation

```
1. Create slideshows throughout the month
2. Build playlist at month end
3. Save playlist: "January 2025"
4. Export with saved script: "monthly_compilation"
5. Repeat next month!
```

### Workflow 3: Custom Ordering

```
1. Load saved playlist
2. Reorder videos (move up/down)
3. Preview with "Play Playlist"
4. Export when satisfied
```

### Workflow 4: Multiple Versions

```
1. Build playlist once
2. Export with concat demuxer (fast, high quality)
3. Export with concat filter (compatible)
4. Compare results
5. Keep best version
```

---

## 💡 Pro Tips

### Tip 1: Use Concat Demuxer When Possible
- All your slideshows use same settings
- No re-encoding = fastest + best quality
- Perfect for videos from this app

### Tip 2: Save Playlists Frequently
- Easy to rebuild later
- Try different orderings
- Share with others (future feature)

### Tip 3: Name Scripts Descriptively
- `monthly_highlights_1080p`
- `best_moments_fast_export`
- `family_vacation_compilation`

### Tip 4: Track Usage Statistics
- See which scripts you use most
- Optimize your workflow
- Delete unused scripts

### Tip 5: Preview Before Export
- Use "Play Playlist" to check order
- Verify all videos load correctly
- Adjust as needed

---

## 🐛 Troubleshooting

### Problem: Playlist Won't Play

**Solution:**
1. Check VLC is installed: `vlc --version`
2. Verify video files exist
3. Check `slideshow_manager.log` for errors

### Problem: Export Fails

**Solution:**
1. Check FFmpeg is installed: `ffmpeg -version`
2. Verify disk space available
3. Check output directory permissions
4. Try different concatenation method

### Problem: Database Errors

**Solution:**
1. Database auto-creates on first run
2. Location: `~/.slideshow_scripts.db`
3. Delete to reset (loses saved data)
4. Restart application

### Problem: Videos Out of Order

**Solution:**
1. Use "⬆️ Move Up" / "⬇️ Move Down" buttons
2. Videos play top-to-bottom in playlist
3. Save playlist after reordering

---

## 📊 Example Session

Here's a complete example session:

```
1. Launch app: python3 slideshow_manager_pyqt.py
2. Go to "Image Gallery" tab
3. Select 10 images
4. Click "Create Slideshow"
5. Wait for slideshow to render (30 seconds)
6. Go to "Video Player & Playlist" tab
7. Add 3 slideshows to playlist
8. Reorder: Move best one to top
9. Click "Play Playlist" to preview
10. Click "📤 Export FFmpeg"
11. Choose "concat demuxer (fast, no re-encode)"
12. Name: "best_slideshows_compilation"
13. Output: "my_best_moments.mp4"
14. Click "💾 Save Script to Database"
15. Click "📤 Export & Run"
16. Wait 2 seconds
17. Done! Video at ~/Pictures/Screenshots/my_best_moments.mp4
```

---

## 🎓 Learning Path

### Beginner (5 minutes)
- ✅ Add videos to playlist
- ✅ Play playlist
- ✅ Export with default settings

### Intermediate (15 minutes)
- ✅ Save and load playlists
- ✅ Try all 3 concatenation methods
- ✅ Save scripts to database

### Advanced (30 minutes)
- ✅ Customize FFmpeg commands
- ✅ Create reusable script templates
- ✅ Optimize for different use cases
- ✅ Track usage statistics

---

## 📚 Additional Resources

### Documentation
- **PLAYLIST_FEATURES.md** - Complete feature guide
- **IMPLEMENTATION_SUMMARY.md** - Technical details
- **README.md** - General application info

### External Resources
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [VLC Python Bindings](https://wiki.videolan.org/Python_bindings)
- [PyQt5 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt5/)

---

## ✨ You're Ready!

That's it! You now know how to:

✅ Build video playlists  
✅ Play playlists in VLC  
✅ Export concatenated videos  
✅ Save and reuse scripts  
✅ Optimize your workflow  

**Start creating amazing video compilations!** 🎉

---

## 🆘 Need Help?

- Check the logs: `slideshow_manager.log`
- Read full docs: `PLAYLIST_FEATURES.md`
- Verify installations: `ffmpeg -version` and `vlc --version`

**Happy video editing!** 🎬

