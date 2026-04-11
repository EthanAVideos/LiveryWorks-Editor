"""
License Manager Addon
Checks and validates license keys on startup using hashed license list
"""

import os
import sys
import json
import hashlib
import urllib.request
import urllib.error
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

TOOL_NAME = "License Manager"
TOOL_DESCRIPTION = "Manages software license validation"

# GitHub raw URL where the hashed license list is stored
LICENSE_LIST_URL = "https://github.com/EthanAVideos/EthanA-Videos-Authentication/raw/refs/heads/main/l.txt"

class LicenseDialog(QDialog):
    """Dialog for entering license key"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("License Registration")
        self.setModal(True)
        self.setMinimumWidth(450)
        self.setMinimumHeight(200)
        self.license_valid = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Title
        title = QLabel("Software License Registration")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #4CAF50;")
        layout.addWidget(title)

        layout.addSpacing(10)

        # Info text
        info = QLabel("This software requires a valid license key to continue.\n"
                     "Please enter your license key below.")
        info.setWordWrap(True)
        layout.addWidget(info)

        label = QLabel()
        label.setText('<a href="https://forms.gle/FATbAUJWQdiyj69Q8">Request License Key</a>')
        label.setOpenExternalLinks(True)
        label.setWordWrap(True)
        layout.addWidget(label)

        layout.addSpacing(10)

        # License input
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("License Key:"))
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.license_input.setMinimumWidth(250)
        input_layout.addWidget(self.license_input)
        layout.addLayout(input_layout)

        layout.addSpacing(10)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #ff5555;")
        layout.addWidget(self.status_label)

        layout.addSpacing(10)

        # Buttons
        button_layout = QHBoxLayout()
        self.verify_btn = QPushButton("Verify & Register")
        self.verify_btn.clicked.connect(self.verify_license)
        self.verify_btn.setMinimumWidth(120)
        button_layout.addWidget(self.verify_btn)

        self.cancel_btn = QPushButton("Exit")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setMinimumWidth(80)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def hash_license(self, license_key):
        """Hash a license key using SHA-256"""
        # Normalize the license key: uppercase and remove any spaces
        normalized = license_key.strip().upper().replace(" ", "")
        # Create SHA-256 hash
        hash_obj = hashlib.sha256(normalized.encode())
        return hash_obj.hexdigest()

    def verify_license(self):
        """Verify the entered license key"""
        license_key = self.license_input.text().strip().upper()

        if not license_key:
            self.status_label.setText("Please enter a license key")
            return

        # Hash the entered key
        hashed_key = self.hash_license(license_key)

        # Show loading
        self.verify_btn.setEnabled(False)
        self.verify_btn.setText("Verifying...")
        self.status_label.setText("Checking license...")
        self.status_label.setStyleSheet("color: #ffcc00;")

        # Check in background thread
        self.checker = LicenseChecker(hashed_key)
        self.checker.finished.connect(self.on_verification_complete)
        self.checker.start()

    def on_verification_complete(self, is_valid):
        """Handle verification result"""
        self.verify_btn.setEnabled(True)
        self.verify_btn.setText("Verify & Register")

        if is_valid:
            self.status_label.setText("License valid! Registering...")
            self.status_label.setStyleSheet("color: #88ff88;")
            self.license_valid = True
            # Store the original key (not the hash)
            self.original_key = self.license_input.text().strip().upper()
            self.accept()
        else:
            self.status_label.setText("Invalid license key. Please check and try again.")
            self.status_label.setStyleSheet("color: #ff5555;")
            self.license_valid = False

    def get_license(self):
        """Return the entered license key"""
        return self.original_key if hasattr(self, 'original_key') else ""

class LicenseChecker(QThread):
    """Thread to check license validity without blocking UI"""

    finished = pyqtSignal(bool)

    def __init__(self, hashed_key):
        super().__init__()
        self.hashed_key = hashed_key

    def run(self):
        """Check hashed license against online list"""
        try:
            # Create request with timeout
            req = urllib.request.Request(LICENSE_LIST_URL)
            req.add_header('User-Agent', 'Mozilla/5.0')

            with urllib.request.urlopen(req, timeout=10) as response:
                data = response.read().decode('utf-8')
                # Load hashed licenses from file (one hash per line)
                valid_hashes = [line.strip() for line in data.split('\n')
                               if line.strip() and not line.startswith('#')]

                # Check if the hash is in the list
                is_valid = self.hashed_key in valid_hashes
                self.finished.emit(is_valid)

        except urllib.error.URLError as e:
            print(f"Network error checking license: {e}")
            # If can't reach server, fail closed (deny access)
            self.finished.emit(False)
        except Exception as e:
            print(f"Error checking license: {e}")
            self.finished.emit(False)

class LicenseManager:
    """Main license manager class"""

    def __init__(self):
        self.addons_folder = None
        self.data_file = None
        self.license_key = None

    def get_addons_folder(self):
        """Find the addons folder path"""
        # Try to find relative to current file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up to find addons folder
        for _ in range(5):
            if os.path.basename(current_dir) == "addons":
                return current_dir
            current_dir = os.path.dirname(current_dir)

        # Fallback: look for addons folder in current directory
        if os.path.exists(os.path.join(os.getcwd(), "addons")):
            return os.path.join(os.getcwd(), "addons")

        return None

    def hash_license(self, license_key):
        """Hash a license key using SHA-256"""
        normalized = license_key.strip().upper().replace(" ", "")
        hash_obj = hashlib.sha256(normalized.encode())
        return hash_obj.hexdigest()

    def load_license(self):
        """Load license from data.json"""
        self.addons_folder = self.get_addons_folder()
        if not self.addons_folder:
            return None

        self.data_file = os.path.join(self.addons_folder, "data.json")

        if not os.path.exists(self.data_file):
            return None

        try:
            with open(self.data_file, 'r') as f:
                config = json.load(f)

            # Check for license in addonSystem or root
            if "addonSystem" in config and "license" in config["addonSystem"]:
                return config["addonSystem"]["license"]
            elif "license" in config:
                return config["license"]
        except:
            pass

        return None

    def save_license(self, license_key):
        """Save license to data.json"""
        if not self.data_file or not os.path.exists(self.data_file):
            # Create data.json if it doesn't exist
            config = {}
        else:
            try:
                with open(self.data_file, 'r') as f:
                    config = json.load(f)
            except:
                config = {}

        # Ensure addonSystem exists
        if "addonSystem" not in config:
            config["addonSystem"] = {}

        # Save license (store the original key, not the hash)
        config["addonSystem"]["license"] = license_key

        # Save back to file
        try:
            with open(self.data_file, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving license: {e}")
            return False

    def check_license(self):
        """Check if license is valid, show dialog if not"""
        # Load existing license
        self.license_key = self.load_license()

        if self.license_key:
            # Hash the stored license
            hashed_key = self.hash_license(self.license_key)

            # Verify online
            dialog = QDialog()
            status_label = QLabel("Verifying license...")
            layout = QVBoxLayout()
            layout.addWidget(status_label)
            dialog.setLayout(layout)
            dialog.setModal(True)
            dialog.show()

            # Create checker thread
            checker = LicenseChecker(hashed_key)
            result = [False]

            def on_finished(is_valid):
                result[0] = is_valid
                dialog.accept()

            checker.finished.connect(on_finished)
            checker.start()

            # Wait for result
            dialog.exec_()

            if result[0]:
                print("License valid")
                return True
            else:
                print("License invalid, need new license")
                # License invalid, clear it and ask for new one
                self.license_key = None

        # No valid license, show registration dialog
        license_dialog = LicenseDialog()
        result = license_dialog.exec_()

        if result == QDialog.Accepted and license_dialog.license_valid:
            new_license = license_dialog.get_license()
            if self.save_license(new_license):
                print(f"License saved")
                return True

        return False

# Global instance
license_manager = None

def on_load():
    """Called when the addon is loaded"""
    global license_manager
    license_manager = LicenseManager()
    print("License Manager addon loaded")

def on_editor_start(editor):
    """Called when the editor starts - check license before anything else"""
    global license_manager

    if not license_manager:
        license_manager = LicenseManager()

    # Check license, exit if invalid
    if not license_manager.check_license():
        # Show error message and exit
        QMessageBox.critical(None, "License Error",
                            "Invalid or missing license key.\n\n"
                            "Please obtain a valid license to use this software.\n\n"
                            "The application will now exit.")
        sys.exit(1)

    print("License validated successfully")

def on_ui_ready(editor):
    """Called when UI is ready"""
    pass

print("License Manager module loaded")
