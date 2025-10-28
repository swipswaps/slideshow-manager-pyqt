#!/usr/bin/env python3
"""
Slideshow Manager with PyQt5 GUI - Manage, preview, and create slideshows from images.

Features:
- Image gallery with thumbnails, sort, search, rename, add, hide, remove
- Video player with embedded VLC support
- Video playlist management (add, remove, reorder, save, load)
- FFmpeg export with 3 concatenation methods (demuxer, filter, protocol)
- SQLite database for storing scripts and playlists
- Keyboard shortcuts for playlist operations
- Duplicate detection and file validation
- Progress estimation for FFmpeg operations
- Usage tracking for saved scripts

New in v2.0 (2025-10-28):
✅ Video playlist manager with drag-free reordering
✅ FFmpeg export dialog with 3 concatenation methods
✅ SQLite database for scripts and playlists
✅ Duplicate detection and file validation
✅ Playlist count with duration estimate
✅ Keyboard shortcuts (Delete, Ctrl+Up/Down)
✅ Progress estimation for exports
✅ Confirmation dialogs for destructive actions
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
import sqlite3

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QListWidget, QListWidgetItem, QFileDialog,
                             QDialog, QLineEdit, QComboBox, QSpinBox, QCheckBox, QTabWidget,
                             QScrollArea, QGridLayout, QSplitter, QMessageBox, QInputDialog,
                             QTextEdit, QPlainTextEdit, QSlider, QFrame)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QTimer, QRect, QMimeData, QPoint
from PyQt5.QtGui import QIcon, QPixmap, QFont, QColor, QPalette, QImage, QDrag, QPainter
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve

from PIL import Image
import vlc

# Configure logging - output to console for visibility
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('slideshow_manager.log'),
    ]
)
logger = logging.getLogger(__name__)

# Constants
IMAGES_DIR = Path.home() / "Pictures" / "Screenshots"
OUTPUT_DIR = Path.home() / "Pictures" / "Screenshots"
CONFIG_FILE = Path.home() / ".slideshow_config.json"
DB_FILE = Path.home() / ".slideshow_scripts.db"
THUMBNAIL_SIZE = (120, 120)
SUPPORTED_FORMATS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')
VIDEO_FORMATS = ('.mp4', '.avi', '.mov', '.mkv')


class FFmpegScriptDatabase:
    """Database manager for FFmpeg scripts and playlists."""

    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Table for FFmpeg scripts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ffmpeg_scripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                command TEXT NOT NULL,
                created_at TEXT NOT NULL,
                modified_at TEXT NOT NULL,
                times_used INTEGER DEFAULT 0
            )
        ''')

        # Table for video playlists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                video_paths TEXT NOT NULL,
                created_at TEXT NOT NULL,
                modified_at TEXT NOT NULL
            )
        ''')

        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")

    def save_script(self, name, command, description=""):
        """Save or update an FFmpeg script."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        try:
            cursor.execute('''
                INSERT INTO ffmpeg_scripts (name, description, command, created_at, modified_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, description, command, now, now))
        except sqlite3.IntegrityError:
            # Update existing script
            cursor.execute('''
                UPDATE ffmpeg_scripts
                SET command = ?, description = ?, modified_at = ?
                WHERE name = ?
            ''', (command, description, now, name))

        conn.commit()
        conn.close()
        logger.info(f"Saved FFmpeg script: {name}")

    def get_script(self, name):
        """Get an FFmpeg script by name."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM ffmpeg_scripts WHERE name = ?', (name,))
        result = cursor.fetchone()

        conn.close()

        if result:
            return {
                'id': result[0],
                'name': result[1],
                'description': result[2],
                'command': result[3],
                'created_at': result[4],
                'modified_at': result[5],
                'times_used': result[6]
            }
        return None

    def list_scripts(self):
        """List all FFmpeg scripts."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT name, description, modified_at, times_used FROM ffmpeg_scripts ORDER BY modified_at DESC')
        results = cursor.fetchall()

        conn.close()
        return results

    def delete_script(self, name):
        """Delete an FFmpeg script."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM ffmpeg_scripts WHERE name = ?', (name,))

        conn.commit()
        conn.close()
        logger.info(f"Deleted FFmpeg script: {name}")

    def increment_usage(self, name):
        """Increment usage counter for a script."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('UPDATE ffmpeg_scripts SET times_used = times_used + 1 WHERE name = ?', (name,))

        conn.commit()
        conn.close()

    def save_playlist(self, name, video_paths, description=""):
        """Save or update a video playlist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        video_paths_json = json.dumps(video_paths)

        try:
            cursor.execute('''
                INSERT INTO playlists (name, description, video_paths, created_at, modified_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, description, video_paths_json, now, now))
        except sqlite3.IntegrityError:
            # Update existing playlist
            cursor.execute('''
                UPDATE playlists
                SET video_paths = ?, description = ?, modified_at = ?
                WHERE name = ?
            ''', (video_paths_json, description, now, name))

        conn.commit()
        conn.close()
        logger.info(f"Saved playlist: {name}")

    def get_playlist(self, name):
        """Get a playlist by name."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM playlists WHERE name = ?', (name,))
        result = cursor.fetchone()

        conn.close()

        if result:
            return {
                'id': result[0],
                'name': result[1],
                'description': result[2],
                'video_paths': json.loads(result[3]),
                'created_at': result[4],
                'modified_at': result[5]
            }
        return None

    def list_playlists(self):
        """List all playlists."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT name, description, modified_at FROM playlists ORDER BY modified_at DESC')
        results = cursor.fetchall()

        conn.close()
        return results

    def delete_playlist(self, name):
        """Delete a playlist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM playlists WHERE name = ?', (name,))

        conn.commit()
        conn.close()
        logger.info(f"Deleted playlist: {name}")


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
                text-align: center;
            }
            QPushButton:hover {
                background-color: #404040;
            }
            QPushButton:pressed {
                background-color: #303030;
            }
        """)
        self.setCursor(Qt.PointingHandCursor)
        self.setFlat(False)


class DraggableThumbnail(QPushButton):
    """Thumbnail button that supports drag-and-drop."""

    def __init__(self, file_path, pixmap=None, parent=None):
        super().__init__(parent)
        self.file_path = Path(file_path)
        self.pixmap = pixmap
        self.drag_start_position = None

        self.setFixedSize(100, 100)
        self.setCursor(Qt.OpenHandCursor)
        self.setAcceptDrops(False)  # Thumbnails don't accept drops, only timeline does

        # Set thumbnail image or placeholder
        if pixmap:
            self.setIcon(QIcon(pixmap))
            self.setIconSize(QSize(90, 90))
        else:
            # Placeholder based on file type
            if self.file_path.suffix.lower() in VIDEO_FORMATS:
                self.setText("📹")
            else:
                self.setText("🖼️")

        # Styling
        self.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                border: 2px solid #3d3d3d;
                border-radius: 8px;
                color: white;
                font-size: 32px;
            }
            QPushButton:hover {
                border: 2px solid #4a9eff;
                background-color: #3a3a3a;
            }
        """)

        # Tooltip
        self.setToolTip(f"{self.file_path.name}\n\nDrag to timeline to add")

    def mousePressEvent(self, event):
        """Store drag start position."""
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Start drag operation if mouse moved far enough."""
        if not (event.buttons() & Qt.LeftButton):
            return
        if self.drag_start_position is None:
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return

        # Create drag object
        drag = QDrag(self)
        mime_data = QMimeData()

        # Store file path in mime data
        mime_data.setText(str(self.file_path))
        mime_data.setData("application/x-slideshow-file", str(self.file_path).encode())

        drag.setMimeData(mime_data)

        # Set drag pixmap (thumbnail preview)
        if self.pixmap:
            drag.setPixmap(self.pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            # Create a simple pixmap with text
            pixmap = QPixmap(80, 80)
            pixmap.fill(QColor("#2a2a2a"))
            painter = QPainter(pixmap)
            painter.setPen(QColor("white"))
            painter.setFont(QFont("Arial", 24))
            if self.file_path.suffix.lower() in VIDEO_FORMATS:
                painter.drawText(pixmap.rect(), Qt.AlignCenter, "📹")
            else:
                painter.drawText(pixmap.rect(), Qt.AlignCenter, "🖼️")
            painter.end()
            drag.setPixmap(pixmap)

        drag.setHotSpot(QPoint(40, 40))

        # Execute drag
        drag.exec_(Qt.CopyAction | Qt.MoveAction)
        self.setCursor(Qt.OpenHandCursor)

    def mouseReleaseEvent(self, event):
        """Reset cursor on release."""
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)


class TimelineThumbnail(QPushButton):
    """Thumbnail in timeline that can be reordered and removed."""

    removed = pyqtSignal(object)  # Signal emitted when thumbnail is removed

    def __init__(self, file_path, pixmap=None, parent=None):
        super().__init__(parent)
        self.file_path = Path(file_path)
        self.pixmap = pixmap
        self.drag_start_position = None

        self.setFixedSize(80, 80)
        self.setCursor(Qt.OpenHandCursor)

        # Set thumbnail image or placeholder
        if pixmap:
            self.setIcon(QIcon(pixmap))
            self.setIconSize(QSize(70, 70))
        else:
            if self.file_path.suffix.lower() in VIDEO_FORMATS:
                self.setText("📹")
            else:
                self.setText("🖼️")

        # Styling with remove button overlay
        self.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                border: 2px solid #00ff00;
                border-radius: 6px;
                color: white;
                font-size: 24px;
            }
            QPushButton:hover {
                border: 2px solid #4a9eff;
                background-color: #3a3a3a;
            }
        """)

        # Tooltip
        self.setToolTip(f"{self.file_path.name}\n\nDrag to reorder\nRight-click to remove")

        # Context menu for removal
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, pos):
        """Show context menu for removal."""
        from PyQt5.QtWidgets import QMenu
        menu = QMenu(self)
        remove_action = menu.addAction("❌ Remove from Timeline")
        action = menu.exec_(self.mapToGlobal(pos))
        if action == remove_action:
            self.removed.emit(self)

    def mousePressEvent(self, event):
        """Store drag start position."""
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Start drag operation for reordering."""
        if not (event.buttons() & Qt.LeftButton):
            return
        if self.drag_start_position is None:
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return

        # Create drag object
        drag = QDrag(self)
        mime_data = QMimeData()

        # Store file path and mark as timeline reorder
        mime_data.setText(str(self.file_path))
        mime_data.setData("application/x-timeline-reorder", str(self.file_path).encode())

        drag.setMimeData(mime_data)

        # Set drag pixmap
        if self.pixmap:
            drag.setPixmap(self.pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        drag.setHotSpot(QPoint(30, 30))

        # Execute drag
        result = drag.exec_(Qt.MoveAction)
        self.setCursor(Qt.OpenHandCursor)

        # If drag was successful (moved), remove this thumbnail
        if result == Qt.MoveAction:
            self.removed.emit(self)

    def mouseReleaseEvent(self, event):
        """Reset cursor on release."""
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)


class TimelineWidget(QFrame):
    """Timeline widget that accepts dropped thumbnails and displays them in sequence."""

    timeline_changed = pyqtSignal(list)  # Signal emitted when timeline changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.timeline_items = []  # List of file paths in order
        self.thumbnail_widgets = []  # List of TimelineThumbnail widgets

        self.setAcceptDrops(True)
        self.setMinimumHeight(120)
        self.setMaximumHeight(120)

        # Styling
        self.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border: 2px dashed #3d3d3d;
                border-radius: 8px;
            }
        """)

        # Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # Scroll area for thumbnails
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        # Container for thumbnails
        self.timeline_container = QWidget()
        self.timeline_layout = QHBoxLayout(self.timeline_container)
        self.timeline_layout.setSpacing(5)
        self.timeline_layout.setContentsMargins(5, 5, 5, 5)
        self.timeline_layout.addStretch()

        scroll.setWidget(self.timeline_container)
        main_layout.addWidget(scroll)

        # Empty state label
        self.empty_label = QLabel("📽️ Drag thumbnails here to build your timeline")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #666; font-size: 14px; font-weight: bold;")
        main_layout.addWidget(self.empty_label)

        self.update_empty_state()

    def update_empty_state(self):
        """Show/hide empty state label."""
        is_empty = len(self.timeline_items) == 0
        self.empty_label.setVisible(is_empty)
        if is_empty:
            self.setStyleSheet("""
                QFrame {
                    background-color: #1a1a1a;
                    border: 2px dashed #3d3d3d;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #1a1a1a;
                    border: 2px solid #00ff00;
                    border-radius: 8px;
                }
            """)

    def dragEnterEvent(self, event):
        """Accept drag events with file data."""
        if event.mimeData().hasFormat("application/x-slideshow-file") or \
           event.mimeData().hasFormat("application/x-timeline-reorder"):
            event.acceptProposedAction()
            self.setStyleSheet("""
                QFrame {
                    background-color: #2a3a2a;
                    border: 2px solid #00ff00;
                    border-radius: 8px;
                }
            """)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """Reset styling when drag leaves."""
        self.update_empty_state()

    def dropEvent(self, event):
        """Handle dropped files."""
        if event.mimeData().hasFormat("application/x-slideshow-file"):
            # New file dropped from gallery
            file_path = event.mimeData().text()
            self.add_item(file_path)
            event.acceptProposedAction()
        elif event.mimeData().hasFormat("application/x-timeline-reorder"):
            # Reordering within timeline
            file_path = event.mimeData().text()
            # Find drop position
            drop_pos = event.pos()
            insert_index = self.get_insert_index(drop_pos)
            self.reorder_item(file_path, insert_index)
            event.acceptProposedAction()

        self.update_empty_state()

    def get_insert_index(self, pos):
        """Get the index where item should be inserted based on drop position."""
        # Find which thumbnail the drop is closest to
        for i, widget in enumerate(self.thumbnail_widgets):
            widget_pos = widget.mapTo(self, QPoint(0, 0))
            widget_center = widget_pos.x() + widget.width() // 2
            if pos.x() < widget_center:
                return i
        return len(self.thumbnail_widgets)

    def add_item(self, file_path, pixmap=None):
        """Add item to timeline."""
        file_path = Path(file_path)

        # Avoid duplicates
        if str(file_path) in [str(p) for p in self.timeline_items]:
            logger.debug(f"Item already in timeline: {file_path.name}")
            return

        self.timeline_items.append(file_path)

        # Create thumbnail widget
        thumbnail = TimelineThumbnail(file_path, pixmap)
        thumbnail.removed.connect(self.remove_thumbnail)
        self.thumbnail_widgets.append(thumbnail)

        # Insert before stretch
        self.timeline_layout.insertWidget(len(self.thumbnail_widgets) - 1, thumbnail)

        self.update_empty_state()
        self.timeline_changed.emit(self.timeline_items)
        logger.info(f"Added to timeline: {file_path.name}")

    def remove_thumbnail(self, thumbnail):
        """Remove thumbnail from timeline."""
        if thumbnail in self.thumbnail_widgets:
            index = self.thumbnail_widgets.index(thumbnail)
            self.thumbnail_widgets.remove(thumbnail)
            self.timeline_items.pop(index)
            thumbnail.deleteLater()
            self.update_empty_state()
            self.timeline_changed.emit(self.timeline_items)
            logger.info(f"Removed from timeline: {thumbnail.file_path.name}")

    def reorder_item(self, file_path, new_index):
        """Reorder item in timeline."""
        file_path = Path(file_path)

        # Find current index
        try:
            old_index = [str(p) for p in self.timeline_items].index(str(file_path))
        except ValueError:
            return

        # Remove from old position
        self.timeline_items.pop(old_index)
        old_widget = self.thumbnail_widgets.pop(old_index)
        self.timeline_layout.removeWidget(old_widget)

        # Insert at new position
        new_index = min(new_index, len(self.timeline_items))
        self.timeline_items.insert(new_index, file_path)
        self.thumbnail_widgets.insert(new_index, old_widget)
        self.timeline_layout.insertWidget(new_index, old_widget)

        self.timeline_changed.emit(self.timeline_items)
        logger.info(f"Reordered in timeline: {file_path.name} to position {new_index}")

    def clear(self):
        """Clear all items from timeline."""
        for widget in self.thumbnail_widgets:
            widget.deleteLater()
        self.thumbnail_widgets.clear()
        self.timeline_items.clear()
        self.update_empty_state()
        self.timeline_changed.emit(self.timeline_items)
        logger.info("Timeline cleared")

    def set_items(self, file_paths, thumbnail_cache=None):
        """Set timeline items from list of file paths."""
        self.clear()
        for file_path in file_paths:
            pixmap = None
            if thumbnail_cache and Path(file_path) in thumbnail_cache:
                pixmap = thumbnail_cache[Path(file_path)]
            self.add_item(file_path, pixmap)


class PlaylistExportDialog(QDialog):
    """Dialog for exporting playlist as FFmpeg concatenation script."""

    def __init__(self, playlist, db, parent=None):
        super().__init__(parent)
        self.playlist = playlist
        self.db = db
        self.setWindowTitle("Export Playlist as FFmpeg Script")
        self.setGeometry(200, 200, 800, 600)
        self.setup_ui()

    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout()

        # Title
        title = QLabel("📤 Export Playlist as FFmpeg Concatenation Script")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)

        # Playlist info
        info_label = QLabel(f"Playlist contains {len(self.playlist)} videos")
        layout.addWidget(info_label)

        # Script name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Script Name:"))
        self.name_input = QLineEdit()
        self.name_input.setText(f"concat_playlist_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        # Description
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Description:"))
        self.desc_input = QLineEdit()
        self.desc_input.setText("FFmpeg concatenation script for video playlist")
        desc_layout.addWidget(self.desc_input)
        layout.addLayout(desc_layout)

        # Output filename
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output File:"))
        self.output_input = QLineEdit()
        self.output_input.setText(f"concatenated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
        output_layout.addWidget(self.output_input)
        layout.addLayout(output_layout)

        # Concatenation method
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("Method:"))
        self.method_combo = QComboBox()
        self.method_combo.addItems([
            "concat demuxer (fast, no re-encode)",
            "concat filter (re-encode, more compatible)",
            "concat protocol (simple, re-encode)"
        ])
        self.method_combo.currentIndexChanged.connect(self.update_preview)
        method_layout.addWidget(self.method_combo)
        layout.addLayout(method_layout)

        # FFmpeg command preview
        preview_label = QLabel("FFmpeg Command Preview:")
        preview_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(preview_label)

        self.command_preview = QTextEdit()
        self.command_preview.setReadOnly(True)
        self.command_preview.setMaximumHeight(150)
        self.command_preview.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #14FFEC;
                font-family: monospace;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.command_preview)

        # Load saved scripts
        saved_layout = QHBoxLayout()
        saved_layout.addWidget(QLabel("Load Saved Script:"))
        self.saved_scripts_combo = QComboBox()
        self.load_saved_scripts()
        self.saved_scripts_combo.currentIndexChanged.connect(self.load_saved_script)
        saved_layout.addWidget(self.saved_scripts_combo)
        layout.addLayout(saved_layout)

        # Buttons
        btn_layout = QHBoxLayout()

        btn_save = QPushButton("💾 Save Script to Database")
        btn_save.clicked.connect(self.save_script)
        btn_layout.addWidget(btn_save)

        btn_export = QPushButton("📤 Export & Run")
        btn_export.clicked.connect(self.export_and_run)
        btn_layout.addWidget(btn_export)

        btn_export_file = QPushButton("💾 Export to File")
        btn_export_file.clicked.connect(self.export_to_file)
        btn_layout.addWidget(btn_export_file)

        btn_cancel = QPushButton("❌ Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.update_preview()

    def load_saved_scripts(self):
        """Load saved scripts from database."""
        self.saved_scripts_combo.clear()
        self.saved_scripts_combo.addItem("-- Select a saved script --")

        scripts = self.db.list_scripts()
        for script in scripts:
            name, desc, modified, times_used = script
            display = f"{name} (used {times_used}x)"
            self.saved_scripts_combo.addItem(display, userData=name)

    def load_saved_script(self, index):
        """Load a saved script into the preview."""
        if index <= 0:
            return

        name = self.saved_scripts_combo.itemData(index)
        script_data = self.db.get_script(name)

        if script_data:
            self.command_preview.setPlainText(script_data['command'])
            self.name_input.setText(script_data['name'])
            self.desc_input.setText(script_data['description'])

    def update_preview(self):
        """Update the FFmpeg command preview."""
        method = self.method_combo.currentIndex()
        output_file = self.output_input.text()

        if method == 0:  # concat demuxer
            command = self.generate_concat_demuxer_script(output_file)
        elif method == 1:  # concat filter
            command = self.generate_concat_filter_script(output_file)
        else:  # concat protocol
            command = self.generate_concat_protocol_script(output_file)

        self.command_preview.setPlainText(command)

    def generate_concat_demuxer_script(self, output_file):
        """Generate FFmpeg concat demuxer script (fast, no re-encode)."""
        # Create file list
        file_list = "# FFmpeg concat demuxer file list\n"
        for video_path in self.playlist:
            file_list += f"file '{video_path}'\n"

        command = f"""# Step 1: Create concat.txt file with video list
cat > concat.txt << 'EOF'
{file_list}EOF

# Step 2: Run FFmpeg concat demuxer (fast, no re-encode)
ffmpeg -f concat -safe 0 -i concat.txt -c copy {output_file}

# Step 3: Cleanup
rm concat.txt
"""
        return command

    def generate_concat_filter_script(self, output_file):
        """Generate FFmpeg concat filter script (re-encode, more compatible)."""
        inputs = ""
        filter_complex = ""

        for i, video_path in enumerate(self.playlist):
            inputs += f"-i '{video_path}' "
            filter_complex += f"[{i}:v:0][{i}:a:0]"

        filter_complex += f"concat=n={len(self.playlist)}:v=1:a=1[outv][outa]"

        command = f"""# FFmpeg concat filter (re-encode for compatibility)
ffmpeg {inputs}\\
  -filter_complex "{filter_complex}" \\
  -map "[outv]" -map "[outa]" \\
  -c:v libx264 -preset medium -crf 23 \\
  -c:a aac -b:a 192k \\
  {output_file}
"""
        return command

    def generate_concat_protocol_script(self, output_file):
        """Generate FFmpeg concat protocol script (simple, re-encode)."""
        concat_str = "concat:" + "|".join(self.playlist)

        command = f"""# FFmpeg concat protocol (simple, re-encode)
ffmpeg -i "{concat_str}" \\
  -c:v libx264 -preset medium -crf 23 \\
  -c:a aac -b:a 192k \\
  {output_file}
"""
        return command

    def save_script(self):
        """Save the script to database."""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Please enter a script name")
            return

        description = self.desc_input.text().strip()
        command = self.command_preview.toPlainText()

        self.db.save_script(name, command, description)
        QMessageBox.information(self, "Success", f"Script '{name}' saved to database!")
        self.load_saved_scripts()

    def export_and_run(self):
        """Export script and run it immediately."""
        command = self.command_preview.toPlainText()
        output_file = self.output_input.text()

        # Validate output filename
        if not output_file or output_file.strip() == "":
            QMessageBox.warning(self, "Error", "Please enter an output filename")
            return

        # Check if output file already exists
        output_path = OUTPUT_DIR / output_file
        if output_path.exists():
            reply = QMessageBox.question(
                self, "File Exists",
                f"'{output_file}' already exists.\nOverwrite it?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        # Estimate duration
        method = self.method_combo.currentIndex()
        video_count = len(self.playlist)
        if method == 0:  # concat demuxer
            estimated_time = "1-2 seconds"
        else:  # re-encode methods
            estimated_time = f"{video_count * 30}-{video_count * 60} seconds"

        # Confirm
        reply = QMessageBox.question(
            self, "Confirm",
            f"Run FFmpeg concatenation?\n\nOutput: {output_file}\nVideos: {video_count}\nEstimated time: {estimated_time}",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Save script to database
            name = self.name_input.text().strip()
            if name:
                self.db.save_script(name, command, self.desc_input.text())
                self.db.increment_usage(name)

            # Run in background thread
            thread = threading.Thread(target=self._run_concat_worker, args=(command, output_file), daemon=True)
            thread.start()

            QMessageBox.information(
                self, "Running",
                f"FFmpeg concatenation started in background\n\nEstimated time: {estimated_time}\nCheck logs for progress"
            )
            self.accept()

    def _run_concat_worker(self, command, output_file):
        """Worker thread to run FFmpeg concatenation."""
        try:
            # Execute the script
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=600,
                cwd=str(OUTPUT_DIR)
            )

            if result.returncode == 0:
                logger.info(f"Concatenation successful: {output_file}")
            else:
                logger.error(f"Concatenation failed: {result.stderr}")
        except Exception as e:
            logger.error(f"Error running concatenation: {e}")

    def export_to_file(self):
        """Export script to a shell file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Script", f"concat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sh",
            "Shell Scripts (*.sh)"
        )

        if file_path:
            command = self.command_preview.toPlainText()

            with open(file_path, 'w') as f:
                f.write("#!/bin/bash\n")
                f.write(f"# Generated by Slideshow Manager on {datetime.now().isoformat()}\n")
                f.write(f"# Playlist: {len(self.playlist)} videos\n\n")
                f.write(command)

            os.chmod(file_path, 0o755)
            QMessageBox.information(self, "Success", f"Script exported to:\n{file_path}")


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
        self.selected_images = set()
        self.previous_selected_images = set()
        self.select_all_state = 0  # 0=normal, 1=all selected, 2=none selected

        # Performance optimization: thumbnail cache
        self.thumbnail_cache = {}  # {path: QPixmap}
        self.video_frame_cache = {}  # {path: frame_path}
        self.thumbnail_buttons = {}  # {index: button}
        self.thumbnail_loader_thread = None
        self.stop_loading = False

        # Default FFmpeg command (uses image2 demuxer with numbered files)
        # Includes padding to handle odd dimensions and scaling to 1920x1080
        self.default_ffmpeg_cmd = (
            "ffmpeg -y -loglevel error -framerate 1/5 "
            "-i %04d.png "
            "-vf \"format=yuv420p,scale='min(1920,iw*min(1920/iw\\,1080/ih))':'min(1080,ih*min(1920/iw\\,1080/ih))':force_original_aspect_ratio=decrease,pad=1920:1080:(1920-iw)/2:(1080-ih)/2\" "
            "-c:v libx264 -r 30 -pix_fmt yuv420p -y output.mp4"
        )

        # Initialize database for scripts and playlists
        self.db = FFmpegScriptDatabase()

        # Playlist management
        self.current_playlist = []  # List of video paths in order
        self.selected_videos_for_playlist = set()  # Set of video paths selected for playlist

        # Load configuration
        self.load_config()
        self.detect_video_players()

        # Setup UI
        self.setup_ui()
        self.load_images()
        self.show_available_videos()

        # Show video grid on startup (since player is stopped)
        QTimer.singleShot(500, self.show_video_grid)

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

        control_layout.addStretch()
        main_layout.addLayout(control_layout)

        # Splitter for resizable sections
        splitter = QSplitter(Qt.Vertical)

        # Thumbnails panel with statistics (FIRST)
        thumbnails_panel = self.create_thumbnails_panel()
        splitter.addWidget(thumbnails_panel)

        # FFmpeg command panel (SECOND)
        ffmpeg_panel = self.create_ffmpeg_panel()
        splitter.addWidget(ffmpeg_panel)

        # Video selection panel (THIRD)
        video_panel = self.create_video_panel()
        splitter.addWidget(video_panel)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 1)

        main_layout.addWidget(splitter)

        # Apply dark theme
        self.apply_dark_theme()
    
    def create_video_panel(self):
        """Create video player panel with embedded VLC and playlist functionality."""
        panel = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # Left side: Player
        left_layout = QVBoxLayout()

        # Header with title and video selector
        header_layout = QHBoxLayout()
        label = QLabel("🎬 Video Player & Playlist")
        label.setFont(QFont("Arial", 11, QFont.Bold))
        header_layout.addWidget(label)
        header_layout.addStretch()

        # Video dropdown selector
        self.video_combo = QComboBox()
        self.video_combo.setMaximumWidth(300)
        self.video_combo.currentIndexChanged.connect(self.on_video_selected)
        header_layout.addWidget(self.video_combo)

        left_layout.addLayout(header_layout)

        # VLC player widget - FIXED: Use media_player_new() instead of media_list_player_new()
        self.vlc_instance = vlc.Instance()
        self.media_player = self.vlc_instance.media_player_new()

        # Create a stacked widget to hold both VLC player and video thumbnail grid
        from PyQt5.QtWidgets import QStackedWidget, QScrollArea
        self.player_stack = QStackedWidget()

        # Page 0: VLC player widget
        self.vlc_widget = QWidget()
        self.vlc_widget.setStyleSheet("background-color: #1a1a1a; border-radius: 4px;")
        self.vlc_widget.setMinimumSize(640, 360)  # FIXED: Set minimum size so widget is visible

        # CRITICAL FIX: Attach VLC to the widget's window handle
        # This is platform-specific and required for embedded playback
        if sys.platform.startswith('linux'):  # Linux using X Server
            self.media_player.set_xwindow(int(self.vlc_widget.winId()))
        elif sys.platform == "win32":  # Windows
            self.media_player.set_hwnd(int(self.vlc_widget.winId()))
        elif sys.platform == "darwin":  # macOS
            self.media_player.set_nsobject(int(self.vlc_widget.winId()))

        self.player_stack.addWidget(self.vlc_widget)

        # Page 1: Video thumbnail grid (shown when stopped)
        self.video_grid_widget = QWidget()
        self.video_grid_widget.setStyleSheet("background-color: #1a1a1a; border-radius: 4px;")
        video_grid_scroll = QScrollArea()
        video_grid_scroll.setWidgetResizable(True)
        video_grid_scroll.setWidget(self.video_grid_widget)
        video_grid_scroll.setStyleSheet("background-color: #1a1a1a; border: none;")

        self.video_grid_layout = QGridLayout(self.video_grid_widget)
        self.video_grid_layout.setSpacing(10)
        self.video_grid_layout.setContentsMargins(10, 10, 10, 10)

        self.player_stack.addWidget(video_grid_scroll)

        # Start with VLC player visible
        self.player_stack.setCurrentIndex(0)

        left_layout.addWidget(self.player_stack, 1)

        # Timeline widget
        timeline_header = QLabel("🎞️ Timeline (Drag & Drop)")
        timeline_header.setFont(QFont("Arial", 10, QFont.Bold))
        timeline_header.setStyleSheet("color: #00ff00; margin-top: 5px;")
        left_layout.addWidget(timeline_header)

        self.timeline_widget = TimelineWidget()
        self.timeline_widget.timeline_changed.connect(self.on_timeline_changed)
        left_layout.addWidget(self.timeline_widget)

        # Timeline control buttons
        timeline_controls = QHBoxLayout()

        btn_timeline_play = RoundedButton("▶️ Play Timeline")
        btn_timeline_play.clicked.connect(self.play_timeline)
        timeline_controls.addWidget(btn_timeline_play)

        btn_timeline_export = RoundedButton("📤 Export Timeline")
        btn_timeline_export.clicked.connect(self.export_timeline_ffmpeg)
        timeline_controls.addWidget(btn_timeline_export)

        btn_timeline_clear = RoundedButton("🗑️ Clear Timeline")
        btn_timeline_clear.clicked.connect(self.clear_timeline)
        timeline_controls.addWidget(btn_timeline_clear)

        timeline_controls.addStretch()
        left_layout.addLayout(timeline_controls)

        # Control buttons
        controls_layout = QHBoxLayout()

        self.btn_play_pause = RoundedButton("▶️ Play")
        self.btn_play_pause.clicked.connect(self.vlc_play_pause_toggle)
        controls_layout.addWidget(self.btn_play_pause)

        btn_stop = RoundedButton("⏹️ Stop")
        btn_stop.clicked.connect(self.vlc_stop)
        controls_layout.addWidget(btn_stop)

        controls_layout.addStretch()

        btn_folder = RoundedButton("📁 Open Folder")
        btn_folder.clicked.connect(self.open_videos_folder)
        controls_layout.addWidget(btn_folder)

        left_layout.addLayout(controls_layout)

        # Right side: Playlist Manager
        right_layout = QVBoxLayout()

        # Playlist header with count
        playlist_header_layout = QHBoxLayout()
        playlist_label = QLabel("📋 Playlist")
        playlist_label.setFont(QFont("Arial", 10, QFont.Bold))
        playlist_header_layout.addWidget(playlist_label)

        self.playlist_count_label = QLabel("(0 items)")
        self.playlist_count_label.setStyleSheet("color: #888;")
        playlist_header_layout.addWidget(self.playlist_count_label)
        playlist_header_layout.addStretch()

        right_layout.addLayout(playlist_header_layout)

        # Playlist list widget
        self.playlist_widget = QListWidget()
        self.playlist_widget.setMaximumWidth(300)
        self.playlist_widget.setStyleSheet("""
            QListWidget {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 4px;
                border-radius: 2px;
            }
            QListWidget::item:selected {
                background-color: #0d7377;
            }
        """)

        # Add keyboard shortcuts tooltip
        self.playlist_widget.setToolTip(
            "Keyboard shortcuts:\n"
            "Delete - Remove selected item\n"
            "Ctrl+Up - Move item up\n"
            "Ctrl+Down - Move item down"
        )

        right_layout.addWidget(self.playlist_widget)

        # Playlist control buttons
        playlist_btn_layout = QVBoxLayout()

        # Add selected videos counter and button
        selected_videos_layout = QHBoxLayout()
        self.selected_videos_label = QLabel("Selected: 0 videos")
        self.selected_videos_label.setStyleSheet("color: #00ff00; font-weight: bold;")
        selected_videos_layout.addWidget(self.selected_videos_label)

        btn_add_selected_videos = RoundedButton("➕ Add Selected Videos")
        btn_add_selected_videos.clicked.connect(self.add_selected_videos_to_playlist)
        selected_videos_layout.addWidget(btn_add_selected_videos)

        playlist_btn_layout.addLayout(selected_videos_layout)

        btn_add_to_playlist = RoundedButton("➕ Add from Dropdown")
        btn_add_to_playlist.clicked.connect(self.add_to_playlist)
        playlist_btn_layout.addWidget(btn_add_to_playlist)

        btn_remove_from_playlist = RoundedButton("➖ Remove")
        btn_remove_from_playlist.clicked.connect(self.remove_from_playlist)
        playlist_btn_layout.addWidget(btn_remove_from_playlist)

        btn_move_up = RoundedButton("⬆️ Move Up")
        btn_move_up.clicked.connect(self.move_playlist_up)
        playlist_btn_layout.addWidget(btn_move_up)

        btn_move_down = RoundedButton("⬇️ Move Down")
        btn_move_down.clicked.connect(self.move_playlist_down)
        playlist_btn_layout.addWidget(btn_move_down)

        btn_clear_playlist = RoundedButton("🗑️ Clear All")
        btn_clear_playlist.clicked.connect(self.clear_playlist)
        playlist_btn_layout.addWidget(btn_clear_playlist)

        btn_play_playlist = RoundedButton("▶️ Play Playlist")
        btn_play_playlist.clicked.connect(self.play_playlist)
        playlist_btn_layout.addWidget(btn_play_playlist)

        btn_save_playlist = RoundedButton("💾 Save Playlist")
        btn_save_playlist.clicked.connect(self.save_playlist_dialog)
        playlist_btn_layout.addWidget(btn_save_playlist)

        btn_load_playlist = RoundedButton("📂 Load Playlist")
        btn_load_playlist.clicked.connect(self.load_playlist_dialog)
        playlist_btn_layout.addWidget(btn_load_playlist)

        btn_export_concat = RoundedButton("📤 Export FFmpeg")
        btn_export_concat.clicked.connect(self.export_playlist_ffmpeg)
        playlist_btn_layout.addWidget(btn_export_concat)

        right_layout.addLayout(playlist_btn_layout)

        # Add layouts to main layout
        main_layout.addLayout(left_layout, 2)
        main_layout.addLayout(right_layout, 1)

        panel.setLayout(main_layout)
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

        # Header with statistics and Select All button
        header_layout = QHBoxLayout()
        header_label = QLabel("📸 Image Thumbnails")
        header_label.setFont(QFont("Arial", 11, QFont.Bold))
        header_layout.addWidget(header_label)

        self.stats_label = QLabel()
        self.stats_label.setFont(QFont("Arial", 9))
        header_layout.addStretch()
        header_layout.addWidget(self.stats_label)

        # Select All button
        self.btn_select_all = RoundedButton("☑️ Select All")
        self.btn_select_all.clicked.connect(self.toggle_select_all)
        self.btn_select_all.setMaximumWidth(120)
        header_layout.addWidget(self.btn_select_all)

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

    def extract_video_first_frame(self, video_path):
        """Extract first frame from video file using FFmpeg (optimized for speed)."""
        try:
            # Create temporary PNG file for the frame
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp_path = tmp.name

            # Use FFmpeg to extract first frame - optimized for speed
            # -ss 0 seeks to start, -vframes 1 gets only 1 frame, -q:v 5 is faster than 2
            cmd = [
                'ffmpeg', '-y', '-loglevel', 'error',
                '-ss', '0',
                '-i', str(video_path),
                '-vframes', '1',
                '-q:v', '5',
                tmp_path
            ]

            try:
                result = subprocess.run(cmd, capture_output=True, timeout=30)
            except subprocess.TimeoutExpired:
                logger.warning(f"FFmpeg timeout extracting frame from {video_path.name}, trying with longer timeout")
                # Try again with longer timeout
                result = subprocess.run(cmd, capture_output=True, timeout=60)

            if result.returncode == 0 and Path(tmp_path).exists():
                logger.debug(f"Successfully extracted frame from {video_path.name}")
                return tmp_path
            else:
                logger.error(f"Failed to extract frame from {video_path}")
                if Path(tmp_path).exists():
                    Path(tmp_path).unlink()
                return None
        except subprocess.TimeoutExpired:
            logger.error(f"FFmpeg timeout extracting frame from {video_path.name} (>60s)")
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()
            return None
        except Exception as e:
            logger.error(f"Error extracting video frame: {e}", exc_info=True)
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()
            return None
    
    def load_images(self):
        """Load images and videos from directory."""
        try:
            if not IMAGES_DIR.exists():
                IMAGES_DIR.mkdir(parents=True, exist_ok=True)

            # Load both images and videos
            all_files = sorted([
                f for f in IMAGES_DIR.glob('*')
                if f.suffix.lower() in SUPPORTED_FORMATS or f.suffix.lower() in VIDEO_FORMATS
            ])

            self.images = all_files

            # Reset selected images when reloading (to avoid stale indices)
            self.selected_images = set(range(len(self.images)))
            self.previous_selected_images = set()
            self.select_all_state = 0

            self.update_thumbnails()
            self.update_statistics()
            logger.info(f"Loaded {len(self.images)} items (images and videos)")
        except Exception as e:
            logger.error(f"Error loading images: {e}")
            self.log_event(f"Error loading images: {e}")
    
    def update_thumbnails(self):
        """Update thumbnail grid with lazy loading."""
        # Clear existing thumbnails
        while self.thumbnails_layout.count():
            self.thumbnails_layout.takeAt(0).widget().deleteLater()

        self.thumbnail_buttons = {}
        self.stop_loading = False

        # Create placeholder buttons and load PNG thumbnails immediately (fast)
        for i, img_path in enumerate(self.images):
            try:
                btn = self._create_placeholder_thumbnail(i, img_path)
                self.thumbnail_buttons[i] = btn
                self.thumbnails_layout.addWidget(btn, i // 6, i % 6)

                # Load PNG/JPG thumbnails immediately on main thread (they're fast)
                if img_path.suffix.lower() in SUPPORTED_FORMATS:
                    pixmap = self._load_single_thumbnail(img_path)
                    if pixmap:
                        self.thumbnail_cache[img_path] = pixmap
                        self._update_thumbnail_ui(btn, pixmap)
            except Exception as e:
                logger.error(f"Error creating placeholder for {img_path}: {e}")

        # Start background thread to load VIDEO thumbnails only
        self.stop_loading = False
        self.thumbnail_loader_thread = threading.Thread(target=self._load_video_thumbnails_background, daemon=True)
        self.thumbnail_loader_thread.start()

    def _create_placeholder_thumbnail(self, index, img_path):
        """Create a fast placeholder thumbnail with drag support."""
        btn = QPushButton()
        btn.setFixedSize(130, 130)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFlat(True)
        btn.index = index
        btn.img_path = img_path
        btn.drag_start_position = None

        # Different behavior for videos vs images
        is_video = img_path.suffix.lower() in VIDEO_FORMATS
        if is_video:
            # Videos: Single click plays, Ctrl+click toggles selection
            btn.clicked.connect(lambda: self.on_thumbnail_clicked(index, img_path))
        else:
            # Images: Click toggles selection
            btn.clicked.connect(lambda: self.toggle_image_selection(index, None))

        # Enable drag-and-drop for timeline
        btn.mousePressEvent = lambda event: self._thumbnail_mouse_press(btn, event)
        btn.mouseMoveEvent = lambda event: self._thumbnail_mouse_move(btn, event)
        btn.mouseReleaseEvent = lambda event: self._thumbnail_mouse_release(btn, event)

        # Set placeholder text
        btn.setText("📹" if is_video else "🖼️")

        # Update border
        self._update_thumbnail_border(btn, index)

        # Set tooltip
        try:
            file_size = img_path.stat().st_size / 1024
            file_name = img_path.name
            file_type = "Video" if is_video else "Image"
            if is_video:
                tooltip_text = f"{file_name}\n{file_type} | Size: {file_size:.1f} KB\n\nClick to play\nCtrl+Click to select"
            else:
                tooltip_text = f"{file_name}\n{file_type} | Size: {file_size:.1f} KB\n\nClick to select"
            btn.setToolTip(tooltip_text)
        except:
            pass

        return btn

    def _load_video_thumbnails_background(self):
        """Load VIDEO thumbnails in background thread (PNG/JPG are loaded on main thread)."""
        for i, img_path in enumerate(self.images):
            if self.stop_loading:
                break

            # Only process videos in background thread
            if img_path.suffix.lower() not in VIDEO_FORMATS:
                continue

            try:
                # Skip if already cached
                if img_path in self.thumbnail_cache:
                    pixmap = self.thumbnail_cache[img_path]
                else:
                    pixmap = self._load_single_thumbnail(img_path)
                    if pixmap:
                        self.thumbnail_cache[img_path] = pixmap

                # Update button on main thread using QTimer
                if i in self.thumbnail_buttons and pixmap:
                    btn = self.thumbnail_buttons[i]
                    QTimer.singleShot(0, lambda b=btn, p=pixmap: self._update_thumbnail_ui(b, p))
            except Exception as e:
                logger.error(f"Error loading video thumbnail {i}: {e}")

    def _update_thumbnail_ui(self, btn, pixmap):
        """Update thumbnail UI on main thread."""
        try:
            btn.setIcon(QIcon(pixmap))
            btn.setIconSize(QSize(120, 120))
            btn.setText("")  # Clear placeholder text
            # CRITICAL: Keep a reference to the pixmap to prevent garbage collection
            # This is the same pattern used in Tkinter (thumb_label.image = thumb)
            btn._pixmap = pixmap
        except Exception as e:
            logger.error(f"Error updating thumbnail UI: {e}")

    def _load_single_thumbnail(self, img_path):
        """Load a single thumbnail (can be called from background thread)."""
        try:
            if img_path.suffix.lower() in VIDEO_FORMATS:
                logger.debug(f"Loading video thumbnail: {img_path.name}")
                # Extract first frame from video
                if img_path in self.video_frame_cache:
                    frame_path = self.video_frame_cache[img_path]
                    logger.debug(f"Using cached frame for {img_path.name}")
                else:
                    logger.debug(f"Extracting frame from {img_path.name}")
                    frame_path = self.extract_video_first_frame(img_path)
                    if frame_path:
                        self.video_frame_cache[img_path] = frame_path
                        logger.debug(f"Cached frame for {img_path.name}")
                    else:
                        logger.warning(f"Failed to extract frame from {img_path.name}")

                if frame_path:
                    logger.debug(f"Opening frame file: {frame_path}")
                    img = Image.open(frame_path)
                    img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                    pixmap = self._pil_to_qpixmap(img)
                    if pixmap:
                        logger.debug(f"Successfully created pixmap for {img_path.name}")
                    return pixmap
                else:
                    logger.warning(f"No frame path for {img_path.name}")
            else:
                # Regular image file
                logger.debug(f"Loading image thumbnail: {img_path.name}")
                img = Image.open(img_path)
                img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                pixmap = self._pil_to_qpixmap(img)
                if pixmap:
                    logger.debug(f"Successfully created pixmap for {img_path.name}")
                return pixmap
        except Exception as e:
            logger.error(f"Error loading thumbnail for {img_path.name}: {e}", exc_info=True)

        return None



    def _pil_to_qpixmap(self, pil_image):
        """Convert PIL image to QPixmap efficiently."""
        try:
            # Ensure image is in RGB mode
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')

            # Use PIL's built-in toqimage method if available, otherwise use temp file
            try:
                # Try direct conversion using PIL's internal method
                from PIL.ImageQt import ImageQt
                qimage = ImageQt(pil_image)
                return QPixmap.fromImage(qimage)
            except:
                # Fallback: save to temp file and load
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    tmp_path = tmp.name
                pil_image.save(tmp_path, 'PNG')
                pixmap = QPixmap(tmp_path)
                Path(tmp_path).unlink()  # Delete temp file
                return pixmap
        except Exception as e:
            logger.error(f"Error converting PIL to QPixmap: {e}")
            return None

    def _update_thumbnail_border(self, btn, index):
        """Update thumbnail border color based on selection state."""
        is_selected = index in self.selected_images

        # Check if it's a video selected for playlist
        is_video_selected_for_playlist = False
        if hasattr(btn, 'img_path'):
            is_video_selected_for_playlist = str(btn.img_path) in self.selected_videos_for_playlist

        # Use brighter green for videos selected for playlist
        if is_video_selected_for_playlist:
            border_color = "#00ff00"  # Bright green for playlist selection
            border_width = "4px"
        elif is_selected:
            border_color = "#00ff00"  # Green for regular selection
            border_width = "4px"
        else:
            border_color = "#3d3d3d"  # Gray if not selected
            border_width = "2px"

        btn.setStyleSheet(f"""
            QPushButton {{
                border: {border_width} solid {border_color};
                border-radius: 4px;
                padding: 0px;
                background-color: #2b2b2b;
            }}
            QPushButton:hover {{
                border: 4px solid #4a9eff;
            }}
        """)

    def _thumbnail_mouse_press(self, btn, event):
        """Handle mouse press on thumbnail for drag-and-drop."""
        if event.button() == Qt.LeftButton:
            btn.drag_start_position = event.pos()
        QPushButton.mousePressEvent(btn, event)

    def _thumbnail_mouse_move(self, btn, event):
        """Handle mouse move on thumbnail to start drag."""
        if not (event.buttons() & Qt.LeftButton):
            return
        if not hasattr(btn, 'drag_start_position') or btn.drag_start_position is None:
            return
        if (event.pos() - btn.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return

        # Start drag operation
        drag = QDrag(btn)
        mime_data = QMimeData()

        # Store file path
        mime_data.setText(str(btn.img_path))
        mime_data.setData("application/x-slideshow-file", str(btn.img_path).encode())

        drag.setMimeData(mime_data)

        # Set drag pixmap (thumbnail preview)
        if hasattr(btn, 'icon') and not btn.icon().isNull():
            pixmap = btn.icon().pixmap(80, 80)
            drag.setPixmap(pixmap)
        elif btn.img_path in self.thumbnail_cache:
            pixmap = self.thumbnail_cache[btn.img_path]
            drag.setPixmap(pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            # Create simple pixmap
            pixmap = QPixmap(80, 80)
            pixmap.fill(QColor("#2a2a2a"))
            painter = QPainter(pixmap)
            painter.setPen(QColor("white"))
            painter.setFont(QFont("Arial", 32))
            is_video = btn.img_path.suffix.lower() in VIDEO_FORMATS
            painter.drawText(pixmap.rect(), Qt.AlignCenter, "📹" if is_video else "🖼️")
            painter.end()
            drag.setPixmap(pixmap)

        drag.setHotSpot(QPoint(40, 40))

        # Execute drag
        drag.exec_(Qt.CopyAction)

    def _thumbnail_mouse_release(self, btn, event):
        """Handle mouse release on thumbnail."""
        QPushButton.mouseReleaseEvent(btn, event)

    def on_thumbnail_clicked(self, index, img_path):
        """Handle thumbnail click - play video or toggle selection based on modifiers."""
        # Check if Ctrl is pressed
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier:
            # Ctrl+Click: Toggle selection
            self.toggle_image_selection(index, None)

            # If it's a video, also add to selected videos for playlist
            if img_path.suffix.lower() in VIDEO_FORMATS:
                self.toggle_video_selection_for_playlist(img_path)
        else:
            # Regular click on video: Play it
            if img_path.suffix.lower() in VIDEO_FORMATS:
                self.play_video_from_thumbnail(img_path)
            else:
                # For images, just toggle selection
                self.toggle_image_selection(index, None)

    def on_video_grid_thumbnail_clicked(self, video_path):
        """Handle video grid thumbnail click - play or select based on modifiers."""
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier:
            # Ctrl+Click: Toggle selection for playlist
            self.toggle_video_selection_for_playlist(video_path)
        else:
            # Regular click: Play video
            self.play_video_from_thumbnail(video_path)

    def toggle_video_selection_for_playlist(self, video_path):
        """Toggle video selection for playlist."""
        video_path_str = str(video_path)

        if video_path_str in self.selected_videos_for_playlist:
            self.selected_videos_for_playlist.discard(video_path_str)
            logger.info(f"Deselected video for playlist: {video_path.name}")
            self.log_event(f"☐ Deselected: {video_path.name}")
        else:
            self.selected_videos_for_playlist.add(video_path_str)
            logger.info(f"Selected video for playlist: {video_path.name}")
            self.log_event(f"☑️ Selected: {video_path.name}")

        # Update the selected videos counter
        self.update_selected_videos_counter()

        # Refresh the video grid to update visual feedback (if visible)
        if self.player_stack.currentIndex() == 1:
            self.show_video_grid()

        # Also update main gallery thumbnails
        if hasattr(self, 'thumbnails_layout'):
            for i in range(self.thumbnails_layout.count()):
                widget = self.thumbnails_layout.itemAt(i).widget()
                if isinstance(widget, QPushButton) and hasattr(widget, 'img_path'):
                    if str(widget.img_path) == video_path_str:
                        self._update_thumbnail_border(widget, widget.index)
                        break

    def update_selected_videos_counter(self):
        """Update the selected videos counter label."""
        count = len(self.selected_videos_for_playlist)
        self.selected_videos_label.setText(f"Selected: {count} video{'s' if count != 1 else ''}")
        logger.debug(f"Selected videos count: {count}")

    def play_video_from_thumbnail(self, video_path):
        """Play a video directly from thumbnail click."""
        try:
            # Find the video in available_videos list
            if video_path in self.available_videos:
                index = self.available_videos.index(video_path)
                self.video_combo.setCurrentIndex(index)

                # Load and play the video
                media = self.vlc_instance.media_new(str(video_path))
                self.media_player.set_media(media)
                self.media_player.play()
                self.btn_play_pause.setText("⏸️ Pause")

                # Hide video grid, show VLC player
                self.player_stack.setCurrentIndex(0)

                logger.info(f"Playing video from thumbnail: {video_path.name}")
                self.log_event(f"▶️ Playing: {video_path.name}")
            else:
                self.log_event(f"❌ Video not found in available videos: {video_path.name}")
        except Exception as e:
            logger.error(f"Error playing video from thumbnail: {e}")
            self.log_event(f"❌ Error playing video: {e}")

    def toggle_image_selection(self, index, state):
        """Toggle image selection for slideshow."""
        # Toggle selection state
        if index in self.selected_images:
            self.selected_images.discard(index)
        else:
            self.selected_images.add(index)

        # Update border color for this thumbnail
        if hasattr(self, 'thumbnails_layout'):
            # Find and update the button
            for i in range(self.thumbnails_layout.count()):
                widget = self.thumbnails_layout.itemAt(i).widget()
                if isinstance(widget, QPushButton) and hasattr(widget, 'index') and widget.index == index:
                    self._update_thumbnail_border(widget, index)
                    break

        # Update statistics
        self.update_statistics()

    def toggle_select_all(self):
        """Toggle between select all, select none, and restore previous selection."""
        total_images = len(self.images)

        if self.select_all_state == 0:  # Normal state -> Select All
            self.previous_selected_images = self.selected_images.copy()
            self.selected_images = set(range(total_images))
            self.select_all_state = 1
            self.btn_select_all.setText("☐ Select None")
        elif self.select_all_state == 1:  # All selected -> Select None
            self.selected_images = set()
            self.select_all_state = 2
            self.btn_select_all.setText("↩️ Restore")
        else:  # None selected -> Restore previous
            self.selected_images = self.previous_selected_images.copy()
            self.select_all_state = 0
            self.btn_select_all.setText("☑️ Select All")

        # Refresh thumbnails to update checkboxes
        self.update_thumbnails()
        self.update_statistics()

    def update_statistics(self):
        """Update statistics display."""
        total = len(self.images)
        hidden = len(self.hidden_images)
        visible = total - hidden
        selected = len(self.selected_images) if hasattr(self, 'selected_images') else total
        size_mb = sum(f.stat().st_size for f in self.images) / (1024 * 1024)

        stats_text = f"Total: {total} | Selected: {selected} | Visible: {visible} | Hidden: {hidden} | Size: {size_mb:.1f} MB"
        self.stats_label.setText(stats_text)
    
    def show_available_videos(self):
        """Show available videos in the combo box."""
        try:
            self.available_videos = sorted([
                f for f in OUTPUT_DIR.glob('slideshow_*.mp4')
            ])

            # Block signals to avoid triggering on_video_selected during population
            self.video_combo.blockSignals(True)
            self.video_combo.clear()

            for video in self.available_videos:
                size_mb = video.stat().st_size / (1024 * 1024)
                mtime = datetime.fromtimestamp(video.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
                display_text = f"{video.name} ({size_mb:.1f} MB) - {mtime}"
                self.video_combo.addItem(display_text, userData=str(video))

            self.video_combo.blockSignals(False)

            if self.available_videos:
                logger.info(f"Showing {len(self.available_videos)} videos")
        except Exception as e:
            logger.error(f"Error showing videos: {e}")
            self.log_event(f"Error showing videos: {e}")

    def on_video_selected(self, index):
        """Handle video selection from combo box."""
        if index < 0 or index >= len(self.available_videos):
            return

        video_path = self.available_videos[index]
        logger.debug(f"Video selected: {video_path.name}")

    def vlc_play_pause_toggle(self):
        """Toggle between play and pause states."""
        try:
            current_state = self.media_player.get_state()

            if current_state == vlc.State.Playing:
                # Currently playing -> Pause
                self.media_player.pause()
                self.btn_play_pause.setText("▶️ Play")
                self.log_event("⏸️ Paused")
                logger.info("Paused playback")
            elif current_state == vlc.State.Paused:
                # Currently paused -> Resume
                self.media_player.play()
                self.btn_play_pause.setText("⏸️ Pause")
                self.log_event("▶️ Resumed")
                logger.info("Resumed playback")
            else:
                # Stopped or no media -> Load and play
                if not self.available_videos or self.video_combo.currentIndex() < 0:
                    self.log_event("❌ No video selected")
                    return

                video_path = self.available_videos[self.video_combo.currentIndex()]
                media = self.vlc_instance.media_new(str(video_path))
                self.media_player.set_media(media)
                self.media_player.play()
                self.btn_play_pause.setText("⏸️ Pause")

                # Hide video grid, show VLC player
                self.player_stack.setCurrentIndex(0)

                logger.info(f"Playing video: {video_path.name}")
                self.log_event(f"▶️ Playing: {video_path.name}")
        except Exception as e:
            logger.error(f"Error toggling play/pause: {e}")
            self.log_event(f"❌ Error: {e}")

    def vlc_stop(self):
        """Stop the video and show video thumbnail grid."""
        try:
            self.media_player.stop()
            self.btn_play_pause.setText("▶️ Play")
            self.log_event("⏹️ Stopped")
            logger.info("Stopped playback")

            # Show video thumbnail grid
            self.show_video_grid()
        except Exception as e:
            logger.error(f"Error stopping video: {e}")

    def show_video_grid(self):
        """Display video thumbnails in the player area when stopped."""
        try:
            # Clear existing grid
            while self.video_grid_layout.count():
                item = self.video_grid_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # Get all video files
            video_files = [img for img in self.images if img.suffix.lower() in VIDEO_FORMATS]

            if not video_files:
                # No videos, show message
                label = QLabel("No videos available")
                label.setStyleSheet("color: #888; font-size: 16px;")
                label.setAlignment(Qt.AlignCenter)
                self.video_grid_layout.addWidget(label, 0, 0)
                self.player_stack.setCurrentIndex(1)
                return

            # Create thumbnail buttons for videos (4 per row)
            for i, video_path in enumerate(video_files):
                row = i // 4
                col = i % 4

                # Create button with drag support
                btn = QPushButton()
                btn.setFixedSize(150, 150)
                btn.setCursor(Qt.PointingHandCursor)
                btn.video_path = video_path  # Store video path for later reference
                btn.drag_start_position = None
                btn.img_path = video_path  # For consistency with main gallery

                # Check if this video is selected
                is_selected = str(video_path) in self.selected_videos_for_playlist
                border_color = "#00ff00" if is_selected else "#3a3a3a"
                border_width = "4px" if is_selected else "2px"

                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #2a2a2a;
                        border: {border_width} solid {border_color};
                        border-radius: 8px;
                        color: white;
                        font-size: 14px;
                    }}
                    QPushButton:hover {{
                        border: 4px solid #4a9eff;
                        background-color: #3a3a3a;
                    }}
                """)

                # Set thumbnail or placeholder
                if video_path in self.thumbnail_cache:
                    pixmap = self.thumbnail_cache[video_path]
                    btn.setIcon(QIcon(pixmap))
                    btn.setIconSize(QSize(140, 140))
                    btn._pixmap = pixmap  # Keep reference
                else:
                    btn.setText("📹")
                    btn.setStyleSheet(btn.styleSheet() + "font-size: 48px;")

                # Set tooltip
                try:
                    file_size = video_path.stat().st_size / (1024 * 1024)
                    tooltip = f"{video_path.name}\nSize: {file_size:.1f} MB\n\nClick to play\nCtrl+Click to select\nDrag to timeline"
                    btn.setToolTip(tooltip)
                except:
                    btn.setToolTip(f"{video_path.name}\n\nClick to play\nCtrl+Click to select\nDrag to timeline")

                # Connect click to handle both play and selection
                btn.clicked.connect(lambda checked, vp=video_path: self.on_video_grid_thumbnail_clicked(vp))

                # Enable drag-and-drop
                btn.mousePressEvent = lambda event, b=btn: self._thumbnail_mouse_press(b, event)
                btn.mouseMoveEvent = lambda event, b=btn: self._thumbnail_mouse_move(b, event)
                btn.mouseReleaseEvent = lambda event, b=btn: self._thumbnail_mouse_release(b, event)

                self.video_grid_layout.addWidget(btn, row, col)

            # Switch to video grid view
            self.player_stack.setCurrentIndex(1)
            logger.info(f"Showing video grid with {len(video_files)} videos")

        except Exception as e:
            logger.error(f"Error showing video grid: {e}")

    def update_playlist_count(self):
        """Update the playlist count label."""
        count = len(self.current_playlist)
        if count == 0:
            self.playlist_count_label.setText("(0 items)")
        elif count == 1:
            self.playlist_count_label.setText("(1 item)")
        else:
            # Calculate total duration estimate (assuming 3 sec per image, 5 images per video)
            estimated_duration = count * 15  # seconds
            minutes = estimated_duration // 60
            seconds = estimated_duration % 60
            self.playlist_count_label.setText(f"({count} items, ~{minutes}m{seconds}s)")

    def add_selected_videos_to_playlist(self):
        """Add all selected videos to playlist."""
        if not self.selected_videos_for_playlist:
            QMessageBox.information(self, "Info", "No videos selected.\n\nCtrl+Click on video thumbnails to select them.")
            self.log_event("❌ No videos selected")
            return

        added_count = 0
        duplicate_count = 0

        for video_path_str in list(self.selected_videos_for_playlist):
            video_path = Path(video_path_str)

            # Validate file exists
            if not video_path.exists():
                self.log_event(f"❌ Video file not found: {video_path.name}")
                continue

            # Check for duplicates
            if video_path_str in self.current_playlist:
                duplicate_count += 1
                continue

            # Add to playlist
            self.current_playlist.append(video_path_str)
            self.playlist_widget.addItem(video_path.name)
            added_count += 1
            logger.info(f"Added to playlist: {video_path.name}")

        # Update timeline with all added videos
        for video_path_str in self.current_playlist:
            video_path = Path(video_path_str)
            pixmap = self.thumbnail_cache.get(video_path)
            if str(video_path) not in [str(p) for p in self.timeline_widget.timeline_items]:
                self.timeline_widget.add_item(video_path_str, pixmap)

        # Clear selection after adding
        self.selected_videos_for_playlist.clear()
        self.update_selected_videos_counter()
        self.update_playlist_count()

        # Show summary
        message = f"✅ Added {added_count} video{'s' if added_count != 1 else ''} to playlist"
        if duplicate_count > 0:
            message += f"\n⚠️ Skipped {duplicate_count} duplicate{'s' if duplicate_count != 1 else ''}"

        self.log_event(message)
        QMessageBox.information(self, "Success", message)

        # Refresh video grid to clear visual selection
        if self.player_stack.currentIndex() == 1:  # If grid is visible
            self.show_video_grid()

    def add_to_playlist(self):
        """Add selected video from dropdown to playlist."""
        if not self.available_videos or self.video_combo.currentIndex() < 0:
            self.log_event("❌ No video selected")
            return

        video_path = self.available_videos[self.video_combo.currentIndex()]

        # Validate file exists
        if not video_path.exists():
            self.log_event(f"❌ Video file not found: {video_path.name}")
            QMessageBox.warning(self, "Error", f"Video file not found:\n{video_path}")
            return

        # Check for duplicates
        if str(video_path) in self.current_playlist:
            reply = QMessageBox.question(
                self, "Duplicate",
                f"'{video_path.name}' is already in the playlist.\nAdd it again?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        self.current_playlist.append(str(video_path))

        # Update playlist widget
        self.playlist_widget.addItem(video_path.name)
        self.update_playlist_count()

        # Update timeline
        pixmap = self.thumbnail_cache.get(video_path)
        self.timeline_widget.add_item(str(video_path), pixmap)

        self.log_event(f"➕ Added to playlist: {video_path.name}")
        logger.info(f"Added to playlist: {video_path.name}")

    def remove_from_playlist(self):
        """Remove selected item from playlist."""
        current_row = self.playlist_widget.currentRow()
        if current_row < 0:
            self.log_event("❌ No playlist item selected")
            return

        item = self.playlist_widget.takeItem(current_row)
        del self.current_playlist[current_row]
        self.update_playlist_count()
        self.log_event(f"➖ Removed from playlist: {item.text()}")
        logger.info(f"Removed from playlist: {item.text()}")

    def move_playlist_up(self):
        """Move selected playlist item up."""
        current_row = self.playlist_widget.currentRow()
        if current_row <= 0:
            return

        # Swap in list
        self.current_playlist[current_row], self.current_playlist[current_row - 1] = \
            self.current_playlist[current_row - 1], self.current_playlist[current_row]

        # Swap in widget
        item = self.playlist_widget.takeItem(current_row)
        self.playlist_widget.insertItem(current_row - 1, item)
        self.playlist_widget.setCurrentRow(current_row - 1)
        self.log_event("⬆️ Moved item up")

    def move_playlist_down(self):
        """Move selected playlist item down."""
        current_row = self.playlist_widget.currentRow()
        if current_row < 0 or current_row >= len(self.current_playlist) - 1:
            return

        # Swap in list
        self.current_playlist[current_row], self.current_playlist[current_row + 1] = \
            self.current_playlist[current_row + 1], self.current_playlist[current_row]

        # Swap in widget
        item = self.playlist_widget.takeItem(current_row)
        self.playlist_widget.insertItem(current_row + 1, item)
        self.playlist_widget.setCurrentRow(current_row + 1)
        self.log_event("⬇️ Moved item down")

    def clear_playlist(self):
        """Clear the entire playlist."""
        if not self.current_playlist:
            return

        # Confirm before clearing
        reply = QMessageBox.question(
            self, "Confirm Clear",
            f"Clear all {len(self.current_playlist)} items from playlist?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.current_playlist.clear()
            self.playlist_widget.clear()
            self.timeline_widget.clear()
            self.update_playlist_count()
            self.log_event("🗑️ Playlist cleared")
            logger.info("Playlist cleared")

    def play_playlist(self):
        """Play all videos in playlist sequentially using VLC."""
        if not self.current_playlist:
            self.log_event("❌ Playlist is empty")
            return

        try:
            # Create VLC media list for playlist
            media_list = self.vlc_instance.media_list_new()

            for video_path in self.current_playlist:
                media = self.vlc_instance.media_new(video_path)
                media_list.add_media(media)

            # Create media list player if not exists
            if not hasattr(self, 'playlist_player'):
                self.playlist_player = self.vlc_instance.media_list_player_new()
                self.playlist_player.set_media_player(self.media_player)

            self.playlist_player.set_media_list(media_list)
            self.playlist_player.play()

            self.log_event(f"▶️ Playing playlist ({len(self.current_playlist)} videos)")
            logger.info(f"Playing playlist with {len(self.current_playlist)} videos")
        except Exception as e:
            logger.error(f"Error playing playlist: {e}")
            self.log_event(f"❌ Error playing playlist: {e}")

    def save_playlist_dialog(self):
        """Show dialog to save current playlist."""
        if not self.current_playlist:
            QMessageBox.warning(self, "Warning", "Playlist is empty")
            return

        name, ok = QInputDialog.getText(self, "Save Playlist", "Enter playlist name:")
        if ok and name:
            description, ok2 = QInputDialog.getText(self, "Save Playlist", "Enter description (optional):")
            if ok2:
                self.db.save_playlist(name, self.current_playlist, description)
                QMessageBox.information(self, "Success", f"Playlist '{name}' saved!")
                self.log_event(f"💾 Saved playlist: {name}")

    def on_timeline_changed(self, file_paths):
        """Handle timeline changes and sync with playlist."""
        # Update playlist to match timeline
        self.current_playlist = [str(p) for p in file_paths]

        # Update playlist widget
        self.playlist_widget.clear()
        for path in self.current_playlist:
            item = QListWidgetItem(Path(path).name)
            self.playlist_widget.addItem(item)

        self.update_playlist_count()
        logger.info(f"Timeline changed: {len(file_paths)} items")
        self.log_event(f"🎞️ Timeline updated: {len(file_paths)} items")

    def play_timeline(self):
        """Play all videos in timeline sequentially."""
        if not self.timeline_widget.timeline_items:
            self.log_event("❌ Timeline is empty")
            QMessageBox.warning(self, "Warning", "Timeline is empty")
            return

        # Sync timeline to playlist and play
        self.current_playlist = [str(p) for p in self.timeline_widget.timeline_items]
        self.play_playlist()
        self.log_event(f"▶️ Playing timeline ({len(self.timeline_widget.timeline_items)} items)")

    def export_timeline_ffmpeg(self):
        """Export timeline as FFmpeg concatenation script."""
        if not self.timeline_widget.timeline_items:
            self.log_event("❌ Timeline is empty")
            QMessageBox.warning(self, "Warning", "Timeline is empty")
            return

        # Sync timeline to playlist and export
        self.current_playlist = [str(p) for p in self.timeline_widget.timeline_items]
        self.export_playlist_ffmpeg()
        self.log_event(f"📤 Exporting timeline ({len(self.timeline_widget.timeline_items)} items)")

    def clear_timeline(self):
        """Clear the timeline."""
        if not self.timeline_widget.timeline_items:
            return

        # Confirm before clearing
        reply = QMessageBox.question(
            self, "Confirm Clear",
            f"Clear all {len(self.timeline_widget.timeline_items)} items from timeline?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.timeline_widget.clear()
            self.log_event("🗑️ Timeline cleared")
            logger.info("Timeline cleared")

    def load_playlist_dialog(self):
        """Show dialog to load a saved playlist."""
        playlists = self.db.list_playlists()
        if not playlists:
            QMessageBox.information(self, "Info", "No saved playlists found")
            return

        # Create selection dialog
        items = [f"{p[0]} - {p[1] or 'No description'}" for p in playlists]
        item, ok = QInputDialog.getItem(self, "Load Playlist", "Select playlist:", items, 0, False)

        if ok and item:
            name = item.split(" - ")[0]
            playlist_data = self.db.get_playlist(name)

            if playlist_data:
                self.current_playlist = playlist_data['video_paths']

                # Update widget
                self.playlist_widget.clear()
                for video_path in self.current_playlist:
                    self.playlist_widget.addItem(Path(video_path).name)

                self.log_event(f"📂 Loaded playlist: {name} ({len(self.current_playlist)} videos)")
                QMessageBox.information(self, "Success", f"Loaded playlist '{name}'")

    def export_playlist_ffmpeg(self):
        """Export playlist as FFmpeg concatenation script."""
        if not self.current_playlist:
            QMessageBox.warning(self, "Warning", "Playlist is empty")
            return

        # Show dialog to customize export
        dialog = PlaylistExportDialog(self.current_playlist, self.db, self)
        dialog.exec_()

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
        """Create slideshow from selected images using FFmpeg (runs in background thread)."""
        if not self.images:
            self.log_event("❌ No images available")
            return

        # Check if any images are selected
        if not hasattr(self, 'selected_images') or not self.selected_images:
            self.log_event("❌ No images selected for slideshow")
            QMessageBox.warning(self, "Warning", "Please select at least one image for the slideshow.")
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

        # Make a copy of selected indices to avoid race conditions with background thread
        selected_indices = sorted(self.selected_images.copy())

        # Run in background thread to prevent UI lockup
        thread = threading.Thread(target=self._create_slideshow_worker, args=(ffmpeg_cmd, selected_indices), daemon=True)
        thread.start()

    def _create_slideshow_worker(self, ffmpeg_cmd, selected_indices):
        """Worker thread for slideshow creation."""
        # Generate output filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = OUTPUT_DIR / f"slideshow_{timestamp}.mp4"

        try:
            # Get selected items in order (indices passed from main thread to avoid race conditions)
            selected_items = [self.images[i] for i in selected_indices]

            self.log_event(f"🎬 Creating slideshow: {output_file.name}")
            self.log_event(f"📊 Processing {len(selected_items)} selected items...")

            # Create temporary directory with symlinks to numbered images
            temp_dir = Path(".slideshow_temp")
            temp_dir.mkdir(exist_ok=True)
            self.log_event(f"📁 Created temp directory")

            # Create numbered symlinks with .png extension for FFmpeg image2 demuxer
            # For videos, extract first frame; for images, create symlink
            item_count = 0
            for i, item_path in enumerate(selected_items):
                link_path = temp_dir / f"{i+1:04d}.png"
                if link_path.exists():
                    link_path.unlink()

                if item_path.suffix.lower() in VIDEO_FORMATS:
                    # Extract first frame from video
                    frame_path = self.extract_video_first_frame(item_path)
                    if frame_path:
                        link_path.symlink_to(Path(frame_path).resolve())
                        item_count += 1
                    else:
                        self.log_event(f"⚠️ Failed to extract frame from {item_path.name}")
                else:
                    # Regular image file
                    link_path.symlink_to(item_path.resolve())
                    item_count += 1

            self.log_event(f"🔗 Created {item_count} symlinks")

            # Replace output placeholder in command
            cmd = ffmpeg_cmd.replace('output.mp4', str(output_file))
            # Update input pattern to use temp directory
            cmd = cmd.replace('%04d.png', f'{temp_dir}/%04d.png')

            self.log_event(f"⚙️ Running FFmpeg command...")
            logger.debug(f"FFmpeg command: {cmd}")

            # Run FFmpeg command with real-time output capture
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait for process with timeout
            try:
                stdout, stderr = process.communicate(timeout=300)
                result_returncode = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                result_returncode = -1
                self.log_event("❌ FFmpeg command timed out (>300s)")
                raise subprocess.TimeoutExpired(cmd, 300)

            # Cleanup temp directory
            for file in temp_dir.glob("*"):
                file.unlink()
            temp_dir.rmdir()
            self.log_event(f"🧹 Cleaned up temporary directory")

            if result_returncode == 0:
                file_size = output_file.stat().st_size / (1024 * 1024)
                duration = len(selected_items) * 5  # 5 seconds per image
                self.log_event(f"✅ Slideshow created successfully!")
                self.log_event(f"📦 Size: {file_size:.1f} MB | Duration: ~{duration}s | Images: {len(selected_items)}")
                self.show_available_videos()
                logger.info(f"Slideshow created successfully: {output_file} ({file_size:.1f} MB)")
                QMessageBox.information(self, "Success",
                    f"✅ Slideshow created: {output_file.name}\nSize: {file_size:.1f} MB | Duration: ~{duration}s | Images: {len(selected_items)}")
            else:
                error_msg = stderr if stderr else "Unknown error"
                self.log_event(f"❌ FFmpeg error: {error_msg[:100]}")
                logger.error(f"FFmpeg error: {error_msg}")
                QMessageBox.critical(self, "FFmpeg Error", f"Error creating slideshow:\n{error_msg[:300]}")

        except subprocess.TimeoutExpired:
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

    def log_event(self, message):
        """Log an event to console."""
        logger.info(message)

    def closeEvent(self, event):
        """Handle window close event gracefully."""
        try:
            # Stop VLC player
            try:
                self.media_player.stop()
            except:
                pass

            # Stop background thumbnail loading thread
            self.stop_loading = True
            if self.thumbnail_loader_thread and self.thumbnail_loader_thread.is_alive():
                self.thumbnail_loader_thread.join(timeout=1)

            logger.info("Slideshow Manager closed gracefully")
            event.accept()
        except Exception as e:
            logger.error(f"Error during close: {e}")
            event.accept()

def main():
    app = QApplication(sys.argv)

    # Handle Ctrl-C gracefully
    import signal
    def signal_handler(sig, frame):
        logger.info("Received Ctrl-C, shutting down gracefully...")
        # Close any open dialogs first
        for widget in app.topLevelWidgets():
            if isinstance(widget, QDialog) and widget.isVisible():
                widget.close()
        app.quit()

    signal.signal(signal.SIGINT, signal_handler)

    # Allow Ctrl-C to interrupt even when dialogs are open
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(100)

    window = SlideshowManager()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

