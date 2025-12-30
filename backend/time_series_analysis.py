from statsmodels.tsa.stattools import grangercausalitytests
import ruptures as rpt
from sktime.param_est.stationarity import StationarityADF, StationarityKPSS
from pmdarima.arima import OCSBTest
from sktime.forecasting.arima import AutoARIMA
import math
import pandas as pd
import contextlib
#parent function for time series analysis
#redirects to specific function for the selected tsa technique after pre-preprocessing of time series, if needed.
#e.g. making time series stationary in case of granger causality or finding seasonal periods in case of forecasting
def time_series_analysis(ts_collection, technique_name, min_seasonal_period, max_seasonal_period, sampling_rate, offset,\
                        change_point_indices_dict, ts_causal_factors_dict, time_intervals, tsa_params = None):

    if technique_name == 'Change Point Detection':
        ar_collection = change_point_detection(ts_collection, tsa_params)
    elif technique_name == 'Granger Causality':
        ts_to_sp_map = get_seasonal_periodicities(ts_collection, min_seasonal_period, max_seasonal_period)
        seasonal_diff_ts_collection = apply_seasonal_differencing(ts_collection, ts_to_sp_map)
        ts_to_diff_order_map = get_first_diff_order(seasonal_diff_ts_collection)
        diff_ts_collection = apply_first_differencing(seasonal_diff_ts_collection, ts_to_diff_order_map)
        ar_collection = granger_causality(diff_ts_collection, change_point_indices_dict, tsa_params)
    elif technique_name == 'Forecasting':
        ts_to_sp_map = get_seasonal_periodicities(ts_collection, min_seasonal_period, max_seasonal_period)
        ar_collection = forecasting(ts_collection, ts_to_sp_map, sampling_rate, offset, \
                                    ts_causal_factors_dict, time_intervals, tsa_params)
    elif technique_name == 'Threshold Based Point Detection':
        ar_collection = threshold_based_point_detection(ts_collection, tsa_params)
    return ar_collection

#performs change point detection on provided collection of time series using the PELT algorithm
#R. Killick, P. Fearnhead, and I. A. Eckley, ‘Optimal detection of changepoints with a linear computational cost’, 2011.
#https://doi.org/10.48550/arXiv.1101.1438

def change_point_detection(ts_collection, change_point_params):

    #get selected values of parameters
    model = change_point_params['model']
    min_size = change_point_params['min_size']
    jump = change_point_params['jump']
    penalty = change_point_params['penalty']

    #if any of the parameters are not provided as input, select default values
    if not model:
        model = 'rbf'
    if not min_size:
        min_size = 3
    if not jump:
        jump = 1
    if not penalty:
        penalty = 1.5

    ar_collection = {}

    #get change points for each series as a list of indices(integers) and assign to the series id (tsid) in ar_collection
    for tsid, ts in ts_collection.items():
        ts = ts.to_frame()
        algo = rpt.Pelt(model=model, min_size=min_size, jump=jump).fit(ts)
        predicted_change_points = algo.predict(pen=penalty)
        if len(ts) in predicted_change_points: 
            predicted_change_points.remove(len(ts))
        ar_collection[tsid] = predicted_change_points
    return ar_collection

#returns a map containing plausible seasonal periods for each time series in the provided collection of time series
#traveses a range of periods (from larger to smaller) between the provided maximum and minimum thresholds
#and determines if a period is found in a time series by performing the 'ocsb test'
# D. R. Osborn, A. P. L. Chui, J. P. Smith, and C. R. Birchenhall, 
# ‘SEASONALITY AND THE ORDER OF INTEGRATION FOR CONSUMPTION*’, 
# Oxf. Bull. Econ. Stat., vol. 50, no. 4, pp. 361–377, Nov. 1988.
# https://doi.org/10.1111/j.1468-0084.1988.mp50004002.x
# when a seasonal component is found in a time series, the next seasonal component must have a period
# of less than half of the previous one (and greater than minimum).

def get_seasonal_periodicities(ts_collection, min_seasonal_period, max_seasonal_period):
    ts_to_sp_map = {}
    for tsid, ts in ts_collection.items():
        if tsid[0].startswith('Threshold Based Points'):
            sp_list = []
        else:
            prev_sp = max_seasonal_period*2 + 1 
            sp_list = []
            seasonal_diff_ts = ts.copy()
            if max_seasonal_period > min_seasonal_period:
                sp_candidates = range(max_seasonal_period, min_seasonal_period-1, -1)
            else:
                sp_candidates = []
            for sp in sp_candidates:
                ocsb_test = OCSBTest(sp)
                if ocsb_test.estimate_seasonal_differencing_term(seasonal_diff_ts) and sp < prev_sp/2:
                    seasonal_diff_ts = seasonal_diff_ts.diff(sp).dropna()
                    sp_list.append(sp)
                    prev_sp = sp
        ts_to_sp_map[tsid] = sp_list
    return ts_to_sp_map

#apply differencing to each time series in a collection according to the seasonal periods provided for each time series
#return differenced time series
def apply_seasonal_differencing(ts_collection, ts_to_sp_map):
    seasonal_diff_ts_collection = {}
    for tsid, ts in ts_collection.items():
        seasonal_diff_ts = ts.copy()
        for sp in ts_to_sp_map[tsid]:
            seasonal_diff_ts = seasonal_diff_ts.diff(sp).dropna()
        seasonal_diff_ts_collection[tsid] = seasonal_diff_ts
    return seasonal_diff_ts_collection

#provides the order (number of times) of first differencing for each time series in a collection until it becomes stationary
#a combination of ADF and KPSS tests is used to determine stationarity.
#time series that don't become stationary after applying first differencing a provided 'max_order' of times 
# are not part of the returned map of time series identifiers to order of first differencing.

def get_first_diff_order(ts_collection, max_order = 2):
    adf = StationarityADF(regression='c')  
    kpss = StationarityKPSS(regression='c')
    ts_to_diff_order_map = {}
    for tsid, ts in ts_collection.items():
        if tsid[0].startswith('Threshold Based Points'):
            ts_to_diff_order_map[tsid] = 0
        else:
            ts_diff = ts.copy()
            for i in range(0, max_order + 1):
                adf_result = adf.fit(ts_diff).get_fitted_params()["stationary"]
                try:
                    kpss_result = kpss.fit(ts_diff).get_fitted_params()["stationary"]
                except:
                    print(f'KPSS test cannot be applied on the time series: {tsid}. Thereby only ADF test will be used to test its stationarity.')
                    kpss_result = True
                if adf_result and kpss_result or (adf_result and i == max_order) or (kpss_result and i == max_order):
                    ts_to_diff_order_map[tsid] = i
                    break
                else:
                    if i < max_order:
                        ts_diff = ts_diff.diff(1).dropna()
                    else:
                        print(f'Time series: {tsid} can not be made stationary after second order differencing, hence will be discarded for the purpose of further analysis.')
    return ts_to_diff_order_map

#apply first differencing to each time series in a collection according to the order of first differencing
#provided for each time series. Return differenced time series.

def apply_first_differencing(ts_collection, ts_to_diff_order_map):
    diff_ts_collection = {}
    for tsid, diff_order in ts_to_diff_order_map.items():
        ts_diff = ts_collection[tsid].copy()
        if diff_order > 0:
            for i in range(0,diff_order):
                ts_diff = ts_diff.diff(1).dropna()
        diff_ts_collection[tsid] = ts_diff
    return diff_ts_collection

#determines granger causality between each pair of time series in a collection for some specified lags
#iterates over each time series t1 in the collection and conducts a statiscal test for every other time series 
# in the collection that returns a p value for a null hypothesis that given a pair of time series (t1,t2), 
# t2 does not granger cause t1. If the returned p value is lower than the threshold, we reject the hypothesis
#and consider than t2 does granger cause t1 and the pair along with the lag to our results. 
# If we can't reject the hypothesis, we  move to the next combination of time series and do not register the results.
#Returns a dataframe containing each combination of time series where granger causality is detected and the corresponding
#lags.

def granger_causality(ts_collection, change_point_indices_dict, granger_params):

    #get selected values of parameters
    lag = granger_params['lag']
    p_val_thresh = granger_params['p_value_threshold']
    use_change_point_difference_as_lag = granger_params['use_change_point_difference_as_lag']

    #if p_value is not provided, select default p_value
    if not p_val_thresh:
        p_val_thresh = 0.01

    gc_pairs_with_lag = []

    for tsid, ts in ts_collection.items():
        ts_df = ts.copy().to_frame()
        other_ts_collection = {k: v for k, v in ts_collection.items() if k != tsid}
        for tsid_2, ts_2 in other_ts_collection.items():
            df = ts_df.merge(ts_2, left_index = True, right_index = True, how = 'left').dropna()
            lag_limit = math.floor((len(df)-1) / 3 - 1)
            if use_change_point_difference_as_lag == 'Yes':
                lag_list = []
                lag_cp_list = []
                caused_cp = change_point_indices_dict[tsid]
                causing_cp = change_point_indices_dict[tsid_2]
                for cp in caused_cp:
                    for cp_2 in causing_cp:
                        possible_lag = cp - cp_2
                        if possible_lag > 0 and possible_lag <= lag_limit:
                            lag_list.append(possible_lag)
                            lag_cp_list.append((f'Causing CP: {cp_2+1}', f'Caused CP: {cp+1}'))
                if not lag_list:
                    continue
            elif not lag:
                lag_list = range(1,lag_limit+1)
            elif isinstance(lag, list):
                lag_list = [x for x in lag if x <= lag_limit]
                if not lag_list:
                    continue
            elif isinstance(lag, int):
                if lag > lag_limit:
                    lag_list = range(1,lag_limit+1)
                else:
                    lag_list = range(1,lag+1)
            try:
                with contextlib.redirect_stdout(None):
                    gc = grangercausalitytests(df, maxlag=lag_list)
            except Exception as err:
                print(f'Warning: Cannot perform Granger Causality test for: ({tsid}, {tsid_2}) due to the following error: \n {err} \n the time series pair will be discarded from the results')
                continue
            for i,l in enumerate(lag_list):
                p_values = []
                for value in gc[l][0].values():
                    p_values.append(value[1])
                if all(p_val < p_val_thresh for p_val in p_values):
                    if use_change_point_difference_as_lag == 'Yes':
                        l = (l,lag_cp_list[i])
                    gc_pairs_with_lag.append((tsid, tsid_2, l))
    gc_df = pd.DataFrame(gc_pairs_with_lag, columns = ['caused', 'causing', 'lag'])
    if gc_df.empty:
        return None
    else:
        gc_df = gc_df.groupby(by= ['caused', 'causing']).agg(list).reset_index()
        return gc_df

#returns forecasts for n = 'periods_to_predict' time periods after the end of the time series for each time series in 
#the provided collection.
#Uses an ARIMA model to generate the predictions. seasonal periods for each time series are provided as an input to the
#function.
def forecasting(ts_collection, ts_to_sp_map, sampling_rate, offset, ts_causal_factors_dict, time_intervals, forecasting_params):

    #get selected values of parameters
    periods_to_predict = forecasting_params['periods_to_predict']
    use_granger_causal_ts_as_exogenous_variables = forecasting_params['use_granger_causal_ts_as_exogenous_variables']
    start_p = forecasting_params['start_p']
    max_p = forecasting_params['max_p']
    start_q = forecasting_params['start_q']
    max_q = forecasting_params['max_q']
    start_P = forecasting_params['start_P']
    max_P = forecasting_params['max_P']
    start_Q = forecasting_params['start_Q']
    max_Q = forecasting_params['max_Q']
    information_criterion = forecasting_params['information_criterion']
    test = forecasting_params['test']
    maxiter = forecasting_params['maxiter']

    #if any of the parameters are not provided as input, select default values
    if not periods_to_predict:
        periods_to_predict = 4
    if not use_granger_causal_ts_as_exogenous_variables: 
        use_granger_causal_ts_as_exogenous_variables = 'No'
    if not start_p:
        start_p = 2
    if not start_q:
        start_q = 2
    if not start_P:
        start_P = 1
    if not start_Q:
        start_Q = 1
    if not max_p:
        max_p = 5
    if not max_q:
        max_q = 5
    if not max_P:
        max_P = 2
    if not max_Q:
        max_Q = 2
    if not information_criterion:
        information_criterion = 'aicc'
    if not test:
        test = 'kpss'
    if not maxiter:
        maxiter = 100

    interimn_ar_collection = {}
    ar_collection = {}
    freq = sampling_rate.removesuffix('E')


    #get forecasts for each time series in the collection
    for tsid, ts in ts_collection.items():
        ts_fc = ts.copy()
        ts_fc.index = pd.PeriodIndex(ts_fc.index, freq=freq)
        sp_list = ts_to_sp_map[tsid]
        if sp_list:
            sp_ts = sp_list[0]
        else:
            sp_ts = 1
        forecaster = AutoARIMA(sp=sp_ts, start_p = start_p, start_q = start_q, start_P = start_P, start_Q = start_Q,\
                                max_p = max_p, max_q = max_q, max_P = max_P, max_Q = max_Q, maxiter= maxiter,\
                                test = test, information_criterion= information_criterion, suppress_warnings=True) 
        forecaster.fit(ts_fc) 
        pred = forecaster.predict(fh= range(1, periods_to_predict+1))
        pred.index = pd.to_datetime(pred.index.end_time.normalize(), utc=True)
        interimn_ar_collection[tsid] = pred

    if use_granger_causal_ts_as_exogenous_variables == 'Yes':
        pred_intervals = []
        for i in range (1, periods_to_predict+1):
            pred_intervals.append(time_intervals[-1].right + i * offset)
            pred_intervals
        for tsid, ts in ts_collection.items():
            if not tsid in ts_causal_factors_dict.keys():
                ar_collection[tsid] = interimn_ar_collection[tsid]
            else:
                causing_ts = ts_causal_factors_dict[tsid]
                causing_df = pd.DataFrame(index=time_intervals.right)
                pred_causing_df = pd.DataFrame(index=pred_intervals)
                for causing_tsid in causing_ts:
                    causing_df[causing_tsid] = ts_collection[causing_tsid].copy()
                    pred_causing_df[causing_tsid] = interimn_ar_collection[causing_tsid].copy()
                ts_fc = ts.copy()
                ts_fc.index = pd.PeriodIndex(ts_fc.index, freq=freq)
                exo_df = causing_df
                exo_df.index = pd.PeriodIndex(exo_df.index, freq=freq)
                pred_exo_df = pred_causing_df
                pred_exo_df.index = pd.PeriodIndex(pred_exo_df.index, freq=freq)
                sp_list = ts_to_sp_map[tsid]
                if sp_list:
                    sp_ts = sp_list[0]
                else:
                    sp_ts = 1
                forecaster = AutoARIMA(sp=sp_ts, start_p = start_p, start_q = start_q, start_P = start_P, start_Q = start_Q,\
                                    max_p = max_p, max_q = max_q, max_P = max_P, max_Q = max_Q, maxiter= maxiter,\
                                    test = test, information_criterion= information_criterion, suppress_warnings=True) 
                forecaster.fit(y=ts_fc, X=exo_df) 
                pred = forecaster.predict(fh=range(1, periods_to_predict+1), X=pred_exo_df)
                pred.index = pd.to_datetime(pred.index.end_time.normalize(), utc=True)
                ar_collection[tsid] = pred
    else:
        ar_collection = interimn_ar_collection

    return ar_collection

#returns a list of indices for each time series that qualify a criteria according to the given parameters. 
#Where the parameters are:
#Mode: The metric on which the threshold is applied.
#      Possible values are 'quantile', 'relative change', 'nsmallest', 'nlargest'
#Comparison Operator: Where applicable, the operator determines how to use the threshold. 
#                     Possible values are 'between', 'greater or equal to', 'lesser or equal to'. 
#                     Only applicable for modes 'quantile' and 'relative change'.                      
#threshold_1: Primary Threshold value
#threshold_2: Secondary threshold value, only applicable for comparison operator 'between'.

def threshold_based_point_detection(ts_collection, threshold_params):
    mode = threshold_params['mode']
    comparison_operator = threshold_params['comparison_operator']
    threshold_1 = threshold_params['threshold_1']
    threshold_2 = threshold_params['threshold_2']

    if not mode:
        raise ValueError('Mode not provided')
    if not comparison_operator and mode in ['quantile', 'relative change']:
        raise ValueError('Comparison operator not provided')
    if not threshold_1:
        raise ValueError('Threshold_1 not provided')
    if not threshold_2 and comparison_operator=='between':
        raise ValueError('Threshold_2 not provided')
    
    ar_collection = {}

    for tsid, ts in ts_collection.items():
        if mode == 'quantile':
            ts_df = ts.copy().reset_index()
            if comparison_operator == 'between':
                bool_sr = ts_df[ts_df.columns[-1]].between(ts_df.quantile(q=threshold_1, interpolation='higher').iloc[1], ts_df.quantile(q=threshold_2, interpolation='higher').iloc[1])
            elif comparison_operator == 'greater or equal to':
                bool_sr = ts_df[ts_df.columns[-1]].ge(ts_df.quantile(q=threshold_1, interpolation='higher').iloc[1])
            elif comparison_operator == 'lesser or equal to':
                bool_sr = ts_df[ts_df.columns[-1]].le(ts_df.quantile(q=threshold_1, interpolation='higher').iloc[1])
            ar = bool_sr[bool_sr].index.values.tolist()
        elif mode == 'relative change':
            rc_df = ts.pct_change().reset_index().dropna()
            if comparison_operator == 'between':
                bool_sr = rc_df[rc_df.columns[-1]].between(threshold_1, threshold_2)
            elif comparison_operator == 'greater or equal to':
                bool_sr = rc_df[rc_df.columns[-1]].ge(threshold_1)
            elif comparison_operator == 'lesser or equal to':
                bool_sr = rc_df[rc_df.columns[-1]].le(threshold_1)
            ar = bool_sr[bool_sr].index.values.tolist()
        elif mode == 'nlargest':
            ts_df = ts.reset_index()
            ar = ts_df[ts_df.columns[-1]].nlargest(threshold_1).index.values.tolist()
        elif mode == 'nsmallest':
            ts_df = ts.reset_index()
            ar = ts_df[ts_df.columns[-1]].nsmallest(threshold_1).index.values.tolist()
        ar_collection[tsid] = ar
    return ar_collection

