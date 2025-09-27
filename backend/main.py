import pm4py
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from pathlib import Path
from setup import *
from EP_measurable_properties import *
from OP_measurable_properties import *
from PP_measurable_properties import *
from RP_measurable_properties import *
from time_series_analysis import *
from dotenv import load_dotenv
import os
from sktime.utils.plotting import plot_series
import matplotlib.pyplot as plt
import math
from statsmodels.tools.sm_exceptions import InterpolationWarning, ValueWarning
import warnings
pd.options.mode.copy_on_write = True
warnings.simplefilter('ignore', InterpolationWarning)
warnings.simplefilter('ignore', ValueWarning)

load_dotenv(dotenv_path="inputs.env")

# inputs provided by user via inputs.env (to be replaced with input from frontend)
path_to_ocel = Path(os.getenv('path_to_ocel')).resolve()

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
int_start = pd.to_datetime(os.getenv('time_series_interval_start'), utc=True)
int_end = pd.to_datetime(os.getenv('time_series_interval_end'), utc=True)

tsa_technique = os.getenv('tsa_technique')

#read inputs for the corresponding tsa technique and perform some type/value checking
if tsa_technique == 'Change Point Detection':
    
    model = os.getenv('cp_model')
    
    min_size = os.getenv('cp_min_size')
    if min_size:
        min_size = int(min_size)
    
    jump = os.getenv('cp_jump')
    if jump:
        jump = int(jump)
    
    penalty = os.getenv('cp_penalty')
    if penalty:
        penalty = float(penalty)
    
    tsa_params = {'model': model, 'min_size': min_size, 'jump': jump, 'penalty': penalty}

elif tsa_technique == 'Granger Causality':
    
    lag = os.getenv('gc_lag')
    if lag:
        if ',' in lag:
            lag = ''.join(lag.split()).split(',')
            lag = list(map(int, lag))

        else:
            lag = int(lag)
    
    p_value_threshold = os.getenv('gc_p_value_thresh')
    if p_value_threshold:
        p_value_threshold = float(p_value_threshold)
    
    tsa_params = {'lag': lag, 'p_value_threshold': p_value_threshold}

elif tsa_technique == 'Forecasting':
    
    periods_to_predict = os.getenv('fc_periods')
    if periods_to_predict:
        periods_to_predict = int(periods_to_predict)
    
    start_p = os.getenv('fc_start_p')
    if start_p:
        start_p = int(start_p)
    
    start_q = os.getenv('fc_start_q')
    if start_q:
        start_q = int(start_q)
    
    start_P = os.getenv('fc_start_P_s')
    if start_P:
        start_P = int(start_P)
    
    start_Q = os.getenv('fc_start_Q_s')
    if start_Q:
        start_Q = int(start_Q)
    
    max_p = os.getenv('fc_max_p')
    if max_p:
        max_p = int(max_p)
    
    max_q = os.getenv('fc_max_q')
    if max_q:
        max_q = int(max_q)
    
    max_P = os.getenv('fc_max_P_s')
    if max_P:
        max_P = int(max_P)
    
    max_Q = os.getenv('fc_max_Q_s')
    if max_Q:
        max_Q = int(max_Q)
    
    information_criterion = os.getenv('fc_information_criterion')
    if information_criterion not in ['aicc', 'aic', 'bic', 'hqic', 'oob', '', None]:
        raise ValueError('Invalid information criterion specified for forecasting')
    
    test = os.getenv('fc_test')
    if test not in ['adf', 'kpss', 'pp', '', None]:
        raise ValueError('Invalid test specified for forecasting')
    
    maxiter = os.getenv('fc_maxiter')
    if maxiter:
        maxiter = int(maxiter)
    
    tsa_params = {'periods_to_predict': periods_to_predict, 'start_p': start_p, 'start_q': start_q, 'start_P': start_P,\
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

if format == '.json':
    ocel = pm4py.read_ocel2_json(str(path_to_ocel))
elif format == '.sqlite':
    ocel = pm4py.read_ocel2_sqlite(str(path_to_ocel))
elif format == '.xml':
    ocel = pm4py.read_ocel2_xml(str(path_to_ocel))
else:
    raise TypeError('Invalid format')

#set pm4py ocel column names
event_id_column = ocel.event_id_column
event_timestamp_column = ocel.event_timestamp
event_type_column = ocel.event_activity
object_id_column = ocel.object_id_column
object_type_column = ocel.object_type_column
changed_field_column = ocel.changed_field
qualifier_column = ocel.qualifier

#setup essential tables(dataframes) and variables
events_df = get_events_df(ocel)

event_types = list(events_df[event_type_column].unique())
object_types = pm4py.ocel.ocel_get_object_types(ocel)

event_object_combinations = get_event_object_combinations(ocel, event_type_column, object_type_column)
objects_summary_df = get_objects_summary_df(ocel)
event_to_object_relations_df = get_event_to_object_relations_df(ocel)
event_to_object_relations_df_map = get_event_to_object_type_relations_df_map(event_to_object_relations_df.copy(), event_object_combinations)
objects_df = get_objects_df(ocel)
object_changes_df = get_object_changes_df(ocel)
object_interactions_df = get_object_interactions_df(ocel)
ocel_extended_df = get_ocel_extended_df(ocel)

#check if the specified endtime attribute for events exists. If yes then we assume the presence of 
# non-atomic events in the log.
if event_endtime_column in events_df.columns:
    atomic_evs = False
    #for all atomic events (where endtime column has empty/null values, replace with value in ocel:timestamp column)
    events_df = adjust_events_end_time(events_df.copy(), event_endtime_column)
    ocel_extended_df[event_endtime_column] = events_df.merge(ocel_extended_df, on=event_id_column, how='inner')[event_endtime_column]

    # calculate lifecycle end time for objects to be calculated based on the maximum endtime of all events associated with
    # an object. By default, pm4py calculates this assuming atomic events which can not be used if non-atomic events exist.
    objects_summary_df = update_object_lifecycle_end_for_non_atomic_events(objects_summary_df.copy(), event_to_object_relations_df.copy(),\
                                                                    events_df.copy(), event_endtime_column)
else:
    atomic_evs = True

# if time interval start is unspecified, fetch from event log as the earliest timestamp of an event
if int_start == '':
    int_start = events_df[event_timestamp_column].min()
    #adjust start so that 1st event can be accounted for in further calculations
    int_start = int_start - pd.Timedelta('1m')

# if time interval end is unspecified, fetch from event log as 
# if all events are atomic => the latest ocel:timestamp value of any event
# if all events are not atomic => the latest endtime value of any event
if int_end == '':
    if atomic_evs:
        int_end = events_df[event_timestamp_column].max()
    else:
        int_end = events_df[event_endtime_column].max()


#<-----------Remove in prod-----------
#add endtime column to events_df for testing. Each event gets a runtime ranging from it's start time 
# i.e. ocel:timestamp up to a month from the start time.
""" endtimes_hours = np.random.randint(0, 30, len(events_df)).astype('timedelta64[h]')
endtimes_minutes = np.random.randint(0, 300, len(events_df)).astype('timedelta64[m]')
events_df[event_endtime_column] = events_df[event_timestamp_column] + endtimes_hours + endtimes_minutes
ocel_extended_df[event_endtime_column] = events_df.merge(ocel_extended_df, on=event_id_column, how='inner')[event_endtime_column]
atomic_evs = False
objects_summary_df = update_object_lifecycle_end_for_non_atomic_events(objects_summary_df, event_to_object_relations_df,\
                                                                    events_df, event_endtime_column) """
#-----------Remove in prod----------->

#get time intervals given the sampling rate and total interval. The intervals represent the division of the total interval
#into time intervals of length equal to the sampling rate. Except the first and last time interval which may be smaller
#if outside the range of the total interval.
time_intervals = get_time_intervals(int_start, int_end, sampling_rate)

#get list of events and objects assigned to a time interval 
#if assign_mech = overlap then we get duplicate events/objects
#if assign_mech = contains then a lot of events/objects are usually discarded
#if assign_mech = starting or assign_mech = ending then we get the same number of events/objects as in the original ocel
#atomic events remain unaffected by assign_mech and are neither duplicated nor discarded.
events_to_time_df = get_events_to_time_df(events_df.copy(), time_intervals, assignment_mechanism, event_endtime_column, atomic_evs)
objects_to_time_df = get_objects_to_time_df(objects_summary_df.copy(), time_intervals, assignment_mechanism)


object_types_to_df_map = get_object_types_to_df_map(objects_df.copy(), object_changes_df.copy(), object_types)
event_types_to_df_map = get_event_types_to_df_map(events_df.copy(), event_types, atomic_evs, event_endtime_column)

event_object_count_df_map = get_event_object_count_df_map(ocel, event_types_to_df_map.copy())
object_type_summary_df_map = get_object_type_summary_df_map(objects_summary_df.copy(), object_types_to_df_map.copy())

#get preceding events df for performance perspective properties
preceding_events_df = get_preceding_events_df(ocel_extended_df, object_types, atomic_evs, event_endtime_column)

#get all properties of the event perspective
ep1_dict = ep1(event_types_to_df_map, events_to_time_df, sampling_rate)
ep2_dict = ep2(event_types_to_df_map, events_to_time_df, aggregation_mode, sampling_rate, atomic_evs, event_endtime_column)
ep3_dict = ep3(event_object_count_df_map, events_to_time_df, aggregation_mode, sampling_rate)
ep4_dict = ep4(event_object_combinations, event_object_count_df_map, events_to_time_df, aggregation_mode, sampling_rate)

#get all properties of the object perspective
op1_dict = op1(object_types_to_df_map, objects_to_time_df, sampling_rate)
op2_dict = op2(object_types_to_df_map, objects_to_time_df, aggregation_mode, sampling_rate)
op3_dict = op3(object_type_summary_df_map, objects_to_time_df, aggregation_mode, sampling_rate)
op4_dict = op4(event_to_object_relations_df_map, objects_to_time_df, aggregation_mode, sampling_rate)
op5_dict = op5(object_type_summary_df_map, objects_to_time_df, aggregation_mode, sampling_rate)
op6_dict = op6(object_interactions_df, events_to_time_df, aggregation_mode, sampling_rate)

#get all properties of the performance perspective
pp1_dict = pp1(preceding_events_df, event_types, events_to_time_df, aggregation_mode, sampling_rate)
pp2_dict = pp2(preceding_events_df, event_types, events_to_time_df, aggregation_mode, sampling_rate)
if atomic_evs:
    pp3_dict = {}
else:
    pp3_dict = pp3(event_types_to_df_map, events_to_time_df, aggregation_mode, sampling_rate, event_endtime_column)
pp4_dict = pp4(pp1_dict, preceding_events_df, event_types, event_endtime_column, atomic_evs, events_to_time_df,\
                aggregation_mode, sampling_rate)
pp5_dict = pp5(preceding_events_df, event_types, event_endtime_column, atomic_evs, events_to_time_df,\
                aggregation_mode, sampling_rate)
pp6_dict = pp6(preceding_events_df, event_object_combinations, events_to_time_df, aggregation_mode, sampling_rate)
pp7_dict = pp7(preceding_events_df, event_object_combinations, events_to_time_df, aggregation_mode, sampling_rate)

#get all properties of the resource perspective
rp1_dict = rp1(ep4_dict, resource_object_type)
rp2_dict = rp2(event_to_object_relations_df, events_to_time_df, resource_object_type, sampling_rate)
rp3_dict = rp3(op2_dict, resource_object_type)

#assign time series dicts to property ids
property_dicts_map = {'ep1': ep1_dict, 'ep2': ep2_dict, 'ep3': ep3_dict, 'ep4': ep4_dict ,\
                'op1': op1_dict, 'op2': op2_dict, 'op3': op3_dict, 'op4': op4_dict,\
                'op5': op5_dict, 'op6': op6_dict, 'pp1': pp1_dict, 'pp2': pp2_dict,\
                'pp3': pp3_dict, 'pp4': pp4_dict, 'pp5': pp5_dict, 'pp6': pp6_dict,\
                'pp7': pp7_dict, 'rp1': rp1_dict, 'rp2': rp2_dict, 'rp3': rp3_dict}

#assign property names to porperty ids
property_names_dict = {'ep1': 'Event Frequency',\
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
                    'rp3': 'Resrouce Attribute'}


TS_collection = {}
#process time series by padding on both ends with null values to represent missing values 
#then discard any time series with any null values (not only on the ends but anywhere) and assign remaining
#to a dict called 'TS_collection' which is then used ahead. 
#Plot all series being assigned to 'TS_collection'. Plots will be saved to 'backend/assets/plots'.
for property, property_dict in property_dicts_map.items():
    if property_dict:
        for non_temporal_parameters, ts in property_dict.items():
            if not ts.empty:
                #padding the timeseries on both ends to align with specified intervals.
                processed_ts = time_intervals.right.to_frame().merge(ts, left_index=True, right_index=True, how='left')\
                    .drop(columns=0).iloc[:,0]
                if not processed_ts.isna().any():
                    TS_collection[(property, non_temporal_parameters)] = processed_ts
                    if isinstance(non_temporal_parameters, tuple):
                        non_temporal_parameters = ', '.join(non_temporal_parameters)
                    ts_file_path = str(Path(f'backend/assets/timeseries/{property}_{non_temporal_parameters}.csv').resolve())
                    processed_ts.to_csv(ts_file_path)   
                    plot_file_path = str(Path(f'backend/assets/plots/{property}_{non_temporal_parameters}.png').resolve())
                    plot_series(processed_ts, title=f'{property_names_dict[property]} for inputs ({non_temporal_parameters})')
                    plt.savefig(plot_file_path, bbox_inches='tight', dpi = 200)
                    plt.close()

#constant time series i.e. where all time periods have the same value will not be considered for further analysis.
#so we discard all such time series and assign remaining to a dict 'ar_ts_collection'.
ar_ts_collection = {}
for tsid, ts in TS_collection.items():
    if not len(ts.unique()) == 1:
        ar_ts_collection[tsid] = ts

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
    max_seasonal_period = math.ceil(series_length/3)
if sampling_rate == 'ME':
    series_length = (int_end - int_start) / pd.Timedelta(30,'D')
    min_seasonal_period = 3
    max_seasonal_period = math.ceil(series_length/3)
if sampling_rate == 'QE':
    series_length = (int_end - int_start) / pd.Timedelta(90,'D')
    min_seasonal_period = 2
    max_seasonal_period = math.ceil(series_length/3)
if sampling_rate == 'YE':
    series_length = (int_end - int_start) / pd.Timedelta(365,'D')
    min_seasonal_period = 2
    max_seasonal_period = math.ceil(series_length/3)
if max_seasonal_period < min_seasonal_period:
    max_seasonal_period = min_seasonal_period

#perform time series analysis and save the results to a json file available in 'backend/assets/analysis_results'
if tsa_technique:
    ar_collection = time_series_analysis(ar_ts_collection, tsa_technique, min_seasonal_period, max_seasonal_period, sampling_rate, tsa_params)
    save_ar_to_json(ar_collection, tsa_technique)