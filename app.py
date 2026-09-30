import streamlit as st
import simplekml
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import zipfile
import io
import os

def get_exif_data(image):
    """Extracts raw EXIF data from the image."""
    exif_data = {}
    info = image._getexif()
    if info:
        for tag, value in info.items():
            decoded = TAGS.get(tag, tag)
            if decoded == "GPSInfo":
                gps_data = {}
                for t in value:
                    sub_decoded = GPSTAGS.get(t, t)
                    gps_data[sub_decoded] = value[t]
                exif_data[decoded] = gps_data
            else:
                exif_data[decoded] = value
    return exif_data

def get_decimal_coordinates(info):
    """Converts standard GPS EXIF data to decimal format (Longitude, Latitude)."""
    for key in ['Latitude', 'Longitude']:
        if 'GPS'+key not in info or 'GPS'+key+'Ref' not in info:
            return None

    def convert_to_degrees(value):
        d, m, s = value
        return float(d) + (float(m) / 60.0) + (float(s) / 3600.0)

    lat = convert_to_degrees(info['GPSLatitude'])
    lon = convert_to_degrees(info['GPSLongitude'])

    if info['GPSLatitudeRef'] != 'N':
        lat = -lat
    if info['GPSLongitudeRef'] != 'E':
        lon = -lon

    return lon, lat

# --- Streamlit Web App Interface ---
st.set_page_config(page_title="Photo to KMZ Converter", layout="centered")

st.title("📍 Photo to KMZ Converter")
st.write("Upload a folder of photos. The app will extract their GPS coordinates and output a KMZ file with pins named after the files.")

uploaded_files = st.file_uploader("Upload Photos (JPG/PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if uploaded_files:
    if st.button("Generate KMZ"):
        kml = simplekml.Kml()
        valid_photos = 0

        for file in uploaded_files:
            try:
                # Open image and extract metadata
                img = Image.open(file)
                exif = get_exif_data(img)
                
                if 'GPSInfo' in exif:
                    coords = get_decimal_coordinates(exif['GPSInfo'])
                    if coords:
                        # Get filename without extension for the pin name
                        pin_name = os.path.splitext(file.name)[0]
                        
                        # Create the point in KML
                        kml.newpoint(name=pin_name, coords=[coords])
                        valid_photos += 1
                    else:
                        st.warning(f"Could not parse coordinates for {file.name}")
                else:
                    st.warning(f"No GPS metadata found in {file.name}")
            except Exception as e:
                st.error(f"Error processing {file.name}: {e}")

        if valid_photos > 0:
            st.success(f"Successfully processed {valid_photos} photos! 🎉")
            
            # Generate KML string and zip it into a KMZ file in-memory
            kml_string = kml.kml()
            kmz_io = io.BytesIO()
            with zipfile.ZipFile(kmz_io, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('map.kml', kml_string)
            
            # Provide the download button
            st.download_button(
                label="📥 Download KMZ File",
                data=kmz_io.getvalue(),
                file_name="photos_map.kmz",
                mime="application/vnd.google-earth.kmz"
            )
        else:
            st.error("None of the uploaded photos contained valid GPS coordinates.")