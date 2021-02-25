import dash
import dash_html_components as html
import dash_bootstrap_components as dbc
import locale
import pandas as pd
from dotenv import load_dotenv
from flask.cli import with_appcontext
from dsadata.bootstrap_stuff import get_sidebar_layout

load_dotenv()
from dash.dependencies import Output, Input, State

# from dsadata.mec_query import db
from dsadata import init_app, bootstrap_stuff, mec_query

locale.setlocale(locale.LC_ALL, "en_US.UTF-8")

# server = init_app()
# server.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
# server.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# db.init_app(server)


# from mec_query import Candidate


def init_dashboard(server):
    dash_app = dash.Dash(
        server=server,
        routes_pathname_prefix="/",
        external_stylesheets=[dbc.themes.BOOTSTRAP],
    )
    dash_app.layout = get_sidebar_layout()
    init_callbacks(dash_app)
    return dash_app.server


def init_callbacks(app):
    # Contest Selected: Look at stat
    @app.callback(
        [
            Output("candidate-select", "options"),
            Output("candidate-select", "value"),
            Output("precincts-geojson", "url"),
            Output("neighborhood-geojson", "url"),
            Output("zip-geojson", "url"),
        ],
        [Input("contest-select", "value")],
    )
    def select_contest(contest):
        if contest is None:
            contest = "Mayor - City of St. Louis"
        contest_name = mec_query.get_standard_contest_name(contest)
        print(contest_name)
        candidate_df = pd.read_csv("dsadata/static/candidates_2021-03-02.csv")
        contest_candidates_df = candidate_df[candidate_df["Office Sought"] == contest]
        select_options = [{"label": "All candidates", "value": "all"}]
        for index, row in contest_candidates_df.iterrows():
            select_options.append(
                {"label": row["Candidate Name"].title(), "value": row["MECID"]}
            )
        return [
            select_options,
            "all",
            "dsadata/static/geobuf/"
            + mec_query.get_standard_contest_name(contest_name)
            + "-stl-city-and-county-precincts.pbf",
            "dsadata/static/geobuf/"
            + mec_query.get_standard_contest_name(contest_name)
            + "-neighborhoods-and-municipalities.pbf",
            "dsadata/static/geobuf/"
            + mec_query.get_standard_contest_name(contest_name)
            + "-stl-region-zip.pbf",
        ]

    # Candidate Selected: Look at stats from that candidate
    @app.callback(
        [
            Output("candidate_info_collapse", "is_open"),
            Output("candidate_info_collapse", "children"),
            Output("precincts-geojson", "hideout"),
            Output("neighborhood-geojson", "hideout"),
            Output("zip-geojson", "hideout"),
        ],
        [Input("candidate-select", "value")],
        [State("contest-select", "value")],
    )
    def candidate_selected(selected_mec_id, contest):
        if contest is None:
            contest = "Mayor - City of St. Louis"
        contest_name = mec_query.get_standard_contest_name(contest)
        if selected_mec_id != "all":
            color_prop = "mec_donations_" + selected_mec_id
            hideout = bootstrap_stuff.build_choropleth_hideout(color_prop)
            return (
                True,
                [],  # [bootstrap_stuff.get_candidate_info_card(candidate_row)],
                hideout,
                hideout,
                hideout,
            )
        hideout = bootstrap_stuff.build_choropleth_hideout(
            "total_monetary_donations_" + contest_name
        )
        return (False, [], hideout, hideout, hideout)

    # @app.callback(
    #     Output("base-layer-name", "children"),
    #     [Input("geojson-layer-control", "baseLayer")],
    # )
    # def layer_change(base_layer):
    #     # TODO: We need to probably add an indication of how much $ we aren't showing, either b/c address etc is missing, or it is out of view (e.g. not in a STL city neighborhood/precinct)
    #     return base_layer

    @app.callback(
        [
            Output("precinct-baselayer", "checked"),
            Output("neighborhood-baselayer", "checked"),
            Output("zip-baselayer", "checked"),
            Output("precinct-button", "active"),
            Output("neighborhood-button", "active"),
            Output("zip-button", "active"),
        ],
        [
            Input("precinct-button", "n_clicks"),
            Input("neighborhood-button", "n_clicks"),
            Input("zip-button", "n_clicks"),
        ],
    )
    def layer_button_click(precinct_clicks, neighborhood_clicks, zip_clicks):
        changed_id = [p["prop_id"] for p in dash.callback_context.triggered][0]
        if "precinct-button" in changed_id:
            return [True, False, False, True, False, False]
        elif "neighborhood-button" in changed_id:
            return [False, True, False, False, True, False]
        elif "zip-button" in changed_id:
            return [False, False, True, False, False, True]
        else:
            return [True, False, False, True, False, False]

    @app.callback(
        [
            Output("floatbox-neighborhood", "children"),
            Output("floatbox-neighborhood", "className"),
        ],
        [
            Input("neighborhood-geojson", "click_feature"),
            Input("card-box-close-neighborhood", "n_clicks"),
        ],
        [State("contest-select", "value")],
    )
    def neighborhood_click(feature, n_clicks, contest):
        contest_name = mec_query.get_standard_contest_name(contest)
        class_name = "displayNone"
        header_text = "Error"
        card_contents = bootstrap_stuff.get_floatbox_card_contents("neighborhood")

        if feature:
            print(feature)
            if (
                "NHD_NAME" in feature["properties"]
                and feature["properties"]["NHD_NAME"]
            ):
                header_text = feature["properties"]["NHD_NAME"]
            else:
                header_text = feature["properties"]["MUNICIPALI"].title()
            body_contents = [
                html.Strong("Total monetary donations: "),
                html.Span(
                    locale.currency(
                        feature["properties"][
                            "total_monetary_donations_" + contest_name
                        ],
                        grouping=True,
                    )
                ),
            ]
            class_name = "floatbox"
            card_contents = bootstrap_stuff.get_floatbox_card_contents(
                "neighborhood", header_text, body_contents
            )

        if n_clicks:
            class_name = "displayNone"

        return [card_contents, class_name]

    @app.callback(
        [
            Output("floatbox-precinct", "children"),
            Output("floatbox-precinct", "className"),
        ],
        [
            Input("precincts-geojson", "click_feature"),
            Input("card-box-close-precinct", "n_clicks"),
        ],
        [State("contest-select", "value")],
    )
    def precinct_click(feature, n_clicks, contest):
        contest_name = mec_query.get_standard_contest_name(contest)
        class_name = "displayNone"
        header_text = "Error"
        card_contents = bootstrap_stuff.get_floatbox_card_contents("precinct")

        if feature:
            # print(feature["properties"])
            if (
                "WARD10" in feature["properties"] and feature["properties"]["WARD10"]
            ):  # STL City precinct
                header_text = f"STL City: Ward {feature['properties']['WARD10']}, Precinct {feature['properties']['PREC10']}"
            elif feature["properties"]["PRECINCTID"]:  # STL County precinct
                header_text = (
                    f"STL County: Precinct {feature['properties']['PRECINCTID']}"
                )
            body_contents = [
                html.Strong("Total monetary donations: "),
                html.Span(
                    locale.currency(
                        feature["properties"][
                            "total_monetary_donations_" + contest_name
                        ],
                        grouping=True,
                    )
                ),
            ]
            class_name = "floatbox"
            card_contents = bootstrap_stuff.get_floatbox_card_contents(
                "precinct", header_text, body_contents
            )

        if n_clicks:
            class_name = "displayNone"

        return [card_contents, class_name]

    @app.callback(
        [Output("floatbox-zip", "children"), Output("floatbox-zip", "className")],
        [
            Input("zip-geojson", "click_feature"),
            Input("card-box-close-zip", "n_clicks"),
        ],
        [State("contest-select", "value")],
    )
    def zip_click(feature, n_clicks, contest):
        contest_name = mec_query.get_standard_contest_name(contest)
        class_name = "displayNone"
        header_text = "Error"
        card_contents = bootstrap_stuff.get_floatbox_card_contents("zip")

        if feature:
            header_text = f"ZIP Code {feature['properties']['ZCTA5CE10']}"
            body_contents = [
                html.Strong("Total monetary donations: "),
                html.Span(
                    locale.currency(
                        feature["properties"][
                            "total_monetary_donations_" + contest_name
                        ],
                        grouping=True,
                    )
                ),
            ]
            class_name = "floatbox"
            card_contents = bootstrap_stuff.get_floatbox_card_contents(
                "zip", header_text, body_contents
            )

        if n_clicks:
            class_name = "displayNone"

        return [card_contents, class_name]
