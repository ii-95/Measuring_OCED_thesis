# Measuring_OCED_thesis
1. Navigate to project directory
2. Install packages in ./requirements.txt
3. Place your OCEL (in .json format) in ./input_logs
4. Run the following command to launch the app in a browser (localhost:8501):
    streamlit run backend/main_frontend.py

## Notes:
- Python 3.11 is recommended to avoid conflicts with packages in requirements.txt. Eventually the app will be dockerized to avoid conflicts.
- If the number of data points is large (>200, likely if 'daily' sampling rate is selected), runtime for 'Granger Causality' with a large number of lags or 'Forecasting' with exogenous variables will be very high (>> 10 minutes)
- In case if you select a wrong option that you can't just change, refresh the webpage and start over.
- Bug reports are highly appreciated :) 

## Reason for only supporting .json format:
PM4PY routinely faces trouble reading OCELs (available on the the ocel-standard webpage) in .sqlite and .xml formats. In case of former, it sometimes discards object types/event types and reports constaint violations. Whereas in case of latter, it sometimes to read it altogether. Json works remarkbly well. Since fixing PM4PY or stock OCEL errors is out of scope for this thesis and so is creating an OCEL reader from scratch, we will stick to only using .json formats.