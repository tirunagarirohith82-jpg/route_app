import streamlit as st
import pandas as pd
import pydeck as pdk
import os

st.set_page_config(page_title="Route Map App", layout="wide")

st.title("🗺️ Asset Route Map Navigator")

DEFAULT_FILE = "route.xlsx"
df = None

# 1. Automatically load route.xlsx if it exists in the app directory
if os.path.exists(DEFAULT_FILE):
    df = pd.read_excel(DEFAULT_FILE)
    st.info(f"📁 Automatically loaded default file: `{DEFAULT_FILE}`")

# 2. Allow uploading a different file if needed
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
            # Route line connections between consecutive coordinates
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

            # Clean and match image filename
            raw_img_name = str(asset_info.get('image_path', '')).strip()
            img_file = os.path.basename(raw_img_name)
            local_img_path = os.path.join("images", img_file)
            
            # Check local file or URL
            if os.path.exists(local_img_path):
                st.image(local_img_path, caption=asset_info["name"], use_container_width=True)
            elif raw_img_name.startswith("http"):
                st.image(raw_img_name, caption=asset_info["name"], use_container_width=True)
            else:
                st.warning(f"Image file `{img_file}` not found in the `images` folder.")
    else:
        st.error("Missing required columns: 'Asset Name', 'Latitude', or 'Longitude'.")