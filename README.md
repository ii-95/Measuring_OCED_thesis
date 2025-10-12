# Measuring_OCED_thesis
This repository contains the implementation of the Master's Thesis 'Measuring OCED' at the PADS chair of RWTH Aachen University.

The project can be considered to consist of 3 components:

1. Extraction of time series of measurable properties from an OCEL

    Output: Time series .csv files (availabile in backend/assets/timeseries) and plots (availabile in backend/assets/plots).

2. Perform time series analysis on the extracted time series (available techniques are Change Point Detection, Forecasting, Granger Causality, Threshold Based Point Detection).

    Output: Analysis results (available in assets/analysis_results) and analysis results visualization (available in assets/analysis_results_plots)

3. Convert analysis results into OCED and update the input OCEL with the results.

    Output: A modified OCEL containing all event data in input OCEL as well as analysis results encoded as OCED. This can be used again as input to the tool. You can either select different analysis techniques each time with no connection to prior results or you can select some of the given options in the .env file that enable the usage of prior analysis results to generate a higher level analysis.

The implementation of all 3 components is complete and the tool can be used via command line. Work on the front/UI will commence soon.

The project requires python and can be run by following the steps below:

1) Install required packages contained within /requirements.txt using tool of choice. Ideally use Python 3.11 to avoid dependency conflicts. If Granger Causality is the selected TSA technique, you must have Graphviz installed on your system to generate the visualizations. See https://graphviz.org/download/#executable-packages for installation instructions. Otherwise, you can disable the option for visualizations in inputs.env i.e., set generate_visualizations=N. 

2) Configure user inputs in /inputs.env. These include the OCEL filepath, time series parameters (such as sampling rate, aggregation function, etc) as well as a tsa technique and associated parameters.  Fields which require you to choose from options have the options mentioned above them in the inputs.env file.

3) Run the script /backend/main.py

Furthermore, please note the following:

- Runtime varies significantly depending on the selected analysis technique and parameters. Change Point Detection and Threshold Based Point Detection run rather quickly (few seconds to less than a minute). Forecasting and especially Granger Causality take a siginficant amount of  time to run (ranging from atleast a minute to several minutes) with the default parameter configuration.

- The analysis results are json files containing lists of (tsid, ar) pairs where 'tsid' is the time series identifier (property name, non-temporal parameters) and ar contain the analysis results for that time series.

An informal specification of the format for .json analysis results file for each analysis technique is as follows (improvements may follow):

    - Change Point Detection:

        tsid: [property_id, non-temporal parameters], 

        ar:  [(list of indices of change points detected in the time series)]

    - Threshold Based Point Detection:

        tsid: [property_id, non-temporal parameters], 

        ar:  [(list of indices of points detected based on inputs to the analysis technique in the time series)]

    - Forecasting:

        tsid: [property_id, non-temporal parameters], 

        ar:  {(a map of timestamps (iso string format) and float values that represent a series of forecast values for a given number of time periods)}

    - Granger Causality:

        tsid: [property_id, non-temporal parameters], 

        ar:  [(list of pairs where each pair contains the identifier of a time series and a list of integers representing the lags by which that time series granger causes the time series whose identifier is the key i.e. tsid)]

- Time series with null values during any of the time periods within the provided interval (in inputs.env) are discarded before plotting (and not used ahead either). Furthermore, any time series with constant values across all time intervals, even though plotted will not be used for time series analysis. 

- The project supports non-atomic events by specifying an event attribute that contains the end time of events. If your provided log does not contain any such attribute and you wish to test this feature please uncomment lines 261-267 from backend/main.py. Same applies for the log provided in the default config that does not contain any such attribute.

- Property functions EP2, OP2 and RP3 only create time series for values of numerical attributes of events and objects, respectively.

- The log in the default config doesn't contain any numerical event attribute. If you wish to test EP2 then please uncomment line 67 in backend/setup.py. The default log however does contain a few numerical object attributes but no attributes for resources i.e., the objects of 'employees' object type.

- The project is in the development phase. The front end is yet to be built. The provided plotting functionality is only for interim testing and not a reflection of what the front UI will look like (which will hopefully be much nicer).
