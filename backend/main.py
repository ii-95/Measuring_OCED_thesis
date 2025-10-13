import pm4py
import numpy as np
import pandas as pd
from pathlib import Path
from setup import *
from EP_measurable_properties import *
from OP_measurable_properties import *
from PP_measurable_properties import *
from RP_measurable_properties import *
from time_series_analysis import *
from tsa_to_oced import *
from dotenv import load_dotenv
import os
import math
from statsmodels.tools.sm_exceptions import InterpolationWarning, ValueWarning
import warnings
from jsonschema import validate
import json
import datetime
pd.options.mode.copy_on_write = True
warnings.simplefilter('ignore', InterpolationWarning)
warnings.simplefilter('ignore', ValueWarning)

load_dotenv(dotenv_path="inputs.env")

# inputs provided by user via inputs.env (to be replaced with input from frontend)
path_to_ocel = Path(os.getenv('path_to_ocel')).resolve()
mod_ocel_write_format = os.getenv('mod_ocel_write_format')
aggregation_mode = os.getenv('aggregation_mode')
if aggregation_mode not in ['sum', 'mean', 'min', 'max']:
    raise ValueError('Invalid aggregation mode')

sampling_rate = os.getenv('sampling_rate')
if sampling_rate not in ['W','ME','QE','YE']:
    raise ValueError('Invalid sampling rate')

assignment_mechanism = os.getenv('assignment_mechanism')
if assignment_mechanism not in ['starting', 'ending', 'contains', 'overlaps']:
    raise ValueError('Invalid assignment mechanism')

#resource_object_type is the object type whose objects are to be trated as 
#resource objects for properties in the resource perspective.
resource_object_type = os.getenv('resource_object_type')

#endtime is the event attribute that is to be treated as the end time of non-atomic events
event_endtime_column = os.getenv('events_endtime_attribute')

#start and end of the time interval over which time series are to be constructed
int_start = os.getenv('time_series_interval_start')
if int_start:
    int_start = pd.to_datetime(int_start, utc=True)
int_end = os.getenv('time_series_interval_end')
if int_end:
    int_end = pd.to_datetime(int_end, utc=True)
#midnight timestamps, if at the boundary of time intervals, can create problems while generating time intervals
#e.g. if int_start = 01-01-2023 00:00:00+00:00 and sampling rate = ME (month end) then first interval should be
#(01-01-2023 00:00:00+00:00, 31-01-2023 00:00:00+00:00) but instead it will be (01-12-2022 00:00:00+00:00, 31-12-2022 00:00:00+00:00)
#to circumvent this issue we add a second to int_start and subtract a second from int_end.

if int_start and int_start.hour == 0 and int_start.minute == 0 and int_start.second == 0:
    int_start = int_start + pd.Timedelta('1s')
if int_end and int_end.hour == 0 and int_end.minute == 0 and int_end.second == 0:
    int_end = int_end - pd.Timedelta('1s')
offset_ti = get_offset_for_sampling_rate(sampling_rate)
offset = get_offset_for_sampling_rate(sampling_rate)
tsa_technique = os.getenv('tsa_technique')

generate_ts_visualizations = os.getenv('generate_ts_visualizations')
generate_ar_visualizations = os.getenv('generate_ar_visualizations')
generate_ts_data_files = os.getenv('generate_ts_data_files')
generate_ar_data_files = os.getenv('generate_ar_data_files')

if generate_ts_visualizations not in ['Y', 'N']:
    generate_ts_visualizations = 'N'
if generate_ar_visualizations not in ['Y', 'N']:
    generate_ar_visualizations = 'N'
if generate_ts_data_files not in ['Y', 'N']:
    generate_ts_data_files = 'N'
if generate_ar_data_files not in ['Y', 'N']:
    generate_ar_data_files = 'N'

append_forecasts_to_ts = os.getenv('append_forecasts_to_ts')
if append_forecasts_to_ts not in ['Y', 'N']:
    append_forecasts_to_ts = 'N'

use_change_point_difference_as_lag = os.getenv('use_change_point_difference_as_lag')
if not use_change_point_difference_as_lag in ['Y', 'N']:
    use_change_point_difference_as_lag = 'N'

use_tbpd_results_as_ts_for_granger_causality = os.getenv('use_tbpd_results_as_ts_for_granger_causality')
if not use_tbpd_results_as_ts_for_granger_causality in ['Y', 'N']:
    use_tbpd_results_as_ts_for_granger_causality = 'N'

only_compare_threshold_ts = os.getenv('only_compare_tbpd_ts')
if not only_compare_threshold_ts:
    only_compare_threshold_ts = 'N'

generate_visualizations_for_tbpd_ts = os.getenv('generate_visualizations_for_tbpd_ts')
if not generate_visualizations_for_tbpd_ts:
    generate_visualizations_for_tbpd_ts = 'N'

use_granger_causal_ts_as_exogenous_variables = os.getenv('use_granger_causal_ts_as_exogenous_variables')
if not use_granger_causal_ts_as_exogenous_variables in ['Y', 'N']:
    use_granger_causal_ts_as_exogenous_variables = 'N'

#read inputs for the corresponding tsa technique and perform some type/value checking
if tsa_technique == 'Change Point Detection':
    
    model = os.getenv('cp_model')

    if not model:
        model = 'rbf'
    elif model not in ['rbf', 'l1', 'l2']:
        raise ValueError('Invalid model specified for Change Point Detection')
    
    min_size = os.getenv('cp_min_size')
    if min_size:
        min_size = int(min_size)
    else:
        min_size = 3
    
    jump = os.getenv('cp_jump')
    if jump:
        jump = int(jump)
    else:
        jump = 1
    
    penalty = os.getenv('cp_penalty')
    if penalty:
        penalty = float(penalty)
    else:
        penalty = 1.5
    
    tsa_params = {'model': model, 'min_size': min_size, 'jump': jump, 'penalty': penalty}

elif tsa_technique == 'Granger Causality':
    
    lag = os.getenv('gc_lag')
    if lag:
        if ',' in lag:
            lag = ''.join(lag.split()).split(',')
            if len(lag) > 2:
                lag = list(map(int, lag))
            else:
                lag = [int(lag[0])]
        else:
            lag = int(lag)
    
    p_value_threshold = os.getenv('gc_p_value_thresh')
    if p_value_threshold:
        p_value_threshold = float(p_value_threshold)
    
    tsa_params = {'lag': lag, 'p_value_threshold': p_value_threshold, 'use_change_point_difference_as_lag': use_change_point_difference_as_lag}

elif tsa_technique == 'Forecasting':
    
    periods_to_predict = os.getenv('fc_periods')
    if periods_to_predict:
        periods_to_predict = int(periods_to_predict)
    else:
        periods_to_predict = 4

    start_p = os.getenv('fc_start_p')
    if start_p:
        start_p = int(start_p)
    else:
        start_p = 2

    start_q = os.getenv('fc_start_q')
    if start_q:
        start_q = int(start_q)
    else:
        start_q = 2

    start_P = os.getenv('fc_start_P_s')
    if start_P:
        start_P = int(start_P)
    else:
        start_P = 1

    start_Q = os.getenv('fc_start_Q_s')
    if start_Q:
        start_Q = int(start_Q)
    else:
        start_Q = 1

    max_p = os.getenv('fc_max_p')
    if max_p:
        max_p = int(max_p)
    else:
        max_p = 5

    max_q = os.getenv('fc_max_q')
    if max_q:
        max_q = int(max_q)
    else:
        max_q = 5

    max_P = os.getenv('fc_max_P_s')
    if max_P:
        max_P = int(max_P)
    else:
        max_P = 2

    max_Q = os.getenv('fc_max_Q_s')
    if max_Q:
        max_Q = int(max_Q)
    else:
        max_Q = 2

    information_criterion = os.getenv('fc_information_criterion')
    if not information_criterion:
        information_criterion = 'aicc'
    elif information_criterion not in ['aicc', 'aic', 'bic', 'hqic', 'oob']:
        raise ValueError('Invalid information criterion specified for forecasting')
    
    test = os.getenv('fc_test')
    if not test:
        test = 'kpss'
    elif test not in ['adf', 'kpss', 'pp']:
        raise ValueError('Invalid test specified for forecasting')
    
    maxiter = os.getenv('fc_maxiter')
    if maxiter:
        maxiter = int(maxiter)
    else:
        maxiter = 100
        
    tsa_params = {'periods_to_predict': periods_to_predict, 'use_granger_causal_ts_as_exogenous_variables': use_granger_causal_ts_as_exogenous_variables, \
                   'start_p': start_p, 'start_q': start_q, 'start_P': start_P,\
                    'start_Q': start_Q, 'max_p': max_p, 'max_q': max_q, 'max_P': max_P, 'max_Q': max_Q,\
                    'information_criterion': information_criterion, 'test': test, 'maxiter': maxiter}

elif tsa_technique == 'Threshold Based Point Detection':
    
    mode = os.getenv('thresh_pd_mode')
    if mode not in ['quantile', 'relative change', 'nsmallest', 'nlargest']:
        raise ValueError('Invalid mode selected for Threshold Based Point Detection')
    
    comparison_operator = os.getenv('thresh_pd_comparison_operator')
    if mode in ['quantile', 'relative change']:
        if comparison_operator not in ['between', 'greater or equal to', 'lesser or equal to']:
            raise ValueError('Invalid comparison operator selected for Threshold Based Point Detection')
    else:
        comparison_operator = None
    
    threshold_1 = os.getenv('thresh_pd_threshold_1')
    if not threshold_1:
        raise ValueError('A primary threshold must be provided')
    else:
        threshold_1 = float(threshold_1)

    if mode == 'quantile' and (threshold_1 < 0 or threshold_1 > 1):
        raise ValueError('Threshold for quantile must be between 0 and 1')

    threshold_2 = os.getenv('thresh_pd_threshold_2')

    if comparison_operator == 'between': 
        if not threshold_2:
            raise ValueError('An upper threshold must be provided')
        else:
            threshold_2 = float(threshold_2)

        if threshold_2 < threshold_1:
            raise ValueError('Upper threshold cannot be lesser than the lower threshold')

        if mode == 'quantile' and (threshold_2 < 0 or threshold_2 > 1):
                raise ValueError('Threshold for quantile must be between 0 and 1 when mode = quantile')
    else:
        threshold_2 = None
    
    tsa_params = {'mode': mode, 'comparison_operator' : comparison_operator, 'threshold_1': threshold_1, \
                  'threshold_2': threshold_2 }

elif not tsa_technique:
    tsa_technique = None
    
else: 
    raise ValueError('Invalid tsa technique selected')

#We use use the ocel as a pm4py object 'ocel' for data processing and analysis.
# get ocel as a pm4py object 
format = path_to_ocel.suffix
input_ocel_filename = ''.join(path_to_ocel.name.split('.')[:-1])
if format == '.json':
    ocel = pm4py.read_ocel2_json(path_to_ocel)
elif format == '.sqlite':
    ocel = pm4py.read_ocel2_sqlite(path_to_ocel)
else:
    raise TypeError('Invalid or unsupported OCEL 2.0 format. Please provide a json or sqlite file.')

#for conversion of timeseries and analysis results to ocel, we need to convert the log into json format.
#This is also done even if the original ocel file was in json format as pm4py performs some cleanup activities that are helpful
#in maintaining a uniform structure of the input log and hence result in stable functionality of this tool.
#e.g. resetting initial values of object attributes to timestamp 0 ("1970-01-01T00:00:00Z") or removing objects that are not
#related to any events.
converted_ocel_file_path =  str(Path('backend/assets/temp/convert_ocel.json').resolve())
try:
    os.remove(converted_ocel_file_path)
except OSError:
    pass
pm4py.write_ocel2_json(ocel, converted_ocel_file_path)
with open('backend/assets/temp/convert_ocel.json') as f:
    ocel_json_dict = json.load(f)

#set pm4py ocel column names
event_id_column = ocel.event_id_column
event_timestamp_column = ocel.event_timestamp
event_type_column = ocel.event_activity
object_id_column = ocel.object_id_column
object_type_column = ocel.object_type_column
changed_field_column = ocel.changed_field
qualifier_column = ocel.qualifier

attribute_names = pm4py.ocel.ocel_get_attribute_names(ocel)
if 'tsvalues' in attribute_names:
    first_iteration = False
else:
    first_iteration = True

if first_iteration and (append_forecasts_to_ts == 'Y' or use_change_point_difference_as_lag == 'Y' \
                        or use_tbpd_results_as_ts_for_granger_causality == 'Y' or only_compare_threshold_ts == 'Y'
                        or use_granger_causal_ts_as_exogenous_variables == 'Y'):
    raise ValueError('Options to use previous analysis results cannot be selected in the first iteration since they do not exist in the log yet.')

if append_forecasts_to_ts == 'Y' and (use_change_point_difference_as_lag == 'Y' \
                        or use_tbpd_results_as_ts_for_granger_causality == 'Y' or only_compare_threshold_ts == 'Y'
                        or use_granger_causal_ts_as_exogenous_variables == 'Y'):
    raise ValueError('Options to append forecasts can not be selected if any other option to use previous tsa results is selected')

if use_change_point_difference_as_lag == 'Y' and (use_tbpd_results_as_ts_for_granger_causality == 'Y'\
                                                    or only_compare_threshold_ts == 'Y'):
    raise ValueError('Cannot use change points as lag while using theshold based points as time series')

if use_tbpd_results_as_ts_for_granger_causality == 'Y' and only_compare_threshold_ts == 'Y':
    raise ValueError('Select at most one from the following two options: use_tbpd_results_as_ts_for_granger_causality and only_compare_threshold_ts')

#if not first iteration, disregard input given by the user for the following fields and replace with those given in first iteration
#for the remaining fields that are not overwritten, they can either be changed during each iteration e.g. tsa technique, tsa params, etc.
#otherwise they are inconsequential for iterations > 1 e.g. event_endtime_column or resource_object_type as these are only
#required to generate the time series in the first iteration.
if not first_iteration:
    int_start = pd.to_datetime(ocel.events.loc[ocel.events[event_id_column] == 'start_dummy_event', event_timestamp_column].values[0], utc=True)
    int_end = pd.to_datetime(ocel.events.loc[ocel.events[event_id_column] == 'end_dummy_event', event_timestamp_column].values[0], utc=True)
    sampling_rate = ocel.objects['sampling_rate'].dropna().drop_duplicates().values[0]
    aggregation_mode = ocel.objects['aggregation_mode'].dropna().drop_duplicates().values[0]
    #since offset is already determined in first iteration, we just difference by the 1s difference we introduced between original 
    #values of int_start and int_end before saving to timestamps of dummy event while converting the first iterations result to OCED.
    offset_ti = pd.Timedelta('1s')

#setup essential tables(dataframes) and variables
events_df = get_events_df(ocel)

event_types = list(events_df[event_type_column].unique())
object_types = pm4py.ocel.ocel_get_object_types(ocel)

event_object_combinations = get_event_object_combinations(ocel, event_type_column, object_type_column)
objects_summary_df = get_objects_summary_df(ocel)
event_to_object_relations_df = get_event_to_object_relations_df(ocel)
objects_df = get_objects_df(ocel)
object_changes_df = get_object_changes_df(ocel)


#check if the specified endtime attribute for events exists. If yes then we assume the presence of 
# non-atomic events in the log.
if event_endtime_column in events_df.columns:
    atomic_evs = False
    #for all atomic events (where endtime column has empty/null values, replace with value in ocel:timestamp column)
    events_df = adjust_events_end_time(events_df.copy(), event_endtime_column)
    # calculate lifecycle end time for objects to be calculated based on the maximum endtime of all events associated with
    # an object. By default, pm4py calculates this assuming atomic events which can not be used if non-atomic events exist.
    objects_summary_df = update_object_lifecycle_end_for_non_atomic_events(objects_summary_df.copy(), event_to_object_relations_df.copy(),\
                                                                    events_df.copy(), event_endtime_column)
else:
    atomic_evs = True

#verify if the specificed resource object type exists in the log, else set to empty.
if not resource_object_type in object_types:
    resource_object_type = ''

# if time interval start is unspecified, fetch from event log as the earliest timestamp of an event
if first_iteration and not int_start:
    int_start = pd.to_datetime(events_df[event_timestamp_column].min(), utc = True)
    if int_start.hour == 0 and int_start.minute == 0 and int_start.second == 0:
        int_start = int_start + pd.Timedelta('1s')
# if time interval end is unspecified, fetch from event log as 
# if all events are atomic => the latest ocel:timestamp value of any event
# if all events are not atomic => the latest endtime value of any event
if first_iteration and not int_end:
    if atomic_evs:
        int_end = pd.to_datetime(events_df[event_timestamp_column].max(), utc = True)
    else:
        int_end = pd.to_datetime(events_df[event_endtime_column].max(), utc = True)

    if int_end.hour == 0 and int_end.minute == 0 and int_end.second == 0:
        int_end = int_end - pd.Timedelta('1s')


#<-----------Remove in prod----------->
#add endtime column to events_df for testing. Each event gets a runtime ranging from it's start time 
# i.e. ocel:timestamp up to a month from the start time.
""" endtimes_hours = np.random.randint(0, 30, len(events_df)).astype('timedelta64[h]')
endtimes_minutes = np.random.randint(0, 300, len(events_df)).astype('timedelta64[m]')
events_df[event_endtime_column] = events_df[event_timestamp_column] + endtimes_hours + endtimes_minutes
ocel_extended_df[event_endtime_column] = events_df.merge(ocel_extended_df, on=event_id_column, how='inner')[event_endtime_column]
atomic_evs = False
objects_summary_df = update_object_lifecycle_end_for_non_atomic_events(objects_summary_df, event_to_object_relations_df,\
                                                                    events_df, event_endtime_column) """
#<-----------Remove in prod----------->

#get time intervals given the sampling rate and total interval. The start and end are first adjust by an offset 
#(depending on the sampling rate) such that int_start is offset to start of its respective time interval and int_end to the end
#e.g. if sampling rate is 'ME' i.e., month end then int_start = 2023-03-02 12:23:44+00:00 becomes 2023-03-01 00:00:00+00:00
#and int_end = 2024-05-28 12:23:56+00:00 becomes 2024-06-30 00:00:00
#The intervals represent the division of the total interval into time intervals of length equal to the sampling rate.

time_intervals = get_time_intervals(int_start, int_end, sampling_rate, offset_ti)

if len(time_intervals) < 30:
    warnings.warn(f'The specified sampling rate and/or time interval range leads to time series containing too few ({len(time_intervals)}) data points whereas a minimum of 30 data points is recommended. \n This will lead to unreliable analysis results and in extreme cases, failure to execute the analysis altogether.')
#update start and end according to the time intervals calculated
int_start = time_intervals[0].left
int_end = time_intervals[-1].right
#get a cross product of objects and events df with the time intervals
#ti_cross_objs_df = get_time_intervals_cross_objects_summary_df(objects_summary_df, time_intervals)
#ti_cross_evs_df = get_time_intervals_cross_events_df(events_df, time_intervals, event_endtime_column)

#get list of events and objects assigned to a time interval 
#if assign_mech = overlap then we get duplicate events/objects
#if assign_mech = contains then a lot of events/objects are usually discarded
#if assign_mech = starting or assign_mech = ending then we get the same number of events/objects as in the original ocel
#atomic events remain unaffected by assign_mech and are neither duplicated nor discarded.
events_to_time_df = get_events_to_time_df(events_df.copy(), time_intervals, assignment_mechanism, event_endtime_column, atomic_evs)
objects_to_time_df = get_objects_to_time_df(objects_summary_df.copy(), time_intervals, assignment_mechanism)


object_types_to_df_map = get_object_types_to_df_map(objects_df.copy(), object_changes_df.copy(), object_types)
event_types_to_df_map = get_event_types_to_df_map(events_df.copy(), event_types, atomic_evs, event_endtime_column)

#determine range of possible seasonal periods
#minimum seasonal period for each sampling rate is selected manually considering the shortest possible repitive pattern
#that can probably occur in event data.
#Maximum seasonal period is selected as 1/3rd of the time series length because a time series must contain atleast
#a few cycles of the season to be detected. 
#The decisions for minimum and maximum periods were taken based on a review of time series literature and discussions
#Nevertheless, there is no absolutely 'correct' choice.
if sampling_rate == 'W':
    series_length = (int_end - int_start) / pd.Timedelta(7,'D')
    min_seasonal_period = 4
    max_seasonal_period = math.floor(series_length/3)
if sampling_rate == 'ME':
    series_length = (int_end - int_start) / pd.Timedelta(30,'D')
    min_seasonal_period = 3
    max_seasonal_period = math.floor(series_length/3)
if sampling_rate == 'QE':
    series_length = (int_end - int_start) / pd.Timedelta(90,'D')
    min_seasonal_period = 2
    max_seasonal_period = math.floor(series_length/3)
if sampling_rate == 'YE':
    series_length = (int_end - int_start) / pd.Timedelta(365,'D')
    min_seasonal_period = 2
    max_seasonal_period = math.floor(series_length/3)
if max_seasonal_period < min_seasonal_period:
    max_seasonal_period = min_seasonal_period
    

property_names_dict = {
                    'ep1': 'Event Frequency',\
                    'ep2': 'Event Attribute Value', \
                    'ep3': 'Number of Objects per Event', \
                    'ep4': 'Number of Objects of a type per Event' , \
                    'op1': 'Object Frequency',\
                    'op2': 'Object Attribute Value', \
                    'op3': 'Number of Events per Object', \
                    'op4': 'Number of Events of a Type per Object', \
                    'op5': 'Lifecycle Duration (Hours)', \
                    'op6': 'Number of Object Interactions per Event', \
                    'pp1': 'Waiting Time (Hours)', \
                    'pp2': 'Synchronization Time (Hours)', \
                    'pp3': 'Service Time (Hours)', \
                    'pp4': 'Soujourn Time (Hours)', \
                    'pp5': 'Flow Time (Hours)', \
                    'pp6': 'Pooling Time(Hours)',\
                    'pp7': 'Lagging Time(Hours)', \
                    'rp1': 'Number of Involved Resources per Event',\
                    'rp2': 'Number of Active Resources',\
                    'rp3': 'Resrouce Attribute'
                    }

# this dict is used in the conversion of time series to OCED
property_parameters_map = {
                    'ep1': ['event type'],\
                    'ep2': ['event type', 'event attribute'], \
                    'ep3': ['event type'], \
                    'ep4': ['event type', 'object type'], \
                    'op1': ['object type'],\
                    'op2': ['object type', 'object attribute'], \
                    'op3': ['object type'], \
                    'op4': ['object type', 'event type'], \
                    'op5': ['object type'], \
                    'op6': ['object type', 'object type'], \
                    'pp1': ['event type'], \
                    'pp2': ['event type'], \
                    'pp3': ['event type'], \
                    'pp4': ['event type'], \
                    'pp5': ['event type'], \
                    'pp6': ['event type', 'object type'],\
                    'pp7': ['event type', 'object type'], \
                    'rp1': ['event type', 'object type'],\
                    'rp2': ['object type'],\
                    'rp3': ['object type', 'object attribute']
                    }

if first_iteration:
    event_to_object_relations_df_map = get_event_to_object_type_relations_df_map(event_to_object_relations_df.copy(), event_object_combinations)
    object_interactions_df = get_object_interactions_df(ocel)
    ocel_extended_df = get_ocel_extended_df(ocel)
    #check if the specified endtime attribute for events exists. If yes then we assume the presence of 
    # non-atomic events in the log.
    if event_endtime_column in events_df.columns:
        ocel_extended_df[event_endtime_column] = events_df.merge(ocel_extended_df, on=event_id_column, how='inner')[event_endtime_column]

    event_object_count_df_map = get_event_object_count_df_map(ocel, event_types_to_df_map.copy())
    object_type_summary_df_map = get_object_type_summary_df_map(objects_summary_df.copy(), object_types_to_df_map.copy())
    #get preceding events df for performance perspective properties
    preceding_events_df = get_preceding_events_df(ocel_extended_df, object_types, atomic_evs, event_endtime_column)
    #get all properties of the event perspective
    ep1_dict = ep1(event_types_to_df_map, events_to_time_df, sampling_rate)
    ep2_dict = ep2(event_types_to_df_map, events_to_time_df, aggregation_mode, sampling_rate, atomic_evs, event_endtime_column)
    ep3_dict = ep3(event_object_count_df_map, events_to_time_df, aggregation_mode, sampling_rate)
    ep4_dict = ep4(event_object_combinations, event_object_count_df_map, events_to_time_df, aggregation_mode, sampling_rate)

    op1_dict = op1(object_types_to_df_map, objects_to_time_df, sampling_rate)
    op2_dict = op2(object_types_to_df_map, objects_to_time_df, aggregation_mode, sampling_rate)
    op3_dict = op3(object_type_summary_df_map, objects_to_time_df, aggregation_mode, sampling_rate)
    op4_dict = op4(event_to_object_relations_df_map, objects_to_time_df, aggregation_mode, sampling_rate)
    op5_dict = op5(object_type_summary_df_map, objects_to_time_df, aggregation_mode, sampling_rate)
    op6_dict = op6(object_interactions_df, events_to_time_df, aggregation_mode, sampling_rate)

    pp1_dict = pp1(preceding_events_df, event_types, events_to_time_df, aggregation_mode, sampling_rate)
    pp2_dict = pp2(preceding_events_df, event_types, events_to_time_df, aggregation_mode, sampling_rate)
    #service time (pp3) for atomic events is always 0 and  
    #soujourn time (pp4) is equal to waiting time for atomic events
    #so we don't generate any time series for these properties if all events in the log are atomic.  
    if atomic_evs:
        pp3_dict = {}
        pp4_dict = {}
    else:
        pp3_dict = pp3(event_types_to_df_map, events_to_time_df, aggregation_mode, sampling_rate, event_endtime_column)
        pp4_dict = pp4(pp1_dict, preceding_events_df, event_types, event_endtime_column, atomic_evs, events_to_time_df,\
                        aggregation_mode, sampling_rate)
    pp5_dict = pp5(preceding_events_df, event_types, event_endtime_column, atomic_evs, events_to_time_df,\
                    aggregation_mode, sampling_rate)
    pp6_dict = pp6(preceding_events_df, event_object_combinations, events_to_time_df, aggregation_mode, sampling_rate)
    pp7_dict = pp7(preceding_events_df, event_object_combinations, events_to_time_df, aggregation_mode, sampling_rate)

    rp1_dict = rp1(ep4_dict, resource_object_type)
    rp2_dict = rp2(event_to_object_relations_df, events_to_time_df, resource_object_type, sampling_rate)
    rp3_dict = rp3(op2_dict, resource_object_type)

    property_dicts_map = {
                    'ep1': ep1_dict, 'ep2': ep2_dict, 'ep3': ep3_dict, 'ep4': ep4_dict ,\
                    'op1': op1_dict, 'op2': op2_dict, 'op3': op3_dict, 'op4': op4_dict,\
                    'op5': op5_dict, 'op6': op6_dict, 'pp1': pp1_dict, 'pp2': pp2_dict,\
                    'pp3': pp3_dict, 'pp4': pp4_dict, 'pp5': pp5_dict, 'pp6': pp6_dict,\
                    'pp7': pp7_dict, 'rp1': rp1_dict, 'rp2': rp2_dict, 'rp3': rp3_dict
                    }

    #process time series by padding on both ends with null values to represent missing values 
    #then discard any time series with any null values (not only on the ends but anywhere) and assign remaining
    #to a dict called 'TS_collection' which is then used ahead. 
    #Plot all series being assigned to 'TS_collection'. Plots will be saved to 'backend/assets/plots'.
    TS_collection = {}
    for property, property_dict in property_dicts_map.items():
        if property_dict:
            for non_temporal_parameters, ts in property_dict.items():
                if not ts.empty:
                    #padding the timeseries on both ends to align with specified intervals.
                    processed_ts = time_intervals.right.to_frame().merge(ts, left_index=True, right_index=True, how='left')\
                        .drop(columns=0).iloc[:,0]
                    if not processed_ts.isna().any():
                        TS_collection[(property, non_temporal_parameters)] = processed_ts
else:
    prev_iterations_data = op2(object_types_to_df_map, objects_to_time_df, aggregation_mode, sampling_rate)

#retrieve time series and tsa results from previous iterations
change_point_indices_dict = {}
ts_causal_factors_dict = {}
if not first_iteration:
    TS_collection = {}
    change_point_ts_dict = {}
    change_point_idx_ts_dict = {}
    
    threshold_based_ts_dict = {}
    for key, value in prev_iterations_data.items():
        if key[0].startswith('ts'):
            name_list = key[0].split('-')
            property = name_list[1]
            non_temporal_parameters_str = name_list[2]
            non_temporal_parameters_list = non_temporal_parameters_str.split('_')
            if len(non_temporal_parameters_list) > 1:
                non_temporal_parameters = tuple(non_temporal_parameters_list)
            else:
                non_temporal_parameters = non_temporal_parameters_list[0]
            if key[1] == 'tsvalues':
                ts = value
                ts.index.name = None
                TS_collection[(property, non_temporal_parameters)] = ts
            if key[1].startswith('Change Point Detection'):
                if tsa_technique == 'Change Point Detection':
                    raise ValueError ('Cannot run change point detection on the same log twice.')
                cpd_property = f'Change Points for {property}'
                change_point_idx_ts_dict[(property, non_temporal_parameters)] = value
                change_point_ts_dict[(cpd_property, non_temporal_parameters)] = value
            if key[1].startswith('Threshold Based Point Detection'):
                tbpd_params = '{' + key[1].split('{')[1]
                tbpd_property = f'Threshold Based Points for {property} with params {tbpd_params}'
                threshold_based_ts_dict[(tbpd_property, non_temporal_parameters)] = value
                
    o2o_df = ocel.o2o.copy()
    granger_df = o2o_df[o2o_df['ocel:qualifier'].str.startswith('Granger')].reset_index(drop=True)
    if not granger_df.empty:
        if tsa_technique == 'Granger Causality':
            raise ValueError('Cannot run granger causality on the same log twice.')
        if tsa_technique == 'Forecasting':
            granger_df = granger_df[['ocel:oid','ocel:oid_2']].rename(columns={'ocel:oid':'caused', 'ocel:oid_2':'causing'})\
                .groupby('caused').agg(list).reset_index()
            ts_causal_factors_list = granger_df.to_dict('records')
            for ts_factors in ts_causal_factors_list:
                causing_tsid_list = []
                caused_ts = ts_factors['caused']
                causing_ts_list = ts_factors['causing']
                caused_ts_str = caused_ts.split('-')
                caused_ts_property = caused_ts_str[1]
                caused_ts_non_temporal_parameters_str = caused_ts_str[2]
                caused_non_temporal_parameters_list = caused_ts_non_temporal_parameters_str.split('_')
                if len(caused_non_temporal_parameters_list) > 1:
                    caused_non_temporal_parameters = tuple(caused_non_temporal_parameters_list)
                else:
                    caused_non_temporal_parameters = caused_non_temporal_parameters_list[0]
                for causing_ts in causing_ts_list:
                    causing_ts_str = causing_ts.split('-')
                    causing_ts_property = causing_ts_str[1]
                    causing_ts_non_temporal_parameters_str = causing_ts_str[2]
                    causing_non_temporal_parameters_list = causing_ts_non_temporal_parameters_str.split('_')
                    if len(causing_non_temporal_parameters_list) > 1:
                        causing_non_temporal_parameters = tuple(causing_non_temporal_parameters_list)
                    else:
                        causing_non_temporal_parameters = causing_non_temporal_parameters_list[0]
                    causing_tsid_list.append((causing_ts_property, causing_non_temporal_parameters))
                ts_causal_factors_dict[(caused_ts_property, caused_non_temporal_parameters)] = causing_tsid_list
        
    ts_forecasts_df = ocel.object_changes[ocel.object_changes['ocel:field'].str.startswith('Forecasting')]    
    if not ts_forecasts_df.empty:
        if tsa_technique == 'Forecasting':
            raise ValueError('Cannot run forecasting on the same log twice.')
        for column in ts_forecasts_df.columns:
            if column.startswith('Forecasting'):
                forecast_column = column
        ts_forecasts_df = ts_forecasts_df[['ocel:oid', 'ocel:timestamp', forecast_column]].sort_values(by=['ocel:oid','ocel:timestamp'],ignore_index=True)
        ts_forecasts_df['property'] = ts_forecasts_df['ocel:oid'].str.split(pat='-').str[1]
        ts_forecasts_df['non_temporal_parameters'] = ts_forecasts_df['ocel:oid'].str.split(pat='-').str[-1].str.split(pat='_').apply(lambda x: tuple(x) if len(x) > 1 else x[0])
        ts_forecasts_df['tsid'] = ts_forecasts_df.apply(lambda x: tuple((x['property'], x['non_temporal_parameters'])), axis=1)
        ts_forecasts_df = ts_forecasts_df[['tsid', event_timestamp_column, forecast_column]]

if generate_ts_data_files == 'Y' or generate_ts_visualizations == 'Y':
    create_plots_and_data_for_ts_collection(TS_collection, property_names_dict, generate_ts_data_files, generate_ts_visualizations)

#constant time series i.e. where all time periods have the same value will not be considered for further analysis.
#so we discard all such time series and assign remaining to a dict 'ar_ts_collection'.
#We round the values to 3 decimal places before checking for constant values since they trigger errors in performing tsa ahead
#especially for granger causality and forecasting.
ar_ts_collection = {}
for tsid, ts in TS_collection.items():
    if not len(ts.round(3).unique()) == 1:
        ar_ts_collection[tsid] = ts.copy()

#Handle selected options for using analysis results from previous iterations in current iteration's analysis
if not first_iteration:
    #create lists of change points for each time series
    if tsa_technique == 'Granger Causality' and use_change_point_difference_as_lag == 'Y':
        for tsid, cp_ts in change_point_idx_ts_dict.items():
            cp_df = cp_ts.copy()
            cp_df = cp_df.rename('cp').reset_index()
            change_point_indices_dict[tsid] = cp_df[cp_df['cp']==1].index.values.tolist()
            
    #append forecasts to time series is selected if option is selected
    if append_forecasts_to_ts == 'Y':
        ar_ts_collection_with_forecasts = {}
        for tsid, ts in ar_ts_collection.items():
            forecast_ts = ts_forecasts_df[ts_forecasts_df['tsid'] == tsid][[event_timestamp_column, forecast_column]]
            forecast_ts = forecast_ts.set_index(event_timestamp_column)
            forecast_ts = forecast_ts[forecast_ts.columns[-1]]
            forecast_ts.name = tsid
            ts.name = tsid
            ar_ts_collection_with_forecasts[tsid] = pd.concat([ts, forecast_ts])
        ar_ts_collection = ar_ts_collection_with_forecasts

    #use threshold based point detection results as time series for granger causality, if selected.
    if tsa_technique == 'Granger Causality':
        if use_tbpd_results_as_ts_for_granger_causality == 'Y':
            if generate_visualizations_for_tbpd_ts == 'Y':
                create_plots_and_data_for_ts_collection(threshold_based_ts_dict, property_names_dict, generate_ts_data_files, 'Y')
            for tbp_tsid, tbp_ts in threshold_based_ts_dict.items():
                if not len(tbp_ts.unique()) == 1 and len(tbp_ts[tbp_ts==1]) > 1:
                    ar_ts_collection[tbp_tsid] = tbp_ts
        elif only_compare_threshold_ts == 'Y':
            if generate_visualizations_for_tbpd_ts == 'Y':
                create_plots_and_data_for_ts_collection(threshold_based_ts_dict, property_names_dict, generate_ts_data_files, 'Y')
            processed_threshold_based_ts_dict = {}
            for tbp_tsid, tbp_ts in threshold_based_ts_dict.items():
                if not len(tbp_ts.unique()) == 1 and len(tbp_ts[tbp_ts==1]) > 1 :
                    processed_threshold_based_ts_dict[tbp_tsid] = tbp_ts
            ar_ts_collection = processed_threshold_based_ts_dict

warnings.simplefilter('ignore', InterpolationWarning)
warnings.simplefilter('ignore', ValueWarning)
#perform time series analysis and save the results to a json file available in 'backend/assets/analysis_results'
if tsa_technique:
    if ar_ts_collection:
        ar_collection = time_series_analysis(ar_ts_collection, tsa_technique, min_seasonal_period,\
                                                max_seasonal_period, sampling_rate, offset, change_point_indices_dict, \
                                                ts_causal_factors_dict, time_intervals, tsa_params)
        if isinstance(ar_collection, dict) and not ar_collection:
            print('No analysis results produced')
        elif isinstance(ar_collection, pd.DataFrame) and ar_collection.empty:
            print('No analysis results produced')
        else:
            if generate_ar_data_files == 'Y':
                save_ar_to_json(ar_collection, tsa_technique)
            if generate_ar_visualizations == 'Y':
                visualize_analysis_results(ar_ts_collection, ar_collection, tsa_technique, tsa_params, property_names_dict)
    else:
        print('None of the time series qualify for analysis')

#convert time series and tsa results to OCED and push it into the input ocel
if not append_forecasts_to_ts == 'Y' and not use_tbpd_results_as_ts_for_granger_causality == 'Y' and not only_compare_threshold_ts == 'Y':
    if first_iteration:
        ts_mod_ocel_json_dict = insert_time_series_into_ocel(TS_collection, ocel_json_dict, int_start, int_end, aggregation_mode, sampling_rate, \
                                        property_names_dict, property_parameters_map, events_to_time_df, objects_to_time_df,
                                        event_types_to_df_map, object_types_to_df_map)
    else:
        ts_mod_ocel_json_dict = ocel_json_dict
    if tsa_technique:
        ar_mod_ocel_json_dict = insert_ar_into_ocel(ar_collection, tsa_technique, tsa_params, ts_mod_ocel_json_dict, property_names_dict, time_intervals, offset)
        mod_ocel_json_dict = ar_mod_ocel_json_dict
    else:
        mod_ocel_json_dict = ts_mod_ocel_json_dict
    validate(mod_ocel_json_dict, json_schema)
    #write modified ocel to file in specified format. append timestamp to filename to avoid overwriting logs from previous runs
    current_timestamp = str(datetime.datetime.now())
    mod_ocel_json_dict_file_path = str(Path('backend/assets/temp/mod_ocel_json_dict.json').resolve())
    mod_ocel_file_path = str(Path(f'backend/assets/logs/mod_ocel_{input_ocel_filename}_{current_timestamp}'.split('.')[0] + f'.{mod_ocel_write_format}'))\
        .replace(' ', '-').replace(':','-')
    with open(mod_ocel_json_dict_file_path, 'w', encoding='utf-8') as f:
        json.dump(mod_ocel_json_dict, f)
    mod_ocel = pm4py.read_ocel2_json(mod_ocel_json_dict_file_path)
    if mod_ocel_write_format == 'json':
        pm4py.write_ocel2_json(mod_ocel, mod_ocel_file_path)
    elif format == 'sqlite':
        pm4py.write_ocel2_sqlite(mod_ocel, mod_ocel_file_path)