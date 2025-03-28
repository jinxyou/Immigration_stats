import dash
from dash import Dash, callback, html, Output, Input, dcc
import dash_bootstrap_components as dbc
import dash_vega_components as dvc
import altair as alt
import geopandas as gpd
import pandas as pd
import json

# Enable vegafusion transformer
alt.data_transformers.enable("vegafusion")

# ===== 1. Process BC GeoJSON Data =====
gdf = gpd.read_file("data/raw/geojson/lcsd000b21a_e_simplified_0.25percent.geojson")
columns_to_keep = ['DGUID', 'CSDUID', 'CSDNAME', 'geometry']
gdf = gdf[gdf['DGUID'].astype(str).str.startswith("2021A000559")][columns_to_keep]
gdf.crs = "EPSG:3347"
# Transform from EPSG:3347 (meters) to EPSG:4326 (lat/lon)
gdf_latlon = gdf.to_crs(epsg=4326)
gdf_latlon = gdf_latlon[gdf_latlon.geometry.notnull()]
gdf_latlon["geometry"] = gdf_latlon["geometry"].buffer(0)

# Define high-density regions (cities and metro areas)
regions = {
    "Whole BC": {"scale": 1000, "center": [-126.5, 53.5], "csdnames": None},  # Default BC
    "Lower Mainland": {"scale": 5000, "center": [-123.1, 49.25], "csdnames": [
        "Vancouver", "Burnaby", "Surrey", "Richmond", "Coquitlam", 
        "Delta", "Langley", "North Vancouver", "West Vancouver", "New Westminster",
        "Abbotsford", "Chilliwack", "Maple Ridge", "White Rock", "Mission"
    ]},
    "Victoria": {"scale": 8000, "center": [-123.3656, 48.4284], "csdnames": [
        "Victoria", "Saanich", "Esquimalt", "Langford", "Colwood", "Central Saanich"
    ]},
    "Okanagan": {"scale": 6000, "center": [-119.5, 49.75], "csdnames": [
        "Kelowna", "Penticton", "Vernon", "West Kelowna", "Lake Country", "Summerland"
    ]},
    "Thompson-Nicola": {"scale": 6000, "center": [-120.3, 50.7], "csdnames": [
        "Kamloops", "Merritt", "Chase", "Clearwater"
    ]}
}

# ===== 2. Prepare Immigration Data =====
df = pd.read_parquet("data/processed/immigration_data/immigration_stats_bc_census_subdivisions.parquet")
df_immi = df[(df["Age (8D)"] == "Total - Age") & (df["Gender (3)"] == "Total - Gender")]
df_immi = df_immi[["GEO", "DGUID", "Place of birth (290)",
                    "Immigrant status and period of immigration (11):Total - Immigrant status and period of immigration[1]"]]
df_immi.rename(
    columns={
        "Place of birth (290)": "Birthplace",
        "Immigrant status and period of immigration (11):Total - Immigrant status and period of immigration[1]": "Count"
    },
    inplace=True
)
df_immi["Count"] = pd.to_numeric(df_immi["Count"], errors='coerce')
default_dguid = [df_immi["DGUID"].iloc[0]]

# Load World Map for Immigrants' Birthplaces
world_countries = gpd.read_file("data/processed/geojson/world_countries_clean.geojson")
# print(world_countries)
# world_countries = world_countries.query(
    # 'CONTINENT != "Antarctica"'
# )[['ADMIN', 'geometry']]

# ===== 3. Create Function to Build BC Map Chart with Zoom =====
def create_bc_map(region_filter):
    # Get scale, center, and CSD names for the selected region
    scale = regions[region_filter]["scale"]
    center = regions[region_filter]["center"]
    # csdnames = regions[region_filter]["csdnames"]

    # Filter based on region selection
    # if csdnames:
    #     gdf_filtered = gdf_latlon[gdf_latlon["CSDNAME"].isin(csdnames)]
    # else:
    #     gdf_filtered = gdf_latlon  # Show all BC subdivisions

    # Convert filtered GeoDataFrame to GeoJSON
    geojson_data = json.loads(gdf_latlon.to_json())
    for feature in geojson_data["features"]:
        feature["id"] = feature["properties"]["DGUID"]

    # Define a selection to capture clicked subdivision
    select_sub = alt.selection_point(
        fields=['properties.DGUID'],
        name='select_sub',
        on='click'
    )

    # Create Altair chart with dynamic scale and center
    chart = alt.Chart(alt.Data(values=geojson_data["features"])).mark_geoshape(
        stroke='black'
    ).encode(
        tooltip=alt.Tooltip('properties.CSDNAME:N', title='Subdivision'),
        color=alt.Color('properties.CSDNAME:N').scale(scheme='tableau20'),
        opacity=alt.condition(select_sub, alt.value(0.9), alt.value(0.3))
    ).add_params(
        select_sub
    ).project(
        "mercator",
        scale=scale,
        center=center
    ).properties(
        width=600,
        height=600,
        title=f"BC Subdivisions ({region_filter})"
    )
    
    return chart.to_dict(format="vega")

# ===== 4. Create Function to Build World Map Chart =====
def create_world_chart(selected_dguid):
    df_filtered = df_immi[df_immi["DGUID"].isin(selected_dguid)]
    df_agg = df_filtered.groupby("Birthplace", as_index=False)["Count"].sum()

    merged = world_countries.merge(df_agg, left_on="ADMIN", right_on="Birthplace", how="left")
    merged["Count"] = merged["Count"].fillna(0)

    merged_geojson = json.loads(merged.to_json())

    world_chart = alt.Chart(alt.Data(values=merged_geojson["features"])).mark_geoshape(
        stroke="white"
    ).encode(
        color=alt.Color("properties.Count:Q", scale=alt.Scale(scheme='orangered')),
        tooltip=[
            alt.Tooltip("properties.ADMIN:N", title="Country"),
            alt.Tooltip("properties.Count:Q", title="Immigrant Count")
        ]
    # ).project(
        # "mercator"
    ).properties(
        width=1000,
        height=800,
        title=f"Immigrant Origins for Subdivision {selected_dguid}"
    )

    return world_chart.to_dict(format="vega")

# ===== 5. Build the Dash App Layout =====
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.layout = dbc.Container([
    dcc.RadioItems(
        id="region-toggle",
        options=list(regions.keys()),
        value="Whole BC",
        inline=True,
        style={"marginBottom": "20px"}
    ),
    
    dvc.Vega(
        id='bc-map',
        spec=create_bc_map("Whole BC"),
        signalsToObserve=['select_sub']
    ),
    
    html.Div(id='output', style={'marginTop': '20px', 'fontSize': '20px'}),
    
    dvc.Vega(
        id='world-map',
        spec=create_world_chart(default_dguid)
    )
])

@callback(Output('bc-map', 'spec'), Input('region-toggle', 'value'))
def update_bc_map(region_filter):
    return create_bc_map(region_filter)

# ===== 7. Callback to Update the World Map Based on Selection =====
@callback(
    Output('world-map', 'spec'),
    Input('bc-map', 'signalData')
)
def update_world_map(signalData):
    selected_dguid = default_dguid
    if signalData and 'select_sub' in signalData and 'properties\\.DGUID' in signalData['select_sub']:
        selected_dguid = signalData['select_sub']['properties\\.DGUID']
    return create_world_chart(selected_dguid)

if __name__ == '__main__':
    app.run(debug=True)
