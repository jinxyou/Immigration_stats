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
print(gdf_bc.columns)

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
default_dguid = df_immi["DGUID"].iloc[0]

# === Load & Clean World Countries GeoJSON ===
world_gdf = gpd.read_file("data/processed/geojson/world_countries_clean.geojson")
world_gdf["geometry"] = world_gdf["geometry"].buffer(0)

# === World Style Function ===
# Class breaks for immigrant counts
classes = [0, 0.1, 0.5, 1, 2, 5, 10]
colorscale = ['#FFEDA0', '#FED976', '#FEB24C', '#FD8D3C', '#FC4E2A', '#BD0026', '#800026']

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
    df_filtered = df_immi[df_immi["DGUID"]==selected_dguid]
    df_agg = df_filtered.groupby("Birthplace", as_index=False)["Count"].sum()
    print(df_agg)
    total_count = df_agg.loc[df_agg["Birthplace"] == "Total – Place of birth", "Count"].values[0]

    # Calculate percentage
    df_agg["Percentage"] = (df_agg["Count"] / total_count * 100).round(2)

    # Merge with GeoDataFrame
    merged = world_gdf.merge(df_agg, left_on="ADMIN", right_on="Birthplace", how="left")
    merged["Count"] = merged["Count"].fillna(0)
    merged["Percentage"] = merged["Percentage"].fillna(0)

    # Add tooltip showing country + %
    merged["tooltip"] = merged.apply(
        lambda row: f"{row['ADMIN']}: {row['Percentage']}%", axis=1
    )

    return json.loads(merged.to_json())



# === Initial World GeoJSON ===
world_geojson = get_world_geojson(default_dguid)

# === App Layout ===
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], prevent_initial_callbacks=True)

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
                    options=dict(style=style_handle),
                    hideout=dict(colorscale=colorscale, classes=classes, style=style, colorProp="Percentage")
)
            ],
            center=[20, 0],
            zoom=2,
            style={'width': '100%', 'height': '600px'},
            id="world-map"),
            html.Div(id="world-hover-info", style={"marginTop": "10px"})
        ], width=6)
    ]),
    dcc.Store(id="selected-dguid", data=default_dguid),
    html.Div(id="capital")
], fluid=True)

@callback(
    Output("world-hover-info", "children"),
    Input("world-geojson", "hoverData")
)
def show_world_hover(feature):
    if feature is None:
        return "Hover over a country"
    
    props = feature.get("properties", {})
    country = props.get("ADMIN", "Unknown")
    count = props.get("Count", 0)
    return f"{country}: {int(count)} immigrants"


@app.callback(Output("capital", "children"), [Input("bc-geojson", "clickData")])
def capital_click(feature):
    if feature is not None:
        return f"You clicked {feature['properties']['CSDNAME']}"

@callback(
    Output("selected-dguid", "data"),
    Input("bc-geojson", "clickData")
)
def update_selected(feature):
    if not feature:
        return default_dguid
    dguid = feature["properties"].get("DGUID")
    return dguid if dguid else default_dguid


@callback(
    Output("world-geojson", "data"),
    Input("selected-dguid", "data")
)
def update_world_geojson(selected_dguid):
    return get_world_geojson(selected_dguid)

# === Run App ===
if __name__ == '__main__':
    app.run(debug=True)