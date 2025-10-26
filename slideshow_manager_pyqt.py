#!/usr/bin/env python3
"""
Slideshow Manager with PyQt5 GUI - Manage, preview, and create slideshows from images.
Features: thumbnails, sort, search, rename, add, hide, remove images, video playback.
"""

import os
import sys
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
import json
import threading
import logging
import traceback
from io import StringIO
import tempfile

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QListWidget, QListWidgetItem, QFileDialog,
                             QDialog, QLineEdit, QComboBox, QSpinBox, QCheckBox, QTabWidget,
                             QScrollArea, QGridLayout, QSplitter, QMessageBox, QInputDialog,
                             QTextEdit, QPlainTextEdit)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QTimer, QRect
from PyQt5.QtGui import QIcon, QPixmap, QFont, QColor, QPalette, QImage
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve

from PIL import Image

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('slideshow_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
IMAGES_DIR = Path.home() / "Pictures" / "Screenshots"
OUTPUT_DIR = Path.home() / "Pictures" / "Screenshots"
CONFIG_FILE = Path.home() / ".slideshow_config.json"
THUMBNAIL_SIZE = (120, 120)
SUPPORTED_FORMATS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')

class RoundedButton(QPushButton):
    """Custom button with rounded corners and modern styling."""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #404040;
            }
            QPushButton:pressed {
                background-color: #303030;
            }
        """)
        self.setCursor(Qt.PointingHandCursor)

class SlideshowManager(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Slideshow Manager")
        self.setGeometry(100, 100, 1200, 900)

        # Data
        self.images = []
        self.hidden_images = set()
        self.available_videos = []
        self.video_players = []
        self.config = {}
        self.log_events = []

        # Default FFmpeg command (uses image2 demuxer with numbered files)
        # Includes padding to handle odd dimensions and scaling to 1920x1080
        self.default_ffmpeg_cmd = (
            "ffmpeg -y -loglevel error -framerate 1/5 "
            "-i %04d.png "
            "-vf \"format=yuv420p,scale='min(1920,iw*min(1920/iw\\,1080/ih))':'min(1080,ih*min(1920/iw\\,1080/ih))':force_original_aspect_ratio=decrease,pad=1920:1080:(1920-iw)/2:(1080-ih)/2\" "
            "-c:v libx264 -r 30 -pix_fmt yuv420p -y output.mp4"
        )

        # Load configuration
        self.load_config()
        self.detect_video_players()

        # Setup UI
        self.setup_ui()
        self.load_images()
        self.show_available_videos()

        logger.info("Slideshow Manager started")
    
    def setup_ui(self):
        """Setup the main UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Control panel
        control_layout = QHBoxLayout()
        
        btn_add = RoundedButton("➕ Add Images")
        btn_add.clicked.connect(self.add_images)
        control_layout.addWidget(btn_add)
        
        btn_refresh = RoundedButton("🔄 Refresh")
        btn_refresh.clicked.connect(self.load_images)
        control_layout.addWidget(btn_refresh)
        
        btn_create = RoundedButton("🎬 Create Slideshow")
        btn_create.clicked.connect(self.create_slideshow)
        control_layout.addWidget(btn_create)
        
        btn_settings = RoundedButton("⚙️ Settings")
        btn_settings.clicked.connect(self.show_settings)
        control_layout.addWidget(btn_settings)
        
        btn_log = RoundedButton("📋 Event Log")
        btn_log.clicked.connect(self.show_event_log)
        control_layout.addWidget(btn_log)
        
        control_layout.addStretch()
        main_layout.addLayout(control_layout)
        
        # Splitter for resizable sections
        splitter = QSplitter(Qt.Vertical)

        # Video selection panel
        video_panel = self.create_video_panel()
        splitter.addWidget(video_panel)

        # FFmpeg command panel
        ffmpeg_panel = self.create_ffmpeg_panel()
        splitter.addWidget(ffmpeg_panel)

        # Thumbnails panel with statistics
        thumbnails_panel = self.create_thumbnails_panel()
        splitter.addWidget(thumbnails_panel)

        # Event log panel
        log_panel = self.create_log_panel()
        splitter.addWidget(log_panel)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 2)
        splitter.setStretchFactor(3, 1)

        main_layout.addWidget(splitter)
        
        # Apply dark theme
        self.apply_dark_theme()
    
    def create_video_panel(self):
        """Create video selection panel."""
        panel = QWidget()
        layout = QVBoxLayout()

        label = QLabel("📹 Select Video to Play")
        label.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(label)

        self.video_list = QListWidget()
        layout.addWidget(self.video_list)

        btn_layout = QHBoxLayout()
        btn_play = RoundedButton("▶️ Play Selected")
        btn_play.clicked.connect(self.play_selected_video)
        btn_layout.addWidget(btn_play)

        btn_folder = RoundedButton("📁 Open Folder")
        btn_folder.clicked.connect(self.open_videos_folder)
        btn_layout.addWidget(btn_folder)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        panel.setLayout(layout)
        return panel

    def create_ffmpeg_panel(self):
        """Create FFmpeg command editor panel."""
        panel = QWidget()
        layout = QVBoxLayout()

        label = QLabel("⚙️ FFmpeg Command")
        label.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(label)

        # FFmpeg command editor
        self.ffmpeg_cmd_edit = QPlainTextEdit()
        self.ffmpeg_cmd_edit.setPlainText(self.config.get('ffmpeg_cmd', self.default_ffmpeg_cmd))
        self.ffmpeg_cmd_edit.setMaximumHeight(80)
        layout.addWidget(self.ffmpeg_cmd_edit)

        # Buttons
        btn_layout = QHBoxLayout()

        btn_reset = RoundedButton("🔄 Reset to Default")
        btn_reset.clicked.connect(self.reset_ffmpeg_command)
        btn_layout.addWidget(btn_reset)

        btn_save = RoundedButton("💾 Save Command")
        btn_save.clicked.connect(self.save_ffmpeg_command)
        btn_layout.addWidget(btn_save)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        panel.setLayout(layout)
        return panel
    
    def create_thumbnails_panel(self):
        """Create thumbnails panel with statistics."""
        panel = QWidget()
        layout = QVBoxLayout()
        
        # Header with statistics
        header_layout = QHBoxLayout()
        header_label = QLabel("📸 Image Thumbnails")
        header_label.setFont(QFont("Arial", 11, QFont.Bold))
        header_layout.addWidget(header_label)
        
        self.stats_label = QLabel()
        self.stats_label.setFont(QFont("Arial", 9))
        header_layout.addStretch()
        header_layout.addWidget(self.stats_label)
        
        layout.addLayout(header_layout)
        
        # Thumbnails grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        self.thumbnails_widget = QWidget()
        self.thumbnails_layout = QGridLayout()
        self.thumbnails_layout.setSpacing(10)
        self.thumbnails_widget.setLayout(self.thumbnails_layout)
        
        scroll.setWidget(self.thumbnails_widget)
        layout.addWidget(scroll)
        
        panel.setLayout(layout)
        return panel
    
    def create_log_panel(self):
        """Create event log panel."""
        panel = QWidget()
        layout = QVBoxLayout()
        
        label = QLabel("📋 Event Log")
        label.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(label)
        
        self.log_display = QListWidget()
        layout.addWidget(self.log_display)
        
        panel.setLayout(layout)
        return panel
    
    def apply_dark_theme(self):
        """Apply dark theme to the application."""
        dark_stylesheet = """
            QMainWindow, QWidget {
                background-color: #2b2b2b;
                color: white;
            }
            QLabel {
                color: white;
            }
            QListWidget {
                background-color: #1e1e1e;
                color: white;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #404040;
            }
            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background-color: #3d3d3d;
                border-radius: 6px;
            }
        """
        self.setStyleSheet(dark_stylesheet)
    
    def load_config(self):
        """Load configuration from file."""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r') as f:
                    self.config = json.load(f)
                logger.info("Configuration loaded")
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            self.config = {}
    
    def save_config(self):
        """Save configuration to file."""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info("Configuration saved")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def detect_video_players(self):
        """Detect available video players."""
        players = ['vlc', 'mpv', 'celluloid', 'shotcut', 'ffplay', 'totem']
        self.video_players = [p for p in players if shutil.which(p)]
        logger.info(f"Available players: {self.video_players}")
    
    def load_images(self):
        """Load images from directory."""
        try:
            if not IMAGES_DIR.exists():
                IMAGES_DIR.mkdir(parents=True, exist_ok=True)
            
            self.images = sorted([
                f for f in IMAGES_DIR.glob('*')
                if f.suffix.lower() in SUPPORTED_FORMATS
            ])
            
            self.update_thumbnails()
            self.update_statistics()
            logger.info(f"Loaded {len(self.images)} images")
        except Exception as e:
            logger.error(f"Error loading images: {e}")
            self.log_event(f"Error loading images: {e}")
    
    def update_thumbnails(self):
        """Update thumbnail grid."""
        # Clear existing thumbnails
        while self.thumbnails_layout.count():
            self.thumbnails_layout.takeAt(0).widget().deleteLater()
        
        # Add thumbnails in grid
        col = 0
        for i, img_path in enumerate(self.images):
            try:
                thumb = self.create_thumbnail(img_path)
                self.thumbnails_layout.addWidget(thumb, i // 6, i % 6)
                col = (i + 1) % 6
            except Exception as e:
                logger.error(f"Error creating thumbnail for {img_path}: {e}")
    
    def create_thumbnail(self, img_path):
        """Create a thumbnail widget."""
        btn = QPushButton()
        btn.setFixedSize(120, 120)

        try:
            img = Image.open(img_path)
            img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
            # Convert PIL image to QPixmap using temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                img.save(tmp.name)
                pixmap = QPixmap(tmp.name)
                btn.setIcon(QIcon(pixmap))
                btn.setIconSize(QSize(120, 120))
                os.unlink(tmp.name)
        except Exception as e:
            logger.error(f"Error loading thumbnail: {e}")
        
        btn.setStyleSheet("""
            QPushButton {
                border: 2px solid #3d3d3d;
                border-radius: 4px;
                padding: 0px;
            }
            QPushButton:hover {
                border: 2px solid #404040;
            }
        """)
        
        return btn
    
    def update_statistics(self):
        """Update statistics display."""
        total = len(self.images)
        hidden = len(self.hidden_images)
        visible = total - hidden
        size_mb = sum(f.stat().st_size for f in self.images) / (1024 * 1024)
        
        stats_text = f"Total: {total} | Visible: {visible} | Hidden: {hidden} | Size: {size_mb:.1f} MB"
        self.stats_label.setText(stats_text)
    
    def show_available_videos(self):
        """Show available videos in the list."""
        try:
            self.available_videos = sorted([
                f for f in OUTPUT_DIR.glob('slideshow_*.mp4')
            ])
            
            self.video_list.clear()
            for video in self.available_videos:
                size_mb = video.stat().st_size / (1024 * 1024)
                mtime = datetime.fromtimestamp(video.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                item_text = f"{video.name} ({size_mb:.1f} MB) - {mtime}"
                self.video_list.addItem(item_text)
            
            if self.available_videos:
                self.video_list.setCurrentRow(0)
                logger.info(f"Showing {len(self.available_videos)} videos")
        except Exception as e:
            logger.error(f"Error showing videos: {e}")
            self.log_event(f"Error showing videos: {e}")
    
    def play_selected_video(self):
        """Play the selected video."""
        current_row = self.video_list.currentRow()
        if current_row < 0 or current_row >= len(self.available_videos):
            self.log_event("No video selected")
            return
        
        video_path = self.available_videos[current_row]
        if not self.video_players:
            self.log_event("No video player available")
            return
        
        try:
            player = self.video_players[0]
            subprocess.Popen([player, str(video_path)])
            logger.info(f"Playing video with {player}: {video_path}")
            self.log_event(f"Playing: {video_path.name}")
        except Exception as e:
            logger.error(f"Error playing video: {e}")
            self.log_event(f"Error playing video: {e}")
    
    def add_images(self):
        """Add images from file dialog."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Images", str(IMAGES_DIR),
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        
        if files:
            for file in files:
                try:
                    src = Path(file)
                    dst = IMAGES_DIR / src.name
                    shutil.copy2(src, dst)
                    logger.info(f"Added image: {src.name}")
                except Exception as e:
                    logger.error(f"Error adding image: {e}")
            
            self.load_images()
            self.log_event(f"Added {len(files)} image(s)")
    
    def create_slideshow(self):
        """Create slideshow from images using FFmpeg (runs in background thread)."""
        if not self.images:
            self.log_event("❌ No images available")
            return

        # Check if FFmpeg is installed
        if not shutil.which('ffmpeg'):
            self.log_event("❌ FFmpeg not installed")
            QMessageBox.critical(self, "Error", "FFmpeg is not installed. Please install it first.")
            return

        # Get the FFmpeg command
        ffmpeg_cmd = self.ffmpeg_cmd_edit.toPlainText().strip()
        if not ffmpeg_cmd:
            self.log_event("❌ FFmpeg command is empty")
            return

        # Run in background thread to prevent UI lockup
        thread = threading.Thread(target=self._create_slideshow_worker, args=(ffmpeg_cmd,), daemon=True)
        thread.start()

    def _create_slideshow_worker(self, ffmpeg_cmd):
        """Worker thread for slideshow creation."""
        # Generate output filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = OUTPUT_DIR / f"slideshow_{timestamp}.mp4"

        try:
            self.log_event(f"🎬 Creating slideshow: {output_file.name}")
            logger.info(f"Starting slideshow creation: {output_file}")
            logger.info(f"Images: {len(self.images)}, Output: {output_file}")

            # Create temporary directory with symlinks to numbered images
            temp_dir = Path(".slideshow_temp")
            temp_dir.mkdir(exist_ok=True)
            logger.debug(f"Created temp directory: {temp_dir}")

            # Create numbered symlinks with .png extension for FFmpeg image2 demuxer
            for i, img_path in enumerate(self.images):
                link_path = temp_dir / f"{i+1:04d}.png"
                if link_path.exists():
                    link_path.unlink()
                link_path.symlink_to(img_path.resolve())
            logger.debug(f"Created {len(self.images)} symlinks in temp directory")

            # Replace output placeholder in command
            cmd = ffmpeg_cmd.replace('output.mp4', str(output_file))
            # Update input pattern to use temp directory
            cmd = cmd.replace('%04d.png', f'{temp_dir}/%04d.png')

            logger.debug(f"Running FFmpeg command: {cmd}")

            # Run FFmpeg command
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300
            )

            # Cleanup temp directory
            for file in temp_dir.glob("*"):
                file.unlink()
            temp_dir.rmdir()
            logger.debug("Cleaned up temporary directory")

            if result.returncode == 0:
                file_size = output_file.stat().st_size / (1024 * 1024)
                duration = len(self.images) * 5  # 5 seconds per image
                success_msg = (
                    f"✅ Slideshow created: {output_file.name}\n"
                    f"Size: {file_size:.1f} MB | Duration: ~{duration}s"
                )
                self.log_event(success_msg)
                self.show_available_videos()
                logger.info(f"Slideshow created successfully: {output_file} ({file_size:.1f} MB)")
                QMessageBox.information(self, "Success", success_msg)
            else:
                error_msg = result.stderr if result.stderr else "Unknown error"
                self.log_event(f"❌ FFmpeg error: {error_msg[:100]}")
                logger.error(f"FFmpeg error: {error_msg}")
                QMessageBox.critical(self, "FFmpeg Error", f"Error creating slideshow:\n{error_msg[:300]}")

        except subprocess.TimeoutExpired:
            self.log_event("❌ Slideshow creation timed out (>300s)")
            logger.error("FFmpeg command timed out")
            QMessageBox.critical(self, "Error", "Slideshow creation timed out after 300 seconds")
        except Exception as e:
            error_msg = f"{str(e)}\n\n{traceback.format_exc()}"
            self.log_event(f"❌ Error: {str(e)[:50]}")
            logger.error(f"Error creating slideshow: {error_msg}")
            QMessageBox.critical(self, "Error", f"Error creating slideshow:\n{str(e)}")
    
    def open_videos_folder(self):
        """Open videos folder in file manager."""
        try:
            subprocess.Popen(['xdg-open', str(OUTPUT_DIR)])
            logger.info(f"Opened folder: {OUTPUT_DIR}")
        except Exception as e:
            logger.error(f"Error opening folder: {e}")

    def save_ffmpeg_command(self):
        """Save the FFmpeg command to config."""
        cmd = self.ffmpeg_cmd_edit.toPlainText().strip()
        if not cmd:
            self.log_event("❌ FFmpeg command cannot be empty")
            return

        self.config['ffmpeg_cmd'] = cmd
        self.save_config()
        self.log_event("✅ FFmpeg command saved")
        logger.info("FFmpeg command saved to config")

    def reset_ffmpeg_command(self):
        """Reset FFmpeg command to default."""
        self.ffmpeg_cmd_edit.setPlainText(self.default_ffmpeg_cmd)
        self.log_event("🔄 FFmpeg command reset to default")
        logger.info("FFmpeg command reset to default")
    
    def show_settings(self):
        """Show settings dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.setGeometry(200, 200, 400, 300)
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Settings"))
        layout.addStretch()
        
        btn_close = RoundedButton("Close")
        btn_close.clicked.connect(dialog.close)
        layout.addWidget(btn_close)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def show_event_log(self):
        """Show event log dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Event Log")
        dialog.setGeometry(200, 200, 600, 400)
        
        layout = QVBoxLayout()
        log_display = QListWidget()
        
        for event in self.log_events[-20:]:
            log_display.addItem(event)
        
        layout.addWidget(log_display)
        
        btn_close = RoundedButton("Close")
        btn_close.clicked.connect(dialog.close)
        layout.addWidget(btn_close)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def log_event(self, message):
        """Log an event."""
        if not hasattr(self, 'log_events'):
            self.log_events = []
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        event = f"[{timestamp}] {message}"
        self.log_events.append(event)
        self.log_display.addItem(event)
        
        # Keep only last 100 events
        if len(self.log_events) > 100:
            self.log_events.pop(0)
        
        logger.info(message)

def main():
    app = QApplication(sys.argv)
    window = SlideshowManager()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

