import streamlit as st
import simplekml
from PIL import Image, ExifTags
import zipfile
import rarfile
import tempfile
import io
import os

def get_exif_location(image):
    """Safely extracts EXIF GPS data without crashing if data is missing."""
    try:
        exif = image.getexif()
        if not exif:
            return None

        gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
        if not gps_ifd:
            return None

        gps_data = {ExifTags.GPSTAGS.get(key, key): val for key, val in gps_ifd.items()}

        def convert_to_degrees(value):
            try:
                d = float(value[0])
                m = float(value[1])
                s = float(value[2])
                return d + (m / 60.0) + (s / 3600.0)
            except:
                return None

        if 'GPSLatitude' in gps_data and 'GPSLongitude' in gps_data:
            lat = convert_to_degrees(gps_data['GPSLatitude'])
            lon = convert_to_degrees(gps_data['GPSLongitude'])
            
            if lat is None or lon is None:
                return None

            if gps_data.get('GPSLatitudeRef') == 'S':
                lat = -lat
            if gps_data.get('GPSLongitudeRef') == 'W':
                lon = -lon

            return lon, lat
    except Exception:
        return None
    return None

# --- Web App Interface ---
st.set_page_config(page_title="Photo to KMZ Converter", layout="centered")
st.title("📍 Photo to KMZ Converter")
st.write("**Mobile Users:** Compress your photos into a `.zip` or `.rar` file on your phone first, then upload it here to preserve original filenames and GPS data.")

# Notice we removed the strict file types here so mobile phones don't grey out zip/rar files
uploaded_files = st.file_uploader("Upload Photos, .zip, or .rar files", accept_multiple_files=True)

if uploaded_files and st.button("Generate KMZ"):
    kml = simplekml.Kml()
    valid_photos = 0

    for file in uploaded_files:
        
        # --- HANDLE ZIP FILES ---
        if file.name.lower().endswith('.zip'):
            try:
                with zipfile.ZipFile(file, 'r') as z:
                    for filename in z.namelist():
                        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                            with z.open(filename) as f:
                                with Image.open(f) as img:
                                    coords = get_exif_location(img)
                                    if coords:
                                        pin_name = os.path.splitext(os.path.basename(filename))[0]
                                        kml.newpoint(name=pin_name, coords=[coords])
                                        valid_photos += 1
            except Exception as e:
                st.error(f"Error reading zip file {file.name}: {e}")
                
        # --- HANDLE RAR FILES ---
        elif file.name.lower().endswith('.rar'):
            try:
                # Save the RAR to a temporary file on the server so 'unrar' can read it
                with tempfile.NamedTemporaryFile(delete=False, suffix='.rar') as tmp:
                    tmp.write(file.getvalue())
                    tmp_path = tmp.name

                with rarfile.RarFile(tmp_path) as r:
                    for filename in r.namelist():
                        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                            with r.open(filename) as f:
                                with Image.open(f) as img:
                                    coords = get_exif_location(img)
                                    if coords:
                                        pin_name = os.path.splitext(os.path.basename(filename))[0]
                                        kml.newpoint(name=pin_name, coords=[coords])
                                        valid_photos += 1
                
                # Delete the temporary file to free up memory immediately
                os.remove(tmp_path)
            except Exception as e:
                st.error(f"Error reading RAR file {file.name}: {e}")

        # --- HANDLE DIRECT IMAGE UPLOADS ---
        elif file.name.lower().endswith(('.png', '.jpg', '.jpeg')):
            try:
                with Image.open(file) as img:
                    coords = get_exif_location(img)
                    if coords:
                        pin_name = os.path.splitext(file.name)[0]
                        kml.newpoint(name=pin_name, coords=[coords])
                        valid_photos += 1
            except Exception as e:
                pass

    if valid_photos > 0:
        st.success(f"Successfully processed {valid_photos} photos! 🎉")
        kmz_io = io.BytesIO()
        with zipfile.ZipFile(kmz_io, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('map.kml', kml.kml())
        
        st.download_button(
            label="📥 Download KMZ File",
            data=kmz_io.getvalue(),
            file_name="photos_map.kmz",
            mime="application/vnd.google-earth.kmz"
        )
    else:
        st.error("None of the uploaded photos contained valid GPS coordinates.")
