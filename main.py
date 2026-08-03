import os
import json
import time
import traceback
from datetime import datetime

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.image import Image as KivyImage
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.metrics import dp, sp
from kivy.core.window import Window
from kivy.utils import platform
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.spinner import Spinner

# ---------- THƯ VIỆN ẢNH ----------
try:
    from PIL import Image, ImageDraw, ImageFont, ImageEnhance
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Pillow chưa được cài. Hãy chạy: pip install Pillow")

# ---------- KIỂM TRA NỀN TẢNG ----------
def is_android():
    return platform == "android"

# ---------- CẤU HÌNH ----------
HISTORY_FILE = "print_history.json"
SELECTED_PRINTER_FILE = "selected_printer.json"

# MÀU SẮC
COLOR_PRIMARY = (0.26, 0.65, 0.96, 1)
COLOR_PRIMARY_DARK = (0.12, 0.53, 0.90, 1)
COLOR_SUCCESS = (0.40, 0.73, 0.42, 1)
COLOR_WARNING = (1.0, 0.65, 0.15, 1)
COLOR_ERROR = (0.94, 0.33, 0.31, 1)
COLOR_GRAY = (0.6, 0.6, 0.6, 1)
COLOR_LIGHT_GRAY = (0.96, 0.96, 0.96, 1)
COLOR_WHITE = (1, 1, 1, 1)
COLOR_BLACK = (0.1, 0.1, 0.1, 1)

# ---------- HÀM LƯU/ĐỌC MÁY IN ĐÃ CHỌN ----------
def save_selected_printer(mac, name):
    try:
        with open(SELECTED_PRINTER_FILE, "w", encoding="utf-8") as f:
            json.dump({"mac": mac, "name": name}, f)
    except Exception as e:
        print("Cannot save selected printer:", e)

def load_selected_printer():
    if os.path.exists(SELECTED_PRINTER_FILE):
        try:
            with open(SELECTED_PRINTER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("mac"), data.get("name")
        except:
            return None, None
    return None, None

# ---------- HÀM TIỆN ÍCH LỊCH SỬ ----------
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(h):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(h, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Warning: cannot save history:", e)

def add_history_entry(order_id, customer, box_qty):
    h = load_history()
    h.append({
        "order_id": str(order_id),
        "customer": str(customer),
        "box_qty": int(box_qty),
        "timestamp": datetime.now().isoformat()
    })
    save_history(h)

def has_been_printed(order_id):
    h = load_history()
    return any(item.get("order_id") == str(order_id) for item in h)

# ---------- MODULE CHO ANDROID ----------
if is_android():
    from jnius import autoclass
    import socket
    import sys
    import traceback

    from kivy.uix.camera import Camera
    from android.permissions import request_permissions, Permission, check_permission

    # ==========================================================
    # camera4kivy
    # ==========================================================
    try:
        import camera4kivy

        print("=" * 80)
        print("camera4kivy module found")
        print("Module :", camera4kivy)
        print("File   :", getattr(camera4kivy, "__file__", "Unknown"))
        print("Version:", getattr(camera4kivy, "__version__", "Unknown"))

        from camera4kivy import Preview

        HAS_CAMERA4KIVY = True
        print("camera4kivy Preview imported successfully")
        print("=" * 80)

    except Exception:
        HAS_CAMERA4KIVY = False

        exc_type, exc_value, exc_tb = sys.exc_info()

        print("=" * 80)
        print("camera4kivy IMPORT FAILED")
        print("Exception Type :", exc_type.__name__)
        print("Exception      :", exc_value)
        print("-" * 80)

        traceback.print_exception(exc_type, exc_value, exc_tb)

        print("=" * 80)

    def request_android_permissions():
        try:
            permissions = [
                Permission.BLUETOOTH,
                Permission.BLUETOOTH_ADMIN,
                Permission.BLUETOOTH_CONNECT,
                Permission.BLUETOOTH_SCAN,
                Permission.ACCESS_FINE_LOCATION,
                Permission.CAMERA
            ]
            request_permissions(permissions)
        except Exception as e:
            print("request_android_permissions error:", e)

    def find_paired_printers_pyjnius():
        try:
            BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
            adapter = BluetoothAdapter.getDefaultAdapter()
            if adapter is None:
                return []

            paired = adapter.getBondedDevices()
            devices = []

            try:
                arr = paired.toArray()
                for dev in arr:
                    devices.append((dev.getName(), dev.getAddress()))
            except Exception:
                it = paired.iterator()
                while it.hasNext():
                    dev = it.next()
                    devices.append((dev.getName(), dev.getAddress()))

            return devices

        except Exception as e:
            print("find_paired_printers_pyjnius error:", e)
            return []

    def print_via_bluetooth_pyjnius(mac_addr, payload_bytes):
        try:
            UUID = autoclass('java.util.UUID')
            BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
            adapter = BluetoothAdapter.getDefaultAdapter()
            if adapter is None:
                return False, "Bluetooth không khả dụng"

            device = adapter.getRemoteDevice(mac_addr)
            spp_uuid = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")

            if adapter.isDiscovering():
                adapter.cancelDiscovery()

            max_retries = 3
            connected = False
            sock = None

            for attempt in range(max_retries):
                try:
                    print(f"Connect attempt {attempt+1}/{max_retries}...")
                    sock = device.createRfcommSocketToServiceRecord(spp_uuid)
                    sock.connect()
                    connected = True
                    break
                except Exception as e:
                    print(f"Connect attempt {attempt+1} failed: {e}")
                    if sock:
                        try:
                            sock.close()
                        except:
                            pass
                    if attempt < max_retries - 1:
                        time.sleep(1)

            if not connected:
                return False, "Không thể kết nối sau 3 lần thử"

            out = sock.getOutputStream()

            chunk_size = 512
            total_sent = 0

            for i in range(0, len(payload_bytes), chunk_size):
                chunk = payload_bytes[i:i+chunk_size]
                out.write(chunk)
                out.flush()
                total_sent += len(chunk)
                print(f"Sent {total_sent}/{len(payload_bytes)} bytes")
                time.sleep(0.05)

            time.sleep(1)

            out.close()
            sock.close()
            return True, None

        except Exception as e:
            print(f"Bluetooth print error: {e}")
            return False, str(e)

else:
    # PC: không dùng các module Android
    HAS_CAMERA4KIVY = False

# ---------- SCANNER CORE (ML Kit + Pyzbar) ----------
class ScannerCore:
    def __init__(self):
        self.use_mlkit = False
        self.mlkit_scanner = None
        if is_android():
            self._init_mlkit()
    
    def _init_mlkit(self):
        if not is_android():
            return
        try:
            BarcodeScannerOptions = autoclass('com.google.mlkit.vision.barcode.BarcodeScannerOptions')
            Barcode = autoclass('com.google.mlkit.vision.barcode.Barcode')
            BarcodeScanning = autoclass('com.google.mlkit.vision.barcode.BarcodeScanning')
            
            options = BarcodeScannerOptions.Builder()
            options.setBarcodeFormats(
                Barcode.FORMAT_QR_CODE |
                Barcode.FORMAT_CODE_128 |
                Barcode.FORMAT_EAN_13 |
                Barcode.FORMAT_EAN_8 |
                Barcode.FORMAT_UPC_A |
                Barcode.FORMAT_UPC_E |
                Barcode.FORMAT_CODE_39 |
                Barcode.FORMAT_CODE_93 |
                Barcode.FORMAT_ITF |
                Barcode.FORMAT_CODABAR
            ).build()
            self.mlkit_scanner = BarcodeScanning.getClient(options)
            self.use_mlkit = True
            print("✅ ML Kit Barcode Scanner initialized")
        except Exception as e:
            print(f"❌ ML Kit init error: {e}")
    
    def scan(self, image):
        if is_android() and self.use_mlkit and self.mlkit_scanner:
            try:
                data, fmt = self._scan_mlkit(image)
                if data:
                    return data, fmt
            except Exception as e:
                print(f"ML Kit error: {e}")
        
        # Fallback pyzbar (import trễ - không crash trên PC)
        try:
            from pyzbar.pyzbar import decode
            data, fmt = self._scan_pyzbar(image, decode)
            if data:
                return data, fmt
        except ImportError:
            pass
        except Exception as e:
            print(f"pyzbar error: {e}")
        
        return None, None
    
    def _scan_mlkit(self, image):
        try:
            import io
            from threading import Event
            
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=80)
            img_bytes = buffer.getvalue()
            
            BitmapFactory = autoclass('android.graphics.BitmapFactory')
            bitmap = BitmapFactory.decodeByteArray(img_bytes, 0, len(img_bytes))
            
            InputImage = autoclass('com.google.mlkit.vision.common.InputImage')
            input_image = InputImage.fromBitmap(bitmap, 0)
            
            result = [None, None]
            event = Event()
            
            self.mlkit_scanner.process(input_image).addOnSuccessListener(
                lambda barcodes: self._handle_result(barcodes, result, event)
            )
            self.mlkit_scanner.process(input_image).addOnFailureListener(
                lambda e: event.set()
            )
            
            event.wait(1.0)
            return result[0], result[1]
        except Exception as e:
            print(f"ML Kit scan error: {e}")
            return None, None
    
    def _handle_result(self, barcodes, result, event):
        try:
            if barcodes and barcodes.size() > 0:
                barcode = barcodes.get(0)
                raw = barcode.getRawValue()
                if raw:
                    result[0] = self._decode_universal(raw)
                    result[1] = str(barcode.getFormat())
        except Exception as e:
            print(f"Handle ML Kit result error: {e}")
        finally:
            event.set()
    
    def _scan_pyzbar(self, image, decode):
        try:
            img_gray = image.convert('L')
            enhancer = ImageEnhance.Contrast(img_gray)
            img_enhanced = enhancer.enhance(1.5)
            
            for test_img in [img_enhanced, img_gray, image]:
                try:
                    barcodes = decode(test_img.convert('RGB'))
                    if barcodes:
                        raw = barcodes[0].data
                        data = self._decode_universal(raw)
                        return data, barcodes[0].type
                except:
                    continue
        except Exception as e:
            print(f"pyzbar error: {e}")
        return None, None
    
    def _decode_universal(self, raw_data):
        if isinstance(raw_data, str):
            return raw_data
        
        encodings = [
            'utf-8', 'iso-8859-1', 'windows-1258', 'windows-1252',
            'gbk', 'gb2312', 'shift-jis', 'euc-kr',
            'ascii', 'latin-1', 'cp437', 'mac-roman',
            'cp1252', 'cp1258', 'utf-16', 'utf-16le'
        ]
        
        for enc in encodings:
            try:
                decoded = raw_data.decode(enc)
                if decoded and any(c.isprintable() for c in decoded[:100]):
                    return decoded
            except:
                continue
        
        return raw_data.decode('utf-8', errors='ignore')

# Singleton
_scanner_core = None
def get_scanner_core():
    global _scanner_core
    if _scanner_core is None:
        _scanner_core = ScannerCore()
    return _scanner_core

# =========================================================
# MÀN HÌNH SCANNER (CAMERA4KIVY + ML KIT + PYZBAR) - ĐÃ SỬA LỖI
# =========================================================
class ScannerScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(4))
        
        # Header
        header = BoxLayout(size_hint_y=None, height=dp(44))
        back_btn = Button(text="Trang chủ", font_size=sp(14), size_hint_x=None, width=dp(80),
                          background_color=COLOR_GRAY, color=COLOR_WHITE)
        back_btn.bind(on_release=self.go_back)
        title = Label(text="SCAN QR / BARCODE", font_size=sp(16), bold=True, color=COLOR_PRIMARY_DARK)
        header.add_widget(back_btn)
        header.add_widget(title)
        self.layout.add_widget(header)
        
        # Status
        self.status_label = Label(text="Đang khởi tạo camera...", font_size=sp(14),
                                  size_hint_y=None, height=dp(30), color=COLOR_GRAY)
        self.layout.add_widget(self.status_label)
        
        # Camera preview
        if is_android() and HAS_CAMERA4KIVY:
            self.preview = Preview(aspect_ratio='16:9', size_hint=(1, 0.75))
        else:
            self.preview = Label(text="📱 Camera chỉ hỗ trợ trên Android", font_size=sp(16), color=COLOR_GRAY)
        self.layout.add_widget(self.preview)
        
        # Result
        self.result_label = Label(text="", font_size=sp(16), size_hint_y=None,
                                  height=dp(30), color=COLOR_SUCCESS, bold=True)
        self.layout.add_widget(self.result_label)
        
        # Buttons
        btn_box = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
        self.retry_btn = Button(text="Quét lại", font_size=sp(14),
                                background_color=COLOR_PRIMARY, color=COLOR_WHITE)
        self.retry_btn.bind(on_release=self.restart_scan)
        home_btn = Button(text="Trang chủ", font_size=sp(14),
                          background_color=COLOR_SUCCESS, color=COLOR_WHITE)
        home_btn.bind(on_release=self.go_back_with_current_data)
        btn_box.add_widget(self.retry_btn)
        btn_box.add_widget(home_btn)
        self.layout.add_widget(btn_box)
        
        self.add_widget(self.layout)
        
        # Trạng thái
        self.is_scanning = False
        self.scanned_data = None
        self._permission_popup = None
        self._last_scan_time = 0
        self._scan_cooldown = 0.3
        self._camera_connected = False
        
        # Scanner core
        self.scanner_core = get_scanner_core() if is_android() else None

    def on_enter(self):
        if not is_android():
            self.status_label.text = "Camera chỉ hỗ trợ Android"
            return
        
        if not HAS_CAMERA4KIVY:
            self.status_label.text = "❌ camera4kivy chưa được cài!"
            return
        
        # =========================================================
        # FIX 1: KHÔNG gọi _connect_camera trực tiếp, luôn dùng Clock
        # =========================================================
        if check_permission(Permission.CAMERA):
            self.status_label.text = "Đang mở camera..."
            Clock.schedule_once(lambda dt: self._connect_camera(), 0.5)
        else:
            self.status_label.text = "Đang yêu cầu quyền camera..."
            self._request_camera_permission()

    def _request_camera_permission(self):
        try:
            request_permissions([Permission.CAMERA], self._on_permission_result)
        except Exception as e:
            print(f"Permission request error: {e}")
            self.status_label.text = "Không thể yêu cầu quyền"

    def _on_permission_result(self, permissions, grant_results):
        # =========================================================
        # FIX 2: Đảm bảo callback chạy trên main thread Kivy
        # =========================================================
        Clock.schedule_once(lambda dt: self._handle_permission_result(permissions, grant_results), 0)

    def _handle_permission_result(self, permissions, grant_results):
        if grant_results and len(grant_results) > 0 and grant_results[0]:
            self.status_label.text = "Đã cấp quyền, đang mở camera..."
            Clock.schedule_once(lambda dt: self._connect_camera(), 0.5)
        else:
            self.status_label.text = "Chưa cấp quyền Camera"
            Clock.schedule_once(lambda dt: self._show_permission_guide(), 0.3)

    def _show_permission_guide(self):
        if self._permission_popup:
            return
        
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        guide_text = (
            "Camera chưa được cấp quyền.\n\n"
            "Vui lòng thử 1 trong 2 cách:\n\n"
            "CÁCH 1: Bấm 'Mở Cài đặt'\n"
            "-> Tìm mục Quyền -> Bật Camera\n\n"
            "CÁCH 2: Vào Cài đặt điện thoại\n"
            "-> Ứng dụng -> Order Printer\n"
            "-> Quyền -> Bật Camera\n\n"
            "Sau đó bấm nút SCAN lại."
        )
        lbl = Label(text=guide_text, font_size=sp(14), halign='left', valign='top')
        lbl.bind(size=lambda instance, value: setattr(instance, 'text_size', (value[0] - dp(20), None)))
        content.add_widget(lbl)
        
        btn_box = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
        btn_open_settings = Button(text="Mở Cài đặt", font_size=sp(14),
                                   background_color=COLOR_PRIMARY, color=COLOR_WHITE)
        btn_open_settings.bind(on_release=self._open_app_settings)
        btn_manual = Button(text="Nhập tay", font_size=sp(14),
                            background_color=COLOR_SUCCESS, color=COLOR_WHITE)
        btn_manual.bind(on_release=self._go_back_and_manual)
        btn_box.add_widget(btn_open_settings)
        btn_box.add_widget(btn_manual)
        content.add_widget(btn_box)
        
        self._permission_popup = Popup(title="Cần cấp quyền Camera", content=content,
                                       size_hint=(0.92, 0.55), auto_dismiss=True)
        self._permission_popup.bind(on_dismiss=lambda x: setattr(self, '_permission_popup', None))
        self._permission_popup.open()

    def _open_app_settings(self, *args):
        try:
            if is_android():
                Intent = autoclass('android.content.Intent')
                Settings = autoclass('android.provider.Settings')
                Uri = autoclass('android.net.Uri')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                intent = Intent()
                intent.setAction(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
                uri = Uri.fromParts("package", PythonActivity.getPackageName(), None)
                intent.setData(uri)
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                PythonActivity.mActivity.startActivity(intent)
        except Exception as e:
            print(f"Open settings error: {e}")

    def _go_back_and_manual(self, *args):
        self.go_back()

    def _connect_camera(self):
        if self._camera_connected or not is_android():
            return
        
        # =========================================================
        # FIX 3: Tách connect_camera thành 2 bước, delay thêm 0.3s
        # =========================================================
        Clock.schedule_once(lambda dt: self._do_connect_camera(), 0.3)

    def _do_connect_camera(self):
        try:
            # =========================================================
            # FIX 4: THÊM enable_video=False - GIẢM TẢI PHẦN CỨNG
            # =========================================================
            self.preview.connect_camera(
                enable_analyze_pixels=True,
                enable_video=False,  # ← QUAN TRỌNG: KHÔNG BẬT VIDEO
                analyze_pixels_resolution=(640, 480)
            )
            self.preview.analyze_pixels_callback = self.analyze_pixels
            self._camera_connected = True
            self.status_label.text = "Đang scan..."
            self.is_scanning = True
            print("✅ Camera connected (camera4kivy) with enable_video=False")
        except Exception as e:
            self.status_label.text = f"Lỗi camera: {str(e)[:40]}"
            print(f"Camera connect error: {e}")
            import traceback
            traceback.print_exc()

    def analyze_pixels(self, pixels, image_size, image_pos, scale, mirror):
        if not self.is_scanning or not is_android():
            return
        
        now = time.time()
        if now - self._last_scan_time < self._scan_cooldown:
            return
        self._last_scan_time = now
        
        try:
            width, height = image_size
            if width == 0 or height == 0:
                return
            
            img = Image.frombytes('RGBA', (width, height), pixels)
            
            if self.scanner_core:
                data, fmt = self.scanner_core.scan(img)
                if data:
                    self._on_scan_success(data, fmt)
        except Exception as e:
            print(f"Analyze pixels error: {e}")

    def _on_scan_success(self, data, fmt):
        self.scanned_data = data
        self.result_label.text = f"Đã quét: {data[:50]}"
        self.status_label.text = f"✅ {fmt}! Đang quay về..."
        self.is_scanning = False
        if hasattr(self.preview, 'analyze_pixels_callback'):
            self.preview.analyze_pixels_callback = None
        Clock.schedule_once(lambda dt: self.go_back_with_data(), 0.5)

    def restart_scan(self, *args):
        self.scanned_data = None
        self.result_label.text = ""
        self.status_label.text = "Đang khởi động lại camera..."
        self.is_scanning = True
        if hasattr(self.preview, 'analyze_pixels_callback'):
            self.preview.analyze_pixels_callback = self.analyze_pixels

    def go_back(self, *args):
        self.scanned_data = None
        self._disconnect_camera()
        self.manager.current = "home"

    def go_back_with_data(self, *args):
        data = self.scanned_data
        self.scanned_data = None
        self._disconnect_camera()
        if data:
            home = self.manager.get_screen("home")
            if '\n' in data:
                lines = data.strip().split('\n')
                if hasattr(home, 'so_input') and len(lines) >= 1:
                    home.so_input.text = lines[0].strip()
                if hasattr(home, 'name_input') and len(lines) >= 2:
                    home.name_input.text = lines[1].strip()
            else:
                if hasattr(home, 'so_input'):
                    home.so_input.text = data
        self.manager.current = "home"

    def go_back_with_current_data(self, *args):
        data = self.scanned_data
        self.scanned_data = None
        self._disconnect_camera()
        if data:
            home = self.manager.get_screen("home")
            if '\n' in data:
                lines = data.strip().split('\n')
                if hasattr(home, 'so_input') and len(lines) >= 1:
                    home.so_input.text = lines[0].strip()
                if hasattr(home, 'name_input') and len(lines) >= 2:
                    home.name_input.text = lines[1].strip()
            else:
                if hasattr(home, 'so_input'):
                    home.so_input.text = data
        self.manager.current = "home"

    def _disconnect_camera(self):
        if self._camera_connected and is_android():
            try:
                self.preview.disconnect_camera()
                self._camera_connected = False
                print("✅ Camera disconnected")
            except Exception as e:
                print(f"Disconnect camera error: {e}")

    def on_leave(self):
        self.is_scanning = False
        self._disconnect_camera()
        if self._permission_popup:
            self._permission_popup.dismiss()

# ---------- HÀM TÌM FONT TRÊN HỆ THỐNG ----------
def find_system_font_bold():
    if is_android():
        font_paths = [
            "/system/fonts/Roboto-Bold.ttf",
            "/system/fonts/DroidSans-Bold.ttf",
            "/system/fonts/NotoSans-Bold.ttf",
        ]
        for path in font_paths:
            if os.path.exists(path):
                return path
        return None
    
    if platform == "win":
        font_paths = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/timesbd.ttf",
        ]
        for path in font_paths:
            if os.path.exists(path):
                return path
    
    if platform == "darwin":
        font_paths = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Arial.ttf",
        ]
        for path in font_paths:
            if os.path.exists(path):
                return path
    
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return path
    
    return None

def find_system_font():
    if is_android():
        font_paths = [
            "/system/fonts/Roboto-Regular.ttf",
            "/system/fonts/DroidSans.ttf",
            "/system/fonts/NotoSans-Regular.ttf",
        ]
        for path in font_paths:
            if os.path.exists(path):
                return path
        return find_system_font_bold()
    
    if platform == "win":
        font_paths = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/times.ttf",
            "C:/Windows/Fonts/calibri.ttf",
        ]
        for path in font_paths:
            if os.path.exists(path):
                return path
        return find_system_font_bold()
    
    if platform == "darwin":
        font_paths = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Arial.ttf",
        ]
        for path in font_paths:
            if os.path.exists(path):
                return path
        return find_system_font_bold()
    
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return path
    
    return None

# ---------- TẠO ẢNH PREVIEW (115x70mm) ----------
def create_label_image(order_id, customer, box_index, box_total,
                       width_mm=115, height_mm=70, dpi=203):
    if not HAS_PIL:
        raise ImportError("Pillow chưa được cài đặt.")

    width_px = int(width_mm / 25.4 * dpi)
    height_px = int(height_mm / 25.4 * dpi)

    img = Image.new('RGB', (width_px, height_px), 'white')
    draw = ImageDraw.Draw(img)

    font_bold_path = find_system_font_bold()
    if font_bold_path:
        try:
            font_order_bold = ImageFont.truetype(font_bold_path, size=70)
        except:
            font_order_bold = ImageFont.load_default()
    else:
        font_order_bold = ImageFont.load_default()
    
    font_path = find_system_font()
    if font_path:
        try:
            font_name = ImageFont.truetype(font_path, size=65)
            font_box = ImageFont.truetype(font_path, size=67)
        except:
            font_name = ImageFont.load_default()
            font_box = ImageFont.load_default()
    else:
        font_name = ImageFont.load_default()
        font_box = ImageFont.load_default()

    padding_x = int(width_px * 0.03)
    padding_y = int(height_px * 0.04)

    usable_height = height_px - padding_y * 2
    section_height = usable_height / 3

    y1 = int(padding_y + section_height * 0.1)
    draw.text((int(padding_x), y1), order_id, fill='black', font=font_order_bold)

    y2 = int(padding_y + section_height + section_height * 0.1)
    draw.text((int(padding_x), y2), customer, fill='black', font=font_name)

    y3 = int(padding_y + section_height * 2 + section_height * 0.1)
    box_text = f"Box: #{box_index} / {box_total}"
    bbox = draw.textbbox((0, 0), box_text, font=font_box)
    text_width = bbox[2] - bbox[0]
    x_pos = int(width_px - text_width - padding_x)
    draw.text((x_pos, int(y3)), box_text, fill='black', font=font_box)

    return img

# ---------- TẠO ẢNH RASTER CHO ZPL2 ----------
def create_zpl_raster(order_id, customer, box_index, box_total,
                      width_mm=115, height_mm=70, dpi=203):
    if not HAS_PIL:
        raise ImportError("Pillow chưa được cài đặt.")

    width_px = int(width_mm / 25.4 * dpi)
    height_px = int(height_mm / 25.4 * dpi)

    img = Image.new('RGB', (width_px, height_px), 'white')
    draw = ImageDraw.Draw(img)

    font_bold_path = find_system_font_bold()
    if font_bold_path:
        try:
            font_order_bold = ImageFont.truetype(font_bold_path, size=130)
        except:
            font_order_bold = ImageFont.load_default()
    else:
        font_order_bold = ImageFont.load_default()
    
    font_path = find_system_font()
    if font_path:
        try:
            font_name = ImageFont.truetype(font_path, size=85)
            font_box = ImageFont.truetype(font_path, size=90)
        except:
            font_name = ImageFont.load_default()
            font_box = ImageFont.load_default()
    else:
        font_name = ImageFont.load_default()
        font_box = ImageFont.load_default()

    padding_x = int(width_px * 0.03)
    padding_y = int(height_px * 0.03)

    usable_height = height_px - padding_y * 2
    section_height = usable_height / 3

    y1 = int(padding_y + section_height * 0.05)
    draw.text((int(padding_x), y1), order_id, fill='black', font=font_order_bold)

    y2 = int(padding_y + section_height + section_height * 0.05)
    draw.text((int(padding_x), y2), customer, fill='black', font=font_name)

    y3 = int(padding_y + section_height * 2 + section_height * 0.05)
    box_text = f"Box: #{box_index} / {box_total}"
    bbox = draw.textbbox((0, 0), box_text, font=font_box)
    text_width = bbox[2] - bbox[0]
    x_pos = int(width_px - text_width - padding_x)
    draw.text((x_pos, int(y3)), box_text, fill='black', font=font_box)

    img_rotated = img.rotate(90, expand=True)
    img_bw = img_rotated.convert('1')
    
    return img_bw

def pil_to_zpl_gf_raw(img):
    if img.mode != '1':
        img = img.convert('1')

    width, height = img.size
    width_bytes = (width + 7) // 8

    pixels = img.load()
    hex_list = []

    for y in range(height):
        byte = 0
        bit = 7
        for x in range(width):
            if pixels[x, y] == 0:
                byte |= (1 << bit)
            bit -= 1
            if bit < 0:
                hex_list.append(f'{byte:02X}')
                byte = 0
                bit = 7
        if bit != 7:
            hex_list.append(f'{byte:02X}')

    hex_data = ''.join(hex_list)
    total_bytes = len(hex_data) // 2

    return width_bytes, height, total_bytes, hex_data

def pil_to_hex(img):
    if img.mode != '1':
        img = img.convert('1')
    
    width, height = img.size
    pixels = img.load()
    hex_list = []
    
    for y in range(height):
        byte = 0
        bit = 7
        for x in range(width):
            if pixels[x, y] == 0:
                byte |= (1 << bit)
            bit -= 1
            if bit < 0:
                hex_list.append(f'{byte:02X}')
                byte = 0
                bit = 7
        if bit != 7:
            hex_list.append(f'{byte:02X}')
    
    return ''.join(hex_list)

def pil_to_zpl_gf_chunked(img, max_bytes_per_chunk=30*1024):
    if img.mode != '1':
        img = img.convert('1')
    
    width, height = img.size
    width_bytes = (width + 7) // 8
    
    bytes_per_row = width_bytes
    max_rows_per_chunk = max_bytes_per_chunk // bytes_per_row
    if max_rows_per_chunk < 1:
        max_rows_per_chunk = 1
    
    chunks = []
    pixels = img.load()
    
    for start_y in range(0, height, max_rows_per_chunk):
        end_y = min(start_y + max_rows_per_chunk, height)
        chunk_height = end_y - start_y
        
        chunk_img = Image.new('1', (width, chunk_height), 1)
        chunk_pixels = chunk_img.load()
        
        for y in range(chunk_height):
            for x in range(width):
                chunk_pixels[x, y] = pixels[x, start_y + y]
        
        hex_data = pil_to_hex(chunk_img)
        total_bytes = len(hex_data) // 2
        
        chunks.append({
            'width_bytes': width_bytes,
            'height': chunk_height,
            'total_bytes': total_bytes,
            'hex_data': hex_data,
            'start_y': start_y
        })
    
    return chunks

def get_label_zpl_bytes(order_id, customer, box_index, box_total):
    img = create_zpl_raster(order_id, customer, box_index, box_total,
                            width_mm=115, height_mm=70, dpi=203)

    chunks = pil_to_zpl_gf_chunked(img, max_bytes_per_chunk=30*1024)

    width_px, height_px = img.size

    cmd = ""
    cmd += "^XA\n"
    cmd += f"^PW{width_px}\n"
    cmd += f"^LL{height_px}\n"
    
    for chunk in chunks:
        cmd += f"^FO0,{chunk['start_y']}\n"
        cmd += f"^GFA,{chunk['total_bytes']},{chunk['total_bytes']},{chunk['width_bytes']},{chunk['hex_data']}\n"
        cmd += "^FS\n"
    
    cmd += "^PQ1\n"
    cmd += "^XZ\n"

    return cmd.encode('utf-8')

# ---------- MÀN HÌNH PHỤ ----------
class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        layout.add_widget(Label(text="CÀI ĐẶT", font_size=sp(24), bold=True,
                                size_hint_y=None, height=dp(50), color=COLOR_PRIMARY_DARK))
        layout.add_widget(Label(text="Chọn máy in mặc định, cổng, v.v...\n(Đang phát triển)",
                                font_size=sp(16), color=COLOR_GRAY))
        btn_back = Button(text="Về trang chủ", size_hint_y=None, height=dp(48),
                          background_color=COLOR_GRAY, color=COLOR_WHITE, font_size=sp(16))
        btn_back.bind(on_release=lambda *_: setattr(self.manager, "current", "home"))
        layout.add_widget(btn_back)
        self.add_widget(layout)

class PrinterManagerScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        layout.add_widget(Label(text="MÁY IN", font_size=sp(24), bold=True,
                                size_hint_y=None, height=dp(50), color=COLOR_PRIMARY_DARK))
        
        layout.add_widget(Label(text="Chọn máy in mặc định:", font_size=sp(16), color=COLOR_GRAY,
                                size_hint_y=None, height=dp(30)))
        
        self.printer_spinner = Spinner(
            text="-- Chọn máy in --",
            values=["-- Chọn máy in --"],
            size_hint_y=None,
            height=dp(44),
            background_color=(1,1,1,1),
            color=COLOR_BLACK,
            font_size=sp(16)
        )
        self.printer_spinner.bind(text=self.on_printer_selected)
        layout.add_widget(self.printer_spinner)
        
        self.device_list = ScrollView()
        self.container = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
        self.container.bind(minimum_height=self.container.setter('height'))
        self.device_list.add_widget(self.container)
        layout.add_widget(self.device_list)
        
        btn_refresh = Button(text="Làm mới danh sách", size_hint_y=None, height=dp(40),
                             background_color=COLOR_PRIMARY, color=COLOR_WHITE, font_size=sp(14))
        btn_refresh.bind(on_release=lambda x: self.refresh_devices())
        layout.add_widget(btn_refresh)
        
        btn_test = Button(text="Test kết nối", size_hint_y=None, height=dp(40),
                          background_color=COLOR_WARNING, color=COLOR_WHITE, font_size=sp(14))
        btn_test.bind(on_release=self.test_connection)
        layout.add_widget(btn_test)
        
        btn_back = Button(text="Về trang chủ", size_hint_y=None, height=dp(48),
                          background_color=COLOR_GRAY, color=COLOR_WHITE, font_size=sp(16))
        btn_back.bind(on_release=lambda *_: setattr(self.manager, "current", "home"))
        layout.add_widget(btn_back)
        
        self.add_widget(layout)

    def on_enter(self, *args):
        self.refresh_devices()

    def refresh_devices(self):
        self.container.clear_widgets()
        
        if not is_android():
            self.container.add_widget(Label(text="(Chức năng này chỉ có trên Android)",
                                          font_size=sp(16), color=COLOR_GRAY))
            return
        
        devices = find_paired_printers_pyjnius()
        
        if devices:
            spinner_values = ["-- Chọn máy in --"]
            for name, addr in devices:
                spinner_values.append(f"{name} ({addr[-6:]})")
            self.printer_spinner.values = spinner_values
        
        if not devices:
            self.container.add_widget(Label(text="Chưa có máy in Bluetooth nào được ghép nối",
                                          font_size=sp(16), color=COLOR_GRAY))
            return
        
        selected_mac, selected_name = load_selected_printer()
        
        if selected_name and selected_mac:
            for name, addr in devices:
                if addr == selected_mac:
                    self.printer_spinner.text = f"{name} ({addr[-6:]})"
                    break
        
        for name, addr in devices:
            row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
            
            is_selected = (addr == selected_mac)
            
            lbl = Label(text=f"{name}", font_size=sp(16), color=COLOR_BLACK,
                       halign='left', valign='middle', size_hint_x=0.5)
            lbl.bind(size=lbl.setter('text_size'))
            row.add_widget(lbl)
            
            mac_lbl = Label(text=addr[-6:], font_size=sp(12), color=COLOR_GRAY,
                           halign='left', valign='middle', size_hint_x=0.25)
            mac_lbl.bind(size=mac_lbl.setter('text_size'))
            row.add_widget(mac_lbl)
            
            if is_selected:
                status = Label(text="Đã chọn", font_size=sp(12), color=COLOR_SUCCESS,
                               halign='center', valign='middle', size_hint_x=0.25)
                status.bind(size=status.setter('text_size'))
                row.add_widget(status)
            else:
                btn = Button(text="Chọn", size_hint_x=0.25,
                            background_color=COLOR_PRIMARY, color=COLOR_WHITE,
                            font_size=sp(12))
                btn.bind(on_release=lambda x, a=addr, n=name: self.select_printer(a, n))
                row.add_widget(btn)
            
            self.container.add_widget(row)

    def on_printer_selected(self, spinner, text):
        if text == "-- Chọn máy in --":
            return
        
        devices = find_paired_printers_pyjnius()
        for name, addr in devices:
            if f"{name} ({addr[-6:]})" == text:
                self.select_printer(addr, name)
                break

    def select_printer(self, mac, name):
        save_selected_printer(mac, name)
        self.refresh_devices()
        popup = Popup(title="Đã chọn", 
                      content=Label(text=f"Đã chọn máy in:\n{name}"),
                      size_hint=(.8,.4))
        popup.open()

    def test_connection(self, *args):
        mac, name = load_selected_printer()
        if mac is None:
            Popup(title="Lỗi", content=Label(text="Chưa chọn máy in!"),
                  size_hint=(.8,.4)).open()
            return
        
        test_data = b'^XA\n^FO50,50^ADN,36,20^FDTest Connection^FS\n^XZ\n'
        ok, err = print_via_bluetooth_pyjnius(mac, test_data)
        
        if ok:
            Popup(title="Thành công", 
                  content=Label(text=f"Kết nối với {name} thành công!"),
                  size_hint=(.8,.4)).open()
        else:
            Popup(title="Lỗi", 
                  content=Label(text=f"Kết nối thất bại:\n{err}"),
                  size_hint=(.8,.4)).open()

class HistoryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))
        root.add_widget(Label(text="LỊCH SỬ IN", font_size=sp(24), bold=True,
                              size_hint_y=None, height=dp(50), color=COLOR_PRIMARY_DARK))
        scroll = ScrollView()
        self.container = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
        self.container.bind(minimum_height=self.container.setter('height'))
        scroll.add_widget(self.container)
        root.add_widget(scroll)
        btn_back = Button(text="Về trang chủ", size_hint_y=None, height=dp(48),
                          background_color=COLOR_GRAY, color=COLOR_WHITE, font_size=sp(16))
        btn_back.bind(on_release=lambda *_: setattr(self.manager, "current", "home"))
        root.add_widget(btn_back)
        self.add_widget(root)

    def on_enter(self, *args):
        self.refresh_history()

    def refresh_history(self):
        self.container.clear_widgets()
        data = load_history()
        counts = {}
        for it in data:
            oid = it.get("order_id")
            counts[oid] = counts.get(oid, 0) + 1
        for it in reversed(data):
            oid = it.get("order_id", "?")
            cust = it.get("customer", "?")
            box_qty = it.get("box_qty", 0)
            timestamp = it.get("timestamp", "")
            try:
                date_str = datetime.fromisoformat(timestamp).strftime("%d/%m/%Y %H:%M")
            except:
                date_str = timestamp[:16]
            is_duplicate = counts.get(oid, 0) > 1
            text_color = COLOR_ERROR if is_duplicate else COLOR_BLACK
            text = f"{oid}  |  {cust}  |  {box_qty} box  |  {date_str}"
            row = BoxLayout(size_hint_y=None, height=dp(40), padding=[dp(10),0,dp(10),0])
            lbl = Label(text=text, font_size=sp(16), color=text_color, halign='left', valign='middle')
            lbl.bind(size=lbl.setter('text_size'))
            row.add_widget(lbl)
            self.container.add_widget(row)

# ---------- MÀN HÌNH CHÍNH (HOME) ----------
class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.clearcolor = COLOR_WHITE

        main_layout = BoxLayout(orientation='vertical')

        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        content = BoxLayout(orientation='vertical', size_hint_y=None, padding=dp(12), spacing=dp(8))
        content.bind(minimum_height=content.setter('height'))

        # === SO NUM + NÚT SCAN CÙNG DÒNG ===
        so_box = BoxLayout(orientation='horizontal', spacing=dp(8), size_hint_y=None, height=dp(44))
        self.so_input = TextInput(hint_text="SO Num", font_size=sp(18), multiline=False,
                                  size_hint_x=0.7, background_color=(0.95,0.95,0.95,1),
                                  foreground_color=COLOR_BLACK, padding=[dp(10), dp(6)])
        scan_btn = Button(text="SCAN", font_size=sp(14), size_hint_x=0.3,
                          background_color=COLOR_PRIMARY, color=COLOR_WHITE, bold=True)
        scan_btn.bind(on_release=self.open_scanner)
        so_box.add_widget(self.so_input)
        so_box.add_widget(scan_btn)
        content.add_widget(so_box)

        self.name_input = TextInput(hint_text="Name", font_size=sp(18), multiline=False,
                                    size_hint_y=None, height=dp(44),
                                    background_color=(0.95,0.95,0.95,1),
                                    foreground_color=COLOR_BLACK, padding=[dp(10), dp(6)])
        content.add_widget(self.name_input)

        self.box_input = TextInput(hint_text="Box", font_size=sp(18), multiline=False,
                                   input_filter='int', size_hint_y=None, height=dp(44),
                                   background_color=(0.95,0.95,0.95,1),
                                   foreground_color=COLOR_BLACK, padding=[dp(10), dp(6)])
        content.add_widget(self.box_input)

        btn_print = Button(text="IN TEM", font_size=sp(20), bold=True,
                           size_hint_y=None, height=dp(50),
                           background_color=COLOR_SUCCESS, color=COLOR_WHITE)
        btn_print.bind(on_release=self.on_print)
        content.add_widget(btn_print)

        btn_test = Button(text="TEST IN", font_size=sp(16), bold=True,
                          size_hint_y=None, height=dp(40),
                          background_color=COLOR_WARNING, color=COLOR_WHITE)
        btn_test.bind(on_release=self.test_print)
        content.add_widget(btn_test)

        preview_box = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(500), spacing=dp(4))
        preview_label = Label(text="Preview tem", font_size=sp(16), color=COLOR_GRAY,
                              size_hint_y=None, height=dp(24))
        preview_box.add_widget(preview_label)

        img_frame = BoxLayout(size_hint=(1, 0.85), padding=dp(4))
        with img_frame.canvas.before:
            Color(0.92, 0.92, 0.92, 1)
            self.img_bg = RoundedRectangle(pos=img_frame.pos, size=img_frame.size, radius=[6])
        img_frame.bind(pos=self._update_bg, size=self._update_bg)
        self.preview_image = KivyImage(size_hint=(1, 1), keep_ratio=True)
        img_frame.add_widget(self.preview_image)
        preview_box.add_widget(img_frame)

        nav_box = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(12))
        self.prev_btn = Button(text="Trước", font_size=sp(14), size_hint_x=0.3,
                               background_color=COLOR_GRAY, color=COLOR_WHITE)
        self.prev_btn.bind(on_release=self.prev_page)
        self.page_label = Label(text="1/1", font_size=sp(14), size_hint_x=0.4,
                                color=COLOR_BLACK)
        self.next_btn = Button(text="Tiếp", font_size=sp(14), size_hint_x=0.3,
                               background_color=COLOR_GRAY, color=COLOR_WHITE)
        self.next_btn.bind(on_release=self.next_page)
        nav_box.add_widget(self.prev_btn)
        nav_box.add_widget(self.page_label)
        nav_box.add_widget(self.next_btn)
        preview_box.add_widget(nav_box)

        content.add_widget(preview_box)

        scroll.add_widget(content)
        main_layout.add_widget(scroll)

        nav_bottom = BoxLayout(size_hint_y=None, height=dp(48), spacing=0)
        tabs = ["Nhập liệu", "Lịch sử", "Máy in", "Cài đặt"]
        screen_map = {
            "Nhập liệu": "home",
            "Lịch sử": "history",
            "Máy in": "printer_manager",
            "Cài đặt": "settings"
        }
        for label in tabs:
            btn = Button(text=label, font_size=sp(14),
                         background_color=COLOR_LIGHT_GRAY, color=COLOR_BLACK,
                         halign='center', valign='middle')
            btn.bind(on_release=lambda x, sn=screen_map[label]: self.switch_tab(sn))
            nav_bottom.add_widget(btn)

        main_layout.add_widget(nav_bottom)
        self.add_widget(main_layout)

        self.current_order_id = ""
        self.current_customer = ""
        self.total_boxes = 0
        self.current_page = 0
        self.label_images = []

    def _update_bg(self, *args):
        self.img_bg.pos = self.preview_image.parent.pos
        self.img_bg.size = self.preview_image.parent.size

    def switch_tab(self, screen_name):
        if screen_name == "home":
            return
        else:
            self.manager.current = screen_name

    def open_scanner(self, *args):
        """Mở màn hình scanner"""
        if not is_android():
            Popup(title="Thông báo", 
                  content=Label(text="Tính năng scan chỉ hỗ trợ trên Android.\nVui lòng nhập mã đơn hàng thủ công."),
                  size_hint=(.8,.5)).open()
            return
        
        if not HAS_CAMERA4KIVY:
            Popup(title="Thông báo", 
                  content=Label(text="camera4kivy chưa được cài!\nVui lòng cài:\npip install camera4kivy"),
                  size_hint=(.8,.5)).open()
            return
        
        try:
            if not self.manager.has_screen("scanner"):
                self.manager.add_widget(ScannerScreen(name="scanner"))
            self.manager.current = "scanner"
        except Exception as e:
            print(f"Open scanner error: {e}")
            Popup(title="Lỗi", content=Label(text=f"Không thể mở camera:\n{str(e)[:50]}"),
                  size_hint=(.8,.4)).open()

    def test_print(self, *args):
        if not is_android():
            Popup(title="Thông báo", content=Label(text="Chỉ hoạt động trên Android"),
                  size_hint=(.8,.4)).open()
            return

        mac, name = load_selected_printer()
        if mac is None:
            devices = find_paired_printers_pyjnius()
            if not devices:
                Popup(title="Lỗi", content=Label(text="Không tìm thấy máy in Bluetooth"),
                      size_hint=(.8,.4)).open()
                return
            mac = devices[0][1]
            name = devices[0][0]
            save_selected_printer(mac, name)

        test_data = b'^XA\n^FO50,50^ADN,36,20^FDTest Print^FS\n'
        test_data += b'^FO50,80^ADN,24,16^FDDevelop by Huy Pham.^FS\n'
        test_data += b'^XZ\n'

        popup_content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        status_label = Label(text="Đang in test...", font_size=sp(16))
        popup_content.add_widget(status_label)
        popup = Popup(title="Test Print", content=popup_content, size_hint=(.8,.4))
        popup.open()

        def do_test(dt):
            ok, err = print_via_bluetooth_pyjnius(mac, test_data)
            popup.dismiss()
            if ok:
                Popup(title="Thành công",
                      content=Label(text=f"Test in thành công!\nMáy: {name}"),
                      size_hint=(.8,.4)).open()
            else:
                Popup(title="Lỗi",
                      content=Label(text=f"Test in thất bại:\n{err}"),
                      size_hint=(.8,.4)).open()

        Clock.schedule_once(do_test, 0.5)

    def on_print(self, *args):
        oid = self.so_input.text.strip()
        cust = self.name_input.text.strip()
        box = self.box_input.text.strip()
        if not oid or not cust or not box:
            Popup(title="Thiếu thông tin", content=Label(text="Vui lòng nhập đầy đủ!"),
                  size_hint=(.8,.4)).open()
            return
        try:
            box_n = int(box)
            if box_n <= 0: raise ValueError
        except:
            Popup(title="Lỗi", content=Label(text="Box phải là số nguyên dương"),
                  size_hint=(.8,.4)).open()
            return

        self.current_order_id = oid
        self.current_customer = cust
        self.total_boxes = box_n
        self.current_page = 0
        self.label_images = []
        for i in range(box_n):
            try:
                img = create_label_image(oid, cust, i+1, box_n)
                self.label_images.append(img)
            except Exception as e:
                Popup(title="Lỗi tạo ảnh", content=Label(text=f"{e}"), size_hint=(.8,.4)).open()
                return
        self.update_preview()

        if has_been_printed(oid):
            popup = Popup(title="Cảnh báo", content=Label(text=f"Đơn {oid} đã in trước đó!"),
                          size_hint=(.8,.4))
            popup.open()

        self.show_print_popup(oid, cust, box_n)

    def show_print_popup(self, oid, cust, box_n):
        root = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(8))
        root.add_widget(Label(text=f"In {box_n} nhãn", font_size=sp(18), bold=True))

        if is_android():
            mac, name = load_selected_printer()
            if mac is None:
                devices = find_paired_printers_pyjnius()
                if not devices:
                    Popup(title="Lỗi", content=Label(text="Không tìm thấy máy in Bluetooth"),
                          size_hint=(.8,.4)).open()
                    return
                mac = devices[0][1]
                name = devices[0][0]
                save_selected_printer(mac, name)
            
            btn_bt = Button(text=f"In Bluetooth ({name})", size_hint_y=None, height=dp(44),
                            background_color=COLOR_PRIMARY, color=COLOR_WHITE, font_size=sp(16))
            btn_bt.bind(on_release=lambda x: self.do_print_bt(oid, cust, box_n, root, mac))
            root.add_widget(btn_bt)
        else:
            btn_pc = Button(text="Lưu ảnh (mô phỏng)", size_hint_y=None, height=dp(44),
                            background_color=COLOR_SUCCESS, color=COLOR_WHITE, font_size=sp(16))
            btn_pc.bind(on_release=lambda x: self.simulate_print_pc(oid, cust, box_n))
            root.add_widget(btn_pc)

        btn_cancel = Button(text="Hủy", size_hint_y=None, height=dp(44),
                            background_color=COLOR_ERROR, color=COLOR_WHITE, font_size=sp(16))
        btn_cancel.bind(on_release=lambda x: popup.dismiss())
        root.add_widget(btn_cancel)

        popup = Popup(title="Chọn phương thức in", content=root, size_hint=(.9,.6))
        popup.open()

    def do_print_bt(self, oid, cust, box_n, popup_root, mac):
        if not is_android():
            return
        status_label = Label(text="Đang in...", font_size=sp(14), color=COLOR_PRIMARY)
        popup_root.add_widget(status_label)
        Clock.schedule_once(lambda dt: self._print_bt_thread(oid, cust, box_n, mac, status_label, popup_root), 0.1)

    def _print_bt_thread(self, oid, cust, box_n, mac, status_label, popup_root):
        try:
            for i in range(box_n):
                payload = get_label_zpl_bytes(oid, cust, i+1, box_n)
                ok, err = print_via_bluetooth_pyjnius(mac, payload)
                if not ok:
                    status_label.text = f"Lỗi: {err}"
                    status_label.color = COLOR_ERROR
                    return
                time.sleep(0.5)
            add_history_entry(oid, cust, box_n)
            status_label.text = f"In thành công {box_n} nhãn"
            status_label.color = COLOR_SUCCESS
            Clock.schedule_once(lambda dt: self.dismiss_popup(popup_root), 2)
        except Exception as e:
            status_label.text = f"Lỗi: {str(e)}"
            status_label.color = COLOR_ERROR

    def dismiss_popup(self, widget):
        parent = widget.parent
        while parent and not isinstance(parent, Popup):
            parent = parent.parent
        if parent:
            parent.dismiss()

    def simulate_print_pc(self, oid, cust, box_n):
        import subprocess
        import tempfile
        folder = tempfile.mkdtemp()
        files = []
        for i in range(box_n):
            img = create_label_image(oid, cust, i+1, box_n)
            path = os.path.join(folder, f"label_{i+1}.png")
            img.save(path)
            files.append(path)
        add_history_entry(oid, cust, box_n)
        if files:
            if platform == "win":
                os.startfile(files[0])
            elif platform == "darwin":
                subprocess.call(["open", files[0]])
            else:
                subprocess.call(["xdg-open", files[0]])
        Popup(title="Mô phỏng", content=Label(text=f"Đã lưu {box_n} ảnh tại {folder}"),
              size_hint=(.8,.4)).open()

    def update_preview(self):
        if not self.label_images:
            self.preview_image.texture = None
            self.page_label.text = "0/0"
            return
        total = len(self.label_images)
        if self.current_page >= total:
            self.current_page = total - 1
        if self.current_page < 0:
            self.current_page = 0
        img = self.label_images[self.current_page]

        if img.mode != 'RGB':
            img_rgb = img.convert('RGB')
        else:
            img_rgb = img

        width, height = img.size
        data = img_rgb.tobytes()
        texture = Texture.create(size=(width, height), colorfmt='rgb')
        texture.blit_buffer(data, colorfmt='rgb', bufferfmt='ubyte')
        texture.flip_vertical()

        self.preview_image.texture = texture
        self.preview_image.keep_ratio = True
        self.preview_image.size_hint = (1, 1)

        self.page_label.text = f"{self.current_page+1}/{total}"

    def prev_page(self, *args):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_preview()

    def next_page(self, *args):
        if self.current_page < len(self.label_images)-1:
            self.current_page += 1
            self.update_preview()

    def on_enter(self):
        if self.label_images:
            self.update_preview()

# ---------- ỨNG DỤNG CHÍNH ----------
class OrderPrinterApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(HomeScreen(name="home"))
        sm.add_widget(HistoryScreen(name="history"))
        sm.add_widget(PrinterManagerScreen(name="printer_manager"))
        sm.add_widget(SettingsScreen(name="settings"))
        return sm

if __name__ == "__main__":
    OrderPrinterApp().run()
