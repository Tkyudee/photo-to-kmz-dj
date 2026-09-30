import streamlit as st
import simplekml
from PIL import Image, ExifTags
import zipfile
import io
import os

def get_exif_location(image):
    """Safely extracts EXIF GPS data without crashing if data is missing."""
    try:
        exif = image.getexif()
        if not exif:
            return None

        # Look for GPS info in EXIF IFD
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

            return lon, lat # KML requires Longitude, Latitude order
    except Exception:
        return None
    return None

# --- Web App Interface ---
st.set_page_config(page_title="Photo to KMZ Converter", layout="centered")
st.title("📍 Photo to KMZ Converter")
st.write("Upload photos to extract coordinates. **Mobile Users:** Please select photos from your phone's 'Files' or 'Documents' folder (not the Gallery) to preserve the original filenames and GPS data.")

uploaded_files = st.file_uploader("Upload Photos", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if uploaded_files and st.button("Generate KMZ"):
    kml = simplekml.Kml()
    valid_photos = 0

    for file in uploaded_files:
        try:
            # The 'with' statement ensures the image is closed immediately, preventing memory crashes
            with Image.open(file) as img:
                coords = get_exif_location(img)

                if coords:
                    pin_name = os.path.splitext(file.name)[0]
                    kml.newpoint(name=pin_name, coords=[coords])
                    valid_photos += 1
                else:
                    st.warning(f"No GPS metadata found in {file.name}. (Was it uploaded from a Gallery app?)")
        except Exception as e:
            st.error(f"Error processing {file.name}: {e}")

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
