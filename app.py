import dash
from dash import html, dcc, Output, Input, callback, ctx
import dash_leaflet as dl
import dash_leaflet.express as dlx
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
ctg = [
    "{}+".format(
        cls,
    )
    for i, cls in enumerate(classes[:-1])
] + ["{}+".format(classes[-1])]
colorbar = dlx.categorical_colorbar(categories=ctg, colorscale=colorscale, width=300, height=30, position="bottomleft")


# === Function to Build World GeoJSON from Selection ===
def get_world_geojson(selected_dguid):
    # Determine region name and filter df
    if selected_dguid == "ALL":
        df_filtered = df_csd_combined[df_csd_combined["variable_type"] == 'status'].copy()
        region_name = "All Canada"
    else:
        df_filtered = df_csd_combined[
            (df_csd_combined["DGUID"] == selected_dguid) &
            (df_csd_combined["variable_type"] == 'status')
        ].copy()
        row = gdf_csd[gdf_csd["DGUID"] == selected_dguid]
        region_name = row["NAME"].values[0] if not row.empty else "selected region"

    # Aggregate and calculate percentage
    df_agg = df_filtered.groupby("Birthplace", as_index=False)["Count"].sum()
    match = df_agg.loc[df_agg["Birthplace"] == "Total – Place of birth", "Count"]
    total_count = match.values[0] if not match.empty else df_agg["Count"].sum()
    df_agg["Percentage"] = (df_agg["Count"] / total_count * 100).round(2)

    # Merge with world geometries
    merged = world_gdf.merge(df_agg, left_on="ADMIN", right_on="Birthplace", how="left")
    merged["Count"] = merged["Count"].fillna(0)
    merged["Percentage"] = merged["Percentage"].fillna(0)

    # Format tooltip with HTML line breaks
    merged["tooltip"] = merged.apply(
        lambda row: (
            f"{row['ADMIN']}:<br>"
            f"{int(row['Count'])} people from {row['ADMIN']} in {region_name},<br>"
            f"{row['Percentage']}% of Total population of {int(total_count)} in {region_name}"
            if row["Count"] > 0 else f"{row['ADMIN']}:<br>No data"
        ),
        axis=1
    )

    return json.loads(merged.to_json())


def get_canada_geojson(selected_country):
    if not selected_country:
        gdf = gdf_csd.copy()
        gdf["tooltip"] = gdf["NAME"]
        return json.loads(gdf.to_json())

    df_total = df_csd_combined[
        (df_csd_combined["Birthplace"] == "Total – Place of birth") &
        (df_csd_combined["variable_type"] == 'status')
    ]
    df_total = df_total[["DGUID", "Count"]].rename(columns={"Count": "TotalCount"})

    df_country = df_csd_combined[
        (df_csd_combined["Birthplace"] == selected_country) &
        (df_csd_combined["variable_type"] == 'status')
    ]
    df_country = df_country[["DGUID", "Count"]].rename(columns={"Count": "CountryCount"})

    df_merged = pd.merge(df_total, df_country, on="DGUID", how="left")
    df_merged["CountryCount"] = df_merged["CountryCount"].fillna(0)
    df_merged["Percentage"] = (df_merged["CountryCount"] / df_merged["TotalCount"] * 100).round(2)

    merged = gdf_csd.merge(df_merged, on="DGUID", how="left")
    merged["Percentage"] = merged["Percentage"].fillna(0)
    merged["tooltip"] = merged["NAME"]

    return json.loads(merged.to_json())


# === Initial World GeoJSON ===
world_geojson = get_world_geojson(default_dguid)
csd_geojson = get_canada_geojson(None)

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
            )
        ], width=4),
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("Canada Map", id="canada-map-title")),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Select administrative level:"),
                            dcc.Dropdown(
                                id="canada-admin-level",
                                options=[
                                    {"label": "Census Subdivision (CSD)", "value": "CSD"},
                                    {"label": "Census Division (CD)", "value": "CD"},
                                    {"label": "Province", "value": "Province"},
                                ],
                                value="CSD",
                                clearable=False,
                                style={"marginBottom": "10px", "width": "100%"}
                            ),
                        ], width=3),
                        dbc.Col([
                            dbc.Button(
                                "All Canada",
                                id="reset-dguid-button",
                                color="primary",
                                size="sm",
                                style={"marginTop": "30px", "float": "right"}
                            )
                        ], width=9),
                    ], className="mb-2"),

                    dl.Map([
                        dl.TileLayer(),
                        dl.GeoJSON(
                            data=csd_geojson,
                            id="csd-geojson",
                            zoomToBoundsOnClick=False,
                            hoverStyle=arrow_function(dict(weight=5, color='#666', dashArray='')),
                            options=dict(style=style_handle),
                            hideout=dict(colorscale=colorscale, classes=classes, style=style, colorProp="Percentage")
                        ),
                        colorbar
                    ], center=[54.5, -126], zoom=5, style={'width': '100%', 'height': '600px'}, id="bc-map"),

                    dbc.Row([
                        dbc.Col([dvc.Vega(id="canada-bar-chart")], width=6),
                        dbc.Col([dvc.Vega(id="canada-line-chart")], width=6),
                    ])
                ])
            ])
        ], width=6),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("Immigrant Origins World Map", id="world-map-title")),
                dbc.CardBody([
                    html.Label("Select administrative level:"),
                    dcc.Dropdown(
                        id="world-admin-level",
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
                    
                    dl.Map([
                        dl.TileLayer(),
                        dl.GeoJSON(
                            data=world_geojson,
                            id="world-geojson",
                            zoomToBoundsOnClick=False,
                            hoverStyle=arrow_function(dict(weight=5, color='#666', dashArray='')),
                            options=dict(style=style_handle),
                            hideout=dict(colorscale=colorscale, classes=classes, style=style, colorProp="Percentage")
                        ),
                        colorbar
                    ], center=[20, 0], zoom=2, style={'width': '100%', 'height': '600px'}, id="world-map"),
                    dbc.Row([
                        dbc.Col([dvc.Vega(id="world-bar-chart")], width=6),
                        dbc.Col([dvc.Vega(id="world-line-chart")], width=6),
                    ])
                ])
            ])
        ], width=6)
    ]),

    dbc.Row([
        dbc.Col([
            html.H5(id="intersection-title", className="text-center mb-3")
        ], width=12)
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Gender Breakdown"),
                dbc.CardBody([dvc.Vega(id="intersection-gender-chart")])
            ])
        ], width=4),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Age Breakdown"),
                dbc.CardBody([dvc.Vega(id="intersection-age-chart")])
            ])
        ], width=4),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Immigration Period"),
                dbc.CardBody([dvc.Vega(id="intersection-line-chart")])
            ])
        ], width=4),
    ]),

    dcc.Store(id="selected-dguid", data=default_dguid),
    dcc.Store(id="selected-country", data=None),
    dcc.Store(id="hovered-world-map", data=None),
    dcc.Store(id="hovered-canada-map", data=None),
], fluid=True)


# ========= Callbacks =========


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
    Input("immigrant-status", "value"),
    Input("selected-country", "data"),
    Input("canada-admin-level", "value")
)
def update_canada_geojson(immigrant_status, selected_country, admin_level):
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
    df = df[df["ImmigrantStatus"] == immigrant_status]
    gdf = gdf_map[admin_level].copy()

    if not selected_country:
        # Just show the names in the tooltip
        gdf["tooltip"] = gdf["NAME"]
        return json.loads(gdf.to_json())

    df_total = df[df["Birthplace"] == "Total – Place of birth"].groupby("DGUID", as_index=False)["Count"].sum()
    df_total.rename(columns={"Count": "TotalCount"}, inplace=True)

    df_country = df[df["Birthplace"] == selected_country].groupby("DGUID", as_index=False)["Count"].sum()
    df_country.rename(columns={"Count": "CountryCount"}, inplace=True)

    df_merged = pd.merge(df_total, df_country, on="DGUID", how="left")
    df_merged["CountryCount"] = df_merged["CountryCount"].fillna(0)
    df_merged["Percentage"] = (df_merged["CountryCount"] / df_merged["TotalCount"] * 100).round(2)

    merged = gdf.merge(df_merged, on="DGUID", how="left")
    merged["Percentage"] = merged["Percentage"].fillna(0)

    merged["tooltip"] = merged.apply(
        lambda row: (
            f"{row['NAME']}:<br>"
            f"{int(row['CountryCount'])} people from {selected_country}<br>"
            f"{row['Percentage']}% of the {immigrant_status} population of {int(row['TotalCount'])}"
            if pd.notna(row['CountryCount']) and pd.notna(row['TotalCount']) else f"{row['NAME']}"
        ),
        axis=1
    )

    return json.loads(merged.to_json())



@callback(
    Output("world-geojson", "data"),
    Input("immigrant-status", "value"),
    Input("selected-dguid", "data"),
    Input("world-admin-level", "value"),
    Input("canada-admin-level", "value")
)
def update_world_geojson(immigrant_status, selected_dguid, world_admin_level, canada_admin_level):
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

    df = df_map[canada_admin_level]
    gdf = gdf_map[canada_admin_level]

    # Get selected region name
    if selected_dguid != "ALL":
        row = gdf[gdf["DGUID"] == selected_dguid]
        region_name = row["NAME"].values[0] if not row.empty else "selected region"
        df = df[df["DGUID"] == selected_dguid]
    else:
        region_name = "All Canada"

    # Aggregate counts
    df = df[df["ImmigrantStatus"] == immigrant_status]
    df_agg = df.groupby("Birthplace", as_index=False)["Count"].sum()

    total_key = {
        "Region": "Outside Canada",
        "Continent": "Outside Canada",
        "Country (excluding Canada)": "Outside Canada",
        "Inside Canada (Provinces)": "Inside Canada"
    }.get(world_admin_level, "Total – Place of birth")

    match = df_agg.loc[df_agg["Birthplace"] == total_key, "Count"]
    total_count = match.values[0] if not match.empty else df_agg["Count"].sum()
    df_agg["Percentage"] = (df_agg["Count"] / total_count * 100).round(2)

    # Merge with appropriate world GeoJSON
    if world_admin_level == "Region":
        merged = region_gdf.merge(df_agg, left_on="ADMIN", right_on="Birthplace", how="left")
    elif world_admin_level == "Continent":
        merged = continent_gdf.merge(df_agg, left_on="ADMIN", right_on="Birthplace", how="left")
    elif world_admin_level == "Inside Canada (Provinces)":
        merged = gdf_prov.merge(df_agg, left_on="NAME", right_on="Birthplace", how="left")
        merged.rename(columns={"NAME": "ADMIN"}, inplace=True)
    elif world_admin_level == "Country (excluding Canada)":
        merged = world_gdf[world_gdf["ADMIN"] != "Inside Canada"].merge(df_agg, left_on="ADMIN", right_on="Birthplace", how="left")
    else:
        merged = world_gdf.merge(df_agg, left_on="ADMIN", right_on="Birthplace", how="left")

    # Fill and format tooltip
    tooltip_range={
        "Region": "with origin outside Canada",
        "Continent": "with origin outside Canada",
        "Country (excluding Canada)": "with origin outside Canada",
        "Inside Canada (Provinces)": "with origin inside Canada",
        "Country (including Canada)": ""
        }
    merged["Count"] = merged["Count"].fillna(0)
    merged["Percentage"] = merged["Percentage"].fillna(0)
    merged["tooltip"] = merged.apply(
        lambda row: (
            f"{row['ADMIN']}:<br>"
            f"{int(row['Count'])} people from {row['ADMIN']} in {region_name},<br>"
            f"{row['Percentage']}% of {immigrant_status} population of {int(total_count)} in {region_name} {tooltip_range[world_admin_level]}"
            if row["Count"] > 0 else f"{row['ADMIN']}:<br>No data"
        ),
        axis=1
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
    Input("csd-geojson", "clickData"),
    Input("reset-dguid-button", "n_clicks")
)
def update_selected_dguid_combined(clickData, reset_clicks):
    triggered_id = ctx.triggered_id

    if triggered_id == "reset-dguid-button":
        return "ALL"

    if clickData:
        dguid = clickData["properties"].get("DGUID")
        return dguid if dguid else "ALL"

    return dash.no_update


@callback(
    Output("canada-map-title", "children"),
    Input("canada-admin-level", "value"),
    Input("selected-country", "data")
)
def update_canada_map_title(admin_level, selected_country):
    if selected_country:
        return f"Canada {admin_level} Map for Immigrants from {selected_country}"
    return "Canada Map"

@callback(
    Output("world-map-title", "children"),
    Input("selected-dguid", "data"),
    Input("csd-geojson", "clickData"),
)
def update_world_title(selected_dguid, clickData):
    if selected_dguid == "ALL":
        return "Immigrant Origins for All Canada"

    if clickData and "properties" in clickData and "NAME" in clickData["properties"]:
        return f"Immigrant Origins for {clickData['properties']['NAME']}"

    return "Immigrant Origins"


@callback(
    Output("world-bar-chart", "spec"),
    Input("immigrant-status", "value"),
    Input("selected-dguid", "data"),
    Input("world-admin-level", "value"),
    Input("hovered-world-map", "data"),
    Input("canada-admin-level", "value"),
)
def update_world_bar_chart(immigrant_status, selected_dguid, grouping_level, hovered_label, admin_level):
    df_map = {
        "CSD": df_csd_total,
        "CD": df_cd_total,
        "Province": df_prov_total,
    }
    df = df_map[admin_level]
    df = df[df["ImmigrantStatus"] == immigrant_status]

    if selected_dguid != "ALL":
        df = df[df["DGUID"] == selected_dguid]

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
            .properties(title="No data", width="container").to_dict(format="vega")

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
    ).properties(title="Top Birthplaces", width="container")

    return chart.to_dict(format="vega")



@callback(
    Output("canada-bar-chart", "spec"),
    Input("immigrant-status", "value"),
    Input("selected-country", "data"),
    Input("canada-admin-level", "value"),
    Input("hovered-canada-map", "data"),
)
def update_canada_bar_chart(immigrant_status, selected_country, admin_level, hovered_label):
    if not selected_country:
        return alt.Chart(pd.DataFrame({"label": ["No selected"], "count": [1]})).mark_bar().encode(
            x="label:N", y="count:Q"
        ).properties(title="Click a region in the world map").to_dict(format="vega")

    df_map = {
        "CSD": df_csd_total,
        "CD": df_cd_total,
        "Province": df_prov_total
    }
    df_country = df_map[admin_level]
    df_country = df_country[df_country["ImmigrantStatus"] == immigrant_status]
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
        tooltip=["Label", "Count"],
        opacity=alt.condition(
            alt.datum.Label == hovered_label,
            alt.value(1.0),
            alt.value(0.3)
        ) if hovered_label in df_grouped["Label"].values else alt.value(1.0)
    ).properties(width="container")

    return chart.to_dict(format="vega")

# Helper function for line charts.
def make_line_chart(df, group_col):
    if df.empty:
        empty_df = pd.DataFrame({
            "Period": ["No Data"],
            "Count": [0]
        })
        return alt.Chart(empty_df).mark_text(align="center", baseline="middle", fontSize=15).encode(
            text=alt.value("")
        ).properties(height=200, width="container").to_dict(format="vega")

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

    return base.properties(width="container").to_dict(format="vega")

def make_pie_chart(df, label_col):
    if df.empty:
        return alt.Chart(pd.DataFrame({label_col: ["No data"], "Count": [1]})).mark_arc().encode(
            theta="Count:Q",
            color=f"{label_col}:N"
        ).properties(title="No data").to_dict(format="vega")

    return alt.Chart(df).mark_arc(innerRadius=50).encode(
        theta=alt.Theta(field="Count", type="quantitative"),
        color=alt.Color(field=label_col, type="nominal"),
        tooltip=[label_col, "Count"]
    ).properties(title="Immigration Status Breakdown", width="container").to_dict(format="vega")


@callback(
    Output("canada-line-chart", "spec"),
    Input("selected-country", "data"),
    Input("immigrant-status", "value"),
)
def update_canada_status_chart(selected_country, immigrant_status):
    if not selected_country:
        return make_line_chart(pd.DataFrame(), None)

    if immigrant_status == "Immigrants":
        df = df_csd_combined[
            (df_csd_combined["Birthplace"] == selected_country) &
            (df_csd_combined["variable_type"] == "period") &
            (df_csd_combined["Gender"] == "Total - Gender") &
            (df_csd_combined["Age"] == "Total - Age")
        ]
        grouped = df.groupby("Period", as_index=False)["Count"].sum()
        return make_line_chart(grouped, None)
    elif immigrant_status == "Total":
        df = df_csd_combined[
            (df_csd_combined["Birthplace"] == selected_country) &
            (df_csd_combined["variable_type"] == "status") &
            (df_csd_combined["Gender"] == "Total - Gender") &
            (df_csd_combined["Age"] == "Total - Age") &
            (df_csd_combined["ImmigrantStatus"] != "Total")
        ]
        pie_df = df.groupby("ImmigrantStatus", as_index=False)["Count"].sum()
        return make_pie_chart(pie_df, "ImmigrantStatus")
    else:
        return make_line_chart(pd.DataFrame(), None)



@callback(
    Output("world-line-chart", "spec"),
    Input("selected-dguid", "data"),
    Input("canada-admin-level", "value"),
    Input("immigrant-status", "value"),
)
def update_world_line_chart(selected_dguid, admin_level, immigrant_status):
    df_all = {
        "CSD": df_csd_combined,
        "CD": df_cd_combined,
        "Province": df_prov_combined
    }[admin_level]

    base_filter = (
        (df_all["Birthplace"] == "Total – Place of birth") &
        (df_all["Gender"] == "Total - Gender") &
        (df_all["Age"] == "Total - Age")
    )

    if selected_dguid != "ALL":
        base_filter = base_filter & (df_all["DGUID"] == selected_dguid)

    if immigrant_status == "Immigrants":
        df = df_all[
            base_filter & (df_all["variable_type"] == "period")
        ]
        grouped = df.groupby("Period", as_index=False)["Count"].sum()
        return make_line_chart(grouped, None)

    elif immigrant_status == "Total":
        df = df_all[
            base_filter &
            (df_all["variable_type"] == "status") &
            (df_all["ImmigrantStatus"] != "Total")
        ]
        pie_df = df.groupby("ImmigrantStatus", as_index=False)["Count"].sum()
        return make_pie_chart(pie_df, "ImmigrantStatus")

    else:
        return make_line_chart(pd.DataFrame(), None)




@callback(
    Output("intersection-gender-chart", "spec"),
    Output("intersection-age-chart", "spec"),
    Output("intersection-line-chart", "spec"),
    Input("selected-dguid", "data"),
    Input("selected-country", "data"),
    Input("canada-admin-level", "value"),
    Input("immigrant-status", "value")
)
def update_intersection_charts(selected_dguid, selected_country, admin_level, immigrant_status):
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

    # Base filter for intersection
    base = (
        (df["DGUID"] == selected_dguid) &
        (df["Birthplace"] == selected_country)
    )

    # Gender Bar Chart
    gender_df = df[
        base &
        (df["variable_type"] == "status") &
        (df["Gender"] != "Total - Gender") &
        (df["Age"] == "Total - Age") &
        (df["ImmigrantStatus"] == immigrant_status)
    ]
    gender_chart = alt.Chart(
        gender_df.groupby("Gender", as_index=False)["Count"].sum()
    ).mark_bar().encode(
        x=alt.X("Gender:N", title="Gender"),
        y=alt.Y("Count:Q", title="Count"),
        tooltip=["Gender", "Count"]
    ).properties(title="By Gender", width="container").to_dict(format="vega")

    # Age Bar Chart
    age_df = df[
        base &
        (df["variable_type"] == "status") &
        (df["Gender"] == "Total - Gender") &
        (df["ImmigrantStatus"] == immigrant_status)
    ]
    age_chart = alt.Chart(
        age_df.groupby("Age", as_index=False)["Count"].sum()
    ).mark_bar().encode(
        x=alt.X("Age:N", title="Age Group"),
        y=alt.Y("Count:Q", title="Count"),
        tooltip=["Age", "Count"]
    ).properties(title="By Age Group", width="container").to_dict(format="vega")

    # Line Chart by Period
    if immigrant_status == "Immigrants":
        period_df = df[
            base &
            (df["variable_type"] == "period") &
            (df["Gender"] == "Total - Gender") &
            (df["Age"] == "Total - Age")
        ]
        line_chart = alt.Chart(
            period_df.groupby("Period", as_index=False)["Count"].sum()
        ).mark_line(point=True).encode(
            x=alt.X("Period:N", title="Immigration Period"),
            y=alt.Y("Count:Q", title="Count"),
            tooltip=["Period", "Count"]
        ).properties(title="By Immigration Period", width="container").to_dict(format="vega")
    elif immigrant_status == "Total":
        pie_df = df[
            base &
            (df["variable_type"] == "status") &
            (df["Gender"] == "Total - Gender") &
            (df["Age"] == "Total - Age") &
            (df["ImmigrantStatus"] != "Total")
        ].groupby("ImmigrantStatus", as_index=False)["Count"].sum()
        line_chart = make_pie_chart(pie_df, "ImmigrantStatus")
    else:
        line_chart = make_line_chart(pd.DataFrame(), None)

    return gender_chart, age_chart, line_chart



@callback(
    Output("intersection-title", "children"),
    Input("selected-dguid", "data"),
    Input("selected-country", "data"),
    Input("canada-admin-level", "value")
)
def update_intersection_title(dguid, country, admin_level):
    if not country or dguid == "ALL":
        return "Intersectional Immigration Stats (Select a region and a country)"

    # Get Canadian region name
    gdf_map = {
        "CSD": gdf_csd,
        "CD": gdf_cd,
        "Province": gdf_prov
    }
    gdf = gdf_map[admin_level]
    row = gdf[gdf["DGUID"] == dguid]
    region_name = row["NAME"].values[0] if not row.empty else "Selected Region"

    return f"Immigration Stats: {region_name} ← immigrants from {country}"









# === Run App ===
if __name__ == '__main__':
    app.run(debug=True)
