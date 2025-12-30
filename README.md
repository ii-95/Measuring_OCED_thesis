# Measuring OCED thesis
## Steps to run:
1. Navigate to project directory
2. Install packages in ./requirements.txt using desired method (venv, conda, etc.)
3. Place your OCEL (in .json format) in ./input_logs. Sample logs are already in the repository for testing the tool.
4. Run the following command to launch the app in a browser (localhost:8501):

    ```streamlit run backend/main_frontend.py```

## Notes:
- Python 3.11 is recommended to avoid conflicts with packages in requirements.txt. 
- Whenever the app is loading/executing, an animation showing a running stick figure is displayed at the top right to indicate this. 
- The feature for supporting non-atomic events via specification of an endtime attribute has not been tested extensively due to lack of publicly available OCELs that contain non-atomic events. Therefore, this feature remains experimental and prone to errors.
- Timeseries for service time and soujourn time are only generated if the log contains non-atomic events since they are equal to 0 and waiting time, respectively, in case of atomic events.
- In case if you select a wrong option that cannot be changed after confirming, click the reset button (or refresh the webpage) and start over.
- If you want to minimize the runtime, try to select only a few event types/object types/properties at one time.
- Runtime is also proportional to the size of the log. Time series extraction, analysis and log modification steps for logs with 10,000-50,000 events generally run in the order of a few seconds to few minutes (per step) on standard hardware (4 core cpu, 16 gb RAM). Whereas, logs with >1,000,000 events crash the application on the same hardware but may be able to run fine on a high performance unit.
- If the number of data points is large (>200, likely if 'daily' sampling rate is selected), runtime for 'Forecasting' with exogenous variables will be very high (>> 1 minute per time series). In some cases, such as where a large number of lags are selected or the pool of time series is large, the same may apply for 'Granger Causality'.

## Reason for only supporting .json format:
The implementation relies heavily on pm4py, especially for reading/writing the OCEL. Unfortunately, pm4py frequently faces trouble reading publicly available OCELs (from the ocel-standard webpage) in .sqlite and .xml formats. In case of former, it sometimes discards object types/event types and reports constaint violations whereas in case of latter, it sometimes fails to read the log altogether. On the contrary, .json works without any errors, everytime. Since fixing issues in the logs or PM4PY itself is out of scope for this thesis and so is creating an OCEL reader from scratch, we will stick to only using .json format.