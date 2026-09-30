import streamlit as st
import simplekml
from PIL import Image
import zipfile
import rarfile
import tempfile
import io
import os
import pytesseract
import re

def extract_stamp_data(image):
    """Scans the image visually for text, finds the coordinates, and grabs the line above as the pin name."""
    try:
        # Convert to grayscale to make the white text pop against the black background for better reading
        gray_image = image.convert('L')
        text = pytesseract.image_to_string(gray_image)
        
        # Split the scanned text into individual lines
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        for i, line in enumerate(lines):
            # Look for a pattern that matches Latitude, Longitude (e.g., "7.08874, 125.61593")
            match = re.search(r'(-?\d{1,3}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)', line)
            
            if match:
                lat = float(match.group(1))
                lon = float(match.group(2))
                
                # The pin name (e.g., "2023017cc7-9") is the line directly above the coordinates
                if i > 0:
                    pin_name = lines[i-1]
                else:
                    pin_name = "Unknown_Pole"
                
                return pin_name, (lon, lat)
    except Exception as e:
        return None, None
        
    return None, None

# --- Web App Interface ---
st.set_page_config(page_title="Visual OCR Photo to KMZ", layout="centered")
st.title("📍 Visual OCR Photo to KMZ")
st.write("Upload photos, `.zip`, or `.rar` files. The app will visually scan the photo for Conota stamp text to determine the pole name and coordinates.")

uploaded_files = st.file_uploader("Upload Photos, .zip, or .rar files", accept_multiple_files=True)

if uploaded_files and st.button("Generate KMZ"):
    kml = simplekml.Kml()
    valid_photos = 0

    with st.spinner("Scanning images for text... This may take a moment."):
        for file in uploaded_files:
            
            # --- HANDLE ZIP FILES ---
            if file.name.lower().endswith('.zip'):
                try:
                    with zipfile.ZipFile(file, 'r') as z:
                        for filename in z.namelist():
                            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                                with z.open(filename) as f:
                                    with Image.open(f) as img:
                                        pin_name, coords = extract_stamp_data(img)
                                        if coords and pin_name:
                                            kml.newpoint(name=pin_name, coords=[coords])
                                            valid_photos += 1
                except Exception as e:
                    st.error(f"Error reading zip file {file.name}: {e}")
                    
            # --- HANDLE RAR FILES ---
            elif file.name.lower().endswith('.rar'):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.rar') as tmp:
                        tmp.write(file.getvalue())
                        tmp_path = tmp.name

                    with rarfile.RarFile(tmp_path) as r:
                        for filename in r.namelist():
                            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                                with r.open(filename) as f:
                                    with Image.open(f) as img:
                                        pin_name, coords = extract_stamp_data(img)
                                        if coords and pin_name:
                                            kml.newpoint(name=pin_name, coords=[coords])
                                            valid_photos += 1
                    os.remove(tmp_path)
                except Exception as e:
                    st.error(f"Error reading RAR file {file.name}: {e}")

            # --- HANDLE DIRECT IMAGE UPLOADS ---
            elif file.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                try:
                    with Image.open(file) as img:
                        pin_name, coords = extract_stamp_data(img)
                        if coords and pin_name:
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
            file_name="scanned_photos_map.kmz",
            mime="application/vnd.google-earth.kmz"
        )
    else:
        st.error("No valid text stamps containing coordinates could be read from the uploaded photos.")
