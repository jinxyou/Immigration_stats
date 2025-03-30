import dash
from dash import html, dcc, Output, Input, callback, State
import dash_leaflet as dl
import dash_bootstrap_components as dbc
import geopandas as gpd
import pandas as pd
import json
from dash_extensions.javascript import arrow_function, assign

# === Load & Clean BC GeoJSON ===
gdf_bc = gpd.read_file("data/raw/geojson/lcsd000b21a_e_simplified_0.25percent.geojson")
gdf_bc = gdf_bc[gdf_bc['DGUID'].astype(str).str.startswith("2021A000559")]
gdf_bc.crs = "EPSG:3347"
gdf_bc = gdf_bc.to_crs(epsg=4326)
gdf_bc["geometry"] = gdf_bc["geometry"].buffer(0)
gdf_bc = gdf_bc[~gdf_bc.geometry.is_empty & gdf_bc.geometry.notnull()].copy()
bc_geojson = json.loads(gdf_bc.to_json())

# === Load & Clean Immigration Data ===
df = pd.read_parquet("data/processed/immigration_data/immigration_stats_bc_census_subdivisions.parquet")
df_immi = df[(df["Age (8D)"] == "Total - Age") & (df["Gender (3)"] == "Total - Gender")]
df_immi = df_immi[["GEO", "DGUID", "Place of birth (290)",
                   "Immigrant status and period of immigration (11):Total - Immigrant status and period of immigration[1]"]]
df_immi.rename(columns={
    "Place of birth (290)": "Birthplace",
    "Immigrant status and period of immigration (11):Total - Immigrant status and period of immigration[1]": "Count"
}, inplace=True)
df_immi["Count"] = pd.to_numeric(df_immi["Count"], errors='coerce')
df_immi = df_immi.dropna(subset=["Count"])
default_dguid = [df_immi["DGUID"].iloc[0]]

# === Load & Clean World Countries GeoJSON ===
world_gdf = gpd.read_file("data/processed/geojson/world_countries_clean.geojson")
# if world_gdf.crs != "EPSG:4326":
#     world_gdf = world_gdf.to_crs(epsg=4326)

# === World Style Function ===
# Class breaks for immigrant counts
classes = [0, 50, 100, 500, 1000, 5000]
colorscale = ['#FFEDA0', '#FED976', '#FEB24C', '#FD8D3C', '#FC4E2A', '#E31A1C']

style_handle = assign("""function(feature, context){
    const {classes, colorscale, style, colorProp} = context.hideout;
    const value = feature.properties[colorProp];
    for (let i = 0; i < classes.length; ++i) {
        if (value > classes[i]) {
            style.fillColor = colorscale[i];
        }
    }
    return style;
}""")
style = dict(weight=1, opacity=1, color='black', dashArray='3', fillOpacity=0.7)




# === Function to Build World GeoJSON from Selection ===
def get_world_geojson(selected_dguid):
    df_filtered = df_immi[df_immi["DGUID"].isin(selected_dguid)]
    df_agg = df_filtered.groupby("Birthplace", as_index=False)["Count"].sum()
    merged = world_gdf.merge(df_agg, left_on="ADMIN", right_on="Birthplace", how="left")
    merged["Count"] = merged["Count"].fillna(0)
    geojson_dict = json.loads(merged.to_json())
    return geojson_dict

# === Initial World GeoJSON ===
world_geojson = get_world_geojson(default_dguid)

# === App Layout ===
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H4("BC Subdivisions Map"),
            dl.Map([
                dl.TileLayer(),
                dl.GeoJSON(
                    data=bc_geojson,
                    id="bc-geojson",
                    zoomToBoundsOnClick=False,
                    hoverStyle=arrow_function(dict(weight=5, color='#666', dashArray=''))
                )],
            center=[54.5, -126],
            zoom=5,
            style={'width': '100%', 'height': '600px'},
            id="bc-map")
        ], width=6),

        dbc.Col([
            html.H4("Immigrant Origins World Map"),
            dl.Map([
                dl.TileLayer(),
                dl.GeoJSON(
                    data=world_geojson,
                    id="world-geojson",
                    zoomToBoundsOnClick=False,
                    hoverStyle=arrow_function(dict(weight=5, color='#666', dashArray='')),
                    style=style_handle,
                    hideout=dict(colorscale=colorscale, classes=classes, style=style, colorProp="Count")
)
            ],
            center=[20, 0],
            zoom=2,
            style={'width': '100%', 'height': '600px'},
            id="world-map")
        ], width=6)
    ]),
    dcc.Store(id="selected-dguid", data=default_dguid),
    html.Div(id="capital")
], fluid=True)

@app.callback(Output("capital", "children"), [Input("bc-geojson", "clickData")])
def capital_click(feature):
    if feature is not None:
        return f"You clicked {feature['properties']['DGUID']}"

@callback(
    Output("selected-dguid", "data"),
    Input("bc-geojson", "clickData")
)
def update_selected(feature):
    # print("Clicked feature:", feature)  
    if not feature:
        return default_dguid
    dguid = feature["properties"].get("DGUID")
    print("Selected DGUID:", dguid)    
    return [dguid] if dguid else default_dguid


@callback(
    Output("world-geojson", "data"),
    Input("selected-dguid", "data")
)
def update_world_geojson(selected_dguid):
    return get_world_geojson(selected_dguid)

# === Run App ===
if __name__ == '__main__':
    app.run(debug=True)