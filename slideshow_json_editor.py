#!/usr/bin/env python3
"""
JSON-based Slideshow Preview Player and Editor
Allows users to create, edit, and preview slideshow configurations in JSON format.
"""

import json
import sys
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
        """Show current preview image."""
        images = self.current_config.get("images", [])
        if not images or self.current_preview_index >= len(images):
            return
        
        img_path = images[self.current_preview_index]
        try:
            img = Image.open(img_path)
            img.thumbnail((400, 300), Image.Resampling.LANCZOS)
            
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                img.save(tmp.name)
                pixmap = QPixmap(tmp.name)
                self.preview_label.setPixmap(pixmap)
                
            info = f"Image {self.current_preview_index + 1}/{len(images)}: {Path(img_path).name}"
            self.preview_info.setText(info)
        except Exception as e:
            self.preview_label.setText(f"Error loading image: {e}")
    
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

