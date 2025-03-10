import dash
from dash import Dash, callback, html, Output, Input
import dash_bootstrap_components as dbc
import dash_vega_components as dvc
import altair as alt
import geopandas as gpd
import pandas as pd
import json

# Enable vegafusion transformer
alt.data_transformers.enable("vegafusion")

# ===== 1. Process BC GeoJSON Data =====
# Read and simplify the BC subdivisions GeoJSON
gdf = gpd.read_file("data/raw/geojson/lcsd000b21a_e_simplified_1percent.geojson")
columns_to_keep = ['DGUID', 'CSDUID', 'CSDNAME', 'geometry']
gdf = gdf[columns_to_keep]
gdf.crs = "EPSG:3347"
# Transform from EPSG:3347 (meters) to EPSG:4326 (lat/lon)
gdf_latlon = gdf.to_crs(epsg=4326)
gdf_latlon = gdf_latlon[gdf_latlon.geometry.notnull()]
gdf_latlon["geometry"] = gdf_latlon["geometry"].buffer(0)

# Convert to a GeoJSON dict and assign an "id" to each feature (using DGUID)
geojson_data = json.loads(gdf_latlon.to_json())
for feature in geojson_data["features"]:
    feature["id"] = feature["properties"]["DGUID"]

# ===== 2. Prepare Immigration Data =====
df = pd.read_csv("data/raw/immigration_data/immigration_stats_bc_census_subdivisions.csv")
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
# Use the first subdivision as default
default_dguid = [df_immi["DGUID"].iloc[0]]

# ===== 3. Create the BC Map Chart =====
# Define a single-point selection that listens for a click and captures the CSDUID.
select_sub = alt.selection_point(
    fields=['properties.DGUID'],
    name='select_sub',
    on='click'
)

chart = alt.Chart(alt.Data(values=geojson_data["features"])).mark_geoshape(
    stroke='black'
).encode(
    tooltip=alt.Tooltip('properties.CSDNAME:N', title='Subdivision')
).add_params(
    select_sub
).properties(
    width=600,
    height=600,
    title="BC Subdivisions"
)

world_countries = gpd.read_file("https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip")
world_countries = world_countries[['NAME', 'geometry']]

# ===== 4. Create a Function to Build the World Map Chart =====
def create_world_chart(selected_dguid):
    # Filter immigration data for the selected subdivision (by DGUID)
    df_filtered = df_immi[df_immi["DGUID"].isin(selected_dguid)]
    # Aggregate immigrant counts by Birthplace (country)
    df_agg = df_filtered.groupby("Birthplace", as_index=False)["Count"].sum()
    
    # Merge the aggregated immigration data with the world countries GeoDataFrame.
    merged = world_countries.merge(df_agg, left_on="NAME", right_on="Birthplace", how="left")
    merged["Count"] = merged["Count"].fillna(0)
    
    # Convert merged GeoDataFrame to GeoJSON
    merged_geojson = json.loads(merged.to_json())
    
    # Create an Altair chart using the merged GeoJSON data.
    world_chart = alt.Chart(alt.Data(values=merged_geojson["features"])).mark_geoshape(
        stroke="white"
    ).encode(
        color=alt.Color("properties.Count:Q", scale=alt.Scale(scheme='orangered')),
        tooltip=[
            alt.Tooltip("properties.NAME:N", title="Country"),
            alt.Tooltip("properties.Count:Q", title="Immigrant Count")
        ]
    ).properties(
        width=600,
        height=400,
        title=f"Immigrant Origins for Subdivision {selected_dguid}"
    )
    return world_chart.to_dict(format="vega")

# ===== 5. Build the Dash App Layout =====
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.layout = dbc.Container([
    # BC map rendered with dash_vega_components (working code)
    dvc.Vega(
        id='bc-map',
        spec=chart.to_dict(format="vega"),
        signalsToObserve=['select_sub']
    ),
    # Div to display the clicked subdivision ID (for debugging/feedback)
    html.Div(id='output', style={'marginTop': '20px', 'fontSize': '20px'}),
    # World map that shows immigrant origins for the selected subdivision
    dvc.Vega(
        id='world-map',
        spec=create_world_chart(default_dguid)
    )
])

# ===== 6. Callback to Print the Selected Subdivision ID (Existing) =====
@callback(
    Output('output', 'children'),
    Input('bc-map', 'signalData')
)
def print_selected(signalData):
    print(signalData)
    # Note: dash_vega_components escapes dots in property names, so "properties.CSDUID" becomes "properties\\.CSDUID"
    if signalData and 'select_sub' in signalData and 'properties\\.DGUID' in signalData['select_sub']:
        return f"Selected Subdivision ID: {signalData['select_sub']['properties\\.DGUID']}"
    return "No subdivision selected."

# ===== 7. Callback to Update the World Map Based on Selection =====
@callback(
    Output('world-map', 'spec'),
    Input('bc-map', 'signalData')
)
def update_world_map(signalData):
    # Default to default_dguid if nothing is selected.
    selected_dguid = default_dguid
    if signalData and 'select_sub' in signalData and 'properties\\.DGUID' in signalData['select_sub']:
        selected_dguid = signalData['select_sub']['properties\\.DGUID']
        print(selected_dguid)
    return create_world_chart(selected_dguid)

if __name__ == '__main__':
    app.run(debug=True)
