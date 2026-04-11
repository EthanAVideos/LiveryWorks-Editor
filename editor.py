import sys
import numpy as np
import json
import importlib
import traceback
import hashlib
from PIL import Image, ImageDraw, ImageFilter
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# Try to import OpenGL widgets - handle different PyQt versions
try:
    from PyQt5.QtOpenGL import QGLWidget
except ImportError:
    # For newer PyQt5 versions
    from PyQt5.QtWidgets import QOpenGLWidget as QGLWidget

from OpenGL.GL import *
from OpenGL.GLU import *
import trimesh
import os
import math
from pathlib import Path

# Addon Manager
class AddonManager:
    def __init__(self, app_path):
        self.app_path = app_path
        self.addons_folder = os.path.join(app_path, "addons")
        self.addons = {}
        self.enabled_addons = []
        self.load_addons()

    def load_addons(self):
        """Load all addons from the addons folder"""
        if not os.path.exists(self.addons_folder):
            os.makedirs(self.addons_folder)
            print(f"Created addons folder: {self.addons_folder}")
            return

        # Check for data.json
        data_file = os.path.join(self.addons_folder, "data.json")
        if not os.path.exists(data_file):
            print("No data.json found in addons folder")
            return

        try:
            with open(data_file, 'r') as f:
                config = json.load(f)

            # Check addon system settings
            addon_system = config.get("addonSystem", {})
            check_for_addons = addon_system.get("checkForAddons", "true") == "true"
            load_addons = addon_system.get("loadAddons", "true") == "true"

            if not check_for_addons or not load_addons:
                print("Addon loading disabled in config")
                return

            # Load each addon
            for addon_name, addon_config in config.items():
                if addon_name == "addonSystem":
                    continue

                enabled = addon_config.get("enabled", "false") == "true"
                if not enabled:
                    print(f"Addon {addon_name} is disabled")
                    continue

                addon_file = addon_config.get("addonFile")
                if not addon_file:
                    print(f"No addonFile specified for {addon_name}")
                    continue

                # Load the addon module
                try:
                    addon_path = os.path.join(self.addons_folder, addon_file)
                    if not os.path.exists(addon_path):
                        print(f"Addon file not found: {addon_path}")
                        continue

                    # Add addons folder to path
                    sys.path.insert(0, self.addons_folder)

                    # Import the addon module
                    module_name = addon_file.replace("/", ".").replace(".py", "")
                    addon_module = importlib.import_module(module_name)

                    # Store addon info
                    self.addons[addon_name] = {
                        'module': addon_module,
                        'config': addon_config,
                        'enabled': True
                    }
                    self.enabled_addons.append(addon_name)
                    print(f"Loaded addon: {addon_name} v{addon_config.get('version', 'unknown')}")

                except Exception as e:
                    print(f"Error loading addon {addon_name}: {e}")
                    traceback.print_exc()

        except Exception as e:
            print(f"Error reading addons data.json: {e}")

    def get_addon(self, name):
        """Get a loaded addon by name"""
        return self.addons.get(name)

    def get_all_addons(self):
        """Get all loaded addons"""
        return self.addons

    def get_enabled_addons(self):
        """Get list of enabled addon names"""
        return self.enabled_addons

    def call_addon_method(self, addon_name, method_name, *args, **kwargs):
        """Call a method on an addon if it exists"""
        addon = self.get_addon(addon_name)
        if addon and hasattr(addon['module'], method_name):
            try:
                return getattr(addon['module'], method_name)(*args, **kwargs)
            except Exception as e:
                print(f"Error calling {method_name} on {addon_name}: {e}")
                return None
        return None

    def call_all_addons(self, method_name, *args, **kwargs):
        """Call a method on all enabled addons"""
        results = []
        for addon_name in self.enabled_addons:
            result = self.call_addon_method(addon_name, method_name, *args, **kwargs)
            if result is not None:
                results.append(result)
        return results

# Model UV Settings Manager
class ModelUVSettings:
    def __init__(self):
        self.settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_uv_settings.json")
        self.settings = {}
        self.load_settings()

    def get_model_hash(self, model_path):
        """Generate a unique hash for the model based on file path and modification time"""
        if not os.path.exists(model_path):
            return None
        # Use file path and last modified time to create a unique identifier
        stat = os.stat(model_path)
        hash_str = f"{model_path}_{stat.st_size}_{stat.st_mtime}"
        return hashlib.md5(hash_str.encode()).hexdigest()

    def load_settings(self):
        """Load saved UV settings from file"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    self.settings = json.load(f)
            except:
                self.settings = {}

    def save_settings(self):
        """Save UV settings to file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving UV settings: {e}")

    def get_model_settings(self, model_path):
        """Get UV settings for a specific model"""
        model_hash = self.get_model_hash(model_path)
        if model_hash and model_hash in self.settings:
            return self.settings[model_hash]
        return {"uv_flip_u": False, "uv_flip_v": False, "uv_swap_uv": False}

    def save_model_settings(self, model_path, flip_u, flip_v, swap_uv):
        """Save UV settings for a specific model"""
        model_hash = self.get_model_hash(model_path)
        if model_hash:
            self.settings[model_hash] = {
                "uv_flip_u": flip_u,
                "uv_flip_v": flip_v,
                "uv_swap_uv": swap_uv,
                "model_path": model_path
            }
            self.save_settings()

# Welcome Dialog
class WelcomeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to LiveryWorks Editor")
        self.setModal(True)
        self.setMinimumWidth(550)
        self.setMinimumHeight(500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Title
        title = QLabel("Welcome to LiveryWorks 1.4.7")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #4CAF50;")
        layout.addWidget(title)

        layout.addSpacing(10)

        # Instructions text - this will be modified by addons
        self.instructions = QTextEdit()
        self.instructions.setReadOnly(True)
        self.instructions.setMaximumHeight(400)
        self.set_base_instructions()
        self.instructions.setStyleSheet("background-color: #353535; color: #ffffff;")
        layout.addWidget(self.instructions)

        layout.addSpacing(10)

        # Don't show again checkbox
        checkbox_layout = QHBoxLayout()
        self.dont_show_checkbox = QCheckBox("Don't show this message again")
        self.dont_show_checkbox.setChecked(False)
        checkbox_layout.addWidget(self.dont_show_checkbox)
        checkbox_layout.addStretch()
        layout.addLayout(checkbox_layout)

        layout.addSpacing(10)

        # Close button
        button_layout = QHBoxLayout()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setMinimumWidth(100)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def set_base_instructions(self):
        """Set the base instructions"""
        self.instructions.setHtml("""
        <h3>Getting Started:</h3>
        <ul>
            <li><b>Load a Model:</b> File → Load Model (supports OBJ, STL, PLY, GLB, GLTF)</li>
            <li><b>Load a Texture:</b> If using OBJ, you'll be prompted to load a texture</li>
            <li><b>Load Logos:</b> Click "Load Logo" button and select PNG/JPG images</li>
            <li><b>Select a Logo:</b> Click on logo in the Logos tree view</li>
        </ul>

        <h3>Logo Controls:</h3>
        <ul>
            <li><b>Size:</b> Adjust width and height in world units</li>
            <li><b>2D Spin:</b> Rotates the logo on the texture (affects export)</li>
            <li><b>Tilt X/Y:</b> Visual-only 3D tilt for placement on curved surfaces (does NOT affect export)</li>
            <li><b>Flip:</b> Mirror the logo horizontally or vertically</li>
        </ul>

        <h3>Placing Logos:</h3>
        <ul>
            <li><b>Quick Place:</b> Enter Movement Mode, then click on model surface</li>
            <li><b>Precise Move:</b> Select logo, then drag colored arrows (Red=X, Green=Y, Blue=Z)</li>
            <li><b>Camera Control:</b> Click and drag to rotate view, scroll to zoom</li>
        </ul>

        <h3>UV Orientation (Important for correct placement):</h3>
        <ul>
            <li><b>Flip U/Horizontal:</b> Mirrors logos left/right on texture</li>
            <li><b>Flip V/Vertical:</b> Mirrors logos up/down on texture</li>
            <li><b>Swap U/V:</b> Swaps U and V coordinates</li>
            <li><b>Settings are saved per model</b> - Once calibrated, it remembers!</li>
        </ul>

        <h3>Export:</h3>
        <ul>
            <li>Click "Export Model with Logos" to create a new texture with logos overlaid</li>
            <li>The original model and texture remain untouched</li>
            <li>What you see in the editor is exactly what you get on export!</li>
        </ul>

        <p style="color: #4CAF50;"><b>Tip:</b> Use Tilt X/Y to align logos on curved surfaces without affecting the final texture!</p>

        <p style="color: #888; font-size: 10px;"><b>Note:</b> Additional addon instructions may appear below.</p>
        """)

    def add_instructions(self, instructions_html):
        """Add additional instructions (used by addons)"""
        current_html = self.instructions.toHtml()
        insert_pos = current_html.find('</body>')
        if insert_pos != -1:
            new_html = current_html[:insert_pos] + instructions_html + current_html[insert_pos:]
            self.instructions.setHtml(new_html)

    def should_show(self):
        settings = QSettings("LiveryWorks", "Editor")
        return settings.value("show_welcome", True, type=bool)

    def save_preference(self):
        settings = QSettings("LiveryWorks", "Editor")
        settings.setValue("show_welcome", not self.dont_show_checkbox.isChecked())

# Movement Gizmo
class MovementGizmo:
    def __init__(self):
        self.active_axis = None
        self.start_position = None
        self.start_mouse_pos = None
        self.color_x = (1.0, 0.2, 0.2, 0.9)
        self.color_y = (0.2, 1.0, 0.2, 0.9)
        self.color_z = (0.2, 0.2, 1.0, 0.9)
        self.hover_color = (1.0, 1.0, 0.2, 1.0)
        self.hover_axis = None

    def draw(self, logo_position, model_scale):
        """Draw movement gizmo with thick arrows"""
        glDisable(GL_LIGHTING)
        glDisable(GL_TEXTURE_2D)
        glLineWidth(5.0)

        gizmo_size = model_scale * 0.25

        # Draw X axis (red)
        if self.hover_axis == 'x':
            glColor4f(*self.hover_color)
        else:
            glColor4f(*self.color_x)
        glBegin(GL_LINES)
        glVertex3f(logo_position[0], logo_position[1], logo_position[2])
        glVertex3f(logo_position[0] + gizmo_size, logo_position[1], logo_position[2])
        glEnd()

        # Draw X arrow head
        glPushMatrix()
        glTranslatef(logo_position[0] + gizmo_size, logo_position[1], logo_position[2])
        glRotatef(90, 0, 1, 0)
        self.draw_arrow_head()
        glPopMatrix()

        # Draw Y axis (green)
        if self.hover_axis == 'y':
            glColor4f(*self.hover_color)
        else:
            glColor4f(*self.color_y)
        glBegin(GL_LINES)
        glVertex3f(logo_position[0], logo_position[1], logo_position[2])
        glVertex3f(logo_position[0], logo_position[1] + gizmo_size, logo_position[2])
        glEnd()

        # Draw Y arrow head
        glPushMatrix()
        glTranslatef(logo_position[0], logo_position[1] + gizmo_size, logo_position[2])
        glRotatef(-90, 1, 0, 0)
        self.draw_arrow_head()
        glPopMatrix()

        # Draw Z axis (blue)
        if self.hover_axis == 'z':
            glColor4f(*self.hover_color)
        else:
            glColor4f(*self.color_z)
        glBegin(GL_LINES)
        glVertex3f(logo_position[0], logo_position[1], logo_position[2])
        glVertex3f(logo_position[0], logo_position[1], logo_position[2] + gizmo_size)
        glEnd()

        # Draw Z arrow head
        glPushMatrix()
        glTranslatef(logo_position[0], logo_position[1], logo_position[2] + gizmo_size)
        self.draw_arrow_head()
        glPopMatrix()

        glEnable(GL_LIGHTING)
        glEnable(GL_TEXTURE_2D)

    def draw_arrow_head(self):
        """Draw a large arrow head"""
        size = 0.04
        glBegin(GL_TRIANGLES)
        glVertex3f(0, 0, 0)
        glVertex3f(-size, -size, size)
        glVertex3f(size, -size, size)

        glVertex3f(0, 0, 0)
        glVertex3f(size, -size, size)
        glVertex3f(size, size, size)

        glVertex3f(0, 0, 0)
        glVertex3f(size, size, size)
        glVertex3f(-size, size, size)

        glVertex3f(0, 0, 0)
        glVertex3f(-size, size, size)
        glVertex3f(-size, -size, size)
        glEnd()

    def check_hover(self, mouse_ray_origin, mouse_ray_direction, logo_position, model_scale):
        """Check which axis the mouse is hovering over"""
        gizmo_size = model_scale * 0.25
        epsilon = 0.1

        # Check X axis
        x_end = np.array([logo_position[0] + gizmo_size, logo_position[1], logo_position[2]])
        hit = self.ray_cylinder_intersection(mouse_ray_origin, mouse_ray_direction,
                                              np.array(logo_position), x_end, epsilon)
        if hit:
            self.hover_axis = 'x'
            return 'x'

        # Check Y axis
        y_end = np.array([logo_position[0], logo_position[1] + gizmo_size, logo_position[2]])
        hit = self.ray_cylinder_intersection(mouse_ray_origin, mouse_ray_direction,
                                              np.array(logo_position), y_end, epsilon)
        if hit:
            self.hover_axis = 'y'
            return 'y'

        # Check Z axis
        z_end = np.array([logo_position[0], logo_position[1], logo_position[2] + gizmo_size])
        hit = self.ray_cylinder_intersection(mouse_ray_origin, mouse_ray_direction,
                                              np.array(logo_position), z_end, epsilon)
        if hit:
            self.hover_axis = 'z'
            return 'z'

        self.hover_axis = None
        return None

    def ray_cylinder_intersection(self, ray_origin, ray_dir, start, end, radius):
        """Check if ray intersects a cylinder"""
        cylinder_dir = end - start
        cylinder_len = np.linalg.norm(cylinder_dir)
        if cylinder_len < 0.001:
            return False
        cylinder_dir = cylinder_dir / cylinder_len

        # Find closest point on ray to cylinder axis
        ray_to_start = ray_origin - start
        t_parallel = np.dot(ray_to_start, cylinder_dir)
        t_closest = max(0, min(cylinder_len, t_parallel))

        closest_point_on_axis = start + cylinder_dir * t_closest

        # Project ray onto plane perpendicular to axis
        ray_dir_perp = ray_dir - np.dot(ray_dir, cylinder_dir) * cylinder_dir
        ray_to_axis = ray_origin - closest_point_on_axis
        ray_to_axis_perp = ray_to_axis - np.dot(ray_to_axis, cylinder_dir) * cylinder_dir

        # Solve for intersection
        a = np.dot(ray_dir_perp, ray_dir_perp)
        b = 2 * np.dot(ray_dir_perp, ray_to_axis_perp)
        c = np.dot(ray_to_axis_perp, ray_to_axis_perp) - radius * radius

        discriminant = b*b - 4*a*c
        if discriminant < 0:
            return False

        t = (-b - np.sqrt(discriminant)) / (2*a)
        if t < 0:
            t = (-b + np.sqrt(discriminant)) / (2*a)
            if t < 0:
                return False

        # Check if intersection point is within cylinder length
        intersection_point = ray_origin + ray_dir * t
        t_on_axis = np.dot(intersection_point - start, cylinder_dir)
        return 0 <= t_on_axis <= cylinder_len

class Logo:
    def __init__(self, image_path, position=(0,0,0), width=0.2, height=0.2,
                 rotation_z=0, tilt_x=0, tilt_y=0):
        self.image_path = image_path
        self.position = position
        self.width = width
        self.height = height
        self.rotation_z = rotation_z  # 2D spin - affects export
        self.tilt_x = tilt_x          # Visual only - does NOT affect export
        self.tilt_y = tilt_y          # Visual only - does NOT affect export
        self.flipped_x = False
        self.flipped_y = False
        self.texture_id = None
        self.selected = False
        self.uv_position = (0.5, 0.5)
        self.original_image = None

    def load_texture(self):
        """Load logo image as OpenGL texture"""
        try:
            self.original_image = Image.open(self.image_path)
            if self.original_image.mode != 'RGBA':
                self.original_image = self.original_image.convert('RGBA')

            img = self.original_image.copy()

            # Apply flips to the image for display
            if self.flipped_x:
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            if self.flipped_y:
                img = img.transpose(Image.FLIP_TOP_BOTTOM)

            img_data = img.tobytes('raw', 'RGBA')

            texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture_id)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.width, img.height,
                        0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glGenerateMipmap(GL_TEXTURE_2D)

            return texture_id
        except Exception as e:
            print(f"Error loading logo: {e}")
            return None

class ModelData:
    def __init__(self):
        self.vertices = []
        self.faces = []
        self.uvs = []
        self.normals = []
        self.texture_path = None
        self.texture_id = None
        self.display_list = None
        self.bounding_box = None
        self.center = np.array([0, 0, 0])
        self.face_centers = []
        self.face_normals = []
        self.face_uv_centers = []
        self.model_scale = 1.0
        self.model_path = None
        # UV orientation settings
        self.uv_flip_u = False
        self.uv_flip_v = False
        self.uv_swap_uv = False

    def calculate_bounding_box(self):
        """Calculate the bounding box of the model"""
        if not self.vertices:
            return None
        vertices_array = np.array(self.vertices)
        self.bounding_box = {
            'min': vertices_array.min(axis=0),
            'max': vertices_array.max(axis=0)
        }
        self.center = (self.bounding_box['min'] + self.bounding_box['max']) / 2
        model_size = self.bounding_box['max'] - self.bounding_box['min']
        self.model_scale = max(model_size)
        return self.bounding_box

    def calculate_face_centers_and_normals(self):
        """Calculate center and normal of each face"""
        self.face_centers = []
        self.face_normals = []
        self.face_uv_centers = []

        for face in self.faces:
            v0 = np.array(self.vertices[face[0]])
            v1 = np.array(self.vertices[face[1]])
            v2 = np.array(self.vertices[face[2]])

            center_3d = np.mean([v0, v1, v2], axis=0)
            self.face_centers.append(center_3d)

            normal = np.cross(v1 - v0, v2 - v0)
            normal = normal / (np.linalg.norm(normal) + 1e-8)
            self.face_normals.append(normal)

            if self.uvs:
                face_uvs = [self.uvs[idx] for idx in face if idx < len(self.uvs)]
                if face_uvs:
                    center_uv = np.mean(face_uvs, axis=0)
                    self.face_uv_centers.append(center_uv)
                else:
                    self.face_uv_centers.append(np.array([0.5, 0.5]))
            else:
                self.face_uv_centers.append(np.array([0.5, 0.5]))

        return self.face_centers

    def apply_uv_orientation(self, u, v):
        """Apply UV orientation settings to raw UV coordinates"""
        # Apply swap first
        if self.uv_swap_uv:
            u, v = v, u
        # Apply flips
        if self.uv_flip_u:
            u = 1.0 - u
        if self.uv_flip_v:
            v = 1.0 - v
        return u, v

    def get_uv_from_3d_point(self, point_3d):
        """Get UV coordinates from 3D point with orientation applied"""
        if not self.faces or not self.uvs:
            return (0.5, 0.5)

        closest_distance = float('inf')
        closest_uv = (0.5, 0.5)

        for i, face_center in enumerate(self.face_centers):
            distance = np.linalg.norm(np.array(point_3d) - face_center)
            if distance < closest_distance:
                closest_distance = distance
                if i < len(self.face_uv_centers):
                    raw_uv = self.face_uv_centers[i]
                    # Apply orientation to raw UV before returning
                    closest_uv = self.apply_uv_orientation(raw_uv[0], raw_uv[1])

        return closest_uv

class GLWidget(QGLWidget):
    def __init__(self, parent=None):
        super(GLWidget, self).__init__(parent)
        self.model_data = None
        self.logos = []
        self.rotation_x = 30
        self.rotation_y = 45
        self.zoom = -5
        self.last_pos = QPoint()
        self.movement_mode = False
        self.selected_logo = None
        self.show_grid = True
        self.light_position = [2.0, 3.0, 4.0, 1.0]
        self.main_window = parent
        self.movement_gizmo = MovementGizmo()
        self.gizmo_active = False

    def initializeGL(self):
        glClearColor(0.1, 0.1, 0.1, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glShadeModel(GL_SMOOTH)

        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_LIGHT1)

        glLightfv(GL_LIGHT0, GL_POSITION, [2.0, 3.0, 2.0, 0.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.4, 0.4, 0.4, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])

        glLightfv(GL_LIGHT1, GL_POSITION, [0.0, -1.0, 0.0, 0.0])
        glLightfv(GL_LIGHT1, GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
        glLightfv(GL_LIGHT1, GL_DIFFUSE, [0.5, 0.5, 0.5, 1.0])

        glMaterialfv(GL_FRONT, GL_AMBIENT, [0.6, 0.6, 0.6, 1.0])
        glMaterialfv(GL_FRONT, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.3, 0.3, 0.3, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 20.0)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, w / h if h > 0 else 1, 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(0, 0, self.zoom)
        glRotatef(self.rotation_x, 1, 0, 0)
        glRotatef(self.rotation_y, 0, 1, 0)

        glLightfv(GL_LIGHT0, GL_POSITION, self.light_position)

        if self.show_grid:
            self.draw_grid()

        if self.model_data and self.model_data.display_list:
            glEnable(GL_LIGHTING)
            if self.model_data.texture_id:
                glBindTexture(GL_TEXTURE_2D, self.model_data.texture_id)
            glCallList(self.model_data.display_list)

        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)

        for logo in self.logos:
            if logo.texture_id:
                self.draw_logo_with_texture(logo)

        # Draw movement gizmo for selected logo
        if self.selected_logo and self.model_data and not self.movement_mode:
            self.movement_gizmo.draw(self.selected_logo.position, self.model_data.model_scale)

        glDisable(GL_BLEND)

    def draw_grid(self):
        glDisable(GL_LIGHTING)
        glColor3f(0.3, 0.3, 0.3)
        glBegin(GL_LINES)

        grid_size = 10
        step = 0.5

        for i in range(-grid_size, grid_size + 1):
            glVertex3f(i * step, -1.0, -grid_size * step)
            glVertex3f(i * step, -1.0, grid_size * step)
            glVertex3f(-grid_size * step, -1.0, i * step)
            glVertex3f(grid_size * step, -1.0, i * step)

        glEnd()
        glEnable(GL_LIGHTING)

    def draw_logo_with_texture(self, logo):
        if not logo.texture_id:
            return

        glPushMatrix()
        glTranslatef(logo.position[0], logo.position[1], logo.position[2])

        # Apply visual-only tilts (do NOT affect export)
        glRotatef(logo.tilt_x, 1, 0, 0)
        glRotatef(logo.tilt_y, 0, 1, 0)

        # Apply 2D spin (affects export)
        glRotatef(logo.rotation_z + 90, 0, 0, 1)

        glScalef(logo.width, logo.height, 0.01)

        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glBindTexture(GL_TEXTURE_2D, logo.texture_id)
        glColor4f(1.0, 1.0, 1.0, 1.0)

        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex3f(-0.5, -0.5, 0)
        glTexCoord2f(1, 0); glVertex3f(0.5, -0.5, 0)
        glTexCoord2f(1, 1); glVertex3f(0.5, 0.5, 0)
        glTexCoord2f(0, 1); glVertex3f(-0.5, 0.5, 0)
        glEnd()

        glPopMatrix()

        if logo.selected:
            self.draw_selection_outline(logo)

    def draw_selection_outline(self, logo):
        glDisable(GL_TEXTURE_2D)
        glColor4f(1.0, 0.0, 0.0, 0.9)
        glLineWidth(3.0)

        glPushMatrix()
        glTranslatef(logo.position[0], logo.position[1], logo.position[2])
        glRotatef(logo.tilt_x, 1, 0, 0)
        glRotatef(logo.tilt_y, 0, 1, 0)
        glRotatef(logo.rotation_z + 90, 0, 0, 1)
        glScalef(logo.width, logo.height, 0.01)

        glBegin(GL_LINE_LOOP)
        glVertex3f(-0.5, -0.5, 0.001)
        glVertex3f(0.5, -0.5, 0.001)
        glVertex3f(0.5, 0.5, 0.001)
        glVertex3f(-0.5, 0.5, 0.001)
        glEnd()

        glPopMatrix()
        glEnable(GL_TEXTURE_2D)

    def load_model(self, filepath, texture_path=None, uv_settings=None):
        try:
            mesh = trimesh.load(filepath, force='mesh')

            self.model_data = ModelData()
            self.model_data.model_path = filepath
            self.model_data.vertices = mesh.vertices.tolist()
            self.model_data.faces = mesh.faces.tolist()

            if hasattr(mesh.visual, 'uv') and mesh.visual.uv is not None:
                self.model_data.uvs = mesh.visual.uv.tolist()
                print(f"Loaded UV coordinates: {len(self.model_data.uvs)}")
            else:
                self.model_data.uvs = [[0,0] for _ in range(len(self.model_data.vertices))]

            if hasattr(mesh.visual, 'vertex_normals') and mesh.visual.vertex_normals is not None:
                self.model_data.normals = mesh.visual.vertex_normals.tolist()
            else:
                self.model_data.normals = mesh.vertex_normals.tolist()

            self.model_data.calculate_bounding_box()
            self.model_data.calculate_face_centers_and_normals()

            # Apply saved UV settings if provided
            if uv_settings:
                self.model_data.uv_flip_u = uv_settings.get("uv_flip_u", False)
                self.model_data.uv_flip_v = uv_settings.get("uv_flip_v", False)
                self.model_data.uv_swap_uv = uv_settings.get("uv_swap_uv", False)
                print(f"Loaded UV settings: Flip U={self.model_data.uv_flip_u}, Flip V={self.model_data.uv_flip_v}, Swap={self.model_data.uv_swap_uv}")

            self.compile_display_list()

            if texture_path and os.path.exists(texture_path):
                self.load_model_texture(texture_path)

            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            import traceback
            traceback.print_exc()
            return False

    def compile_display_list(self):
        if not self.model_data:
            return

        self.model_data.display_list = glGenLists(1)
        glNewList(self.model_data.display_list, GL_COMPILE)

        for face in self.model_data.faces:
            glBegin(GL_TRIANGLES)
            for vertex_idx in face:
                vertex = self.model_data.vertices[vertex_idx]

                if self.model_data.normals and vertex_idx < len(self.model_data.normals):
                    normal = self.model_data.normals[vertex_idx]
                    glNormal3f(normal[0], normal[1], normal[2])

                if self.model_data.uvs and vertex_idx < len(self.model_data.uvs):
                    uv = self.model_data.uvs[vertex_idx]
                    glTexCoord2f(uv[0], 1.0 - uv[1])
                else:
                    glTexCoord2f(0, 0)

                glVertex3f(vertex[0], vertex[1], vertex[2])
            glEnd()

        glEndList()

    def load_model_texture(self, texture_path):
        try:
            img = Image.open(texture_path)
            img = img.convert('RGB')
            img_data = img.tobytes('raw', 'RGB')

            texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture_id)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, img.width, img.height,
                        0, GL_RGB, GL_UNSIGNED_BYTE, img_data)
            glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

            self.model_data.texture_id = texture_id
            self.model_data.texture_path = texture_path
            print(f"Texture loaded: {texture_path}")
        except Exception as e:
            print(f"Error loading model texture: {e}")

    def ray_intersect_model(self, ray_origin, ray_direction):
        if not self.model_data or not self.model_data.faces:
            return None, None

        closest_distance = float('inf')
        closest_point = None
        closest_normal = None

        for face in self.model_data.faces:
            v0 = np.array(self.model_data.vertices[face[0]])
            v1 = np.array(self.model_data.vertices[face[1]])
            v2 = np.array(self.model_data.vertices[face[2]])

            intersection, normal = self.ray_triangle_intersection(ray_origin, ray_direction, v0, v1, v2)

            if intersection is not None:
                distance = np.linalg.norm(intersection - ray_origin)
                if distance < closest_distance:
                    closest_distance = distance
                    closest_point = intersection
                    closest_normal = normal

        return closest_point, closest_normal

    def ray_triangle_intersection(self, ray_origin, ray_direction, v0, v1, v2):
        epsilon = 0.000001

        edge1 = v1 - v0
        edge2 = v2 - v0
        h = np.cross(ray_direction, edge2)
        a = np.dot(edge1, h)

        if abs(a) < epsilon:
            return None, None

        f = 1.0 / a
        s = ray_origin - v0
        u = f * np.dot(s, h)

        if u < 0.0 or u > 1.0:
            return None, None

        q = np.cross(s, edge1)
        v = f * np.dot(ray_direction, q)

        if v < 0.0 or u + v > 1.0:
            return None, None

        t = f * np.dot(edge2, q)

        if t > epsilon:
            intersection_point = ray_origin + ray_direction * t
            normal = np.cross(edge1, edge2)
            normal = normal / (np.linalg.norm(normal) + 1e-8)
            return intersection_point, normal

        return None, None

    def get_ray_from_mouse(self, mouse_x, mouse_y):
        viewport = glGetIntegerv(GL_VIEWPORT)
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)

        z1, z2 = 0, 1
        pos1 = gluUnProject(mouse_x, viewport[3] - mouse_y, z1, modelview, projection, viewport)
        pos2 = gluUnProject(mouse_x, viewport[3] - mouse_y, z2, modelview, projection, viewport)

        ray_origin = np.array(pos1)
        ray_direction = np.array(pos2) - np.array(pos1)
        ray_direction = ray_direction / (np.linalg.norm(ray_direction) + 1e-8)

        return ray_origin, ray_direction

    def update_logo_uv_from_position(self, logo):
        """Update UV coordinates based on logo's 3D position"""
        if not self.model_data:
            return

        # Get oriented UV from model
        oriented_uv = self.model_data.get_uv_from_3d_point(logo.position)
        logo.uv_position = oriented_uv

        # Update UI with oriented UV
        if self.main_window and hasattr(self.main_window, 'logo_control'):
            self.main_window.logo_control.uv_label.setText(f"U: {oriented_uv[0]:.3f}, V: {oriented_uv[1]:.3f}")

    def mousePressEvent(self, event):
        ray_origin, ray_direction = self.get_ray_from_mouse(event.x(), event.y())

        # Check movement gizmo for selected logo
        if self.selected_logo and not self.movement_mode and self.model_data:
            axis = self.movement_gizmo.check_hover(ray_origin, ray_direction,
                                                   self.selected_logo.position,
                                                   self.model_data.model_scale)
            if axis:
                self.movement_gizmo.active_axis = axis
                self.movement_gizmo.start_position = self.selected_logo.position.copy()
                self.movement_gizmo.start_mouse_pos = event.pos()
                self.gizmo_active = True
                self.setCursor(Qt.ClosedHandCursor)
                return

        # Handle movement mode for logo placement
        if self.movement_mode and event.button() == Qt.LeftButton and self.selected_logo:
            hit_point, normal = self.ray_intersect_model(ray_origin, ray_direction)

            if hit_point is not None:
                offset = normal * 0.02 if normal is not None else np.array([0, 0.02, 0])
                self.selected_logo.position = (hit_point + offset).tolist()
                # Get oriented UV from the hit point
                oriented_uv = self.model_data.get_uv_from_3d_point(hit_point) if self.model_data else (0.5, 0.5)
                self.selected_logo.uv_position = oriented_uv
                # Update the UI
                if self.main_window and hasattr(self.main_window, 'logo_control'):
                    self.main_window.logo_control.uv_label.setText(f"U: {oriented_uv[0]:.3f}, V: {oriented_uv[1]:.3f}")
                self.update()
                if self.main_window:
                    self.main_window.statusBar.showMessage(f"Logo placed at UV: ({oriented_uv[0]:.3f}, {oriented_uv[1]:.3f})", 3000)

        # Store last position for camera movement
        self.last_pos = event.pos()

    def mouseMoveEvent(self, event):
        # Handle movement gizmo for logos
        if self.gizmo_active and self.movement_gizmo.active_axis and self.movement_gizmo.start_mouse_pos and self.selected_logo:
            dx = event.x() - self.movement_gizmo.start_mouse_pos.x()
            dy = event.y() - self.movement_gizmo.start_mouse_pos.y()

            # Convert screen movement to world movement
            move_speed = 0.008 * (abs(self.zoom) / 5.0)

            new_position = self.movement_gizmo.start_position.copy()
            if self.movement_gizmo.active_axis == 'x':
                new_position[0] += dx * move_speed
            elif self.movement_gizmo.active_axis == 'y':
                new_position[1] -= dy * move_speed
            elif self.movement_gizmo.active_axis == 'z':
                new_position[2] += dx * move_speed

            self.selected_logo.position = new_position
            # Update UV coordinates based on new position
            self.update_logo_uv_from_position(self.selected_logo)
            self.update()
            return

        # Check for hover on movement gizmo
        if not self.gizmo_active and not self.movement_mode and self.selected_logo and self.model_data:
            ray_origin, ray_direction = self.get_ray_from_mouse(event.x(), event.y())
            self.movement_gizmo.check_hover(ray_origin, ray_direction,
                                           self.selected_logo.position,
                                           self.model_data.model_scale)
            self.update()

        # Handle normal camera rotation
        if event.buttons() == Qt.LeftButton and not self.movement_mode and not self.gizmo_active:
            dx = event.x() - self.last_pos.x()
            dy = event.y() - self.last_pos.y()
            self.rotation_y += dx * 0.5
            self.rotation_x += dy * 0.5
            self.last_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        self.gizmo_active = False
        self.movement_gizmo.active_axis = None
        self.movement_gizmo.start_mouse_pos = None
        self.setCursor(Qt.ArrowCursor)

    def wheelEvent(self, event):
        self.zoom += event.angleDelta().y() / 120.0
        self.zoom = max(-20, min(-1, self.zoom))
        self.update()

class LogoControlPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.current_logo = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # Size controls
        size_group = QGroupBox("Size (World Units)")
        size_layout = QVBoxLayout()

        width_layout = QHBoxLayout()
        width_layout.addWidget(QLabel("Width:"))
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(0.01, 2.0)
        self.width_spin.setSingleStep(0.05)
        self.width_spin.setValue(0.2)
        self.width_spin.setDecimals(3)
        self.width_spin.valueChanged.connect(self.on_width_changed)
        width_layout.addWidget(self.width_spin)
        size_layout.addLayout(width_layout)

        height_layout = QHBoxLayout()
        height_layout.addWidget(QLabel("Height:"))
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(0.01, 2.0)
        self.height_spin.setSingleStep(0.05)
        self.height_spin.setValue(0.2)
        self.height_spin.setDecimals(3)
        self.height_spin.valueChanged.connect(self.on_height_changed)
        height_layout.addWidget(self.height_spin)
        size_layout.addLayout(height_layout)

        size_group.setLayout(size_layout)
        layout.addWidget(size_group)

        # 2D Spin control (affects export)
        spin_group = QGroupBox("2D Spin (Affects Export)")
        spin_layout = QVBoxLayout()

        rot_layout = QHBoxLayout()
        rot_layout.addWidget(QLabel("Angle:"))
        self.rotation_spin = QDoubleSpinBox()
        self.rotation_spin.setRange(-360, 360)
        self.rotation_spin.setSingleStep(15)
        self.rotation_spin.setValue(0)
        self.rotation_spin.valueChanged.connect(self.on_rotation_changed)
        rot_layout.addWidget(self.rotation_spin)
        spin_layout.addLayout(rot_layout)

        spin_group.setLayout(spin_layout)
        layout.addWidget(spin_group)

        # Visual-only tilt controls (do NOT affect export)
        tilt_group = QGroupBox("Visual Tilt (View Only - Does NOT Affect Export)")
        tilt_layout = QVBoxLayout()

        tilt_x_layout = QHBoxLayout()
        tilt_x_layout.addWidget(QLabel("Tilt X:"))
        self.tilt_x_spin = QDoubleSpinBox()
        self.tilt_x_spin.setRange(-180, 180)
        self.tilt_x_spin.setSingleStep(15)
        self.tilt_x_spin.setValue(0)
        self.tilt_x_spin.valueChanged.connect(self.on_tilt_x_changed)
        tilt_x_layout.addWidget(self.tilt_x_spin)
        tilt_layout.addLayout(tilt_x_layout)

        tilt_y_layout = QHBoxLayout()
        tilt_y_layout.addWidget(QLabel("Tilt Y:"))
        self.tilt_y_spin = QDoubleSpinBox()
        self.tilt_y_spin.setRange(-180, 180)
        self.tilt_y_spin.setSingleStep(15)
        self.tilt_y_spin.setValue(0)
        self.tilt_y_spin.valueChanged.connect(self.on_tilt_y_changed)
        tilt_y_layout.addWidget(self.tilt_y_spin)
        tilt_layout.addLayout(tilt_y_layout)

        tilt_note = QLabel("Note: Tilt is visual only for placement on curved surfaces")
        tilt_note.setStyleSheet("color: #888; font-size: 9px;")
        tilt_layout.addWidget(tilt_note)

        tilt_group.setLayout(tilt_layout)
        layout.addWidget(tilt_group)

        # Flip buttons
        flip_group = QGroupBox("Flip")
        flip_layout = QVBoxLayout()

        flip_buttons_layout = QHBoxLayout()
        self.flip_x_btn = QPushButton("Flip Horizontal")
        self.flip_x_btn.clicked.connect(self.on_flip_x)
        self.flip_y_btn = QPushButton("Flip Vertical")
        self.flip_y_btn.clicked.connect(self.on_flip_y)
        flip_buttons_layout.addWidget(self.flip_x_btn)
        flip_buttons_layout.addWidget(self.flip_y_btn)
        flip_layout.addLayout(flip_buttons_layout)

        flip_group.setLayout(flip_layout)
        layout.addWidget(flip_group)

        # Movement mode button
        self.move_mode_btn = QPushButton("Enter Movement Mode (Click to Place)")
        self.move_mode_btn.setCheckable(True)
        self.move_mode_btn.clicked.connect(self.on_move_mode)
        self.move_mode_btn.setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }
            QPushButton:checked { background-color: #f44336; }
        """)
        layout.addWidget(self.move_mode_btn)

        # UV position display
        uv_group = QGroupBox("UV Position on Texture")
        uv_layout = QVBoxLayout()
        self.uv_label = QLabel("U: 0.500, V: 0.500")
        self.uv_label.setFont(QFont("Monospace", 10))
        uv_layout.addWidget(self.uv_label)
        uv_group.setLayout(uv_layout)
        layout.addWidget(uv_group)

        layout.addStretch()
        self.setLayout(layout)
        self.setVisible(False)
        self.setMaximumWidth(350)

    def set_logo(self, logo):
        self.current_logo = logo
        if logo:
            self.width_spin.setValue(logo.width)
            self.height_spin.setValue(logo.height)
            self.rotation_spin.setValue(logo.rotation_z)
            self.tilt_x_spin.setValue(logo.tilt_x)
            self.tilt_y_spin.setValue(logo.tilt_y)
            self.uv_label.setText(f"U: {logo.uv_position[0]:.3f}, V: {logo.uv_position[1]:.3f}")
            self.setVisible(True)
        else:
            self.setVisible(False)
            if self.move_mode_btn.isChecked():
                self.move_mode_btn.setChecked(False)
                if self.parent and hasattr(self.parent, 'gl_widget'):
                    self.parent.gl_widget.movement_mode = False

    def on_width_changed(self, value):
        if self.current_logo:
            self.current_logo.width = value
            if self.parent and hasattr(self.parent, 'gl_widget'):
                self.parent.gl_widget.update()

    def on_height_changed(self, value):
        if self.current_logo:
            self.current_logo.height = value
            if self.parent and hasattr(self.parent, 'gl_widget'):
                self.parent.gl_widget.update()

    def on_rotation_changed(self, value):
        if self.current_logo:
            self.current_logo.rotation_z = value
            if self.parent and hasattr(self.parent, 'gl_widget'):
                self.parent.gl_widget.update()

    def on_tilt_x_changed(self, value):
        if self.current_logo:
            self.current_logo.tilt_x = value
            if self.parent and hasattr(self.parent, 'gl_widget'):
                self.parent.gl_widget.update()

    def on_tilt_y_changed(self, value):
        if self.current_logo:
            self.current_logo.tilt_y = value
            if self.parent and hasattr(self.parent, 'gl_widget'):
                self.parent.gl_widget.update()

    def on_flip_x(self):
        if self.current_logo:
            self.current_logo.flipped_x = not self.current_logo.flipped_x
            self.update_logo_texture()

    def on_flip_y(self):
        if self.current_logo:
            self.current_logo.flipped_y = not self.current_logo.flipped_y
            self.update_logo_texture()

    def on_move_mode(self, checked):
        if self.current_logo and self.parent and hasattr(self.parent, 'gl_widget'):
            self.parent.gl_widget.movement_mode = checked
            self.move_mode_btn.setText("Exit Movement Mode" if checked else "Enter Movement Mode (Click to Place)")

    def update_logo_texture(self):
        if self.current_logo and self.current_logo.texture_id:
            glDeleteTextures([self.current_logo.texture_id])
            self.current_logo.texture_id = self.current_logo.load_texture()
            if self.parent and hasattr(self.parent, 'gl_widget'):
                self.parent.gl_widget.update()

class ConsolePanel(QWidget):
    """Collapsible console panel at the bottom of the editor"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_editor = parent
        self.is_collapsed = True
        self.logs = []
        self.max_logs = 1000

        self.init_ui()

    def init_ui(self):
        # Don't set a fixed minimum height - let it be determined by content
        self.setMaximumHeight(400)
        self.setStyleSheet("background-color: #2b2b2b; border-top: 2px solid #4CAF50;")

        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar (always visible, fixed height)
        header = QWidget()
        header.setFixedHeight(30)
        header.setStyleSheet("background-color: #2b2b2b;")
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(5, 2, 5, 2)

        # Expand button
        self.expand_btn = QPushButton("▼ Console")
        self.expand_btn.setFlat(True)
        self.expand_btn.setFixedHeight(24)
        self.expand_btn.clicked.connect(self.toggle_console)
        self.expand_btn.setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; border: none; padding: 2px 8px; border-radius: 3px; font-weight: bold; }
            QPushButton:hover { background-color: #45a049; }
        """)
        header_layout.addWidget(self.expand_btn)

        # Filter dropdown
        header_layout.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Info", "Warning", "Error"])
        self.filter_combo.currentTextChanged.connect(self.on_filter_changed)
        self.filter_combo.setFixedWidth(80)
        header_layout.addWidget(self.filter_combo)

        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.setFlat(True)
        clear_btn.clicked.connect(self.clear_logs)
        clear_btn.setFixedWidth(50)
        header_layout.addWidget(clear_btn)

        # Copy button
        copy_btn = QPushButton("Copy")
        copy_btn.setFlat(True)
        copy_btn.clicked.connect(self.copy_logs)
        copy_btn.setFixedWidth(50)
        header_layout.addWidget(copy_btn)

        # Log count
        self.log_count_label = QLabel("0 logs")
        self.log_count_label.setStyleSheet("color: #888; font-size: 10px;")
        header_layout.addWidget(self.log_count_label)

        header_layout.addStretch()
        header.setLayout(header_layout)
        layout.addWidget(header)

        # Content area (collapsible)
        self.content = QWidget()
        self.content.setMinimumHeight(150)  # Minimum height when expanded
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(5, 5, 5, 5)

        # Log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Monospace", 9))
        self.log_display.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; border: none;")
        content_layout.addWidget(self.log_display)

        # Command input
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel(">>>"))
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Python command...")
        self.command_input.returnPressed.connect(self.execute_command)
        self.command_input.setStyleSheet("background-color: #2d2d2d; color: #d4d4d4; border: 1px solid #3a3a3a; padding: 4px;")
        input_layout.addWidget(self.command_input)
        content_layout.addLayout(input_layout)

        self.content.setLayout(content_layout)
        layout.addWidget(self.content)

        self.setLayout(layout)

        # Start collapsed - content hidden
        self.content.hide()
        self.setMaximumHeight(30)  # Only header height when collapsed

    def toggle_console(self):
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.content.hide()
            self.expand_btn.setText("▼ Console")
            self.setMaximumHeight(30)  # Only header height
            self.setMinimumHeight(30)
        else:
            self.content.show()
            self.expand_btn.setText("▲ Console")
            self.setMaximumHeight(400)  # Max height when expanded
            self.setMinimumHeight(180)  # Minimum height when expanded

    def add_log(self, message, level="info"):
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")

        colors = {"info": "#d4d4d4", "warning": "#ffcc00", "error": "#ff5555", "output": "#88ff88"}
        color = colors.get(level, "#d4d4d4")
        prefix = {"info": "[INFO]", "warning": "[WARNING]", "error": "[ERROR]", "output": "[OUTPUT]"}.get(level, "[INFO]")

        formatted = f'<span style="color: #888;">{timestamp}</span> <span style="color: {color};">{prefix}</span> {message}'
        self.logs.append({'timestamp': timestamp, 'level': level, 'message': message, 'formatted': formatted})

        if len(self.logs) > self.max_logs:
            self.logs.pop(0)
        self.update_display()

    def update_display(self):
        self.log_display.clear()
        filter_text = self.filter_combo.currentText().lower()
        for log in self.logs:
            if filter_text == "all" or log['level'] == filter_text:
                self.log_display.append(log['formatted'])
        self.log_count_label.setText(f"{len(self.logs)} logs")

    def clear_logs(self):
        self.logs = []
        self.update_display()
        self.add_log("Console cleared", "info")

    def copy_logs(self):
        text = "\n".join([f"[{l['timestamp']}] {l['level'].upper()}: {l['message']}" for l in self.logs])
        QApplication.clipboard().setText(text)
        self.add_log("Logs copied", "info")

    def on_filter_changed(self, text):
        self.update_display()

    def execute_command(self):
        command = self.command_input.text()
        if not command:
            return
        self.add_log(f">>> {command}", "output")
        self.command_input.clear()
        try:
            # Create a safe environment with access to editor objects
            editor = self.parent_editor
            gl_widget = editor.gl_widget if editor else None
            result = eval(command, {'__builtins__': __builtins__}, {
                'editor': editor,
                'gl_widget': gl_widget,
                'model': gl_widget.model_data if gl_widget else None,
                'logos': gl_widget.logos if gl_widget else []
            })
            if result is not None:
                self.add_log(str(result), "output")
        except Exception as e:
            self.add_log(f"Error: {e}", "error")

class ModelViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_model_path = None
        self.current_texture_path = None
        self.grid_toggle = None
        self.welcome_dialog_created = False
        self.uv_settings_manager = ModelUVSettings()
        self.console = None

        # Get the application path
        self.app_path = os.path.dirname(os.path.abspath(__file__))

        # Initialize addon manager
        self.addon_manager = AddonManager(self.app_path)

        self.init_ui()

        # Add console after UI is initialized
        self.add_console()

        # Create welcome dialog with addon support
        self.create_welcome_dialog()

        # Call addon initialization
        self.addon_manager.call_all_addons("on_editor_start", self)

    def add_console(self):
        """Add console panel to the editor"""
        try:
            central = self.centralWidget()
            if central and central.layout():
                self.console = ConsolePanel(self)
                central.layout().addWidget(self.console)
                print("Console added to editor")

                # Redirect stdout/stderr to console
                class ConsoleRedirect:
                    def __init__(self, console, level):
                        self.console = console
                        self.level = level
                    def write(self, text):
                        if text and text.strip():
                            self.console.add_log(text.rstrip(), self.level)
                    def flush(self):
                        pass

                sys.stdout = ConsoleRedirect(self.console, "output")
                sys.stderr = ConsoleRedirect(self.console, "error")

                self.console.add_log("=" * 50, "info")
                self.console.add_log("Console ready! Type Python commands below.", "info")
                self.console.add_log("Use 'editor' to access the main editor object.", "info")
                self.console.add_log("=" * 50, "info")

        except Exception as e:
            print(f"Error adding console: {e}")
            import traceback
            traceback.print_exc()

    def create_welcome_dialog(self):
        """Create and show welcome dialog with addon support"""
        welcome = WelcomeDialog(self)

        # Check if we should show the dialog
        if welcome.should_show():
            # Call addons to add their instructions
            self.addon_manager.call_all_addons("add_welcome_instructions", welcome)

            result = welcome.exec_()
            welcome.save_preference()

    def init_ui(self):
        self.setWindowTitle("LiveryWorks 1.4.7 B4")
        self.setGeometry(100, 100, 1400, 900)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Create toolbar
        self.create_toolbar()

        # Create content area
        content_widget = QWidget()
        content_layout = QHBoxLayout()
        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget)

        self.gl_widget = GLWidget(self)
        content_layout.addWidget(self.gl_widget, 3)

        # Create resizable right panel
        self.right_panel = QWidget()
        self.right_panel.setMinimumWidth(250)
        self.right_panel.setMaximumWidth(500)

        # Create splitter for resizable panel
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.gl_widget)
        splitter.addWidget(self.right_panel)
        splitter.setSizes([1050, 350])  # Initial sizes
        content_layout.addWidget(splitter)

        # Create scrollable content for right panel
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setStyleSheet("QScrollArea { border: none; background-color: #2b2b2b; }")

        right_content = QWidget()
        right_layout = QVBoxLayout()
        right_content.setLayout(right_layout)

        # Model info
        model_group = QGroupBox("Model Information")
        model_layout = QVBoxLayout()
        self.model_info = QTextEdit()
        self.model_info.setReadOnly(True)
        self.model_info.setMaximumHeight(100)
        model_layout.addWidget(self.model_info)
        model_group.setLayout(model_layout)
        right_layout.addWidget(model_group)

        # Model scenegraph
        model_group = QGroupBox("Model Structure")
        model_layout = QVBoxLayout()
        self.model_tree = QTreeWidget()
        self.model_tree.setHeaderLabel("Model Parts")
        model_layout.addWidget(self.model_tree)
        model_group.setLayout(model_layout)
        right_layout.addWidget(model_group)

        # Logo scenegraph
        logo_group = QGroupBox("Logos")
        logo_layout = QVBoxLayout()

        self.unselect_btn = QPushButton("Unselect Logo")
        self.unselect_btn.clicked.connect(self.unselect_logo)
        self.unselect_btn.setEnabled(False)
        logo_layout.addWidget(self.unselect_btn)

        self.logo_tree = QTreeWidget()
        self.logo_tree.setHeaderLabel("Loaded Logos")
        self.logo_tree.itemClicked.connect(self.on_logo_selected)
        logo_layout.addWidget(self.logo_tree)

        button_layout = QHBoxLayout()
        self.load_logo_btn = QPushButton("Load Logo")
        self.load_logo_btn.clicked.connect(self.load_logo)
        self.delete_logo_btn = QPushButton("Delete Logo")
        self.delete_logo_btn.clicked.connect(self.delete_logo)
        self.delete_logo_btn.setEnabled(False)
        button_layout.addWidget(self.load_logo_btn)
        button_layout.addWidget(self.delete_logo_btn)
        logo_layout.addLayout(button_layout)

        self.export_btn = QPushButton("Export Model with Logos")
        self.export_btn.clicked.connect(self.export_model)
        logo_layout.addWidget(self.export_btn)

        logo_group.setLayout(logo_layout)
        right_layout.addWidget(logo_group)

        # Logo control panel
        self.logo_control = LogoControlPanel(self)
        right_layout.addWidget(self.logo_control)

        # View controls
        controls_group = QGroupBox("View Controls")
        controls_layout = QVBoxLayout()

        self.grid_toggle = QCheckBox("Show Grid")
        self.grid_toggle.setChecked(True)
        self.grid_toggle.toggled.connect(self.toggle_grid)
        controls_layout.addWidget(self.grid_toggle)

        controls_group.setLayout(controls_layout)
        right_layout.addWidget(controls_group)

        # UV Orientation controls
        uv_group = QGroupBox("UV Orientation (Model Specific)")
        uv_layout = QVBoxLayout()

        self.uv_flip_u = QCheckBox("Flip U (Horizontal)")
        self.uv_flip_u.stateChanged.connect(self.on_uv_flip_u_changed)
        uv_layout.addWidget(self.uv_flip_u)

        self.uv_flip_v = QCheckBox("Flip V (Vertical)")
        self.uv_flip_v.stateChanged.connect(self.on_uv_flip_v_changed)
        uv_layout.addWidget(self.uv_flip_v)

        self.uv_swap_uv = QCheckBox("Swap U/V")
        self.uv_swap_uv.stateChanged.connect(self.on_uv_swap_uv_changed)
        uv_layout.addWidget(self.uv_swap_uv)

        # Save UV button
        save_uv_btn = QPushButton("Save UV Settings for This Model")
        save_uv_btn.clicked.connect(self.save_uv_settings)
        uv_layout.addWidget(save_uv_btn)

        # Reset UV button
        reset_uv_btn = QPushButton("Reset UV Settings")
        reset_uv_btn.clicked.connect(self.reset_uv_settings)
        uv_layout.addWidget(reset_uv_btn)

        # Test button
        test_uv_btn = QPushButton("Test UV Orientation")
        test_uv_btn.clicked.connect(self.test_uv_orientation)
        uv_layout.addWidget(test_uv_btn)

        # Visualize UV button
        vis_uv_btn = QPushButton("Visualize UV Islands")
        vis_uv_btn.clicked.connect(self.visualize_uv_islands)
        uv_layout.addWidget(vis_uv_btn)

        uv_note = QLabel("Adjust these if logos appear in wrong location on texture.\nSettings are saved per model!")
        uv_note.setStyleSheet("color: #888; font-size: 9px;")
        uv_layout.addWidget(uv_note)

        uv_group.setLayout(uv_layout)
        right_layout.addWidget(uv_group)

        # Addon controls group
        addon_group = QGroupBox("Addons")
        addon_layout = QVBoxLayout()

        self.addon_list = QListWidget()
        self.addon_list.setMaximumHeight(100)
        addon_layout.addWidget(self.addon_list)

        # Populate addon list
        for addon_name in self.addon_manager.get_enabled_addons():
            addon = self.addon_manager.get_addon(addon_name)
            if addon:
                version = addon['config'].get('version', 'unknown')
                item = QListWidgetItem(f"{addon_name} v{version}")
                self.addon_list.addItem(item)

        addon_group.setLayout(addon_layout)
        right_layout.addWidget(addon_group)

        right_layout.addStretch()
        right_scroll.setWidget(right_content)

        # Add scroll to right panel
        right_panel_layout = QVBoxLayout()
        right_panel_layout.setContentsMargins(0, 0, 0, 0)
        right_panel_layout.addWidget(right_scroll)
        self.right_panel.setLayout(right_panel_layout)

        self.create_menu_bar()

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready - Click on model to place logo | Use Tilt for visual placement on curved surfaces")

        # Call addon UI initialization
        self.addon_manager.call_all_addons("on_ui_ready", self)

    def create_toolbar(self):
        """Create the main toolbar with icons"""
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setMovable(False)

        # Load model action
        load_action = QAction(self.style().standardIcon(QStyle.SP_DialogOpenButton), "Load Model", self)
        load_action.triggered.connect(self.load_model)
        load_action.setToolTip("Load a 3D model")
        toolbar.addAction(load_action)

        # Load texture action
        texture_action = QAction(self.style().standardIcon(QStyle.SP_FileDialogContentsView), "Load Texture", self)
        texture_action.triggered.connect(self.load_texture_for_model)
        texture_action.setToolTip("Load texture for the model")
        toolbar.addAction(texture_action)

        toolbar.addSeparator()

        # Load logo action
        logo_action = QAction(self.style().standardIcon(QStyle.SP_FileIcon), "Load Logo", self)
        logo_action.triggered.connect(self.load_logo)
        logo_action.setToolTip("Load a logo image")
        toolbar.addAction(logo_action)

        # Export action
        export_action = QAction(self.style().standardIcon(QStyle.SP_DialogSaveButton), "Export Model", self)
        export_action.triggered.connect(self.export_model)
        export_action.setToolTip("Export model with logos")
        toolbar.addAction(export_action)

        toolbar.addSeparator()

        # Grid toggle action
        grid_action = QAction(self.style().standardIcon(QStyle.SP_DesktopIcon), "Toggle Grid", self)
        grid_action.triggered.connect(lambda: self.toggle_grid(not self.grid_toggle.isChecked()))
        grid_action.setToolTip("Show/Hide grid")
        grid_action.setCheckable(True)
        grid_action.setChecked(True)
        toolbar.addAction(grid_action)

        # Reset view action
        reset_action = QAction(self.style().standardIcon(QStyle.SP_BrowserReload), "Reset View", self)
        reset_action.triggered.connect(self.reset_view)
        reset_action.setToolTip("Reset camera view")
        toolbar.addAction(reset_action)

        toolbar.addSeparator()

        # Help action
        help_action = QAction(self.style().standardIcon(QStyle.SP_MessageBoxInformation), "Help", self)
        help_action.triggered.connect(self.show_help)
        help_action.setToolTip("Show help")
        toolbar.addAction(help_action)

        # Addon action
        addon_action = QAction(self.style().standardIcon(QStyle.SP_FileDialogDetailedView), "Addons", self)
        addon_action.triggered.connect(self.show_addons_dialog)
        addon_action.setToolTip("Manage addons")
        toolbar.addAction(addon_action)

    def create_menu_bar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu('File')

        load_model_action = QAction('Load Model', self)
        load_model_action.triggered.connect(self.load_model)
        load_model_action.setShortcut('Ctrl+O')
        file_menu.addAction(load_model_action)

        load_texture_action = QAction('Load Texture for Model', self)
        load_texture_action.triggered.connect(self.load_texture_for_model)
        file_menu.addAction(load_texture_action)

        file_menu.addSeparator()

        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        exit_action.setShortcut('Ctrl+Q')
        file_menu.addAction(exit_action)

        # Help menu
        help_menu = menubar.addMenu('Help')

        show_welcome_action = QAction('Show Welcome Message', self)
        show_welcome_action.triggered.connect(self.show_welcome)
        help_menu.addAction(show_welcome_action)

        show_addons_action = QAction('Manage Addons', self)
        show_addons_action.triggered.connect(self.show_addons_dialog)
        help_menu.addAction(show_addons_action)

        view_menu = menubar.addMenu('View')

        toggle_grid_action = QAction('Toggle Grid', self)
        toggle_grid_action.triggered.connect(lambda: self.toggle_grid(not self.grid_toggle.isChecked()))
        toggle_grid_action.setShortcut('G')
        view_menu.addAction(toggle_grid_action)

        reset_view_action = QAction('Reset View', self)
        reset_view_action.triggered.connect(self.reset_view)
        reset_view_action.setShortcut('R')
        view_menu.addAction(reset_view_action)

    def show_help(self):
        """Show help dialog"""
        QMessageBox.information(self, "Help",
            "LiveryWorks 1.4.7 B4\n\n"
            "Controls:\n"
            "- Left click and drag: Rotate view\n"
            "- Scroll: Zoom\n"
            "- Click on model in movement mode: Place logo\n"
            "- Drag colored arrows: Move selected logo\n\n"
            "Logo Controls:\n"
            "- 2D Spin: Rotates logo on texture (affects export)\n"
            "- Tilt X/Y: Visual placement only\n"
            "- Flip: Mirror logo\n\n"
            "UV Orientation:\n"
            "- If logos export in wrong location, adjust the UV Orientation settings\n"
            "- Settings are saved per model and automatically loaded when you reopen the model\n\n"
            "For more help, see the welcome message in the Help menu.")

    def show_addons_dialog(self):
        """Show addon management dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Addon Manager")
        dialog.setMinimumWidth(500)
        dialog.setMinimumHeight(400)

        layout = QVBoxLayout()

        # Addon list
        list_widget = QListWidget()
        for addon_name in self.addon_manager.get_enabled_addons():
            addon = self.addon_manager.get_addon(addon_name)
            if addon:
                version = addon['config'].get('version', 'unknown')
                author = addon['config'].get('author', 'Unknown')
                item_text = f"{addon_name} v{version} by {author}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, addon_name)
                list_widget.addItem(item)

        layout.addWidget(QLabel("Loaded Addons:"))
        layout.addWidget(list_widget)

        # Info area
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setMaximumHeight(100)
        layout.addWidget(QLabel("Addon Information:"))
        layout.addWidget(info_text)

        def on_item_selected(item):
            addon_name = item.data(Qt.UserRole)
            addon = self.addon_manager.get_addon(addon_name)
            if addon:
                info = f"Name: {addon_name}\n"
                info += f"Version: {addon['config'].get('version', 'unknown')}\n"
                info += f"Author: {addon['config'].get('author', 'Unknown')}\n"
                info += f"Description: {addon['config'].get('description', 'No description')}\n"
                info_text.setText(info)

        list_widget.itemClicked.connect(on_item_selected)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec_()

    def show_welcome(self):
        welcome = WelcomeDialog(self)
        if welcome.should_show():
            # Call addons to add their instructions
            self.addon_manager.call_all_addons("add_welcome_instructions", welcome)
            welcome.exec_()
            welcome.save_preference()

    def load_model(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Load 3D Model", "",
            "3D Models (*.obj *.stl *.ply *.glb *.gltf);;All Files (*.*)")

        if filepath:
            self.current_model_path = filepath

            texture_path = None
            if filepath.endswith('.obj'):
                result = QMessageBox.question(self, "Load Texture",
                                            "Would you like to load a texture for this OBJ model?",
                                            QMessageBox.Yes | QMessageBox.No)
                if result == QMessageBox.Yes:
                    texture_path, _ = QFileDialog.getOpenFileName(
                        self, "Load Texture for Model", "",
                        "Images (*.png *.jpg *.jpeg *.bmp)")

            # Get saved UV settings for this model
            uv_settings = self.uv_settings_manager.get_model_settings(filepath)

            if self.gl_widget.load_model(filepath, texture_path, uv_settings):
                self.statusBar.showMessage(f"Loaded: {os.path.basename(filepath)}")
                self.populate_model_tree(filepath)
                self.update_model_info()

                # Update UV control checkboxes
                self.uv_flip_u.setChecked(uv_settings.get("uv_flip_u", False))
                self.uv_flip_v.setChecked(uv_settings.get("uv_flip_v", False))
                self.uv_swap_uv.setChecked(uv_settings.get("uv_swap_uv", False))

                # Update existing logos with new UV orientation
                self.update_existing_logo_uvs()

    def load_texture_for_model(self):
        if not self.gl_widget.model_data:
            QMessageBox.warning(self, "Warning", "Please load a model first")
            return

        texture_path, _ = QFileDialog.getOpenFileName(
            self, "Load Texture", "", "Images (*.png *.jpg *.jpeg *.bmp)")

        if texture_path:
            self.gl_widget.load_model_texture(texture_path)
            self.statusBar.showMessage(f"Texture loaded: {os.path.basename(texture_path)}")
            self.gl_widget.update()

    def populate_model_tree(self, filepath):
        self.model_tree.clear()
        root = QTreeWidgetItem([os.path.basename(filepath)])

        if self.gl_widget.model_data:
            vertices_item = QTreeWidgetItem([f"Vertices: {len(self.gl_widget.model_data.vertices)}"])
            root.addChild(vertices_item)

            faces_item = QTreeWidgetItem([f"Faces: {len(self.gl_widget.model_data.faces)}"])
            root.addChild(faces_item)

            if self.gl_widget.model_data.uvs:
                uvs_item = QTreeWidgetItem([f"UV Coordinates: {len(self.gl_widget.model_data.uvs)}"])
                root.addChild(uvs_item)

        self.model_tree.addTopLevelItem(root)
        root.setExpanded(True)

    def update_model_info(self):
        if self.gl_widget.model_data:
            bbox = self.gl_widget.model_data.bounding_box
            info = f"Model loaded successfully\n"
            info += f"Vertices: {len(self.gl_widget.model_data.vertices)}\n"
            info += f"Faces: {len(self.gl_widget.model_data.faces)}\n"
            if self.gl_widget.model_data.uvs:
                info += f"UV Mapping: Yes ({len(self.gl_widget.model_data.uvs)} coordinates)\n"
            else:
                info += f"UV Mapping: No\n"
            if self.gl_widget.model_data.texture_path:
                info += f"Texture: {os.path.basename(self.gl_widget.model_data.texture_path)}\n"
            if bbox:
                size = bbox['max'] - bbox['min']
                info += f"Model Size: X:{size[0]:.2f} Y:{size[1]:.2f} Z:{size[2]:.2f}"
            self.model_info.setText(info)

    def load_logo(self):
        if not self.gl_widget.model_data:
            QMessageBox.warning(self, "Warning", "Please load a model first")
            return

        filepath, _ = QFileDialog.getOpenFileName(
            self, "Load Logo", "", "Images (*.png *.jpg *.jpeg *.bmp *.tga)")

        if filepath:
            default_size = self.gl_widget.model_data.model_scale * 0.1
            center = self.gl_widget.model_data.center.copy()
            center[1] += default_size

            logo = Logo(filepath, position=center.tolist(), width=default_size, height=default_size)
            logo.texture_id = logo.load_texture()

            # Get center UV with orientation applied
            oriented_uv = self.gl_widget.model_data.get_uv_from_3d_point(center)
            logo.uv_position = oriented_uv

            self.gl_widget.logos.append(logo)

            item = QTreeWidgetItem([os.path.basename(filepath)])
            item.setData(0, Qt.UserRole, len(self.gl_widget.logos) - 1)
            self.logo_tree.addTopLevelItem(item)

            self.statusBar.showMessage(f"Logo loaded: {os.path.basename(filepath)}")
            self.gl_widget.update()

    def on_logo_selected(self, item, column):
        logo_index = item.data(0, Qt.UserRole)
        if logo_index is not None and logo_index < len(self.gl_widget.logos):
            for logo in self.gl_widget.logos:
                logo.selected = False

            self.gl_widget.logos[logo_index].selected = True
            self.gl_widget.selected_logo = self.gl_widget.logos[logo_index]

            self.logo_control.set_logo(self.gl_widget.logos[logo_index])
            self.delete_logo_btn.setEnabled(True)
            self.unselect_btn.setEnabled(True)

            self.gl_widget.update()

    def unselect_logo(self):
        if self.gl_widget.selected_logo:
            self.gl_widget.selected_logo.selected = False
            self.gl_widget.selected_logo = None
            self.logo_control.set_logo(None)
            self.delete_logo_btn.setEnabled(False)
            self.unselect_btn.setEnabled(False)
            self.logo_tree.clearSelection()

            if self.gl_widget.movement_mode:
                self.gl_widget.movement_mode = False
                if self.logo_control.move_mode_btn.isChecked():
                    self.logo_control.move_mode_btn.setChecked(False)
                    self.logo_control.move_mode_btn.setText("Enter Movement Mode (Click to Place)")

            self.gl_widget.update()

    def delete_logo(self):
        if self.gl_widget.selected_logo:
            index = self.gl_widget.logos.index(self.gl_widget.selected_logo)
            self.gl_widget.logos.pop(index)

            item = self.logo_tree.topLevelItem(index)
            self.logo_tree.takeTopLevelItem(index)

            self.unselect_logo()
            self.statusBar.showMessage("Logo deleted")
            self.gl_widget.update()

    def on_uv_flip_u_changed(self, state):
        """Handle UV flip U change"""
        if self.gl_widget.model_data:
            self.gl_widget.model_data.uv_flip_u = (state == Qt.Checked)
            self.update_existing_logo_uvs()
            self.statusBar.showMessage(f"UV Flip U: {'ON' if state else 'OFF'}", 3000)

    def on_uv_flip_v_changed(self, state):
        """Handle UV flip V change"""
        if self.gl_widget.model_data:
            self.gl_widget.model_data.uv_flip_v = (state == Qt.Checked)
            self.update_existing_logo_uvs()
            self.statusBar.showMessage(f"UV Flip V: {'ON' if state else 'OFF'}", 3000)

    def on_uv_swap_uv_changed(self, state):
        """Handle UV swap change"""
        if self.gl_widget.model_data:
            self.gl_widget.model_data.uv_swap_uv = (state == Qt.Checked)
            self.update_existing_logo_uvs()
            self.statusBar.showMessage(f"UV Swap U/V: {'ON' if state else 'OFF'}", 3000)

    def update_existing_logo_uvs(self):
        """Update all existing logo UVs with new orientation"""
        if not self.gl_widget.model_data:
            return

        for logo in self.gl_widget.logos:
            # Recalculate UV from 3D position with current orientation
            oriented_uv = self.gl_widget.model_data.get_uv_from_3d_point(logo.position)
            logo.uv_position = oriented_uv
            # Update display if this logo is selected
            if logo.selected and self.logo_control:
                self.logo_control.uv_label.setText(f"U: {oriented_uv[0]:.3f}, V: {oriented_uv[1]:.3f}")

        self.gl_widget.update()
        self.statusBar.showMessage("Updated all logo positions with new UV orientation", 3000)

    def save_uv_settings(self):
        """Save current UV settings for the loaded model"""
        if not self.gl_widget.model_data or not self.gl_widget.model_data.model_path:
            QMessageBox.warning(self, "Warning", "No model loaded to save settings for")
            return

        self.uv_settings_manager.save_model_settings(
            self.gl_widget.model_data.model_path,
            self.gl_widget.model_data.uv_flip_u,
            self.gl_widget.model_data.uv_flip_v,
            self.gl_widget.model_data.uv_swap_uv
        )

        self.statusBar.showMessage(f"UV settings saved for {os.path.basename(self.gl_widget.model_data.model_path)}", 3000)
        QMessageBox.information(self, "Settings Saved",
            f"UV orientation settings saved for:\n{os.path.basename(self.gl_widget.model_data.model_path)}\n\n"
            f"Flip U: {self.gl_widget.model_data.uv_flip_u}\n"
            f"Flip V: {self.gl_widget.model_data.uv_flip_v}\n"
            f"Swap UV: {self.gl_widget.model_data.uv_swap_uv}")

    def reset_uv_settings(self):
        """Reset UV settings to defaults"""
        if self.gl_widget.model_data:
            self.gl_widget.model_data.uv_flip_u = False
            self.gl_widget.model_data.uv_flip_v = False
            self.gl_widget.model_data.uv_swap_uv = False

            self.uv_flip_u.setChecked(False)
            self.uv_flip_v.setChecked(False)
            self.uv_swap_uv.setChecked(False)

            self.update_existing_logo_uvs()
            self.statusBar.showMessage("UV settings reset to defaults", 3000)

    def test_uv_orientation(self):
        """Test UV orientation by displaying where UV corners map to"""
        if not self.gl_widget.model_data:
            QMessageBox.warning(self, "Warning", "No model loaded")
            return

        # Get the 3D positions at the corners of the UV map
        uv_corners = [(0, 0), (1, 0), (0, 1), (1, 1)]
        info = "UV Corner Positions (with current orientation):\n\n"
        info += f"Current settings:\n"
        info += f"  Flip U: {self.gl_widget.model_data.uv_flip_u}\n"
        info += f"  Flip V: {self.gl_widget.model_data.uv_flip_v}\n"
        info += f"  Swap UV: {self.gl_widget.model_data.uv_swap_uv}\n\n"

        for u, v in uv_corners:
            # Find the closest face center to this UV coordinate
            closest_dist = float('inf')
            closest_point = None

            for i, face_uv in enumerate(self.gl_widget.model_data.face_uv_centers):
                # Apply current orientation to the face UV to compare
                oriented_uv = self.gl_widget.model_data.apply_uv_orientation(face_uv[0], face_uv[1])
                dist = (oriented_uv[0] - u)**2 + (oriented_uv[1] - v)**2
                if dist < closest_dist:
                    closest_dist = dist
                    closest_point = self.gl_widget.model_data.face_centers[i]

            if closest_point is not None:
                info += f"UV ({u:.1f}, {v:.1f}) -> 3D: ({closest_point[0]:.2f}, {closest_point[1]:.2f}, {closest_point[2]:.2f})\n"

        QMessageBox.information(self, "UV Orientation Test", info)

    def visualize_uv_islands(self):
        """Create a visualization of UV islands on the model"""
        if not self.gl_widget.model_data:
            QMessageBox.warning(self, "Warning", "No model loaded")
            return

        # Create a temporary texture with UV island visualization
        width = 1024
        height = 1024
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Group faces by their UV island (simplified - just draw all UV points)
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
                  (255, 0, 255), (0, 255, 255), (128, 128, 0), (128, 0, 128)]

        # Draw all UV points
        for i, face_uv in enumerate(self.gl_widget.model_data.face_uv_centers):
            color = colors[i % len(colors)]

            # Draw point at UV location
            x = int(face_uv[0] * width)
            y = int(face_uv[1] * height)
            draw.ellipse([x-2, y-2, x+2, y+2], fill=color)

        # Add a grid for reference
        for i in range(0, width, 50):
            draw.line([(i, 0), (i, height)], fill=(128, 128, 128, 100))
            draw.line([(0, i), (width, i)], fill=(128, 128, 128, 100))

        # Add corner labels
        try:
            draw.text((10, 10), "UV (0,0) -> Bottom Left", fill=(255, 255, 255))
            draw.text((width - 150, 10), "UV (1,0) -> Bottom Right", fill=(255, 255, 255))
            draw.text((10, height - 30), "UV (0,1) -> Top Left", fill=(255, 255, 255))
            draw.text((width - 150, height - 30), "UV (1,1) -> Top Right", fill=(255, 255, 255))
        except:
            pass

        # Save and show
        temp_path = os.path.join(os.path.dirname(__file__), "uv_islands.png")
        img.save(temp_path)

        # Open with default image viewer
        if sys.platform == 'linux':
            os.system(f"xdg-open {temp_path}")
        elif sys.platform == 'darwin':
            os.system(f"open {temp_path}")
        else:
            os.startfile(temp_path)

        # Show info
        if self.gl_widget.selected_logo:
            logo_uv = self.gl_widget.selected_logo.uv_position
            QMessageBox.information(self, "UV Islands Visualization",
                f"UV visualization saved to:\n{temp_path}\n\n"
                f"The selected logo's UV coordinates are: ({logo_uv[0]:.3f}, {logo_uv[1]:.3f})\n\n"
                f"Different colors represent different faces.\n"
                f"Your hood is likely the area around these coordinates.")
        else:
            QMessageBox.information(self, "UV Islands Visualization",
                f"UV visualization saved to:\n{temp_path}\n\n"
                f"Select a logo to see its UV coordinates.")

    def export_model(self):
        """Export model with logos properly mapped to UV coordinates"""
        if not self.gl_widget.model_data:
            QMessageBox.warning(self, "Warning", "No model loaded to export")
            return

        if not self.gl_widget.logos:
            QMessageBox.warning(self, "Warning", "No logos to export")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Export Model with Logos", "", "OBJ Files (*.obj)")

        if save_path:
            try:
                if self.gl_widget.model_data.texture_path and os.path.exists(self.gl_widget.model_data.texture_path):
                    # Load original texture
                    original_texture = Image.open(self.gl_widget.model_data.texture_path)
                    original_texture = original_texture.convert('RGBA')

                    # Create overlay
                    overlay = Image.new('RGBA', original_texture.size, (0, 0, 0, 0))

                    for logo in self.gl_widget.logos:
                        # Start with original image
                        logo_img = Image.open(logo.image_path)
                        logo_img = logo_img.convert('RGBA')

                        # Calculate size in pixels
                        uv_width = logo.width / self.gl_widget.model_data.model_scale
                        uv_height = logo.height / self.gl_widget.model_data.model_scale

                        logo_width_px = int(uv_width * original_texture.width)
                        logo_height_px = int(uv_height * original_texture.height)

                        logo_width_px = max(10, min(logo_width_px, original_texture.width))
                        logo_height_px = max(10, min(logo_height_px, original_texture.height))

                        # Resize logo
                        logo_img = logo_img.resize((logo_width_px, logo_height_px), Image.Resampling.LANCZOS)

                        # Apply flips
                        if logo.flipped_x:
                            logo_img = logo_img.transpose(Image.FLIP_LEFT_RIGHT)
                        if logo.flipped_y:
                            logo_img = logo_img.transpose(Image.FLIP_TOP_BOTTOM)

                        # Apply rotation
                        if logo.rotation_z != 0:
                            logo_img = logo_img.rotate(logo.rotation_z, expand=True, fillcolor=(0,0,0,0))

                        # Position based on oriented UV coordinates
                        pos_x = int(logo.uv_position[0] * original_texture.width - logo_img.width / 2)
                        pos_y = int(logo.uv_position[1] * original_texture.height - logo_img.height / 2)

                        # Clamp to texture bounds
                        pos_x = max(0, min(pos_x, original_texture.width - logo_img.width))
                        pos_y = max(0, min(pos_y, original_texture.height - logo_img.height))

                        overlay.paste(logo_img, (pos_x, pos_y), logo_img)
                        print(f"Exported: {os.path.basename(logo.image_path)} - Oriented UV: ({logo.uv_position[0]:.3f}, {logo.uv_position[1]:.3f}) -> Pixel: ({pos_x}, {pos_y})")

                    # Composite textures
                    final_texture = Image.alpha_composite(original_texture, overlay)

                    # Save new texture
                    texture_dir = os.path.dirname(save_path)
                    texture_name = f"texture_with_logos_{os.path.basename(self.gl_widget.model_data.texture_path)}"
                    texture_path = os.path.join(texture_dir, texture_name)
                    final_texture.save(texture_path)

                    QMessageBox.information(self, "Export Complete",
                                          f"Model exported successfully!\nNew texture saved as: {texture_name}")
                else:
                    QMessageBox.warning(self, "Warning", "No base texture found for model")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export: {str(e)}")
                import traceback
                traceback.print_exc()

    def toggle_grid(self, checked):
        self.gl_widget.show_grid = checked
        self.gl_widget.update()
        if hasattr(self, 'grid_toggle') and self.grid_toggle:
            self.grid_toggle.setChecked(checked)

    def reset_view(self):
        self.gl_widget.rotation_x = 30
        self.gl_widget.rotation_y = 45
        self.gl_widget.zoom = -5
        self.gl_widget.update()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Highlight, QColor(142, 45, 197))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)

    viewer = ModelViewer()
    viewer.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
