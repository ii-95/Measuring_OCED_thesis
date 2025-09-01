import pm4py
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from pathlib import Path
from setup import *
from EP_measurable_properties import *

pd.options.mode.copy_on_write = True

# inputs provided by user (to be replaced with input from frontend)
path_to_ocel = Path('assets/logs/ocel2-p2p').resolve()
agg_mode = 'mean'
samp_rate = 'W'
assign_mech = 'starting'
res_obj = ''
#time_int_start = pd.Timestamp('2022-04-01 00:00:00+00:00')
#time_int_end = pd.Timestamp('2024-11-01 00:00:00+00:00')
time_int_start = ''
time_int_end = ''
end_time_evs = ''
endtime = 'endtime'

#We read the tables in the OCEL's sqlite format where feasible for quicker runtime and convert them to dataframes for further
#process using pandas.
#We switch to using pm4py's rendition of the OCEL and the variety of functions offered by PM4PY on OCEL when we deem it
#more suitable than directly using the db tables.

# connect to db i.e. the ocel in sql format
ocel_db_engine = create_engine(f'sqlite:///{path_to_ocel}.sqlite')
# get ocel as a pm4py object 
ocel_obj = pm4py.read_ocel2_json(f'{path_to_ocel}.json')

#setup essential tables(dataframes)
object_types_to_table_df_map = get_object_types_to_table_df_map(ocel_db_engine)
event_types_to_table_df_map = get_event_types_to_table_df_map(ocel_db_engine)
event_object_count_df_map = get_event_object_count_df_map(ocel_obj, event_types_to_table_df_map)
event_object_combinations = get_event_object_combinations(ocel_obj)
events_df = get_events_df(ocel_obj)
objects_df = get_objects_df(ocel_obj)


#check if all events in the log are atomic
if endtime in events_df.columns:
    atomic_evs = False
else:
    atomic_evs = True

# if time interval start is unspecified, fetch from event log as the earliest timestamp of an event
if time_int_start == '':
    time_int_start = events_df['ocel:timestamp'].min()
    #adjust start so that 1st event can be accounted for in further calculations
    time_int_start = time_int_start - pd.Timedelta('1m')

# if time interval end is unspecified, fetch from event log as 
# if all events are atomic => the latest ocel:timestamp value of any event
# if all events are not atomic => the latest endtime value of any event
if time_int_end == '':
    if atomic_evs:
        time_int_end = events_df['ocel:timestamp'].max()
    else:
        time_int_end = events_df[endtime].max()

#add endtime column to events_df for testing. Each event gets a runtime ranging from it's start time 
# i.e. ocel:timestamp up to a month from the start time.
events_df[endtime] = events_df['ocel:timestamp'].apply(lambda x: pd.to_datetime\
                                                       (np.random.randint(x.value//10**9, x.value//10**9 + 2592000), unit='s', utc=True))
#update time_int_end with test endtime max
time_int_end = events_df[endtime].max()

#get time intervals given the sampling rate and total interval
time_intervals = get_time_intervals(time_int_start, time_int_end, samp_rate)

#get a cross product of objects and events df with the time intervals
ti_cross_objs_df = get_time_intervals_cross_objects_df(objects_df, time_intervals)
ti_cross_evs_df = get_time_intervals_cross_events_df(events_df, time_intervals, endtime)

#get list of events and objects assigned to a time interval 
#if assign_mech = overlap then we get duplicate events/objects
#if assign_mech = contains then a lot of events/objects are usually discarded
#if assign_mech = starting or assign_mech = ending then we get the same number of events/objects as in the original ocel
#atomic events remain unaffected by assign_mech and are neither duplicated nor discarded.
events_to_time_df = get_events_to_time_df(events_df, time_intervals, 'overlaps', endtime)
objects_to_time_df = get_objects_to_time_df(objects_df, time_intervals, 'overlaps')

#get all properties of the event perspective
ep1_dict = ep1(event_types_to_table_df_map, events_to_time_df, samp_rate)
ep2_dict = ep2(event_types_to_table_df_map, events_to_time_df, agg_mode, samp_rate)
ep3_dict = ep3(event_object_count_df_map, events_to_time_df, agg_mode, samp_rate)
ep4_dict = ep4(event_object_combinations, event_object_count_df_map, events_to_time_df, agg_mode, samp_rate)

print(ep1_dict)
print(ep2_dict)
print(ep3_dict)
print(ep4_dict)
