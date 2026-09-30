import streamlit as st
import simplekml
import zipfile
import rarfile
import tempfile
import io
import os

def extract_from_filename(filename):
    """
    Extracts pin name and coordinates directly from the filename formatting.
    Example: 28284892cc7-9_7.08874, 125.61593_20261001_000252.jpg
    """
    base_name = os.path.basename(filename)
    name_without_ext = os.path.splitext(base_name)[0]
    
    # Split the filename by underscores
    parts = name_without_ext.split('_')
    
    # Loop through the parts to find the one containing the coordinates
    for i, part in enumerate(parts):
        # The coordinates part will be the one containing a comma
        if ',' in part:
            coords_split = part.split(',')
            if len(coords_split) == 2:
                try:
                    lat = float(coords_split[0].strip())
                    lon = float(coords_split[1].strip())
                    
                    # The pin name is everything before the coordinates
                    pin_name = "_".join(parts[:i])
                    return pin_name, (lon, lat)
                except ValueError:
                    pass
    return None, None

# --- Web App Interface ---
st.set_page_config(page_title="Filename to KMZ Converter", layout="centered")
st.title("📍 Tkyudee KMZ converter")
st.write("Upload `.zip`, `.rar`, or photos. The app instantly extracts the Pin Name and Coordinates directly from the filename.")

uploaded_files = st.file_uploader("Upload Photos, .zip, or .rar files", accept_multiple_files=True)

if uploaded_files and st.button("Generate KMZ"):
    kml = simplekml.Kml()
    valid_photos = 0

    with st.spinner("Processing filenames..."):
        for file in uploaded_files:
            
            # --- HANDLE ZIP FILES ---
            if file.name.lower().endswith('.zip'):
                try:
                    with zipfile.ZipFile(file, 'r') as z:
                        for filename in z.namelist():
                            # Process only image extensions
                            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                                pin_name, coords = extract_from_filename(filename)
                                if pin_name and coords:
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
                                pin_name, coords = extract_from_filename(filename)
                                if pin_name and coords:
                                    kml.newpoint(name=pin_name, coords=[coords])
                                    valid_photos += 1
                    os.remove(tmp_path)
                except Exception as e:
                    st.error(f"Error reading RAR file {file.name}: {e}")

            # --- HANDLE DIRECT IMAGE UPLOADS ---
            elif file.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                pin_name, coords = extract_from_filename(file.name)
                if pin_name and coords:
                    kml.newpoint(name=pin_name, coords=[coords])
                    valid_photos += 1

    if valid_photos > 0:
        st.success(f"Successfully processed {valid_photos} files! 🎉")
        kmz_io = io.BytesIO()
        with zipfile.ZipFile(kmz_io, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('map.kml', kml.kml())
        
        st.download_button(
            label="📥 Download KMZ File",
            data=kmz_io.getvalue(),
            file_name="fast_map.kmz",
            mime="application/vnd.google-earth.kmz"
        )
    else:
        st.error("No valid filenames containing coordinates could be found.")
