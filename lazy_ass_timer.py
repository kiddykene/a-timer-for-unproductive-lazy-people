import sys
import time
import json
import os
from datetime import timedelta
import keyboard
import win32gui
import win32process
import psutil
import threading
from pygame import mixer
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLCDNumber, QPushButton,
                           QVBoxLayout, QHBoxLayout, QWidget, QLabel,
                           QInputDialog, QSpinBox, QDialog, QFormLayout,
                           QDialogButtonBox, QFileDialog, QLineEdit, QColorDialog, QCheckBox)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QColor, QPalette

import kenenet
def get_focused_window_info():
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd: return None
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    process_name = psutil.Process(pid).name()
    return process_name


class SoundPlayer:
    
    def play_sound(self, sound_path, enable_sounds=True):
        try:
            if not enable_sounds:
                return
            kenenet.play_audio.play(sound_path,speed=(0.9,1.15))
            
        except Exception as e:
            print(f"Error playing sound: {e}")


class KeyboardMonitor(QObject):
    key_pressed = pyqtSignal()
    enter_pressed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.last_activity_time = time.time()
        self.running = False
        self.thread = None
    
    def start_monitoring(self):
        self.running = True
        self.thread = threading.Thread(target=self._monitor_keyboard, daemon=True)
        self.thread.start()
    
    def stop_monitoring(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
    
    def _monitor_keyboard(self):
        keyboard.on_press(self._on_key_press)
        while self.running:
            time.sleep(0.1)
    
    def _on_key_press(self, event):
        self.last_activity_time = time.time()
        self.key_pressed.emit()
        if event.name == 'enter':
            self.enter_pressed.emit()
    
    def get_idle_time(self):
        return time.time() - self.last_activity_time


class EditTimeDialog(QDialog):
    def __init__(self, hours, minutes, seconds, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Time")
        
        layout = QFormLayout(self)
        
        # Hours spinner
        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(0, 99)
        self.hours_spin.setValue(hours)
        layout.addRow("Hours:", self.hours_spin)
        
        # Minutes spinner
        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 59)
        self.minutes_spin.setValue(minutes)
        layout.addRow("Minutes:", self.minutes_spin)
        
        # Seconds spinner
        self.seconds_spin = QSpinBox()
        self.seconds_spin.setRange(0, 59)
        self.seconds_spin.setValue(seconds)
        layout.addRow("Seconds:", self.seconds_spin)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
    
    def get_time(self):
        return {
            'hours': self.hours_spin.value(),
            'minutes': self.minutes_spin.value(),
            'seconds': self.seconds_spin.value()
        }


class ColorButton(QPushButton):
    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 30)
        self.color = color
        self.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #000;")
    
    def set_color(self, color):
        self.color = color
        self.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #000;")


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(500, 400)
        
        self.settings = settings
        
        # Create form layout
        layout = QFormLayout(self)
        
        # Process name setting
        self.process_name = QLineEdit(self.settings['target_process_name'])
        layout.addRow("Target Process Name:", self.process_name)
        
        # Default timer setting
        self.timer_hours = QSpinBox()
        self.timer_hours.setRange(0, 24)
        self.timer_hours.setValue(self.settings['default_timer_seconds'] // 3600)
        layout.addRow("Default Time (hours):", self.timer_hours)
        
        # Add minutes setting
        self.timer_mins = QSpinBox()
        self.timer_mins.setRange(0, 59)  # Minutes should be 0-59
        self.timer_mins.setValue((self.settings['default_timer_seconds'] % 3600) // 60)  # Get remaining minutes
        layout.addRow("Default Time (minutes):", self.timer_mins)
        
        # Enter shortcut seconds
        self.shortcut_seconds = QSpinBox()
        self.shortcut_seconds.setRange(1, 300)
        self.shortcut_seconds.setValue(self.settings['enter_shortcut_seconds'])
        layout.addRow("Reward Button:", self.shortcut_seconds)
        
        # Idle timeout
        self.idle_minutes = QSpinBox()
        self.idle_minutes.setRange(1, 30)
        self.idle_minutes.setValue(self.settings['idle_timeout_seconds'] // 60)
        layout.addRow("Auto-pause when idle (minutes):", self.idle_minutes)
        
        # UI Color setting
        layout.addRow(QLabel("UI Color Settings:"))
        
        # Timer display color
        self.color_button = ColorButton(QColor(self.settings['display_color']))
        color_button_layout = QHBoxLayout()
        color_button_layout.addWidget(self.color_button)
        color_button_layout.addWidget(QLabel("Change color"))
        color_button_layout.addStretch()
        layout.addRow("Timer Display Color:", color_button_layout)
        
        # Connect color button click
        self.color_button.clicked.connect(self.choose_color)
        
        # Sound settings
        layout.addRow(QLabel("Sound Settings:"))
        
        # Enter key sound
        self.enable_sounds = QCheckBox("Enable Sound Effects")
        self.enable_sounds.setChecked(self.settings.get('enable_sounds', True))  # Default to enabled
        layout.addRow("", self.enable_sounds)  # Add to layout before the sound settings
        
        self.enter_sound_path = QLabel(self.settings['enter_sound_path'])
        enter_sound_button = QPushButton("Browse...")
        enter_sound_button.clicked.connect(self.browse_enter_sound)
        
        enter_sound_layout = QHBoxLayout()
        enter_sound_layout.addWidget(self.enter_sound_path)
        enter_sound_layout.addWidget(enter_sound_button)
        layout.addRow("Reward Key Sound:", enter_sound_layout)
        
        # Idle timeout sound
        self.idle_sound_path = QLabel(self.settings['idle_sound_path'])
        idle_sound_button = QPushButton("Browse...")
        idle_sound_button.clicked.connect(self.browse_idle_sound)
        
        idle_sound_layout = QHBoxLayout()
        idle_sound_layout.addWidget(self.idle_sound_path)
        idle_sound_layout.addWidget(idle_sound_button)
        layout.addRow("Idle Timeout Sound:", idle_sound_layout)
        
        # Time up sound
        self.time_up_sound_path = QLabel(self.settings['time_up_sound_path'])
        time_up_sound_button = QPushButton("Browse...")
        time_up_sound_button.clicked.connect(self.browse_time_up_sound)
        
        time_up_sound_layout = QHBoxLayout()
        time_up_sound_layout.addWidget(self.time_up_sound_path)
        time_up_sound_layout.addWidget(time_up_sound_button)
        layout.addRow("Time's Up Sound:", time_up_sound_layout)
        
        # Save button
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
    
    def choose_color(self):
        color = QColorDialog.getColor(self.color_button.color, self, "Choose Timer Display Color")
        if color.isValid():
            self.color_button.set_color(color)
    
    def browse_enter_sound(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Enter Key Sound", "", "Audio Files (*.mp3 *.wav)")
        if file_path:
            self.enter_sound_path.setText(file_path)
    
    def browse_idle_sound(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Idle Timeout Sound", "", "Audio Files (*.mp3 *.wav)")
        if file_path:
            self.idle_sound_path.setText(file_path)
    
    def browse_time_up_sound(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Time's Up Sound", "", "Audio Files (*.mp3 *.wav)")
        if file_path:
            self.time_up_sound_path.setText(file_path)
    
    def get_settings(self):
        return {
            'target_process_name': self.process_name.text(),
            'default_timer_seconds': (self.timer_hours.value() * 3600) + (self.timer_mins.value() * 60),
            'enter_shortcut_seconds': self.shortcut_seconds.value(),
            'idle_timeout_seconds': self.idle_minutes.value() * 60,
            'display_color': self.color_button.color.name(),
            'enable_sounds': self.enable_sounds.isChecked(),
            'enter_sound_path': self.enter_sound_path.text(),
            'idle_sound_path': self.idle_sound_path.text(),
            'time_up_sound_path': self.time_up_sound_path.text()
        }


class TimerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Default settings
        self.default_settings = {
            'target_process_name': 'pycharm64.exe',
            'default_timer_seconds': 3 * 60 * 60,  # 3 hours
            'enter_shortcut_seconds': 20,  # 20 seconds
            'idle_timeout_seconds': 3 * 60,  # 3 minutes
            'enable_sounds': True,
            'display_color': '#0078d7',  # Default blue color
            'enter_sound_path': r"assets\pop noise.mp3",
            'idle_sound_path': r"assets\id rather be fat and ugly.mp3",
            'time_up_sound_path': r"assets\yt5s.com - FNAF - 6 AM sound (128 kbps).mp3"
        }
        
        # Load settings from file
        self.settings_file = os.path.join(os.path.expanduser("~"), "pycharm_timer_settings.json")
        self.settings = self.load_settings()
        
        # Sound player
        self.sound_player = SoundPlayer()
        
        # Timer state
        self.time_left = self.settings['default_timer_seconds']
        self.timer_running = False
        self.is_target_focused = False
        
        # Keyboard monitor
        self.keyboard_monitor = KeyboardMonitor()
        self.keyboard_monitor.enter_pressed.connect(self.on_enter_pressed)
        self.keyboard_monitor.start_monitoring()
        
        # Window focus checker
        self.focus_timer = QTimer(self)
        self.focus_timer.timeout.connect(self.check_target_focus)
        self.focus_timer.start(1000)  # Check every second
        
        # Idle checker
        self.idle_timer_reset = 0
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self.check_idle)
        self.idle_timer.start(5000)  # Check every 5 seconds
        
        # Main timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        
        self.init_ui()
    
    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                # Make sure all default settings exist, add any missing ones
                for key, value in self.default_settings.items():
                    if key not in loaded_settings:
                        loaded_settings[key] = value
                return loaded_settings
            else:
                return self.default_settings.copy()
        except Exception as e:
            print(f"Error loading settings: {e}")
            return self.default_settings.copy()
    
    def save_settings(self):
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def init_ui(self):
        self.setWindowTitle('Process Time Tracker')
        self.setGeometry(100, 100, 500, 300)
        
        # Set up the central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Status label
        self.status_label = QLabel(f"{self.settings['target_process_name']} isn't focused")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont('Arial', 12))
        main_layout.addWidget(self.status_label)
        
        # Timer display
        self.time_display = QLCDNumber()
        self.time_display.setDigitCount(8)  # HH:MM:SS
        self.time_display.setSegmentStyle(QLCDNumber.Filled)
        
        # Set display color based on settings
        self.update_display_color()
        
        self.time_display.setMinimumHeight(100)
        main_layout.addWidget(self.time_display)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Start/Pause button
        self.start_pause_button = QPushButton("Start")
        self.start_pause_button.clicked.connect(self.toggle_timer)
        button_layout.addWidget(self.start_pause_button)
        
        # Reset button
        reset_button = QPushButton("Reset")
        reset_button.clicked.connect(self.reset_timer)
        button_layout.addWidget(reset_button)
        
        # Edit time button
        edit_button = QPushButton("Edit Time")
        edit_button.clicked.connect(self.edit_time)
        button_layout.addWidget(edit_button)
        
        # Settings button
        settings_button = QPushButton("Settings")
        settings_button.clicked.connect(self.open_settings)
        button_layout.addWidget(settings_button)
        
        main_layout.addLayout(button_layout)
        
        # Add keyboard shortcut information
        shortcut_label = QLabel(f"Press Enter to subtract {self.settings['enter_shortcut_seconds']} seconds")
        shortcut_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(shortcut_label)
        
        # Update the display initially
        self.update_display()
    
    def update_display_color(self):
        # Set color based on settings
        color = QColor(self.settings['display_color'])
        palette = self.time_display.palette()
        palette.setColor(palette.WindowText, color)
        palette.setColor(palette.Light, color)
        palette.setColor(palette.Dark, color)
        self.time_display.setPalette(palette)
    
    def update_display(self):
        hours, remainder = divmod(self.time_left, 3600)
        minutes, seconds = divmod(remainder, 60)
        time_str = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
        self.time_display.display(time_str)
    
    def toggle_timer(self):
        if self.timer_running:
            self.timer.stop()
            self.timer_running = False
            self.start_pause_button.setText("Start")
            self.status_label.setText("Timer paused")
        else:
            self.timer.start(1000)
            self.timer_running = True
            self.start_pause_button.setText("Pause")
            if self.is_target_focused:
                self.status_label.setText(f"Timing {self.settings['target_process_name']} usage")
            else:
                self.status_label.setText(f"{self.settings['target_process_name']} not in focus - Timer paused")
    
    def reset_timer(self):
        self.time_left = self.settings['default_timer_seconds']
        self.update_display()
        if not self.timer_running:
            self.status_label.setText("Timer reset")
    
    def edit_time(self):
        was_running = self.timer_running
        if was_running:
            self.toggle_timer()  # Pause the timer
        
        # Convert current time to hours, minutes, seconds for easier editing
        hours = int(self.time_left // 3600)
        minutes = int((self.time_left % 3600) // 60)
        seconds = int(self.time_left % 60)
        
        # Open the edit time dialog
        dialog = EditTimeDialog(hours, minutes, seconds, self)
        if dialog.exec_():
            time_values = dialog.get_time()
            self.time_left = (time_values['hours'] * 3600 +
                              time_values['minutes'] * 60 +
                              time_values['seconds'])
            self.update_display()
        
        if was_running:
            self.toggle_timer()  # Resume the timer
    
    def open_settings(self):
        dialog = SettingsDialog(self.settings, self)
        
        # Set color from settings
        dialog.color_button.set_color(QColor(self.settings['display_color']))
        
        if dialog.exec_():
            old_settings = self.settings.copy()
            self.settings = dialog.get_settings()
            
            # Update display color if changed
            if old_settings['display_color'] != self.settings['display_color']:
                self.update_display_color()
            
            # Update the process name in status label if changed
            if old_settings['target_process_name'] != self.settings['target_process_name']:
                self.status_label.setText(f"Waiting for {self.settings['target_process_name']} to be focused")
            
            # Update the shortcut label if the shortcut seconds changed
            if old_settings['enter_shortcut_seconds'] != self.settings['enter_shortcut_seconds']:
                for i in range(self.centralWidget().layout().count()):
                    widget = self.centralWidget().layout().itemAt(i).widget()
                    if isinstance(widget, QLabel) and "Press Enter" in widget.text():
                        widget.setText(f"Press Enter to subtract {self.settings['enter_shortcut_seconds']} seconds")
                        break
            
            # Save settings to file
            self.save_settings()
    
    def update_timer(self):
        if self.timer_running and self.is_target_focused:
            self.time_left = max(0, self.time_left - 1)
            self.update_display()
            
            if self.time_left <= 0:
                self.timer.stop()
                self.timer_running = False
                self.start_pause_button.setText("Start")
                self.status_label.setText("Time's up!")
                self.toggle_timer()
                self.sound_player.play_sound(self.settings['time_up_sound_path'])
    
    def check_target_focus(self):
        process_name = get_focused_window_info()
        
        # Check if target process is the focused window
        self.is_target_focused = process_name == self.settings['target_process_name']
        
        # Calculate percentage complete
        total_time = self.settings['default_timer_seconds']
        time_elapsed = total_time - self.time_left
        percentage_complete = (time_elapsed / total_time) * 100 if total_time > 0 else 0
        
        if self.timer_running:
            if self.is_target_focused:
                self.status_label.setText(f"Timing {self.settings['target_process_name']} usage, {percentage_complete:.1f}% complete")
            else:
                self.status_label.setText(f"{self.settings['target_process_name']} not focused - Timer paused, {percentage_complete:.1f}% complete")
    
    def check_idle(self):
        idle_time = self.keyboard_monitor.get_idle_time()
        process_name = get_focused_window_info()
        if idle_time > self.settings['idle_timeout_seconds'] and self.idle_timer_reset < time.time() and process_name != self.settings['target_process_name']:
            # Play idle sound regardless of timer state or target process focus
            self.sound_player.play_sound(
                self.settings['idle_sound_path'],
                self.settings.get('enable_sounds', True)  # Default to enabled if setting doesn't exist
            )
            self.idle_timer_reset = time.time() + 600
            # If timer is running, auto-pause it
            if self.timer_running:
                self.toggle_timer()  # Auto-pause
                self.status_label.setText(f"Auto-paused after {self.settings['idle_timeout_seconds'] // 60} minutes of inactivity")
        else:
            if not self.timer_running:
                self.toggle_timer()  # Auto-pause
                self.status_label.setText(f"Auto-paused after {self.settings['idle_timeout_seconds'] // 60} minutes of inactivity")
    
    def on_enter_pressed(self):
        process_name = get_focused_window_info()
        if process_name == self.settings['target_process_name'] and self.timer_running:
            self.time_left = max(0, self.time_left - self.settings['enter_shortcut_seconds'])
            self.update_display()
            self.status_label.setText(f"Subtracted {self.settings['enter_shortcut_seconds']} seconds")
            
            # Play enter sound if PyCharm is focused and sounds are enabled
            self.sound_player.play_sound(
                self.settings['enter_sound_path'],
                self.settings.get('enable_sounds', True)  # Default to enabled if setting doesn't exist
            )
            
            # Reset temporary message after 2 seconds
            QTimer.singleShot(2000, self.restore_status_message)
    
    def restore_status_message(self):
        if self.timer_running:
            if self.is_target_focused:
                self.status_label.setText(f"Timing {self.settings['target_process_name']} usage")
            else:
                self.status_label.setText(f"{self.settings['target_process_name']} not in focus - Timer paused")
        else:
            self.status_label.setText("Timer paused")
    
    def closeEvent(self, event):
        # Save settings before closing
        self.save_settings()
        self.keyboard_monitor.stop_monitoring()
        mixer.quit()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for a modern look
    
    # Set application-wide dark palette
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(dark_palette)
    
    window = TimerWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()