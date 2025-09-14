import pm4py
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from pathlib import Path
from setup import *
from EP_measurable_properties import *
from OP_measurable_properties import *
from PP_measurable_properties import *
from dotenv import load_dotenv
import os
from sktime.utils.plotting import plot_series
import matplotlib.pyplot as plt
import math

pd.options.mode.copy_on_write = True

load_dotenv(dotenv_path="inputs.env")

# inputs provided by user (to be replaced with input from frontend)
path_to_ocel = Path(os.getenv('path_to_ocel')).resolve()
aggregation_mode = os.getenv('aggregation_mode')
sampling_rate = os.getenv('sampling_rate')
assignment_mechanism = os.getenv('assignment_mechanism')
#resource_object_type is the object type whose objects are to be trated as 
#resource objects for properties in the resource perspective.
resource_object_type = os.getenv('resource_object_type')
#endtime is the event attribute that is to be treated as the end time of non-atomic events
event_endtime_column = os.getenv('events_endtime_attribute')
#start and end of the time interval over which time series are to be constructed
int_start = os.getenv('time_series_interval_start')
int_end = os.getenv('time_series_interval_end')

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

#update int_end with test endtime maximum
int_end = events_df[event_endtime_column].max()
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
preceding_events_df = get_preceding_events_df(event_to_object_relations_df.copy(), events_df.copy(), atomic_evs, event_endtime_column)
preceding_events_by_object_type_df = get_preceding_events_by_object_type_df\
                                        (event_to_object_relations_df.copy(), events_df.copy(), atomic_evs, event_endtime_column)

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
pp4_dict = pp4(pp1_dict, pp3_dict, event_types, atomic_evs)
pp5_dict = pp5(pp2_dict, pp4_dict, event_types)
pp6_dict = pp6(preceding_events_by_object_type_df, event_object_combinations, events_to_time_df, aggregation_mode, sampling_rate)
pp7_dict = pp7_dict = pp7(preceding_events_df, preceding_events_by_object_type_df, event_object_combinations, events_to_time_df, \
                atomic_evs, event_endtime_column, aggregation_mode, sampling_rate)

property_dicts_map = {'ep1': ep1_dict, 'ep2': ep2_dict, 'ep3': ep3_dict, 'ep4': ep4_dict ,\
                'op1': op1_dict, 'op2': op2_dict, 'op3': op3_dict, 'op4': op4_dict,\
                'op5': op5_dict, 'op6': op6_dict, 'pp1': pp1_dict, 'pp2': pp2_dict,\
                'pp3': pp3_dict, 'pp4': pp4_dict, 'pp5': pp5_dict, 'pp6': pp6_dict,\
                'pp7': pp7_dict}

property_names_dict = {'ep1': 'Event Frequency', 'ep2': 'Event Attribute', \
                    'ep3': 'Number of Objects per Event', \
                    'ep4': 'Number of Objects of a type per Event' , \
                    'op1': 'Object Frequency', 'op2': 'Object Attribute', \
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
                    'pp7': 'Lagging Time(Hours)'}

#process time series and plot
for property, property_dict in property_dicts_map.items():
    if property_dict:
        for non_temporal_parameters, ts in property_dict.items():
            if not ts.empty:
                #padding the timeseries on both ends to align with specified intervals.
                #filling padded intervals as well as interval which had missing values before padding
                #due to oversampling in case of a large sampling rate (time period).
                processed_ts = time_intervals.right.to_frame().merge(ts,\
                            left_index=True, right_index=True, how='left').fillna(0).drop(columns=0)
                #if the length of the last interval is less than sampling rate then copy it's value
                #from the original ts as it will not be included in the merge
                if ts.index[-1] > processed_ts.index[-1]:
                    processed_ts.iloc[-1] = ts.iloc[-1]
                if isinstance(non_temporal_parameters, tuple):
                    non_temporal_parameters = ', '.join(non_temporal_parameters   )
                plot_series(processed_ts, title=f'{property_names_dict[property]} for inputs: ({non_temporal_parameters}) with assignment_mechanism = {assignment_mechanism}')
                plot_file_path = str(Path(f'backend/assets/plots/{property}_{non_temporal_parameters}.png').resolve())
                plt.savefig(plot_file_path, bbox_inches='tight', dpi = 600)
                plt.close()