#!/usr/bin/env python3
"""
JSON-based Slideshow Preview Player and Editor
Allows users to create, edit, and preview slideshow configurations in JSON format.
"""

import json
import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QTextEdit, QFileDialog, QMessageBox,
                             QSplitter, QListWidget, QListWidgetItem, QDialog, QSpinBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPixmap, QIcon
from PyQt5.QtCore import QSize
from PIL import Image
import tempfile

class SlideshowJsonEditor(QMainWindow):
    """JSON-based slideshow editor and preview player."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Slideshow JSON Editor & Preview")
        self.setGeometry(100, 100, 1400, 800)
        
        self.current_config = {}
        self.current_preview_index = 0
        self.preview_timer = QTimer()
        self.preview_timer.timeout.connect(self.next_preview_image)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Left panel: JSON editor
        left_layout = QVBoxLayout()
        left_label = QLabel("📝 JSON Configuration")
        left_label.setFont(QFont("Arial", 11, QFont.Bold))
        left_layout.addWidget(left_label)
        
        self.json_editor = QTextEdit()
        self.json_editor.setPlainText(json.dumps(self.get_default_config(), indent=2))
        left_layout.addWidget(self.json_editor)
        
        # Buttons for JSON editor
        btn_layout = QHBoxLayout()
        btn_load = QPushButton("📂 Load JSON")
        btn_load.clicked.connect(self.load_json)
        btn_layout.addWidget(btn_load)
        
        btn_save = QPushButton("💾 Save JSON")
        btn_save.clicked.connect(self.save_json)
        btn_layout.addWidget(btn_save)
        
        btn_validate = QPushButton("✓ Validate")
        btn_validate.clicked.connect(self.validate_json)
        btn_layout.addWidget(btn_validate)

        btn_export = QPushButton("📤 Export Preview Script")
        btn_export.clicked.connect(self.export_preview_script)
        btn_layout.addWidget(btn_export)

        left_layout.addLayout(btn_layout)
        
        # Right panel: Preview
        right_layout = QVBoxLayout()
        right_label = QLabel("👁️ Preview")
        right_label.setFont(QFont("Arial", 11, QFont.Bold))
        right_layout.addWidget(right_label)
        
        self.preview_label = QLabel()
        self.preview_label.setMinimumSize(400, 300)
        self.preview_label.setStyleSheet("background-color: #1e1e1e; border: 2px solid #3d3d3d;")
        self.preview_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.preview_label)
        
        # Preview controls
        preview_btn_layout = QHBoxLayout()
        btn_prev = QPushButton("⬅️ Previous")
        btn_prev.clicked.connect(self.prev_preview_image)
        preview_btn_layout.addWidget(btn_prev)
        
        btn_play = QPushButton("▶️ Play")
        btn_play.clicked.connect(self.play_preview)
        preview_btn_layout.addWidget(btn_play)
        
        btn_stop = QPushButton("⏹️ Stop")
        btn_stop.clicked.connect(self.stop_preview)
        preview_btn_layout.addWidget(btn_stop)
        
        btn_next = QPushButton("Next ➡️")
        btn_next.clicked.connect(self.next_preview_image)
        preview_btn_layout.addWidget(btn_next)
        
        right_layout.addLayout(preview_btn_layout)
        
        self.preview_info = QLabel("No preview loaded")
        self.preview_info.setFont(QFont("Arial", 9))
        right_layout.addWidget(self.preview_info)
        
        # Add panels to main layout
        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 1)
        
        self.apply_dark_theme()
    
    def get_default_config(self):
        """Get default slideshow configuration."""
        return {
            "name": "My Slideshow",
            "description": "A slideshow created with JSON editor",
            "images": [],
            "settings": {
                "duration_per_image": 5,
                "transition": "fade",
                "resolution": "1920x1080",
                "framerate": 30,
                "codec": "libx264"
            },
            "created": datetime.now().isoformat(),
            "modified": datetime.now().isoformat()
        }
    
    def load_json(self):
        """Load JSON configuration from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Slideshow JSON", "", "JSON Files (*.json)"
        )
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    config = json.load(f)
                self.json_editor.setPlainText(json.dumps(config, indent=2))
                self.current_config = config
                self.load_preview()
                QMessageBox.information(self, "Success", "JSON loaded successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load JSON: {e}")
    
    def save_json(self):
        """Save JSON configuration to file."""
        try:
            config = json.loads(self.json_editor.toPlainText())
            config["modified"] = datetime.now().isoformat()
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Slideshow JSON", "", "JSON Files (*.json)"
            )
            if file_path:
                with open(file_path, 'w') as f:
                    json.dump(config, f, indent=2)
                QMessageBox.information(self, "Success", f"JSON saved to {Path(file_path).name}")
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "Error", f"Invalid JSON: {e}")
    
    def validate_json(self):
        """Validate JSON configuration."""
        try:
            config = json.loads(self.json_editor.toPlainText())
            self.current_config = config
            
            # Check required fields
            required = ["name", "images", "settings"]
            missing = [f for f in required if f not in config]
            
            if missing:
                QMessageBox.warning(self, "Validation", f"Missing fields: {', '.join(missing)}")
            else:
                QMessageBox.information(self, "Validation", "✓ JSON is valid!")
                self.load_preview()
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "Error", f"Invalid JSON: {e}")
    
    def load_preview(self):
        """Load preview from current configuration."""
        if not self.current_config.get("images"):
            self.preview_label.setText("No images in configuration")
            return
        
        self.current_preview_index = 0
        self.show_preview_image()
    
    def show_preview_image(self):
        """Show current preview image or video frame."""
        images = self.current_config.get("images", [])
        if not images or self.current_preview_index >= len(images):
            return

        item_path = images[self.current_preview_index]
        try:
            # Check if it's a video file
            video_formats = ('.mp4', '.avi', '.mov', '.mkv')
            if Path(item_path).suffix.lower() in video_formats:
                # Extract first frame from video
                frame_path = self._extract_video_frame(item_path)
                if frame_path:
                    img = Image.open(frame_path)
                    img.thumbnail((400, 300), Image.Resampling.LANCZOS)
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                        img.save(tmp.name)
                        pixmap = QPixmap(tmp.name)
                        self.preview_label.setPixmap(pixmap)
                    os.unlink(frame_path)
                    info = f"Video {self.current_preview_index + 1}/{len(images)}: {Path(item_path).name}"
                else:
                    self.preview_label.setText("📹 Could not extract video frame")
                    info = f"Video {self.current_preview_index + 1}/{len(images)}: {Path(item_path).name}"
            else:
                # Regular image file
                img = Image.open(item_path)
                img.thumbnail((400, 300), Image.Resampling.LANCZOS)
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    img.save(tmp.name)
                    pixmap = QPixmap(tmp.name)
                    self.preview_label.setPixmap(pixmap)
                info = f"Image {self.current_preview_index + 1}/{len(images)}: {Path(item_path).name}"

            self.preview_info.setText(info)
        except Exception as e:
            self.preview_label.setText(f"Error loading item: {e}")
    
    def _extract_video_frame(self, video_path):
        """Extract first frame from video file using FFmpeg."""
        try:
            import subprocess
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp_path = tmp.name

            cmd = [
                'ffmpeg', '-y', '-loglevel', 'error',
                '-i', str(video_path),
                '-vf', 'select=eq(n\\,0)',
                '-q:v', '2',
                tmp_path
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=10)

            if result.returncode == 0 and Path(tmp_path).exists():
                return tmp_path
            else:
                return None
        except Exception as e:
            return None

    def prev_preview_image(self):
        """Show previous image."""
        if self.current_preview_index > 0:
            self.current_preview_index -= 1
            self.show_preview_image()
    
    def next_preview_image(self):
        """Show next image."""
        images = self.current_config.get("images", [])
        if self.current_preview_index < len(images) - 1:
            self.current_preview_index += 1
            self.show_preview_image()
    
    def play_preview(self):
        """Play preview slideshow."""
        duration = self.current_config.get("settings", {}).get("duration_per_image", 5)
        self.preview_timer.start(duration * 1000)
    
    def stop_preview(self):
        """Stop preview slideshow."""
        self.preview_timer.stop()

    def export_preview_script(self):
        """Export a standalone Python script to preview the slideshow."""
        try:
            config = json.loads(self.json_editor.toPlainText())

            # Validate configuration
            if not config.get("images"):
                QMessageBox.warning(self, "Warning", "No images in configuration")
                return

            # Generate preview script
            script_content = self._generate_preview_script(config)

            # Save script to file
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export Preview Script", "preview_slideshow.py", "Python Scripts (*.py)"
            )
            if file_path:
                with open(file_path, 'w') as f:
                    f.write(script_content)
                os.chmod(file_path, 0o755)  # Make executable
                QMessageBox.information(self, "Success", f"Preview script exported to:\n{Path(file_path).name}")
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "Error", f"Invalid JSON: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export script: {e}")

    def _generate_preview_script(self, config):
        """Generate a preview script from configuration."""
        images = config.get("images", [])
        settings = config.get("settings", {})
        duration = settings.get("duration_per_image", 5)
        name = config.get("name", "Slideshow")

        script = '''#!/usr/bin/env python3
"""
Auto-generated Slideshow Preview Script
Created from JSON configuration
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QPixmap, QFont
from PIL import Image
import tempfile

class SlideshowPreview(QMainWindow):
    """Preview player for slideshow configuration."""

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.images = config.get("images", [])
        self.settings = config.get("settings", {})
        self.current_index = 0
        self.is_playing = False

        self.setWindowTitle(f"Slideshow Preview: {config.get('name', 'Slideshow')}")
        self.setGeometry(100, 100, 800, 600)

        self.setup_ui()
        self.load_image()

        self.timer = QTimer()
        self.timer.timeout.connect(self.next_image)

    def setup_ui(self):
        """Setup the UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()

        # Image display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #1e1e1e;")
        self.image_label.setMinimumSize(600, 400)
        layout.addWidget(self.image_label)

        # Info label
        self.info_label = QLabel()
        self.info_label.setFont(QFont("Arial", 10))
        self.info_label.setStyleSheet("color: white; background-color: #2b2b2b; padding: 10px;")
        layout.addWidget(self.info_label)

        # Controls
        btn_layout = QHBoxLayout()

        btn_prev = QPushButton("⬅️ Previous")
        btn_prev.clicked.connect(self.prev_image)
        btn_layout.addWidget(btn_prev)

        self.btn_play = QPushButton("▶️ Play")
        self.btn_play.clicked.connect(self.toggle_play)
        btn_layout.addWidget(self.btn_play)

        btn_next = QPushButton("Next ➡️")
        btn_next.clicked.connect(self.next_image)
        btn_layout.addWidget(btn_next)

        layout.addLayout(btn_layout)

        central_widget.setLayout(layout)
        self.apply_dark_theme()

    def apply_dark_theme(self):
        """Apply dark theme."""
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #2b2b2b;
                color: white;
            }
            QPushButton {
                background-color: #3d3d3d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #404040;
            }
        """)

    def load_image(self):
        """Load and display current image."""
        if not self.images or self.current_index >= len(self.images):
            return

        img_path = self.images[self.current_index]
        try:
            img = Image.open(img_path)
            img.thumbnail((600, 400), Image.Resampling.LANCZOS)

            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                img.save(tmp.name)
                pixmap = QPixmap(tmp.name)
                self.image_label.setPixmap(pixmap)

            duration = self.settings.get("duration_per_image", 5)
            total_duration = len(self.images) * duration
            info = f"Image {self.current_index + 1}/{len(self.images)} | Duration: {duration}s | Total: ~{total_duration}s"
            self.info_label.setText(info)
        except Exception as e:
            self.image_label.setText(f"Error loading image: {e}")

    def prev_image(self):
        """Show previous image."""
        if self.current_index > 0:
            self.current_index -= 1
            self.load_image()

    def next_image(self):
        """Show next image."""
        if self.current_index < len(self.images) - 1:
            self.current_index += 1
            self.load_image()
        else:
            self.stop_play()

    def toggle_play(self):
        """Toggle play/pause."""
        if self.is_playing:
            self.stop_play()
        else:
            self.start_play()

    def start_play(self):
        """Start playing slideshow."""
        self.is_playing = True
        self.btn_play.setText("⏹️ Stop")
        duration = self.settings.get("duration_per_image", 5)
        self.timer.start(duration * 1000)

    def stop_play(self):
        """Stop playing slideshow."""
        self.is_playing = False
        self.btn_play.setText("▶️ Play")
        self.timer.stop()

def main():
    app = QApplication(sys.argv)

    config = {
        "name": "''' + name + '''",
        "images": [
'''

        # Add images to script
        for img in images:
            script += f'            "{img}",\n'

        script += '''        ],
        "settings": {
            "duration_per_image": ''' + str(duration) + ''',
            "transition": "''' + settings.get("transition", "fade") + '''",
            "resolution": "''' + settings.get("resolution", "1920x1080") + '''",
            "framerate": ''' + str(settings.get("framerate", 30)) + ''',
            "codec": "''' + settings.get("codec", "libx264") + '''"
        }
    }

    preview = SlideshowPreview(config)
    preview.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
'''

        return script

    def apply_dark_theme(self):
        """Apply dark theme."""
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #2b2b2b;
                color: white;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #00ff00;
                font-family: Courier;
                font-size: 10px;
            }
            QPushButton {
                background-color: #3d3d3d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #404040;
            }
            QLabel {
                color: white;
            }
        """)

def main():
    app = QApplication(sys.argv)
    window = SlideshowJsonEditor()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

