import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
import base64

st.set_page_config(page_title="Route Map App", layout="wide")

# Custom CSS to ensure prompts, labels, and text elements are crisp and visible
st.markdown("""
    <style>
    /* Ensure text prompts and input labels are crisp and visible */
    .stSelectbox label, .stFileUploader label, .stMarkdown p {
        color: #FFFFFF !important;
        font-weight: 500 !important;
    }
    /* Info box styling */
    div[data-testid="stNotification"] {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        color: #F8FAFC !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🗺️ Asset Route Map Navigator")

DEFAULT_FILE = "route.xlsx"
df = None

# 1. Automatically load default file
if os.path.exists(DEFAULT_FILE):
    df = pd.read_excel(DEFAULT_FILE)
    st.info(f"📁 Automatically loaded default file: `{DEFAULT_FILE}`")

# 2. File uploader fallback
uploaded_file = st.file_uploader("Or upload a different Excel file (.xlsx)", type=["xlsx"])
if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)

# Helper function to get base64 encoded image string for HTML tooltips
def get_image_base64(asset_info):
    raw_img_name = str(asset_info.get('image_path', '')).strip()
    img_file = os.path.basename(raw_img_name)
    
    clean_target = "".join(img_file.lower().replace(".jpg", "").replace(".png", "").replace(".jpeg", "").split()).replace("_", "")
    
    found_path = None
    if os.path.exists("images"):
        for file in os.listdir("images"):
            clean_file = "".join(file.lower().replace(".jpg", "").replace(".png", "").replace(".jpeg", "").split()).replace("_", "")
            if clean_file == clean_target:
                found_path = os.path.join("images", file)
                break

    if found_path and os.path.exists(found_path):
        with open(found_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
            return f"data:image/jpeg;base64,{encoded_string}"
    elif raw_img_name.startswith("http"):
        return raw_img_name
    return None

if df is not None:
    df = df.rename(columns={
        "Asset Name": "name",
        "Latitude": "lat",
        "Longitude": "lon",
        "Asset Type": "type",
        "Image": "image_path"
    })

    required_cols = {"lat", "lon", "name"}
    if required_cols.issubset(df.columns):
        st.success(f"Successfully loaded {len(df)} asset locations!")

        col1, col2 = st.columns([2, 1])

        with col1:
            center_lat = df["lat"].mean()
            center_lon = df["lon"].mean()
            
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=8,
                tiles="OpenStreetMap"
            )

            # Separate dataframe by network keywords
            srisailam_df = df[df["name"].str.contains("Srisailam|Srisailm|srisailam", case=False, na=False)]
            nsagar_df = df[df["name"].str.contains("Nagarjuna|Nagarjunasagar|nagarjuna", case=False, na=False)]
            mgit_df = df[df["name"].str.contains("MGIT|Mahatma Gandhi", case=False, na=False)]

            # Locate MGIT coordinate as central termination point
            mgit_coord = mgit_df[["lat", "lon"]].values.tolist() if not mgit_df.empty else []

            # 1. Srisailam Route to MGIT (Red Line)
            if not srisailam_df.empty:
                s_coords = srisailam_df[["lat", "lon"]].values.tolist()
                if mgit_coord and mgit_coord[0] not in s_coords:
                    s_coords.append(mgit_coord[0])  # Connect directly to MGIT
                folium.PolyLine(
                    s_coords,
                    color="#E63946",  # Red
                    weight=5,
                    opacity=0.9,
                    tooltip="Srisailam ➔ MGIT Transmission Line"
                ).add_to(m)

            # 2. Nagarjuna Sagar Route to MGIT (Deep Blue Line)
            if not nsagar_df.empty:
                ns_coords = nsagar_df[["lat", "lon"]].values.tolist()
                if mgit_coord and mgit_coord[0] not in ns_coords:
                    ns_coords.append(mgit_coord[0])  # Connect directly to MGIT
                folium.PolyLine(
                    ns_coords,
                    color="#1D3557",  # Deep Blue
                    weight=5,
                    opacity=0.9,
                    tooltip="Nagarjuna Sagar ➔ MGIT Transmission Line"
                ).add_to(m)

            # 3. Add markers for EVERY asset with permanent image tooltips
            for idx, row in df.iterrows():
                asset_name = str(row["name"]).lower()
                if "mgit" in asset_name or "mahatma gandhi" in asset_name:
                    marker_color = "#2A9D8F"  # Teal highlight for MGIT load center
                    net_label = "Central Load Destination (MGIT)"
                elif "srisailam" in asset_name:
                    marker_color = "#E63946"  # Red for Srisailam Network
                    net_label = "Srisailam Network"
                elif "nagarjuna" in asset_name:
                    marker_color = "#1D3557"  # Deep Blue for Nagarjuna Sagar Network
                    net_label = "Nagarjuna Sagar Network"
                else:
                    marker_color = "#457B9D"  # Blue for intermediate grid substations
                    net_label = "Grid Substation"

                img_src = get_image_base64(row)
                if img_src:
                    img_html = f'<img src="{img_src}" style="width:160px;height:100px;object-fit:cover;border-radius:6px;margin-top:5px;" />'
                else:
                    img_html = '<div style="color:gray;font-size:12px;">Image not found</div>'

                tooltip_html = f"""
                <div style="font-family: Arial, sans-serif; padding: 2px;">
                    <b style="font-size:13px; color:{marker_color};">{row['name']}</b><br/>
                    <span style="font-size:11px; color:#333;"><b>Network:</b> {net_label}</span><br/>
                    <span style="font-size:11px; color:#555;"><b>Type:</b> {row.get('type', 'N/A')}</span><br/>
                    {img_html}
                </div>
                """

                # permanent=True shows the card permanently for all points on map load
                folium.CircleMarker(
                    location=[row["lat"], row["lon"]],
                    radius=8 if "mgit" in asset_name else 6,
                    color=marker_color,
                    fill=True,
                    fill_color=