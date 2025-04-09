import dash
from dash import html, dcc, Output, Input, callback
import dash_leaflet as dl
import dash_bootstrap_components as dbc
import geopandas as gpd
import pandas as pd
import json
from dash_extensions.javascript import arrow_function, assign
import dash_vega_components as dvc
import altair as alt
from flask_caching import Cache

alt.data_transformers.enable("vegafusion")

# === Load & Clean Canada GeoJSON ===
gdf_csd = gpd.read_file("data/raw/geojson/lcsd000b21a_e_simplified_0.25percent.geojson")
gdf_csd.crs = "EPSG:3347"
gdf_csd = gdf_csd.to_crs(epsg=4326)
gdf_csd["geometry"] = gdf_csd["geometry"].buffer(0)
gdf_csd = gdf_csd[~gdf_csd.geometry.is_empty & gdf_csd.geometry.notnull()].copy()
gdf_csd.rename(columns={"CSDNAME": "NAME"}, inplace=True)
csd_geojson = json.loads(gdf_csd.to_json())

gdf_cd = gpd.read_file("data/raw/geojson/lcd_000b21a_e_simplified_0.5percent.geojson")
gdf_cd.crs = "EPSG:3347"
gdf_cd = gdf_cd.to_crs(epsg=4326)
gdf_cd["geometry"] = gdf_cd["geometry"].buffer(0)
gdf_cd = gdf_cd[~gdf_cd.geometry.is_empty & gdf_cd.geometry.notnull()].copy()
gdf_cd.rename(columns={"CDNAME": "NAME"}, inplace=True)

gdf_prov = gpd.read_file("data/raw/geojson/lpr_000b21a_e_simplified_0.1percent.geojson")
gdf_prov.crs = "EPSG:3347"
gdf_prov = gdf_prov.to_crs(epsg=4326)
gdf_prov["geometry"] = gdf_prov["geometry"].buffer(0)
gdf_prov = gdf_prov[~gdf_prov.geometry.is_empty & gdf_prov.geometry.notnull()].copy()
gdf_prov.drop(columns=["NAME"], inplace=True, errors="ignore")
gdf_prov.rename(columns={"PRENAME": "NAME"}, inplace=True)

status_options = [
    "Total",
    "Non-immigrants",
    "Immigrants",
    "Non-permanent residents"
]

gender_options = [
    "Total - Gender",
    "Men+",
    "Women+"
]

age_options = [
    "Total - Age",
    "0 to 14 years",
    "15 to 24 years",
    "25 to 54 years",
    "55 to 64 years",
    "65 years and over"
]

immigration_period_cols = {
    "Immigrant status and period of immigration (11):Before 1980[4]": "Before 1980",
    "Immigrant status and period of immigration (11):1980 to 1990[5]": "1980 to 1990",
    "Immigrant status and period of immigration (11):1991 to 2000[6]": "1991 to 2000",
    "Immigrant status and period of immigration (11):2001 to 2010[7]": "2001 to 2010",
    "Immigrant status and period of immigration (11):2011 to 2021[8]": "2011 to 2021",
    "Immigrant status and period of immigration (11):2011 to 2015[9]": "2011 to 2015",
    "Immigrant status and period of immigration (11):2016 to 2021[10]": "2016 to 2021"
}

def melt_immigration_periods(df_raw):
    df_period = df_raw[["GEO", "DGUID", "Place of birth (290)", "Gender (3)", "Age (8D)", "Province"] + list(immigration_period_cols.keys())].copy()
    df_period.rename(columns={
        "Place of birth (290)": "Birthplace",
        "Gender (3)": "Gender",
        "Age (8D)": "Age",
        **immigration_period_cols
    }, inplace=True)

    df_period = df_period.melt(
        id_vars=["DGUID", "Birthplace", "Gender", "Age", "Province"],
        value_vars=list(immigration_period_cols.values()),
        var_name="Period",
        value_name="Count"
    )
    df_period["Count"] = pd.to_numeric(df_period["Count"], errors="coerce")
    df_period = df_period.dropna(subset=["Count"])
    return df_period

# === Load & Clean Immigration Data ===
df_csd_raw = pd.read_parquet("data/processed/immigration_data/immigration_stats_census_subdivisions.parquet")
df_csd = df_csd_raw[["GEO", "DGUID", "Place of birth (290)", "Gender (3)", "Age (8D)",
                   "Immigrant status and period of immigration (11):Total - Immigrant status and period of immigration[1]",
                   "Immigrant status and period of immigration (11):Non-immigrants[2]",
                   "Immigrant status and period of immigration (11):Immigrants[3]",
                   "Immigrant status and period of immigration (11):Non-permanent residents[11]",
                   "Province", "Type"]]
df_csd.rename(columns={
    "Place of birth (290)": "Birthplace",
    "Gender (3)": "Gender",
    "Age (8D)": "Age",
    "Immigrant status and period of immigration (11):Total - Immigrant status and period of immigration[1]": "Total",
    "Immigrant status and period of immigration (11):Non-immigrants[2]": "Non-immigrants",
    "Immigrant status and period of immigration (11):Immigrants[3]": "Immigrants",
    "Immigrant status and period of immigration (11):Non-permanent residents[11]": "Non-permanent residents"
}, inplace=True)
df_csd = df_csd.melt(
    id_vars=["GEO", "DGUID", "Birthplace", "Province", "Type", "Gender", "Age"],
    value_vars=["Total", "Non-immigrants", "Immigrants", "Non-permanent residents"],
    var_name="ImmigrantStatus",
    value_name="Count"
)
df_csd["Count"] = pd.to_numeric(df_csd["Count"], errors='coerce')
df_csd = df_csd.dropna(subset=["Count"])

# Repeat similar processing for Census Divisions and Provinces.
df_cd_raw = pd.read_parquet("data/processed/immigration_data/immigration_stats_census_divisions.parquet")
df_cd = df_cd_raw[["GEO", "DGUID", "Place of birth (290)", "Gender (3)", "Age (8D)",
               "Immigrant status and period of immigration (11):Total - Immigrant status and period of immigration[1]",
               "Immigrant status and period of immigration (11):Non-immigrants[2]",
               "Immigrant status and period of immigration (11):Immigrants[3]",
               "Immigrant status and period of immigration (11):Non-permanent residents[11]",
               "Province", "Type"]]
df_cd.rename(columns={
    "Place of birth (290)": "Birthplace",
    "Gender (3)": "Gender",
    "Age (8D)": "Age",
    "Immigrant status and period of immigration (11):Total - Immigrant status and period of immigration[1]": "Total",
    "Immigrant status and period of immigration (11):Non-immigrants[2]": "Non-immigrants",
    "Immigrant status and period of immigration (11):Immigrants[3]": "Immigrants",
    "Immigrant status and period of immigration (11):Non-permanent residents[11]": "Non-permanent residents"
}, inplace=True)
df_cd = df_cd.melt(
    id_vars=["GEO", "DGUID", "Birthplace", "Province", "Type", "Gender", "Age"],
    value_vars=["Total", "Non-immigrants", "Immigrants", "Non-permanent residents"],
    var_name="ImmigrantStatus",
    value_name="Count"
)
df_cd["Count"] = pd.to_numeric(df_cd["Count"], errors="coerce")
df_cd = df_cd.dropna(subset=["Count"])

df_prov_raw = pd.read_parquet("data/processed/immigration_data/immigration_stats_provinces.parquet")
df_prov = df_prov_raw[["GEO", "DGUID", "Place of birth (290)", "Gender (3)", "Age (8D)",
                   "Immigrant status and period of immigration (11):Total - Immigrant status and period of immigration[1]",
                   "Immigrant status and period of immigration (11):Non-immigrants[2]",
                   "Immigrant status and period of immigration (11):Immigrants[3]",
                   "Immigrant status and period of immigration (11):Non-permanent residents[11]",
                   "Province", "Type"]]
df_prov.rename(columns={
    "Place of birth (290)": "Birthplace",
    "Gender (3)": "Gender",
    "Age (8D)": "Age",
    "Immigrant status and period of immigration (11):Total - Immigrant status and period of immigration[1]": "Total",
    "Immigrant status and period of immigration (11):Non-immigrants[2]": "Non-immigrants",
    "Immigrant status and period of immigration (11):Immigrants[3]": "Immigrants",
    "Immigrant status and period of immigration (11):Non-permanent residents[11]": "Non-permanent residents"
}, inplace=True)
df_prov = df_prov.melt(
    id_vars=["GEO", "DGUID", "Birthplace", "Province", "Type", "Gender", "Age"],
    value_vars=["Total", "Non-immigrants", "Immigrants", "Non-permanent residents"],
    var_name="ImmigrantStatus",
    value_name="Count"
)
df_prov["Count"] = pd.to_numeric(df_prov["Count"], errors="coerce")
df_prov = df_prov.dropna(subset=["Count"])

df_csd_total = df_csd[
    (df_csd["Gender"] == "Total - Gender") &
    (df_csd["Age"] == "Total - Age")
].copy()

df_cd_total = df_cd[
    (df_cd["Gender"] == "Total - Gender") &
    (df_cd["Age"] == "Total - Age")
].copy()

df_prov_total = df_prov[
    (df_prov["Gender"] == "Total - Gender") &
    (df_prov["Age"] == "Total - Age")
].copy()



# === Create Combined DataFrames ===
# For each geographic level we add a new column ("variable_type") so we can later choose between status and period rows.
# For Census Subdivisions:
df_csd_status = df_csd.copy()
df_csd_status['variable_type'] = 'status'
df_csd_period_new = melt_immigration_periods(df_csd_raw)
df_csd_period_new['variable_type'] = 'period'
df_csd_combined = pd.concat([df_csd_status, df_csd_period_new], ignore_index=True)
df_csd_period_total = df_csd_combined[
    (df_csd_combined["variable_type"] == "period") &
    (df_csd_combined["Gender"] == "Total - Gender")
].copy()

# same for CD and Province if used separately


# For Census Divisions:
df_cd_status = df_cd.copy()
df_cd_status['variable_type'] = 'status'
df_cd_period_new = melt_immigration_periods(df_cd_raw)
df_cd_period_new['variable_type'] = 'period'
df_cd_combined = pd.concat([df_cd_status, df_cd_period_new], ignore_index=True)
df_cd_period_total = df_cd_combined[
    (df_cd_combined["variable_type"] == "period") &
    (df_cd_combined["Gender"] == "Total - Gender")
].copy()

# same for CD and Province if used separately


# For Provinces:
df_prov_status = df_prov.copy()
df_prov_status['variable_type'] = 'status'
df_prov_period_new = melt_immigration_periods(df_prov_raw)
df_prov_period_new['variable_type'] = 'period'
df_prov_combined = pd.concat([df_prov_status, df_prov_period_new], ignore_index=True)
df_prov_period_total = df_prov_combined[
    (df_prov_combined["variable_type"] == "period") &
    (df_prov_combined["Gender"] == "Total - Gender")
].copy()

# same for CD and Province if used separately


default_dguid = "ALL"

# === Load & Clean World Countries GeoJSON ===
world_gdf = gpd.read_file("data/processed/geojson/world_countries_clean.geojson")
world_gdf["geometry"] = world_gdf["geometry"].buffer(0)

region_gdf = gpd.read_file("data/processed/geojson/region_clean.geojson")
region_gdf["geometry"] = region_gdf["geometry"].buffer(0)

continent_gdf = gpd.read_file("data/processed/geojson/continent_clean.geojson")
continent_gdf["geometry"] = continent_gdf["geometry"].buffer(0)

# === World Style Function ===
classes = [0, 0.1, 0.5, 1, 2, 5, 10]
colorscale = ['#FFEDA0', '#FED976', '#FEB24C', '#FD8D3C', '#FC4E2A', '#BD0026', '#800026']

style_handle = assign("""function(feature, context){
    const {classes, colorscale, style, colorProp} = context.hideout;
    const value = feature.properties[colorProp];
    for (let i = 0; i < classes.length; ++i) {
        if (value >= classes[i]) {
            style.fillColor = colorscale[i];
        }
    }
    return style;
}""")
style = dict(weight=1, opacity=1, color='white', dashArray='3', fillOpacity=0.5)

# === Function to Build World GeoJSON from Selection ===
def get_world_geojson(selected_dguid):
    if selected_dguid == "ALL":
        df_filtered = df_csd_combined[df_csd_combined["variable_type"] == 'status'].copy()
    else:
        df_filtered = df_csd_combined[(df_csd_combined["DGUID"] == selected_dguid) &
                                      (df_csd_combined["variable_type"] == 'status')].copy()

    df_agg = df_filtered.groupby("Birthplace", as_index=False)["Count"].sum()
    match = df_agg.loc[df_agg["Birthplace"] == "Total – Place of birth", "Count"]
    total_count = match.values[0] if not match.empty else df_agg["Count"].sum()

    df_agg["Percentage"] = (df_agg["Count"] / total_count * 100).round(2)

    merged = world_gdf.merge(df_agg, left_on="ADMIN", right_on="Birthplace", how="left")
    merged["Count"] = merged["Count"].fillna(0)
    merged["Percentage"] = merged["Percentage"].fillna(0)
    merged["tooltip"] = merged.apply(
        lambda row: f"{row['ADMIN']}: {int(row['Count'])} ({row['Percentage']}%)", axis=1
    )

    return json.loads(merged.to_json())

def get_csd_geojson(selected_country):
    if not selected_country:
        return csd_geojson

    df_total = df_csd_combined[(df_csd_combined["Birthplace"] == "Total – Place of birth") &
                               (df_csd_combined["variable_type"] == 'status')]
    df_total = df_total[["DGUID", "Count"]].rename(columns={"Count": "TotalCount"})

    df_country = df_csd_combined[(df_csd_combined["Birthplace"] == selected_country) &
                                 (df_csd_combined["variable_type"] == 'status')]
    df_country = df_country[["DGUID", "Count"]].rename(columns={"Count": "CountryCount"})

    df_merged = pd.merge(df_total, df_country, on="DGUID", how="left")
    df_merged["CountryCount"] = df_merged["CountryCount"].fillna(0)
    df_merged["Percentage"] = (df_merged["CountryCount"] / df_merged["TotalCount"] * 100).round(2)

    merged = gdf_csd.merge(df_merged, on="DGUID", how="left")
    merged["Percentage"] = merged["Percentage"].fillna(0)
    merged["tooltip"] = merged.apply(
        lambda row: f"{row['NAME']}: {int(row['CountryCount'])} immigrants ({row['Percentage']}%)" 
        if pd.notna(row['CountryCount']) else f"{row['NAME']}: 0 immigrants (0%)",
        axis=1
    )

    return json.loads(merged.to_json())

# === Initial World GeoJSON ===
world_geojson = get_world_geojson(default_dguid)
csd_geojson = get_csd_geojson(None)

indent = "\u00A0\u00A0\u00A0"

# === App Layout ===
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], prevent_initial_callbacks=True)
cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache-dir'
})

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.Label("Immigrant status:"),
            dcc.Dropdown(
                id="immigrant-status",
                options=[{"label": s, "value": s} for s in status_options],
                value="Total",
                clearable=False,
                style={"marginBottom": "10px"}
        )], width=4),
        # dbc.Col([
        #     html.Label("Gender:"),
        #     dcc.Dropdown(
        #         id="gender-filter",
        #         options=[{"label": g, "value": g} for g in gender_options],
        #         value="Total - Gender",
        #         clearable=False,
        #         style={"marginBottom": "10px"}
        #     )], width=4),
        # dbc.Col([
        #     html.Label("Age:"),
        #     dcc.Dropdown(
        #         id="age-filter",
        #         options=[{"label": a, "value": a} for a in age_options],
        #         value=["Total - Age"],
        #         multi=True,
        #         clearable=False,
        #         style={"marginBottom": "10px"}
        #     )], width=4),
    ]),
    dbc.Row([
        dbc.Col([
            html.Label("Select administrative level:"),
            dcc.Dropdown(
                id="admin-level",
                options=[
                    {"label": "Census Subdivision (CSD)", "value": "CSD"},
                    {"label": "Census Division (CD)", "value": "CD"},
                    {"label": "Province", "value": "Province"},
                ],
                value="CSD",
                clearable=False,
                style={"marginBottom": "10px", "width": "300px"}
            ),
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
            id="bc-map"),
        ], width=6),
        dbc.Col([
            html.Label("Select administrative level:"),
            dcc.Dropdown(
                id="pie-grouping",
                options=[
                    {"label": f"World", "value": "Country (including Canada)"},
                    {"label": f"{indent}Inside Canada", "value": "---", "disabled": True},
                    {"label": f"{indent*2}Province", "value": "Inside Canada (Provinces)"},
                    {"label": f"{indent}Outside Canada", "value": "---", "disabled": True},
                    {"label": f"{indent*2}Continent", "value": "Continent"},
                    {"label": f"{indent*2}Region", "value": "Region"},
                    {"label": f"{indent*2}Country (excluding Canada)", "value": "Country (excluding Canada)"}
                ],
                value="Country (including Canada)",
                clearable=False,
                style={"marginBottom": "10px", "width": "300px"}
            ),
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
        ], width=6)
    ]),
    dbc.Row([
        dbc.Col([
            dvc.Vega(id="csd-pie-chart"),
        ], width=3),
        dbc.Col([dvc.Vega(id="canada-line-chart")], width=3),
        dbc.Col([
            dvc.Vega(id="origin-pie-chart"),
        ], width=3),
        dbc.Col([dvc.Vega(id="world-line-chart")], width=3),
    ]),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Intersectional Immigration Stats"),
                dbc.CardBody([
                    html.P("People in selected Canada region originally from selected world region"),
                    dvc.Vega(id="intersection-gender-chart"),
                    dvc.Vega(id="intersection-age-chart"),
                    dvc.Vega(id="intersection-line-chart")
                ])
            ])
        ], width=12)
    ]),


    # dcc.Store(id="filtered-data"),
    dcc.Store(id="selected-dguid", data=default_dguid),
    dcc.Store(id="selected-country", data=None),
    dcc.Store(id="hovered-world-map", data=None),
    dcc.Store(id="hovered-canada-map", data=None),
], fluid=True)

# ========= Callbacks =========

# @cache.memoize(timeout=60)
# @callback(
#     Output("filtered-data", "data"),
#     Input("immigrant-status", "value"),
#     Input("admin-level", "value")
# )
# def filter_base_data(immigrant_status, admin_level):
#     if admin_level == "CD":
#         df = df_cd_combined[df_cd_combined['variable_type'] == 'status']
#     elif admin_level == "Province":
#         df = df_prov_combined[df_prov_combined['variable_type'] == 'status']
#     else:
#         df = df_csd_combined[df_csd_combined['variable_type'] == 'status']

#     filtered_df = df[
#         (df["ImmigrantStatus"] == immigrant_status)
#     ]
#     return filtered_df.to_json(date_format='iso', orient='split')

@callback(
    Output("hovered-world-map", "data"),
    Input("world-geojson", "hoverData")
)
def update_hovered_region(feature):
    if not feature:
        return None
    return feature["properties"].get("ADMIN")

@callback(
    Output("hovered-canada-map", "data"),
    Input("csd-geojson", "hoverData")
)
def update_hovered_canada(feature):
    if not feature:
        return None
    return feature["properties"].get("NAME")

@callback(
    Output("csd-geojson", "data"),
    Input("selected-country", "data"),
    Input("admin-level", "value")
)
def update_subdivision_geojson(selected_country, admin_level):
    df_map = {
        "CSD": df_csd_total,
        "CD": df_cd_total,
        "Province": df_prov_total,
    }
    gdf_map = {
        "CSD": gdf_csd,
        "CD": gdf_cd,
        "Province": gdf_prov,
    }

    df = df_map[admin_level]
    gdf = gdf_map[admin_level]

    if not selected_country:
        return json.loads(gdf.to_json())

    df_total = df[df["Birthplace"] == "Total – Place of birth"][["DGUID", "Count"]].rename(columns={"Count": "TotalCount"})
    df_country = df[df["Birthplace"] == selected_country][["DGUID", "Count"]].rename(columns={"Count": "CountryCount"})

    df_merged = pd.merge(df_total, df_country, on="DGUID", how="left")
    df_merged["CountryCount"] = df_merged["CountryCount"].fillna(0)
    df_merged["Percentage"] = (df_merged["CountryCount"] / df_merged["TotalCount"] * 100).round(2)

    merged = gdf.merge(df_merged, on="DGUID", how="left")
    merged["Percentage"] = merged["Percentage"].fillna(0)
    merged["tooltip"] = merged.apply(
        lambda row: f"{row['NAME']}: {int(row['CountryCount'])} immigrants ({row['Percentage']}%)"
        if pd.notna(row['CountryCount']) else f"{row['NAME']}: 0 immigrants (0%)", axis=1
    )

    return json.loads(merged.to_json())



@callback(
    Output("world-geojson", "data"),
    Input("selected-dguid", "data"),
    Input("pie-grouping", "value"),
    Input("admin-level", "value")
)
def update_world_geojson(selected_dguid, pie_grouping, admin_level):
    df_map = {
        "CSD": df_csd_total,
        "CD": df_cd_total,
        "Province": df_prov_total,
    }
    df = df_map[admin_level]

    if selected_dguid != "ALL":
        df = df[df["DGUID"] == selected_dguid]

    df_agg = df.groupby("Birthplace", as_index=False)["Count"].sum()

    total_key = {
        "Region": "Outside Canada",
        "Continent": "Outside Canada",
        "Country (excluding Canada)": "Outside Canada",
        "Inside Canada (Provinces)": "Inside Canada"
    }.get(pie_grouping, "Total – Place of birth")

    match = df_agg.loc[df_agg["Birthplace"] == total_key, "Count"]
    total_count = match.values[0] if not match.empty else df_agg["Count"].sum()
    df_agg["Percentage"] = (df_agg["Count"] / total_count * 100).round(2)

    if pie_grouping == "Region":
        merged = region_gdf.merge(df_agg, left_on="ADMIN", right_on="Birthplace", how="left")
    elif pie_grouping == "Continent":
        merged = continent_gdf.merge(df_agg, left_on="ADMIN", right_on="Birthplace", how="left")
    elif pie_grouping == "Inside Canada (Provinces)":
        merged = gdf_prov.merge(df_agg, left_on="NAME", right_on="Birthplace", how="left")
        merged.rename(columns={"NAME": "ADMIN"}, inplace=True)
    elif pie_grouping == "Country (excluding Canada)":
        merged = world_gdf[world_gdf["ADMIN"] != "Inside Canada"].merge(df_agg, left_on="ADMIN", right_on="Birthplace", how="left")
    else:
        merged = world_gdf.merge(df_agg, left_on="ADMIN", right_on="Birthplace", how="left")

    merged["Count"] = merged["Count"].fillna(0)
    merged["Percentage"] = merged["Percentage"].fillna(0)
    merged["tooltip"] = merged.apply(
        lambda row: f"{row['ADMIN']}: {int(row['Count'])} ({row['Percentage']}%)", axis=1
    )

    return json.loads(merged.to_json())


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
    Input("admin-level", "value"),
    Input("selected-country", "data")
)
def update_canada_map_title(admin_level, selected_country):
    if selected_country:
        return f"Canada {admin_level} Map for Immigrants from {selected_country}"
    return "Canada Subdivisions Map"

@callback(
    Output("world-map-title", "children"),
    Input("csd-geojson", "clickData")
)
def update_world_title(feature):
    if feature:
        return f"Immigrant Origins for {feature['properties']['NAME']}"
    return "Immigrant Origins for All Subdivisions"

@callback(
    Output("origin-pie-chart", "spec"),
    Input("selected-dguid", "data"),
    Input("pie-grouping", "value"),
    Input("hovered-world-map", "data"),
    # Input("filtered-data", "data"),
    Input("admin-level", "value"),
)
def update_world_pie_chart(selected_dguid, grouping_level, hovered_label, admin_level):
    if selected_dguid == "ALL":
        return alt.Chart(pd.DataFrame({"label": ["No subdivision selected"], "count": [1]})) \
            .mark_bar().encode(x="label:N", y="count:Q") \
            .properties(title="No data").to_dict(format="vega")

    df_map = {
        "CSD": df_csd_total,
        "CD": df_cd_total,
        "Province": df_prov_total,
    }
    df = df_map[admin_level]


    if grouping_level == "Country (including Canada)":
        df = df[df["Type"].isin(["Country", "Inside Canada"])]
    elif grouping_level == "Country (excluding Canada)":
        df = df[df["Type"] == "Country"]
    elif grouping_level == "Inside Canada (Provinces)":
        df = df[df["Type"] == "Province"]
    elif grouping_level in ["Region", "Continent"]:
        df = df[(df["Type"] == grouping_level) | (df["Birthplace"] == "Oceania")]

    if df.empty:
        return alt.Chart(pd.DataFrame({"label": ["No data"], "count": [1]})) \
            .mark_bar().encode(x="label:N", y="count:Q") \
            .properties(title="No data").to_dict(format="vega")

    df_agg = df.groupby("Birthplace", as_index=False)["Count"].sum()
    df_agg = df_agg.sort_values("Count", ascending=False).head(15)
    df_agg.rename(columns={"Birthplace": "Label"}, inplace=True)

    chart = alt.Chart(df_agg).mark_bar().encode(
        x=alt.X("Label:N", sort=df_agg["Label"].tolist(), title="Birthplace"),
        y=alt.Y("Count:Q", title="Number of Immigrants"),
        tooltip=["Label", "Count"],
        opacity=alt.condition(
            alt.datum.Label == hovered_label,
            alt.value(1.0),
            alt.value(0.3)
        ) if hovered_label in df_agg["Label"].values else alt.value(1.0)
    ).properties(title="Top Birthplaces")

    return chart.to_dict(format="vega")


@callback(
    Output("csd-pie-chart", "spec"),
    Input("selected-country", "data"),
    Input("admin-level", "value"),
    Input("hovered-canada-map", "data"),
    # Input("filtered-data", "data"),
)
def update_csd_pie_chart(selected_country, admin_level, hovered_label):
    if not selected_country:
        return alt.Chart(pd.DataFrame({"label": ["No country selected"], "count": [1]})).mark_bar().encode(
            x="label:N", y="count:Q"
        ).properties(title="Select a country on the world map").to_dict(format="vega")

    df_map = {
        "CSD": df_csd_total,
        "CD": df_cd_total,
        "Province": df_prov_total
    }
    df_country = df_map[admin_level]
    df_country = df_country[df_country["Birthplace"] == selected_country].copy()


    if admin_level in ["CSD", "CD"]:
        merge_df = gdf_csd[["DGUID", "NAME"]] if admin_level == "CSD" else gdf_cd[["DGUID", "NAME"]]
        df_country = df_country.merge(merge_df, on="DGUID", how="left")
        group_col = "NAME"
    elif admin_level == "Province":
        group_col = "Province"
    else:
        group_col = "Birthplace"

    df_totals = df_country[df_country["Gender"] == "Total - Gender"].groupby(group_col, as_index=False)["Count"].sum()
    df_totals = df_totals.sort_values("Count", ascending=False).head(15)
    label_order = df_totals[group_col].tolist()

    df_country = df_country[df_country["Gender"] == "Total - Gender"]
    df_grouped = df_country[df_country[group_col].isin(label_order)].groupby(group_col, as_index=False)["Count"].sum()

    df_grouped.rename(columns={group_col: "Label"}, inplace=True)

    if df_grouped.empty:
        return alt.Chart(pd.DataFrame({"label": ["No data"], "count": [1]})).mark_bar().encode(
            x="label:N", y="count:Q"
        ).properties(title="No data").to_dict(format="vega")

    chart = alt.Chart(df_grouped).mark_bar().encode(
        x=alt.X("Label:N", sort=label_order, title=admin_level),
        y=alt.Y("Count:Q", title="Number of Immigrants"),
        tooltip=["Label", "Count"]
    )

    return chart.to_dict(format="vega")

# Helper function for line charts.
def make_line_chart(df, group_col):
    if df.empty:
        empty_df = pd.DataFrame({
            "Period": ["No Data"],
            "Count": [0]
        })
        return alt.Chart(empty_df).mark_text(align="center", baseline="middle", fontSize=15).encode(
            text=alt.value("No data available")
        ).properties(height=200).to_dict(format="vega")

    base = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X("Period:N", title="Immigration Period"),
        y=alt.Y("Count:Q", title="Number of Immigrants")
    )

    if group_col == "Gender":
        base = base.encode(color=alt.Color("Gender:N", title="Gender"), tooltip=["Period", "Gender", "Count"])
    elif group_col == "Age":
        base = base.encode(color=alt.Color("Age:N", title="Age Group"), tooltip=["Period", "Age", "Count"])
    else:
        base = base.encode(tooltip=["Period", "Count"])

    return base.to_dict(format="vega")

@callback(
    Output("canada-line-chart", "spec"),
    Input("selected-country", "data"),
)
def update_canada_line_chart(selected_country):
    if not selected_country:
        return make_line_chart(pd.DataFrame(), None)
    # Use only period rows for the line chart
    df = df_csd_combined[(df_csd_combined["Birthplace"] == selected_country) &
                         (df_csd_combined["variable_type"] == 'period')].copy()

    df = df[df["Gender"] == "Total - Gender"]
    grouped = df.groupby("Period", as_index=False)["Count"].sum()
    return make_line_chart(grouped, None)

@callback(
    Output("world-line-chart", "spec"),
    Input("selected-dguid", "data"),
    Input("admin-level", "value"),
)
def update_world_line_chart(selected_dguid, admin_level):
    if selected_dguid == "ALL":
        return make_line_chart(pd.DataFrame(), None)

    if admin_level == "CD":
        df_all = df_cd_combined
    elif admin_level == "Province":
        df_all = df_prov_combined
    else:
        df_all = df_csd_combined

    # Use period rows for the line chart
    df = df_all[(df_all["DGUID"] == selected_dguid) &
                (df_all["Birthplace"] == "Total – Place of birth") &
                (df_all["variable_type"] == 'period')]

    df = df[df["Gender"] == "Total - Gender"]
    grouped = df.groupby("Period", as_index=False)["Count"].sum()
    return make_line_chart(grouped, None)

@callback(
    Output("intersection-gender-chart", "spec"),
    Output("intersection-age-chart", "spec"),
    Output("intersection-line-chart", "spec"),
    Input("selected-dguid", "data"),
    Input("selected-country", "data"),
    Input("admin-level", "value")
)
def update_intersection_charts(selected_dguid, selected_country, admin_level):
    if not selected_country or selected_dguid == "ALL":
        return tuple([alt.Chart(pd.DataFrame({"label": ["No data"], "count": [0]}))
            .mark_bar().encode(x="label:N", y="count:Q")
            .properties(title="No data").to_dict(format="vega")] * 3)

    # Pick correct DataFrame
    df = {
        "CSD": df_csd_combined,
        "CD": df_cd_combined,
        "Province": df_prov_combined
    }[admin_level]

    # Filter for intersection
    df_inter = df[
        (df["DGUID"] == selected_dguid) &
        (df["Birthplace"] == selected_country)
    ]

    # Gender Bar Chart
    gender_df = df_inter[(df_inter["Gender"].isin(["Men+", "Women+"])) &
                         (df_inter["variable_type"] == "status")]
    gender_chart = alt.Chart(gender_df.groupby("Gender", as_index=False)["Count"].sum()).mark_bar().encode(
        x=alt.X("Gender:N", title="Gender"),
        y=alt.Y("Count:Q", title="Count"),
        tooltip=["Gender", "Count"]
    ).properties(title="By Gender").to_dict(format="vega")

    # Age Bar Chart
    age_df = df_inter[(df_inter["Gender"] == "Total - Gender") &
                      (df_inter["variable_type"] == "status")]
    age_chart = alt.Chart(age_df.groupby("Age", as_index=False)["Count"].sum()).mark_bar().encode(
        x=alt.X("Age:N", title="Age Group"),
        y=alt.Y("Count:Q", title="Count"),
        tooltip=["Age", "Count"]
    ).properties(title="By Age Group").to_dict(format="vega")

    # Line Chart by Period
    period_df = df_inter[(df_inter["Gender"] == "Total - Gender") &
                         (df_inter["variable_type"] == "period")]
    line_chart = alt.Chart(period_df.groupby("Period", as_index=False)["Count"].sum()).mark_line(point=True).encode(
        x=alt.X("Period:N", title="Immigration Period"),
        y=alt.Y("Count:Q", title="Count"),
        tooltip=["Period", "Count"]
    ).properties(title="By Immigration Period").to_dict(format="vega")

    return gender_chart, age_chart, line_chart












# === Run App ===
if __name__ == '__main__':
    app.run(debug=True)
