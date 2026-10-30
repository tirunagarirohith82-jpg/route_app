import streamlit as st
import pandas as pd
import pydeck as pdk
import os

st.set_page_config(page_title="Route Map App", layout="wide")

st.title("🗺️ Asset Route Map Navigator")

DEFAULT_FILE = "route.xlsx"
df = None

# 1. Automatically load route.xlsx if present in directory
if os.path.exists(DEFAULT_FILE):
    df = pd.read_excel(DEFAULT_FILE)
    st.info(f"📁 Automatically loaded default file: `{DEFAULT_FILE}`")

# 2. Optional file uploader fallback
uploaded_file = st.file_uploader("Or upload a different Excel file (.xlsx)", type=["xlsx"])
if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)

if df is not None:
    # Standardize column names
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
            # Construct line segments between sequential points
            path_data = [
                {
                    "path": [
                        [df.loc[i, "lon"], df.loc[i, "lat"]],
                        [df.loc[i+1, "lon"], df.loc[i+1, "lat"]]
                    ],
                    "name": f"Leg {i+1}: {df.loc[i, 'name']} ➔ {df.loc[i+1, 'name']}"
                }
                for i in range(len(df) - 1)
            ]

            line_layer = pdk.Layer(
                "PathLayer",
                data=path_data,
                get_path="path",
                get_color=[220, 20, 60, 225],  # Crimson route line
                width_scale=20,
                width_min_pixels=4,
            )

            scatterplot_layer = pdk.Layer(
                "ScatterplotLayer",
                data=df,
                get_position=["lon", "lat"],
                get_fill_color=[0, 102, 204, 200],  # Blue asset markers
                get_radius=4000,
                pickable=True,
            )

            view_state = pdk.ViewState(
                latitude=df["lat"].mean(),
                longitude=df["lon"].mean(),
                zoom=7,
                pitch=0,
            )

            # Map rendering using light street basemap
            st.pydeck_chart(
                pdk.Deck(
                    map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
                    layers=[line_layer, scatterplot_layer],
                    initial_view_state=view_state,
                    tooltip={"text": "Asset: {name}\nType: {type}"},
                )
            )

        with col2:
            st.subheader("🖼️ Asset Details & Photos")
            selected_asset = st.selectbox("Select an Asset to view photo:", df["name"].unique())
            
            asset_info = df[df["name"] == selected_asset].iloc[0]
            st.write(f"**Asset Type:** {asset_info.get('type', 'N/A')}")
            st.write(f"**Latitude:** {asset_info['lat']}")
            st.write(f"**Longitude:** {asset_info['lon']}")

            # Smart image lookup (handles spaces, underscores, typos, case differences)
            raw_img_name = str(asset_info.get('image_path', '')).strip()
            img_file = os.path.basename(raw_img_name)
            
            clean_target = img_file.lower().replace(" ", "").replace("_", "")
            
            found_path = None
            if os.path.exists("images"):
                for file in os.listdir("images"):
                    clean_file = file.lower().replace(" ", "").replace("_", "")
                    if clean_file == clean_target:
                        found_path = os.path.join("images", file)
                        break

            if found_path and os.path.exists(found_path):
                st.image(found_path, caption=asset_info["name"], use_container_width=True)
            elif raw_img_name.startswith("http"):
                st.image(raw_img_name, caption=asset_info["name"], use_container_width=True)
            else:
                st.warning(f"Image file `{img_file}` not found in the `images` folder.")
    else:
        st.error("Missing required columns: 'Asset Name', 'Latitude', or 'Longitude'.")