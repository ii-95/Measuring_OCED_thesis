# Measuring OCED thesis
## Steps to run:
1. Navigate to project directory
2. Install packages in ./requirements.txt using desired method (venv, conda, etc.)
3. Place your OCEL (in .json format) in ./input_logs. Sample logs are already in the repository for testing the tool.
4. Run the following command to launch the app in a browser (localhost:8501):

    ```streamlit run backend/main_frontend.py```

## Notes:
- Python 3.11 is recommended to avoid conflicts with packages in requirements.txt. Eventually the app will be dockerized to avoid conflicts.
- Whenever the app is loading/executing, an animation is displayed at the top right to indicate this. 
- If you want to minimize the runtime, try to select only a few event types/object types/properties at one time.
- If the number of data points is large (>200, likely if 'daily' sampling rate is selected), runtime for 'Forecasting' with exogenous variables will be very high (>> 1 minute per time series). In some cases, such as where a large number of lags are selected or the pool of time series is large, the same may apply for 'Granger Causality'.
- Timeseries for service time and soujourn time are only generated if the log contains non-atomic events. As they are equal to 0 and waiting time, respectively in case of atomic events.
- In case if you select a wrong option that cannot be changed after confirming, click the reset button (or refresh the webpage) and start over.
- Bug reports are highly appreciated :) 

## Reason for only supporting .json format:
The implementation relies heavily on pm4py, especially for reading/writing the OCEL. Unfortunately, pm4py frequently faces trouble reading OCELs (available on the the ocel-standard webpage) in .sqlite and .xml formats. In case of former, it sometimes discards object types/event types and reports constaint violations whereas in case of latter, it sometimes fails to read the log altogether. On the contrary, .json works remarkbly well, everytime. Since fixing issues in the logs or PM4PY itself is out of scope for this thesis and so is creating an OCEL reader from scratch, we will stick to only using .json format.