# Measuring_OCED_thesis
This repository contains the implementation of the Master's Thesis 'Measuring OCED' at the PADS chair of RWTH Aachen University.

The project requires python and can be run by following the steps below:

1) Install required packages contained within requirements.txt using tool of choice.

2) Configure user inputs in /inputs.env. Fields which require you to choose from options have the options mentioned above them in the inputs.env file.

3) Run the script backend/main.py

The output are time series plots that can be found in /backend/assets/plots

The plots for the default config as found in inputs.env are already present in the the plots directory. If you want to try a different configuration then follow the steps above.

The OCEL used for the project currently needs to be provided in both sqlite and json format. This will be resolved eventually.

The project supports non-atomic events by specifying an event attribute that contains
the end time of events. If your provided log does not contain any such attribute and you wish to test this feature please uncomment lines 94-102 from backend/main.py.

Property functions EP2 and OP2 only create time series for numerical attributes of events
and objects, respectively.

The log in the default config doesn't contain any numerical event attribute. If you wish to test EP2 then please uncomment line 53 in backend/EP_measurable_properties.py

The project is in a working state. The front end is yet to built. The provided plotting functionality is only for interim testing and not a reflection of what the front UI will look like (which will hopefully be much nicer).
