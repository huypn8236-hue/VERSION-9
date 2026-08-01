[app]
# --- Thông tin ứng dụng ---
title = Order Printer
package.name = orderprinter
package.domain = org.example

# --- File nguồn ---
source.dir = .
source.include_exts = py,png,jpg,jpeg,ttf,xml,json
icon.filename = %(source.dir)s/icon.png

# --- Phiên bản ---
version = 1.0.0

# --- Hiển thị ---
orientation = portrait
fullscreen = 0

# --- Thư viện yêu cầu ---
# ⚡ THÊM camera4kivy CHO CAMERA MỚI
requirements = python3,kivy,pyjnius,pillow,plyer,certifi,pyzbar,camera4kivy

# --- Quyền Android ---
android.permissions = INTERNET,ACCESS_NETWORK_STATE,BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_CONNECT,BLUETOOTH_SCAN,ACCESS_FINE_LOCATION,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,CAMERA

# === SỬ DỤNG FILE MANIFEST TỰ TẠO ===
android.manifest = android-manifest.xml

# === CAMERA FEATURE (CHO PHÉP APP CHẠY TRÊN MÁY KHÔNG CÓ CAMERA) ===
android.manifest.extra = 
    <uses-feature android:name="android.hardware.camera" android:required="false" />
    <uses-feature android:name="android.hardware.camera.autofocus" android:required="false" />

# === LIBZBAR (CHO PYZBAR) ===
# ⚠️ "android.add_src = libzbar" KHÔNG ĐÚNG CÚ PHÁP
# Cách đúng: đặt libzbar.so vào thư mục libs/
# HOẶC bỏ dòng này, để pyzbar tự tìm
# Tạm thời comment để tránh lỗi build
# android.add_src = libzbar

# --- Tài nguyên đính kèm ---
# android.add_assets = arial.ttf,wifi_printers.json

# --- Màn hình khởi động ---
presplash.filename = %(source.dir)s/icon.png
android.presplash_color = #FFFFFF

# =========================================================
# THÊM CẤU HÌNH CHO CAMERA4KIVY + ML KIT
# =========================================================

# BOOTSTRAP PHẢI LÀ sdl2_gradle (ĐỂ HỖ TRỢ GRADLE DEPENDENCIES)
# android.bootstrap = sdl2

# GRADLE REPOSITORIES CHO ML KIT
android.gradle_repositories = maven { url 'https://maven.google.com' }, google(), mavenCentral()

# GRADLE DEPENDENCIES CHO ML KIT
android.gradle_dependencies = com.google.mlkit:barcode-scanning:17.2.0, androidx.core:core:1.9.0, androidx.appcompat:appcompat:1.6.1, androidx.camera:camera-core:1.4.0, androidx.camera:camera-camera2:1.4.0, androidx.camera:camera-lifecycle:1.4.0, androidx.camera:camera-view:1.4.0

# =========================================================
# ANDROID SDK / NDK - GIỮ NGUYÊN
# =========================================================
android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.archs = arm64-v8a

p4a.branch = develop
p4a.bootstrap = sdl2

android.allow_backup = True
android.enable_androidx = True

# --- Giảm kích thước APK ---
exclude_patterns = tests,docs,*.pyc,*.pyo,*.md,__pycache__,.git

# --- Môi trường ---
environment = 
    PYTHONOPTIMIZE=2
    KIVY_METRICS_DENSITY=2

[buildozer]
log_level = 2
warn_on_root = 1
android.accept_sdk_license = True
