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
    .stSelectbox label, .stFileUploader label, .stMarkdown p {
        color: #FFFFFF !important;
        font-weight: 500 !important;
    }
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

# Helper function to get base64 encoded image string for tooltips
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

        # Initialize session state for bi-directional map & sidebar sync
        if "selected_asset" not in st.session_state or st.session_state.selected_asset not in df["name"].values:
            st.session_state.selected_asset = None

        col1, col2 = st.columns([2, 1])

        # Determine center and zoom level based on selection
        if st.session_state.selected_asset is None:
            center_lat = df["lat"].mean()
            center_lon = df["lon"].mean()
            zoom_level = 8
        else:
            asset_info = df[df["name"] == st.session_state.selected_asset].iloc[0]
            center_lat = asset_info["lat"]
            center_lon = asset_info["lon"]
            zoom_level = 12

        with col1:
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=zoom_level,
                tiles="OpenStreetMap"
            )

            # Separate dataframe by network keywords
            srisailam_df = df[df["name"].str.contains("Srisailam|Srisailm|srisailam", case=False, na=False)]
            nsagar_df = df[df["name"].str.contains("Nagarjuna|Nagarjunasagar|nagarjuna", case=False, na=False)]
            mgit_df = df[df["name"].str.contains("MGIT|Mahatma Gandhi", case=False, na=False)]

            mgit_coord = mgit_df[["lat", "lon"]].values.tolist() if not mgit_df.empty else []

            # 1. Srisailam Route to MGIT (Red Line)
            if not srisailam_df.empty:
                s_coords = srisailam_df[["lat", "lon"]].values.tolist()
                if mgit_coord and mgit_coord[0] not in s_coords:
                    s_coords.append(mgit_coord[0])
                folium.PolyLine(
                    s_coords,
                    color="#E63946",
                    weight=5,
                    opacity=0.9,
                    tooltip="Srisailam ➔ MGIT Transmission Line"
                ).add_to(m)

            # 2. Nagarjuna Sagar Route to MGIT (Deep Blue Line)
            if not nsagar_df.empty:
                ns_coords = nsagar_df[["lat", "lon"]].values.tolist()
                if mgit_coord and mgit_coord[0] not in ns_coords:
                    ns_coords.append(mgit_coord[0])
                folium.PolyLine(
                    ns_coords,
                    color="#1D3557",
                    weight=5,
                    opacity=0.9,
                    tooltip="Nagarjuna Sagar ➔ MGIT Transmission Line"
                ).add_to(m)

            # 3. Clean Circle Markers (No clutter)
            for idx, row in df.iterrows():
                asset_name = str(row["name"]).lower()
                is_selected = (row["name"] == st.session_state.selected_asset)

                if "mgit" in asset_name or "mahatma gandhi" in asset_name:
                    marker_color = "#2A9D8F"
                    net_label = "Central Load Destination (MGIT)"
                elif "srisailam" in asset_name:
                    marker_color = "#E63946"
                    net_label = "Srisailam Network"
                elif "nagarjuna" in asset_name:
                    marker_color = "#1D3557"
                    net_label = "Nagarjuna Sagar Network"
                else:
                    marker_color = "#457B9D"
                    net_label = "Grid Substation"

                marker_img_src = get_image_base64(row)
                if marker_img_src:
                    img_html = f'<img src="{marker_img_src}" style="width:180px;height:120px;object-fit:cover;border-radius:6px;margin-top:5px;" />'
                else:
                    img_html = '<div style="color:gray;font-size:12px;">Image not found</div>'

                card_html = f"""
                <div style="font-family: Arial, sans-serif; padding: 2px;">
                    <b style="font-size:13px; color:{marker_color};">{row['name']}</b><br/>
                    <span style="font-size:11px; color:#333;"><b>Network:</b> {net_label}</span><br/>
                    <span style="font-size:11px; color:#555;"><b>Type:</b> {row.get('type', 'N/A')}</span><br/>
                    {img_html}
                </div>
                """

                popup_obj = folium.Popup(card_html, max_width=220, show=is_selected)

                folium.CircleMarker(
                    location=[row["lat"], row["lon"]],
                    radius=12 if is_selected else (8 if "mgit" in asset_name else 6),
                    color="#FFD700" if is_selected else marker_color,
                    fill=True,
                    fill_color=marker_color,
                    fill_opacity=1.0 if is_selected else 0.8,
                    tooltip=folium.Tooltip(card_html, sticky=True),
                    popup=popup_obj
                ).add_to(m)

            # High-Contrast Map Legend
            legend_html = """
            <div style="position: fixed; bottom: 30px; left: 30px; width: 250px; 
                        background-color: rgba(255, 255, 255, 0.95); border: 2px solid #333; z-index: 9999; 
                        font-family: Arial, sans-serif; font-size: 13px; color: #111;
                        padding: 10px 14px; border-radius: 8px; box-shadow: 2px 2px 8px rgba(0,0,0,0.3);">
                <b style="font-size:14px; color:#000; display:block; margin-bottom:8px;">Transmission Routes</b>
                <div style="margin-bottom: 6px;">
                    <i style="background:#E63946; width:18px; height:4px; display:inline-block; margin-right:8px; vertical-align:middle;"></i>
                    <span style="color:#000; font-weight:600;">Srisailam ➔ MGIT</span>
                </div>
                <div style="margin-bottom: 6px;">
                    <i style="background:#1D3557; width:18px; height:4px; display:inline-block; margin-right:8px; vertical-align:middle;"></i>
                    <span style="color:#000; font-weight:600;">Nagarjuna Sagar ➔ MGIT</span>
                </div>
                <div>
                    <i style="background:#2A9D8F; width:10px; height:10px; border-radius:50%; display:inline-block; margin-right:12px; vertical-align:middle;"></i>
                    <span style="color:#000; font-weight:600;">MGIT Load Destination</span>
                </div>
            </div>
            """
            m.get_root().html.add_child(folium.Element(legend_html))

            map_data = st_folium(m, width="100%", height=600, key=f"map_{st.session_state.selected_asset}")

            # Two-way sync: Update selection when user clicks a map marker
            if map_data and map_data.get("last_object_clicked_popup"):
                clicked_popup = map_data["last_object_clicked_popup"]
                for name in df["name"].unique():
                    if name in clicked_popup and name != st.session_state.selected_asset:
                        st.session_state.selected_asset = name
                        st.rerun()

        with col2:
            st.subheader("🖼️ Selected Asset Details")
            asset_options = ["-- View Entire Network --"] + list(df["name"].unique())
            current_index = 0
            if st.session_state.selected_asset in df["name"].values:
                current_index = asset_options.index(st.session_state.selected_asset)

            selected_option = st.selectbox(
                "Select an Asset to inspect:",
                options=asset_options,
                index=current_index
            )

            if selected_option == "-- View Entire Network --":
                if st.session_state.selected_asset is not None:
                    st.session_state.selected_asset = None
                    st.rerun()
                st.info("Showing complete transmission route overview.")
            else:
                if selected_option != st.session_state.selected_asset:
                    st.session_state.selected_asset = selected_option
                    st.rerun()

                asset_info = df[df["name"] == st.session_state.selected_asset].iloc[0]
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