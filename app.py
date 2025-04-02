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
gdf_csd.crs = "EPSG:3347"
gdf_csd = gdf_csd.to_crs(epsg=4326)
gdf_csd["geometry"] = gdf_csd["geometry"].buffer(0)
gdf_csd = gdf_csd[~gdf_csd.geometry.is_empty & gdf_csd.geometry.notnull()].copy()
gdf_csd.rename(columns={"CSDNAME": "NAME"}, inplace=True)
csd_geojson=json.loads(gdf_csd.to_json())

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

# === Load & Clean Immigration Data ===
df_csd = pd.read_parquet("data/processed/immigration_data/immigration_stats_census_subdivisions.parquet")
df_csd = df_csd[(df_csd["Age (8D)"] == "Total - Age") & (df_csd["Gender (3)"] == "Total - Gender")]
df_csd = df_csd[["GEO", "DGUID", "Place of birth (290)",
                   "Immigrant status and period of immigration (11):Total - Immigrant status and period of immigration[1]",
                   "Immigrant status and period of immigration (11):Non-immigrants[2]",
                   "Immigrant status and period of immigration (11):Immigrants[3]",
                   "Immigrant status and period of immigration (11):Non-permanent residents[11]",
                   "Province", "Type"]]
df_csd.rename(columns={
    "Place of birth (290)": "Birthplace",
    "Immigrant status and period of immigration (11):Total - Immigrant status and period of immigration[1]": "Total",
    "Immigrant status and period of immigration (11):Non-immigrants[2]": "Non-immigrants",
    "Immigrant status and period of immigration (11):Immigrants[3]": "Immigrants",
    "Immigrant status and period of immigration (11):Non-permanent residents[11]": "Non-permanent residents"
}, inplace=True)
df_csd = df_csd.melt(
    id_vars=["GEO", "DGUID", "Birthplace", "Province", "Type"],
    value_vars=["Total", "Non-immigrants", "Immigrants", "Non-permanent residents"],
    var_name="ImmigrantStatus",
    value_name="Count"
)
df_csd["Count"] = pd.to_numeric(df_csd["Count"], errors='coerce')
df_csd = df_csd.dropna(subset=["Count"])


# Add the same transformation to df_cd
df_cd = pd.read_parquet("data/processed/immigration_data/immigration_stats_census_divisions.parquet")
df_cd = df_cd[(df_cd["Age (8D)"] == "Total - Age") & (df_cd["Gender (3)"] == "Total - Gender")]
df_cd = df_cd[["GEO", "DGUID", "Place of birth (290)",
               "Immigrant status and period of immigration (11):Total - Immigrant status and period of immigration[1]",
               "Immigrant status and period of immigration (11):Non-immigrants[2]",
               "Immigrant status and period of immigration (11):Immigrants[3]",
               "Immigrant status and period of immigration (11):Non-permanent residents[11]",
               "Province", "Type"]]
df_cd.rename(columns={
    "Place of birth (290)": "Birthplace",
    "Immigrant status and period of immigration (11):Total - Immigrant status and period of immigration[1]": "Total",
    "Immigrant status and period of immigration (11):Non-immigrants[2]": "Non-immigrants",
    "Immigrant status and period of immigration (11):Immigrants[3]": "Immigrants",
    "Immigrant status and period of immigration (11):Non-permanent residents[11]": "Non-permanent residents"
}, inplace=True)
df_cd = df_cd.melt(
    id_vars=["GEO", "DGUID", "Birthplace", "Province", "Type"],
    value_vars=["Total", "Non-immigrants", "Immigrants", "Non-permanent residents"],
    var_name="ImmigrantStatus",
    value_name="Count"
)
df_cd["Count"] = pd.to_numeric(df_cd["Count"], errors="coerce")
df_cd = df_cd.dropna(subset=["Count"])


# === Load & Clean Province Immigration Data ===
df_prov = pd.read_parquet("data/processed/immigration_data/immigration_stats_provinces.parquet")
df_prov = df_prov[(df_prov["Age (8D)"] == "Total - Age") & (df_prov["Gender (3)"] == "Total - Gender")]

df_prov = df_prov[["GEO", "DGUID", "Place of birth (290)",
                   "Immigrant status and period of immigration (11):Total - Immigrant status and period of immigration[1]",
                   "Immigrant status and period of immigration (11):Non-immigrants[2]",
                   "Immigrant status and period of immigration (11):Immigrants[3]",
                   "Immigrant status and period of immigration (11):Non-permanent residents[11]",
                   "Province", "Type"]]

df_prov.rename(columns={
    "Place of birth (290)": "Birthplace",
    "Immigrant status and period of immigration (11):Total - Immigrant status and period of immigration[1]": "Total",
    "Immigrant status and period of immigration (11):Non-immigrants[2]": "Non-immigrants",
    "Immigrant status and period of immigration (11):Immigrants[3]": "Immigrants",
    "Immigrant status and period of immigration (11):Non-permanent residents[11]": "Non-permanent residents"
}, inplace=True)

df_prov = df_prov.melt(
    id_vars=["GEO", "DGUID", "Birthplace", "Province", "Type"],
    value_vars=["Total", "Non-immigrants", "Immigrants", "Non-permanent residents"],
    var_name="ImmigrantStatus",
    value_name="Count"
)
df_prov["Count"] = pd.to_numeric(df_prov["Count"], errors="coerce")
df_prov = df_prov.dropna(subset=["Count"])




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
        df_filtered = df_csd.copy()
    else:
        df_filtered = df_csd[df_csd["DGUID"] == selected_dguid]

    df_agg = df_filtered.groupby("Birthplace", as_index=False)["Count"].sum()
    match = df_agg.loc[df_agg["Birthplace"] == "Total – Place of birth", "Count"]
    total_count = match.values[0] if not match.empty else df_agg["Count"].sum()

    df_agg["Percentage"] = (df_agg["Count"] / total_count * 100).round(2)

    merged = world_gdf.merge(df_agg, left_on="ADMIN", right_on="Birthplace", how="left")
    # merged = merged[~merged["Count"].isna()]
    merged["Count"] = merged["Count"].fillna(0)
    merged["Percentage"] = merged["Percentage"].fillna(0)
    merged["tooltip"] = merged.apply(
        lambda row: f"{row['ADMIN']}: {int(row['Count'])} ({row['Percentage']}%)", axis=1
    )


    return json.loads(merged.to_json())

def get_csd_geojson(selected_country):
    if not selected_country:
        return csd_geojson

    print(selected_country)

    # Total immigrants per CSD (from "Total – Place of birth" rows)
    df_total = df_csd[df_csd["Birthplace"] == "Total – Place of birth"]
    df_total = df_total[["DGUID", "Count"]].rename(columns={"Count": "TotalCount"})

    # Immigrants from selected country per CSD
    df_country = df_csd[df_csd["Birthplace"] == selected_country]
    df_country = df_country[["DGUID", "Count"]].rename(columns={"Count": "CountryCount"})

    # Merge and compute percentage
    df_merged = pd.merge(df_total, df_country, on="DGUID", how="left")
    # df_merged = df_merged[~df_merged["CountryCount"].isna()]
    df_merged["CountryCount"] = df_merged["CountryCount"].fillna(0)
    df_merged["Percentage"] = (df_merged["CountryCount"] / df_merged["TotalCount"] * 100).round(2)

    # Merge with spatial data
    merged = gdf_csd.merge(df_merged, on="DGUID", how="left")
    # merged = merged[~merged["CountryCount"].isna()]
    merged["Percentage"] = merged["Percentage"].fillna(0)

    # Tooltip display
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

app.layout = dbc.Container([
    dbc.Row([
        html.Label("Immigrant status:"),
        dcc.Dropdown(
            id="immigrant-status",
            options=[{"label": s, "value": s} for s in status_options],
            value="Total",
            clearable=False,
            style={"marginBottom": "10px"}
        ),
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

            dvc.Vega(id="csd-pie-chart"),
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
            dvc.Vega(id="origin-pie-chart"),
        ], width=6)
    ]),
    dcc.Store(id="selected-dguid", data=default_dguid),
    dcc.Store(id="selected-country", data=None),
    dcc.Store(id="admin-level-store", data="CSD"),
    dcc.Store(id="hovered-world-map", data=None),
    dcc.Store(id="hovered-canada-map", data=None),


], fluid=True)

@callback(
    Output("hovered-world-map", "data"),
    Input("world-geojson", "hoverData")
)
def update_hovered_region(feature):
    if not feature:
        return None
    return feature["properties"].get("ADMIN")  # or NAME if you're using NAME

@callback(
    Output("hovered-canada-map", "data"),
    Input("csd-geojson", "hoverData")
)
def update_hovered_canada(feature):
    if not feature:
        return None
    return feature["properties"].get("NAME")  # or use DGUID if that's your label




@callback(
    Output("admin-level-store", "data"),
    Input("admin-level", "value")
)
def sync_admin_level_to_store(val):
    return val

@callback(
    Output("csd-geojson", "data"),
    Input("immigrant-status", "value"),
    Input("selected-country", "data"),
    Input("admin-level", "value")
)
def update_subdivision_geojson(immigrant_status, selected_country, admin_level):
    if admin_level == "CSD":
        # Existing logic for CSD level
        if not selected_country:
            return json.loads(gdf_csd.to_json())

        df_total = df_csd[(df_csd["Birthplace"] == "Total – Place of birth") & (df_csd["ImmigrantStatus"] == immigrant_status)]
        df_total = df_total[["DGUID", "Count"]].rename(columns={"Count": "TotalCount"})

        df_country = df_csd[(df_csd["Birthplace"] == selected_country) & (df_csd["ImmigrantStatus"] == immigrant_status)]
        df_country = df_country[["DGUID", "Count"]].rename(columns={"Count": "CountryCount"})

        df_merged = pd.merge(df_total, df_country, on="DGUID", how="left")
        df_merged["CountryCount"] = df_merged["CountryCount"].fillna(0)
        df_merged["Percentage"] = (df_merged["CountryCount"] / df_merged["TotalCount"] * 100).round(2)

        merged = gdf_csd.merge(df_merged, on="DGUID", how="left")
        merged["Percentage"] = merged["Percentage"].fillna(0)
        merged["tooltip"] = merged.apply(
            lambda row: f"{row['NAME']}: {int(row['CountryCount'])} immigrants ({row['Percentage']}%)"
            if pd.notna(row['CountryCount']) else f"{row['NAME']}: 0 immigrants (0%)", axis=1)

        return json.loads(merged.to_json())

    elif admin_level == "CD":
        # New logic for CD level
        if not selected_country:
            return json.loads(gdf_cd.to_json())

        df_total = df_cd[(df_cd["Birthplace"] == "Total – Place of birth") & (df_cd["ImmigrantStatus"] == immigrant_status)]
        df_total = df_total[["DGUID", "Count"]].rename(columns={"Count": "TotalCount"})

        df_country = df_cd[(df_cd["Birthplace"] == selected_country) & (df_cd["ImmigrantStatus"] == immigrant_status)]
        df_country = df_country[["DGUID", "Count"]].rename(columns={"Count": "CountryCount"})

        df_merged = pd.merge(df_total, df_country, on="DGUID", how="left")
        df_merged["CountryCount"] = df_merged["CountryCount"].fillna(0)
        df_merged["Percentage"] = (df_merged["CountryCount"] / df_merged["TotalCount"] * 100).round(2)

        merged = gdf_cd.merge(df_merged, on="DGUID", how="left")
        merged["Percentage"] = merged["Percentage"].fillna(0)
        merged["tooltip"] = merged.apply(
            lambda row: f"{row['NAME']}: {int(row['CountryCount'])} immigrants ({row['Percentage']}%)"
            if pd.notna(row['CountryCount']) else f"{row['NAME']}: 0 immigrants (0%)", axis=1)

        return json.loads(merged.to_json())
    
    elif admin_level == "Province":
        if not selected_country:
            return json.loads(gdf_prov.to_json())

        df_total = df_prov[(df_prov["Birthplace"] == "Total – Place of birth") & (df_prov["ImmigrantStatus"] == immigrant_status)]
        df_total = df_total[["DGUID", "Count"]].rename(columns={"Count": "TotalCount"})

        df_country = df_prov[(df_prov["Birthplace"] == selected_country) & (df_prov["ImmigrantStatus"] == immigrant_status)]
        df_country = df_country[["DGUID", "Count"]].rename(columns={"Count": "CountryCount"})

        df_merged = pd.merge(df_total, df_country, on="DGUID", how="left")
        df_merged["CountryCount"] = df_merged["CountryCount"].fillna(0)
        df_merged["Percentage"] = (df_merged["CountryCount"] / df_merged["TotalCount"] * 100).round(2)

        merged = gdf_prov.merge(df_merged, on="DGUID", how="left")
        merged["Percentage"] = merged["Percentage"].fillna(0)
        merged["tooltip"] = merged.apply(
            lambda row: f"{row['NAME']}: {int(row['CountryCount'])} immigrants ({row['Percentage']}%)"
            if pd.notna(row['CountryCount']) else f"{row['NAME']}: 0 immigrants (0%)", axis=1
        )

        return json.loads(merged.to_json())


    return json.loads(gdf_csd.to_json())  # fallback

# @callback(
#     Output("csd-geojson", "data"),
#     Input("selected-country", "data")
# )
# def update_csd_geojson(selected_country):
#     return get_csd_geojson(selected_country)

@callback(
    Output("world-geojson", "data"),
    Input("immigrant-status", "value"),
    Input("selected-dguid", "data"),
    Input("admin-level-store", "data"),
    Input("pie-grouping", "value")
)
def update_world_geojson(immigrant_status, selected_dguid, admin_level, pie_grouping):
    if admin_level == "CD":
        df_selected = df_cd
    elif admin_level == "Province":
        df_selected = df_prov
    else:
        df_selected = df_csd


    if selected_dguid == "ALL":
        df_filtered = df_selected.copy()
    else:
        df_filtered = df_selected[
            (df_selected["DGUID"] == selected_dguid) &
            (df_selected["ImmigrantStatus"] == immigrant_status)
        ]


    df_agg = df_filtered.groupby("Birthplace", as_index=False)["Count"].sum()


    if pie_grouping == "Region":
        match = df_agg.loc[df_agg["Birthplace"] == "Outside Canada", "Count"]
        total_count = match.values[0] if not match.empty else df_agg["Count"].sum()
        df_agg["Percentage"] = (df_agg["Count"] / total_count * 100).round(2)
        merged = region_gdf.merge(df_agg, left_on="ADMIN", right_on="Birthplace", how="left")
    elif pie_grouping == "Continent":
        match = df_agg.loc[df_agg["Birthplace"] == "Outside Canada", "Count"]
        total_count = match.values[0] if not match.empty else df_agg["Count"].sum()
        df_agg["Percentage"] = (df_agg["Count"] / total_count * 100).round(2)
        merged = continent_gdf.merge(df_agg, left_on="ADMIN", right_on="Birthplace", how="left")
    elif pie_grouping == "Inside Canada (Provinces)":
        match = df_agg.loc[df_agg["Birthplace"] == "Inside Canada", "Count"]
        total_count = match.values[0] if not match.empty else df_agg["Count"].sum()
        df_agg["Percentage"] = (df_agg["Count"] / total_count * 100).round(2)
        merged = gdf_prov.merge(df_agg, left_on="NAME", right_on="Birthplace", how="left")
        merged.rename(columns={"NAME": "ADMIN"}, inplace=True)
    elif pie_grouping == "Country (including Canada)":
        match = df_agg.loc[df_agg["Birthplace"] == "Total – Place of birth", "Count"]
        total_count = match.values[0] if not match.empty else df_agg["Count"].sum()
        df_agg["Percentage"] = (df_agg["Count"] / total_count * 100).round(2)
        merged = world_gdf.merge(df_agg, left_on="ADMIN", right_on="Birthplace", how="left")
    elif pie_grouping == "Country (excluding Canada)":
        match = df_agg.loc[df_agg["Birthplace"] == "Outside Canada", "Count"]
        total_count = match.values[0] if not match.empty else df_agg["Count"].sum()
        df_agg["Percentage"] = (df_agg["Count"] / total_count * 100).round(2)
        world_without_canada = world_gdf[world_gdf["ADMIN"]!="Inside Canada"]
        merged = world_without_canada.merge(df_agg, left_on="ADMIN", right_on="Birthplace", how="left")

    print("map:", merged)

    # merged = world_gdf.merge(df_agg, left_on="ADMIN", right_on="Birthplace", how="left")
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
    Input("admin-level-store", "data"),
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


def collapse_small_slices(df, label_col, total, count_col="Count", threshold=1):
    df = df.copy()
    if total is None:
        total = df[count_col].sum()
    df["Percentage"] = df[count_col] / total * 100
    print(total)

    major = df[df["Percentage"] >= threshold]
    minor = df[df["Percentage"] < threshold]

    if not minor.empty:
        other = pd.DataFrame({
            label_col: ["Other"],
            count_col: [minor[count_col].sum()],
            "Percentage": [minor["Percentage"].sum()]
        })
        df_final = pd.concat([major, other], ignore_index=True)
    else:
        df_final = major

    df_final["Percentage"] = df_final["Percentage"].round(2)
    return df_final



@callback(
    Output("origin-pie-chart", "spec"),
    Input("immigrant-status", "value"),
    Input("selected-dguid", "data"),
    Input("pie-grouping", "value"),
    Input("admin-level-store", "data"),
    Input("hovered-world-map", "data")
)
def update_world_pie_chart(immigrant_status, selected_dguid, grouping_level, admin_level, hovered_label):
    if selected_dguid == "ALL":
        return alt.Chart(pd.DataFrame({
            "label": ["No subdivision selected"],
            "count": [1]
        })).mark_bar().encode(
            x="label:N",
            y="count:Q"
        ).properties(title="No data").to_dict(format="vega")

    # Select the correct DataFrame
    df_selected = df_cd if admin_level == "CD" else df_prov if admin_level == "Province" else df_csd

    # Filter by selected DGUID and status
    df_filtered = df_selected[
        (df_selected["DGUID"] == selected_dguid) &
        (df_selected["ImmigrantStatus"] == immigrant_status) &
        (df_selected["Birthplace"] != "Total – Place of birth")
    ].copy()


    # Grouping logic
    if grouping_level == "Country (including Canada)":
        df_filtered = df_filtered[df_filtered["Type"].isin(["Country", "Inside Canada"])]
        label_col = "Birthplace"
        match = df_filtered.loc[df_filtered["Birthplace"] == "Total – Place of birth", "Count"]
        total_count = match.values[0] if not match.empty else df_filtered["Count"].sum()
    elif grouping_level == "Country (excluding Canada)":
        df_filtered = df_filtered[df_filtered["Type"] == "Country"]
        label_col = "Birthplace"
        match = df_filtered.loc[df_filtered["Birthplace"] == "Outside Canada", "Count"]
        total_count = match.values[0] if not match.empty else df_filtered["Count"].sum()
    elif grouping_level == "Inside Canada (Provinces)":
        df_filtered = df_filtered[df_filtered["Type"] == "Province"]
        label_col = "Birthplace"
        match = df_filtered.loc[df_filtered["Birthplace"] == "Inside Canada", "Count"]
        total_count = match.values[0] if not match.empty else df_filtered["Count"].sum()
    elif grouping_level in ["Region", "Continent"]:
        match = df_filtered.loc[df_filtered["Birthplace"] == "Outside Canada", "Count"]
        total_count = match.values[0] if not match.empty else df_filtered["Count"].sum()
        df_filtered = df_filtered[
            (df_filtered["Type"] == grouping_level) | (df_filtered["Birthplace"] == "Oceania")
        ]
        label_col = "Birthplace"
    else:
        return alt.Chart(pd.DataFrame({
            "label": ["Invalid grouping"],
            "count": [1]
        })).mark_bar().encode(
            x="label:N",
            y="count:Q"
        ).properties(title="Invalid grouping").to_dict(format="vega")
    
    

    if df_filtered.empty:
        return alt.Chart(pd.DataFrame({
            "label": ["No data"],
            "count": [1]
        })).mark_bar().encode(
            x="label:N",
            y="count:Q"
        ).properties(title="No data").to_dict(format="vega")

    # Aggregate
    df_grouped = df_filtered.groupby(label_col, as_index=False)["Count"].sum()
    df_grouped.rename(columns={label_col: "Label"}, inplace=True)
    df_grouped["Percentage"] = (df_grouped["Count"] / total_count * 100).round(2)
    df_grouped = df_grouped.sort_values("Count", ascending=False).head(15)


    print(df_grouped)

    # Create chart with normal color, but fade out unhovered bars
    chart = alt.Chart(df_grouped).mark_bar().encode(
        x=alt.X("Label:N", sort="-y", title=grouping_level),
        y=alt.Y("Count:Q", title="Number of Immigrants"),
        tooltip=["Label", "Count", "Percentage"],
        color=alt.Color("Label:N", legend=None),
        opacity=alt.condition(
            alt.datum.Label == hovered_label,
            alt.value(1.0),
            alt.value(0.3)
        ) if hovered_label in df_grouped["Label"].values else alt.value(1.0)
    )



    return chart.to_dict(format="vega")




@callback(
    Output("csd-pie-chart", "spec"),
    Input("immigrant-status", "value"),
    Input("selected-country", "data"),
    Input("admin-level-store", "data"),
    Input("hovered-canada-map", "data")
)
def update_csd_pie_chart(immigrant_status, selected_country, grouping_level, hovered_label):
    if not selected_country:
        return alt.Chart(pd.DataFrame({
            "label": ["No country selected"],
            "count": [1]
        })).mark_bar().encode(
            x="label:N",
            y="count:Q"
        ).properties(title="Select a country on the world map").to_dict(format="vega")


    # Use both dataframes depending on grouping
    if grouping_level == "CSD":
        df_selected = df_csd
        gdf_selected = gdf_csd
        name_col = "NAME"
    elif grouping_level == "CD":
        df_selected = df_cd
        gdf_selected = gdf_cd
        name_col = "NAME"
    elif grouping_level == "Province":
        df_selected = df_csd  # can use either
        name_col = "Province"
        gdf_selected = None
    else:
        return alt.Chart(pd.DataFrame({
            "label": ["Invalid grouping"],
            "count": [1]
        })).mark_bar().encode(
            x="label:N",
            y="count:Q"
        ).properties(title="Invalid grouping").to_dict(format="vega")

    df_country = df_selected[
        (df_selected["Birthplace"] == selected_country) &
        (df_selected["ImmigrantStatus"] == immigrant_status)
    ].copy()

    if grouping_level in ["CSD", "CD"]:
        df_country = df_country.merge(gdf_selected[["DGUID", name_col]], on="DGUID", how="left")
        df_grouped = df_country.groupby(name_col, as_index=False)["Count"].sum()
        df_grouped.rename(columns={name_col: "Label"}, inplace=True)
    else:  # Province
        df_grouped = df_country.groupby("Province", as_index=False)["Count"].sum()
        df_grouped.rename(columns={"Province": "Label"}, inplace=True)

    if df_grouped.empty:
        return alt.Chart(pd.DataFrame({
            "label": ["No data"],
            "count": [1]
        })).mark_bar().encode(
            x="label:N",
            y="count:Q"
        ).properties(title="No data").to_dict(format="vega")

    df_grouped = df_grouped.sort_values("Count", ascending=False).head(15)
    total = df_grouped["Count"].sum()
    df_grouped["Percentage"] = df_grouped["Count"] / total * 100

    chart = alt.Chart(df_grouped).mark_bar().encode(
        x=alt.X("Label:N", sort="-y", title=grouping_level),
        y=alt.Y("Count:Q", title="Number of Immigrants"),
        tooltip=["Label", "Count", "Percentage"],
        color=alt.Color("Label:N", legend=None),
        opacity=alt.condition(
            alt.datum.Label == hovered_label,
            alt.value(1.0),
            alt.value(0.3)
        ) if hovered_label in df_grouped["Label"].values else alt.value(1.0)
    )


    return chart.to_dict(format="vega")





# === Run App ===
if __name__ == '__main__':
    app.run(debug=True)