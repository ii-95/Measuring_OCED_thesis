# Measuring_OCED_thesis
This repository contains the implementation of the Master's Thesis 'Measuring OCED' at the PADS chair of RWTH Aachen University.

The project requires python and can be run by following the steps below:

1) Install required packages contained within /backend/requirements.txt using tool of choice.

2) Configure user inputs in /inputs.env. Fields which require you to choose from options have the options mentioned above them in the inputs.env file.

3) Run the script /backend/main.py

Furthermore, please note the following:

- The output is a bunch of time series plots that can be found in /backend/assets/plots

- The plots for the default config (ocel: https://zenodo.org/records/8428112) as found in inputs.env are already present in the the plots directory. If you want to try a different configuration then follow the steps above.

- The processing of time series before visualization includes zero padding on either side of the series to co-incide with the interval provided in inputs.env. Any other intervals with missing values are also replaced with 0. This can be replaced with a nicer methodology but I wish to discuss this before implementing anything further.

- The project supports non-atomic events by specifying an event attribute that contains
the end time of events. If your provided log does not contain any such attribute and you wish to test this feature please uncomment lines 101-109 from backend/main.py. Same applies for the log provided in the default config that does not contain any such attribute.

- Property functions EP2 and OP2 only create time series for values of numerical attributes of events and objects, respectively.

- The log in the default config doesn't contain any numerical event attribute. If you wish to test EP2 then please uncomment line 60 in backend/setup.py. The default log however does contain a few numerical object attributes.

- The project is in the development phase. The front end is yet to be built. The provided plotting functionality is only for interim testing and not a reflection of what the front UI will look like (which will hopefully be much nicer).
