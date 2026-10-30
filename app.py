import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
import base64

st.set_page_config(page_title="Route Map App", layout="wide")

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
            # Create interactive Folium map centered on assets
            center_lat = df["lat"].mean()
            center_lon = df["lon"].mean()
            
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=8,
                tiles="OpenStreetMap"
            )

            # Draw crimson route lines
            coords = df[["lat", "lon"]].values.tolist()
            folium.PolyLine(
                coords,
                color="#DC143C",
                weight=4,
                opacity=0.8,
                tooltip="Asset Route Line"
            ).add_to(m)

            # Add markers with hover photo tooltips
            for idx, row in df.iterrows():
                img_src = get_image_base64(row)
                
                # HTML template for hover card / popup
                if img_src:
                    img_html = f'<img src="{img_src}" style="width:180px;height:120px;object-fit:cover;border-radius:6px;margin-top:5px;" />'
                else:
                    img_html = '<div style="color:gray;font-size:12px;">Image not found</div>'

                tooltip_html = f"""
                <div style="font-family: Arial, sans-serif; padding: 4px;">
                    <b style="font-size:14px; color:#0066CC;">{row['name']}</b><br/>
                    <span style="font-size:12px; color:#555;">Type: {row.get('type', 'N/A')}</span><br/>
                    {img_html}
                </div>
                """

                folium.CircleMarker(
                    location=[row["lat"], row["lon"]],
                    radius=7,
                    color="#0066CC",
                    fill=True,
                    fill_color="#0066CC",
                    fill_opacity=0.9,
                    tooltip=folium.Tooltip(tooltip_html, sticky=True),
                    popup=folium.Popup(tooltip_html, max_width=220)
                ).add_to(m)

            # Render map on Streamlit
            st_folium(m, width="100%", height=550)

        with col2:
            st.subheader("🖼️ Selected Asset Details")
            selected_asset = st.selectbox("Select an Asset to inspect:", df["name"].unique())
            
            asset_info = df[df["name"] == selected_asset].iloc[0]
            st.write(f"**Asset Type:** {asset_info.get('type', 'N/A')}")
            st.write(f"**Latitude:** {asset_info['lat']}")
            st.write(f"**Longitude:** {asset_info['lon']}")

            img_src = get_image_base64(asset_info)
            if img_src:
                st.image(img_src, caption=asset_info["name"], use_container_width=True)
            else:
                st.warning("Image file not found in the `images` folder.")
    else:
        st.error("Missing required columns: 'Asset Name', 'Latitude', or 'Longitude'.")