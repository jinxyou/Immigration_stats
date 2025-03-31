import dash
from dash import html, dcc, Output, Input, callback, State
import dash_leaflet as dl
import dash_bootstrap_components as dbc
import geopandas as gpd
import pandas as pd
import json
from dash_extensions.javascript import arrow_function, assign
import dash_vega_components as dvc
import altair as alt

# === Load & Clean Canada GeoJSON ===
gdf_csd = gpd.read_file("data/raw/geojson/lcsd000b21a_e_simplified_0.25percent.geojson")
# gdf_bc = gdf_bc[gdf_bc['DGUID'].astype(str).str.startswith("2021A000559")]
gdf_csd.crs = "EPSG:3347"
gdf_csd = gdf_csd.to_crs(epsg=4326)
gdf_csd["geometry"] = gdf_csd["geometry"].buffer(0)
gdf_csd = gdf_csd[~gdf_csd.geometry.is_empty & gdf_csd.geometry.notnull()].copy()
csd_geojson = json.loads(gdf_csd.to_json())



# === Load & Clean Immigration Data ===
df = pd.read_parquet("data/processed/immigration_data/immigration_stats_census_subdivisions.parquet")
df_immi = df[(df["Age (8D)"] == "Total - Age") & (df["Gender (3)"] == "Total - Gender")]
df_immi = df_immi[["GEO", "DGUID", "Place of birth (290)",
                   "Immigrant status and period of immigration (11):Total - Immigrant status and period of immigration[1]", "Type"]]
df_immi.rename(columns={
    "Place of birth (290)": "Birthplace",
    "Immigrant status and period of immigration (11):Total - Immigrant status and period of immigration[1]": "Count"
}, inplace=True)
df_immi["Count"] = pd.to_numeric(df_immi["Count"], errors='coerce')
df_immi = df_immi.dropna(subset=["Count"])
default_dguid = "ALL"

# === Load & Clean World Countries GeoJSON ===
world_gdf = gpd.read_file("data/processed/geojson/world_countries_clean.geojson")
world_gdf["geometry"] = world_gdf["geometry"].buffer(0)
world_gdf = world_gdf[world_gdf["ADMIN"] != "Canada"]


# === World Style Function ===
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
    if selected_dguid == "ALL":
        df_filtered = df_immi.copy()
    else:
        df_filtered = df_immi[df_immi["DGUID"] == selected_dguid]

    df_agg = df_filtered.groupby("Birthplace", as_index=False)["Count"].sum()
    match = df_agg.loc[df_agg["Birthplace"] == "Total – Place of birth", "Count"]
    total_count = match.values[0] if not match.empty else df_agg["Count"].sum()

    df_agg["Percentage"] = (df_agg["Count"] / total_count * 100).round(2)

    merged = world_gdf.merge(df_agg, left_on="ADMIN", right_on="Birthplace", how="left")
    merged = merged[~merged["Count"].isna()]
    merged["tooltip"] = merged.apply(
        lambda row: f"{row['ADMIN']}: {int(row['Count'])} ({row['Percentage']}%)", axis=1
    )


    return json.loads(merged.to_json())

def get_csd_geojson(selected_country):
    if not selected_country:
        return csd_geojson

    print(selected_country)

    # Total immigrants per CSD (from "Total – Place of birth" rows)
    df_total = df_immi[df_immi["Birthplace"] == "Total – Place of birth"]
    df_total = df_total[["DGUID", "Count"]].rename(columns={"Count": "TotalCount"})

    # Immigrants from selected country per CSD
    df_country = df_immi[df_immi["Birthplace"] == selected_country]
    df_country = df_country[["DGUID", "Count"]].rename(columns={"Count": "CountryCount"})

    # Merge and compute percentage
    df_merged = pd.merge(df_total, df_country, on="DGUID", how="left")
    df_merged = df_merged[~df_merged["CountryCount"].isna()]
    # df_merged["CountryCount"] = df_merged["CountryCount"].fillna(0)
    df_merged["Percentage"] = (df_merged["CountryCount"] / df_merged["TotalCount"] * 100).round(2)

    # Merge with spatial data
    merged = gdf_csd.merge(df_merged, on="DGUID", how="left")
    merged = merged[~merged["CountryCount"].isna()]
    # merged["Percentage"] = merged["Percentage"].fillna(0)

    # Tooltip display
    merged["tooltip"] = merged.apply(
        lambda row: f"{row['CSDNAME']}: {int(row['CountryCount'])} immigrants ({row['Percentage']}%)" 
        if pd.notna(row['CountryCount']) else f"{row['CSDNAME']}: 0 immigrants (0%)",
        axis=1
    )

    return json.loads(merged.to_json())




# === Initial World GeoJSON ===
world_geojson = get_world_geojson(default_dguid)
csd_geojson = get_csd_geojson(None)

# === App Layout ===
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], prevent_initial_callbacks=True)

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H4("Canada Subdivisions Map", id="canada-map-title"),
            dl.Map([
                dl.TileLayer(),
                dl.GeoJSON(
                    data=csd_geojson,
                    id="csd-geojson",
                    zoomToBoundsOnClick=False,
                    hoverStyle=arrow_function(dict(weight=5, color='#666', dashArray='')),
                    options=dict(style=style_handle),
                    hideout=dict(colorscale=colorscale, classes=classes, style=style, colorProp="Percentage")
                )],
            center=[54.5, -126],
            zoom=5,
            style={'width': '100%', 'height': '600px'},
            id="bc-map")
        ], width=6),

        dbc.Col([
            html.H4("Immigrant Origins World Map", id="world-map-title"),
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
            html.Label("Group pie chart by:"),
            dcc.Dropdown(
                id="pie-grouping",
                options=[
                    {"label": "Continent", "value": "Continent"},
                    {"label": "Region", "value": "Region"},
                    {"label": "Country", "value": "Country"},
                ],
                value="Country",  # default view
                clearable=False,
                style={"marginBottom": "10px"}
            ),
            dvc.Vega(id="origin-pie-chart"),
        ], width=6)
    ]),
    dcc.Store(id="selected-dguid", data=default_dguid),
    dcc.Store(id="selected-country", data=None),
    html.Div(id="selected-region")
], fluid=True)


@callback(
    Output("csd-geojson", "data"),
    Input("selected-country", "data")
)
def update_csd_geojson(selected_country):
    return get_csd_geojson(selected_country)

@callback(
    Output("world-geojson", "data"),
    Input("selected-dguid", "data")
)
def update_world_geojson(selected_dguid):
    return get_world_geojson(selected_dguid)


@callback(
    Output("selected-country", "data"),
    Input("world-geojson", "clickData"),
)
def update_selected_country(feature):
    if not feature:
        return None
    return feature["properties"].get("ADMIN")


@callback(
    Output("selected-dguid", "data"),
    Input("csd-geojson", "clickData")
)
def update_selected_dguid(feature):
    if not feature:
        return "ALL"
    dguid = feature["properties"].get("DGUID")
    return dguid if dguid else "ALL"


@callback(
    Output("canada-map-title", "children"),
    Input("selected-country", "data")
)
def update_canada_map_title(selected_country):
    if selected_country:
        return f"Canada Subdivisions Map for Immigrants from {selected_country}"
    return "Canada Subdivisions Map"


@callback(
    Output("world-map-title", "children"),
    Input("csd-geojson", "clickData")
)
def update_world_title(feature):
    if feature:
        return f"Immigrant Origins for {feature['properties']['CSDNAME']}"
    return "Immigrant Origins for All Subdivisions"


@callback(
    Output("origin-pie-chart", "spec"),
    Input("selected-dguid", "data"),
    Input("pie-grouping", "value")
)
def update_pie_chart_altair(selected_dguid, grouping_level):
    if selected_dguid == "ALL":
        return alt.Chart(pd.DataFrame({
            "label": ["No subdivision selected"],
            "count": [1]
        })).mark_arc().encode(
            theta="count:Q",
            color="label:N"
        ).properties(title="Select a subdivision").to_dict()

    # Filter for selected CSD and remove total
    df_filtered = df_immi[
        (df_immi["DGUID"] == selected_dguid) &
        (df_immi["Birthplace"] != "Total – Place of birth")
    ].copy()

    # Ensure Type column exists
    if "Type" not in df_filtered.columns:
        return alt.Chart(pd.DataFrame({
            "label": ["Missing 'Type' column"],
            "count": [1]
        })).mark_arc().encode(
            theta="count:Q",
            color="label:N"
        ).properties(title="Error").to_dict()

    # Keep only rows of the selected type
    df_filtered = df_filtered[df_filtered["Type"] == grouping_level]

    if df_filtered.empty:
        return alt.Chart(pd.DataFrame({
            "label": [f"No data for {grouping_level}"],
            "count": [1]
        })).mark_arc().encode(
            theta="count:Q",
            color="label:N"
        ).properties(title="No data").to_dict()

    df_agg = df_filtered.groupby("Birthplace", as_index=False)["Count"].sum()

    chart = alt.Chart(df_agg).mark_arc().encode(
        theta=alt.Theta("Count:Q"),
        color=alt.Color("Birthplace:N"),
        tooltip=["Birthplace", "Count"]
    ).properties(
        title=f"Immigrants by {grouping_level}"
    )

    return chart.to_dict(format="vega")



# === Run App ===
if __name__ == '__main__':
    app.run(debug=True)