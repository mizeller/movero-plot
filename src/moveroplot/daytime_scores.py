# pylint: skip-file
# Standard library
from datetime import datetime, timedelta
from pathlib import Path
from pprint import pprint
import matplotlib.dates as mdates

# Third-party
import matplotlib.dates as md
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import numpy as np
import re
import pandas as pd

from moveroplot.config.plot_settings import PlotSettings

# Local
# import datetime
from .utils.atab import Atab
from .utils.check_params import check_params
from .utils.parse_plot_synop_ch import cat_daytime_score_range
from .utils.parse_plot_synop_ch import daytime_score_range


# enter directory / read station_scores files / call plotting pipeline
def _daytime_scores_pipeline(
    plot_setup,
    lt_ranges,
    file_prefix,
    file_postfix,
    input_dir,
    output_dir,
    debug,
) -> None:
    """Read all ```ATAB``` files that are present in: data_dir/season/model_version/<file_prefix><...><file_postfix>.

        Extract relevant information (parameters/scores)
        from these files into a dataframe.
        Rows --> Scores | Columns --> Stations |
        For each parameter, a separate station_scores File exists.

    Args:
        lt_ranges (list): lead time ranges, for which plots should be generated (i.e. 01-06, 07-12,...). part of the file name
        parameters (list): parameters, for which plots should be generated (i.e. CLCT, DD_10M, FF_10M, PMSL,...). part of file name
        file_prefix (str): prefix of files (i.e. time_scores)
        file_postfix (str): postfix of files (i.e. '.dat')
        input_dir (str): directory to seasons (i.e. /scratch/osm/movero/wd)
        output_dir (str): output directory (i.e. plots/)
        model_version (str): model_version of interest (i.e. C-1E_ch)
        scores (list): list of scores, for which plots should be generated
        debug (bool): print further comments & debug statements

    """  # noqa: E501
    print("\n--- initialising daytime score pipeline")
    if not lt_ranges:
        lt_ranges = "19-24"
    for model_plots in plot_setup["model_versions"]:
        for parameter, scores in plot_setup["parameter"].items():
            model_data = collect_relevant_files(
                input_dir,
                file_prefix,
                file_postfix,
                debug,
                model_plots,
                parameter,
                lt_ranges,
            )
            _generate_daytime_plots(
                plot_scores=scores,
                models_data=model_data,
                parameter=parameter,
                output_dir=output_dir,
                debug=debug,
            )
            return
    return
    model_versions = plot_setup["model_versions"][0][0]
    print(model_versions, plot_setup)
    for lt_range in lt_ranges:
        for parameter in plot_setup["parameter"].keys():
            # retrieve list of scores, relevant for current parameter
            scores = plot_setup[parameter]  # this scores is a list of lists
            print("PARAMETER ", parameter)
            # define file path to the current parameter (station_score atab file)
            file = f"{file_prefix}{lt_range}_{parameter}{file_postfix}"
            path = Path(f"{input_dir}/{model_versions}/{file}")
            return
            # check if the file exists
            if not path.exists():
                print(
                    f"""WARNING: No data file for parameter {parameter} could be found.
                    {path} does not exist."""
                )
                continue  # for the current parameter no file could be retrieved

            if debug:
                print(f"\nFilepath:\t{path}")

            # extract header & dataframe
            header = Atab(file=path, sep=" ").header
            df = Atab(file=path, sep=" ").data
            return
            # > remove/replace missing values in dataframe with np.NaN
            df = df.replace(float(header["Missing value code"][0]), np.NaN)

            # > if there are columns (= scores), that only contain np.NaN, remove them
            # df = df.dropna(axis=1, how="all")

            # > check which relevant scores are available; extract those from df
            all_scores = df.columns.tolist()
            available_scores = ["hh"]
            multiplot_scores = {}
            for score in scores:
                if len(score) == 1:
                    if score[0] in all_scores:
                        available_scores.append(score[0])
                    else:  # warn that a relevant score was not available in dataframe
                        print(
                            f"""WARNING: Score {score[0]} not
                            available for parameter {parameter}."""
                        )
                if (
                    len(score) > 1
                ):  # # currently only 2-in-1 plots are currently possible
                    multiplot_scores[score[0]] = score[1]
                    for sc in score:
                        if sc in all_scores:
                            available_scores.append(sc)
                        else:
                            print(
                                f"""WARNING: Score {sc} not available
                                for parameter {parameter}."""
                            )

            df = df[available_scores]
            df = df.set_index("hh")

            if debug:
                print("\nFile header:")
                pprint(header)
                print("\nData:")
                pprint(df)
                print(
                    f"""Generating plot for {parameter} for
                    lt_range: {lt_range}. (File: {file})"""
                )

            # for each score in df, create one map
            _generate_daytime_plot(
                data=df,
                multiplots=multiplot_scores,
                lt_range=lt_range,
                variable=parameter,
                file=file,
                file_postfix=file_postfix,
                header_dict=header,
                output_dir=output_dir,
                grid=grid,
                debug=debug,
            )


# PLOTTING PIPELINE FOR DAYTIME SCORES PLOTS
def collect_relevant_files(
    input_dir, file_prefix, file_postfix, debug, model_plots, parameter, lt_ranges
):
    corresponding_files_dict = {}
    extracted_model_data = {}
    # for dbg purposes:
    files_list = []
    for model in model_plots:
        source_path = Path(f"{input_dir}/{model}")
        for file_path in source_path.glob(f"{file_prefix}*{parameter}{file_postfix}"):
            if file_path.is_file():
                ltr_match = re.search(r"(\d{2})-(\d{2})", file_path.name)
                if ltr_match:
                    lt_range = ltr_match.group()
                else:
                    raise IOError(
                        f"The filename {file_path.name} does not contain a LT range."
                    )

                in_lt_ranges = True
                if lt_ranges:
                    in_lt_ranges = lt_range in lt_ranges

                if in_lt_ranges:
                    # extract header & dataframe
                    loaded_Atab = Atab(file=file_path, sep=" ")

                    header = loaded_Atab.header
                    df = loaded_Atab.data
                    df["hh"] = df["hh"].astype(int)
                    # clean df
                    df = df.replace(float(header["Missing value code"][0]), np.NaN)

                    # add information to dict
                    if lt_range not in corresponding_files_dict:
                        corresponding_files_dict[lt_range] = {}

                    corresponding_files_dict[lt_range][model] = {
                        "header": header,
                        "df": df,
                    }

                    # add path of file to list of relevant files
                    files_list.append(file_path)

    if debug:
        print(f"\nFor parameter: {parameter} these files are relevant:\n")
        pprint(files_list)

    extracted_model_data = corresponding_files_dict
    return extracted_model_data


def _initialize_plots(labels: list):
    fig, ((ax0), (ax1)) = plt.subplots(
        nrows=2, ncols=1, tight_layout=True, figsize=(10, 10), dpi=200
    )
    custom_lines = [
        Line2D([0], [0], color=PlotSettings.modelcolors[i], lw=2)
        for i in range(len(labels))
    ]
    fig.legend(
        custom_lines,
        labels,
        loc="upper right",
        ncol=1,
        frameon=False,
    )
    plt.tight_layout(w_pad=8, h_pad=5, rect=[0.05, 0.05, 0.90, 0.90])
    return fig, [ax0, ax1]


def _clear_empty_axes_if_necessary(subplot_axes, idx):
    # remove empty ``axes`` instances
    if idx % 2 != 1:
        [ax.axis("off") for ax in subplot_axes[(idx + 1) % 2 :]]


def _plot_and_save_scores(
    output_dir,
    base_filename,
    parameter,
    plot_scores_setup,
    sup_title,
    ltr_models_data,
    debug=False,
):
    for ltr, models_data in ltr_models_data.items():
        fig, subplot_axes = _initialize_plots(ltr_models_data[ltr].keys())
        headers = [data["header"] for data in models_data.values()]
        total_start_date = min(
            [
                datetime.strptime(
                    " ".join(header["Start time"][0:3:2]), "%Y-%m-%d %H:%M"
                )
                for header in headers
            ]
        )
        total_end_date = max(
            [
                datetime.strptime(" ".join(header["End time"][0:2]), "%Y-%m-%d %H:%M")
                for header in headers
            ]
        )
        title_base = f"{parameter.upper()}: "
        model_info = (
            f" {list(models_data.keys())[0]}" if len(models_data.keys()) == 1 else ""
        )

        x_label_base = f"""{total_start_date.strftime("%Y-%m-%d %H:%M")} - {total_end_date.strftime("%Y-%m-%d %H:%M")} """
        filename = base_filename
        for idx, score_setup in enumerate(plot_scores_setup):
            title = title_base + ",".join(score_setup) + model_info
            ax = subplot_axes[idx % 2]
            for model_idx, data in enumerate(models_data.values()):
                model_plot_color = PlotSettings.modelcolors[model_idx]
                header = data["header"]
                unit = header["Unit"][0]
                y_label = ",".join(score_setup)
                ax.set_ylabel(f"{y_label.upper()} ({unit})")
                ax.set_xlabel(x_label_base + ltr)
                ax.set_title(title)

                for score_idx, score in enumerate(score_setup):
                    x_int = list(data["df"]["hh"])
                    score_values = data["df"][score].to_list()
                    if 0 not in x_int:
                        bound_x_values = x_int[:: -len(x_int) + 1]
                        bound_x_values[0] -= 24
                        score_value0 = np.interp(
                            0, bound_x_values, score_values[:: len(x_int) - 1]
                        )
                        x_int = [0] + x_int + [24]
                        score_values = [score_value0] + score_values + [score_value0]

                    x_datetimes = [
                        datetime.combine(datetime.now().date(), datetime.min.time())
                        + timedelta(hours=hour)
                        for hour in x_int
                    ]
                    ax.plot(
                        x_datetimes,
                        score_values,
                        color=model_plot_color,
                        linestyle=PlotSettings.line_styles[score_idx],
                        fillstyle="none",
                        label=f"{score.upper()}",
                        marker="D",
                    )
                    ax.tick_params(axis="both", which="major", labelsize=8)
                    ax.tick_params(axis="both", which="minor", labelsize=6)
                    ax.autoscale(axis="y")
                    ax.set_xlim(x_datetimes[0], x_datetimes[-1])
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            if len(score_setup) > 1:
                sub_plot_legend = ax.legend(
                    score_setup,
                    loc="upper right",
                    markerscale=0.9,
                    bbox_to_anchor=(1.1, 1.05),
                )
                for line in sub_plot_legend.get_lines():
                    line.set_color("black")
            filename += "_" + "_".join(score_setup)

            if idx % 2 == 1 or idx == len(plot_scores_setup) - 1:
                _clear_empty_axes_if_necessary(subplot_axes, idx)
                fig.savefig(f"{output_dir}/{filename}.png")
                filename = base_filename
                fig, subplot_axes = _initialize_plots(ltr_models_data[ltr].keys())


def _generate_daytime_plots(
    plot_scores,
    models_data,
    parameter,
    output_dir,
    debug,
):
    model_plot_colors = PlotSettings.modelcolors
    model_versions = list(models_data.keys())

    # initialise filename
    base_filename = (
        f"daytime_scores_{model_versions[0]}_{parameter}"
        if len(model_versions) == 1
        else f"daytime_scores_{parameter}"
    )
    '''
    headers = [
        data[sorted(list(data.keys()), key=lambda x: int(x.split("-")[0]))[-1]][
            "header"
        ]
        for data in models_data.values()
    ]

    total_start_date = min(
        datetime.strptime(header["Start time"][0], "%Y-%m-%d") for header in headers
    )

    total_end_date = max(
        datetime.strptime(header["End time"][0], "%Y-%m-%d") for header in headers
    )

    model_info = (
        "" if len(model_versions) > 1 else f"Model: {headers[0]['Model version'][0]} | \n"
    )
    sup_title = (
        model_info
        + f"""Period: {total_start_date.strftime("%Y-%m-%d")} - {total_end_date.strftime("%Y-%m-%d")} | © MeteoSwiss"""
    )
    '''
    sup_title = ""
    # plot regular scores
    _plot_and_save_scores(
        output_dir,
        base_filename,
        parameter,
        plot_scores["regular_scores"],
        sup_title,
        models_data,
        debug=False,
    )

    _plot_and_save_scores(
        output_dir,
        base_filename,
        parameter,
        plot_scores["cat_scores"],
        sup_title,
        models_data,
        debug=False,
    )
