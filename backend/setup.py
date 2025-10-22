import pm4py
import pandas as pd
import numpy as np
import pandas as pd
from pandas.api.types import is_any_real_numeric_dtype
import itertools
import json
from pathlib import Path
import os
from sktime.utils.plotting import plot_series
import matplotlib.pyplot as plt
import rustworkx as rx
from rustworkx.visualization import graphviz_draw
import graphviz
import plotly.express as px
import streamlit as st

def agg(series, aggregation_mode, sampling_rate):
    if type(series) == pd.Series:
        if aggregation_mode == 'mean':
            return series.resample(sampling_rate).mean()
        elif aggregation_mode == 'sum':
            return series.resample(sampling_rate).sum()
        elif aggregation_mode == 'min':
            return series.resample(sampling_rate).min()
        elif aggregation_mode == 'max':
            return series.resample(sampling_rate).max()
        
def get_events_df(ocel):
    events_df = ocel.events
    return events_df

def get_event_to_object_relations_df(ocel):
    event_to_object_relations_df = ocel.relations
    return event_to_object_relations_df

def get_objects_df(ocel):
    objects_df = ocel.objects
    return objects_df

def get_objects_summary_df(ocel):
    object_summary_df = pm4py.ocel_objects_summary(ocel)
    return object_summary_df

def get_object_changes_df(ocel):
    object_changes_df = ocel.object_changes
    return object_changes_df

def get_object_interactions_df(ocel):
    object_interactions_df = pm4py.ocel.ocel_objects_interactions_summary(ocel)
    return object_interactions_df

def get_ocel_extended_df(ocel):
    ocel_extended_df = ocel.get_extended_table()
    return ocel_extended_df

def get_o2o_df(ocel):
    o2o_df = ocel.o2o
    return o2o_df

#if non-atomic events exist in the log, then fill in endtimes for any possible atomic events 
# in the log (those with null/empty values in endtine column) with their starting time.
def adjust_events_end_time(events_df, event_endtime_column, event_timestamp_column = 'ocel:timestamp'):
    #replaces all null and empty values with pd.NaT
    events_df[event_endtime_column] = pd.to_datetime(events_df[event_endtime_column], utc = True)
    #replaces all pd.NaT values with value in ocel:timestamp column
    events_df.loc[events_df[event_endtime_column].isnull(), event_endtime_column] = events_df[event_timestamp_column]
    return events_df

#returns a dictionary that maps each event type to a dataframe containing all events of those types along with
#timestamps and numerical attributes
def get_event_types_to_df_map(events_df, event_types, atomic_evs, event_endtime_column, event_id_column = 'ocel:eid',\
                                    event_timestamp_column = 'ocel:timestamp', event_type_column = 'ocel:activity'):

    event_types_to_df_map = {}
    #<-----------Remove in prod----------->
    #dummy attribute for testing
    #events_df['test_attribute'] = np.random.randint(1, 100, events_df.shape[0])
    #<------------------------------------>
    if atomic_evs:
        event_attributes = list(set(events_df.columns.values) \
                                - set([event_id_column, event_timestamp_column, event_type_column]))
    else:
        event_attributes = list(set(events_df.columns.values) \
                                - set([event_id_column, event_timestamp_column, event_type_column, event_endtime_column]))
    non_numerical_attributes = []
    for event_attribute in event_attributes:
        #check if event attribute is not numerical, then add to list of non-numerical attributes
        if not is_any_real_numeric_dtype(events_df[event_attribute]):
            non_numerical_attributes.append(event_attribute)
    #remove all non-numerical attributes
    if non_numerical_attributes:
        events_df = events_df.drop(non_numerical_attributes, axis=1)
    for event_type in event_types:
        #get rows for events of event_type
        event_type_df = events_df[events_df[event_type_column] == event_type]
        #drop attribute columns that don't belong to the event type i.e., null for all events of the type
        event_type_df = event_type_df.dropna(axis=1, how='all')
        #remove event type column
        event_type_df = event_type_df.drop(event_type_column, axis=1)
        event_types_to_df_map[event_type] = event_type_df
    return event_types_to_df_map

#returns a dictionary that  maps each object type to a dataframe containing all objects of those types along with
#timestamps and numerical attributes
def get_object_types_to_df_map(objects_df, object_changes_df, object_types, object_id_column = 'ocel:oid',\
                               timestamp_column = 'ocel:timestamp', object_type_column = 'ocel:type',\
                                changed_field_column = 'ocel:field'):
     
    if '@@cumcount' in object_changes_df.columns:
        object_changes_df = object_changes_df.drop('@@cumcount', axis = 1)
        object_changes_df
    objects_df['ocel:timestamp'] = pd.to_datetime('1970-01-01T00:00:00.000Z')
    objects_df['ocel:field'] = None

    objects_df = pd.concat([objects_df,object_changes_df])

    object_types_to_df_map = {}
    
    object_attributes = list(set(objects_df.columns.values) \
                            - set([object_id_column, timestamp_column, object_type_column, changed_field_column]))
    non_numerical_attributes = []
    for object_attribute in object_attributes:
        #check if object attribute is not numerical, then add to list of non-numerical attributes
        if not is_any_real_numeric_dtype(objects_df[object_attribute]):
            non_numerical_attributes.append(object_attribute)
    #remove all non-numerical attributes
    if non_numerical_attributes:
        objects_df = objects_df.drop(non_numerical_attributes, axis=1)
    for object_type in object_types:
        #get rows for objects of object_type
        object_type_df = objects_df[objects_df[object_type_column] == object_type]
        #drop attribute columns that don't belong to the object type i.e., null for all objects of the type
        tmp = object_type_df[object_type_df.columns.difference([changed_field_column])].isna().all()
        object_type_df = object_type_df.drop(tmp.index[tmp], axis=1)
        #remove object type column
        object_type_df = object_type_df.drop(object_type_column, axis=1)
        object_types_to_df_map[object_type] = object_type_df
    return object_types_to_df_map



# returns a dictionary mapping each event type to a dataframe containing the number of objects of each object type 
# per event of the specified event type
def get_event_object_count_df_map(ocel, event_types_to_df_map, event_id_column = 'ocel:eid',\
                                    event_timestamp_column = 'ocel:timestamp'):
    event_object_count_df = pd.DataFrame.from_dict(pm4py.ocel_objects_ot_count(ocel)).transpose()
    event_object_count_df.index.name = event_id_column
    event_object_count_df = event_object_count_df.reset_index()
    event_object_count_df = event_object_count_df.replace(np.nan, 0)
    event_object_count_df_map = {}

    for event_type, event_type_df in event_types_to_df_map.items():
        event_object_count_df_map[event_type] = event_type_df.merge(event_object_count_df, on=event_id_column, how='inner')
    return event_object_count_df_map

# returns a dictionary mapping each object type to a dataframe containing the rows of 'object_summary_df' for objects
# of that type
def get_object_type_summary_df_map(objects_summary_df, object_types_to_df_map, object_id_column = 'ocel:oid'):
    object_type_summary_df_map = {}
    for object_type, object_type_df in object_types_to_df_map.items():
        object_type_summary_df_map[object_type] = objects_summary_df.merge(object_type_df, on=object_id_column, \
                                                        how='inner', suffixes=('_2', None))
    return object_type_summary_df_map

# get all existing combinations of event types and object types in the ocel
# returns an array of  lists where each list is a combination => [object type, event type] that occurs in the log
def get_event_object_combinations(ocel, event_type_column='ocel:eid', object_type_column='ocel:oid'):
    event_object_combinations = pm4py.ocel_objects_interactions_summary(ocel)[[event_type_column, object_type_column]]\
                                .drop_duplicates().values
    return event_object_combinations

# returns a dictionary mapping each combination of an event type and object type (that exists in the log) to
# a dataframe containing rows of 'event_object_relations_df' i.e. pm4py.ocel.relations df where ocel:type is equal to
# the specified object type and ocel:activity is equal to specified event type 
def get_event_to_object_type_relations_df_map(event_to_object_relations_df, event_object_combinations):
    event_to_object_relations_df_map = {}
    for (event_type, object_type) in event_object_combinations:
        event_to_object_relations_df_map[((event_type, object_type))] = event_to_object_relations_df[
                                                                (event_to_object_relations_df['ocel:type']==object_type) \
                                                            & (event_to_object_relations_df['ocel:activity'] == event_type)]
    return event_to_object_relations_df_map

# returns a dataframe with a row for each event 'e' containing all it's preceding events i.e. events that: 
# - Occur (or end if non-atomic events) before in time compared to e
# - Have atleast one related object (of each object type, excluding each object type, including all object types) 
#   in common with 'e' that is not shared by another event (that is not e)
#   that occurs (or ends if non-atomic events) after it but before e.
# also includes timestamps for these events in an ordered list (from the latest to earliest)
# columns with name ending in 'alltypes' contain information irrespective of object type, columns with name ending
# in an object type contain information only with respect to that object type, whereas columns with name ending in
# excluding_{object_type} contain information with respect to all types excluding that object type.


# Note: The function is not easy to read as it copies many columns of a dataframe into separate lists/arrays and manipulates
# them so it's difficult to follow but it does so to achieve a much better performance level as compared to code that 
# would have been more readable i.e. apply functions and similar. 
# Using pandas vectorization was not applicable/possible in this scenario.
@st.cache_data
def get_preceding_events_df(_ocel_extended_df, object_types, atomic_evs, event_endtime_column,\
                            event_id_column ='ocel:eid', event_timestamp_column = 'ocel:timestamp',\
                            object_type_column = 'ocel:type'):
    preceding_events_df = _ocel_extended_df.copy()
    object_cols = [col for col in preceding_events_df.columns if object_type_column in col]
    df = preceding_events_df[object_cols]
    df = df.map(lambda d: d if isinstance(d, list) else [])
    preceding_events_df[object_cols] = df
    objects_2d_list = df.values.tolist()
    column_list = list()
    for x in objects_2d_list:
        column_list.append(list(itertools.chain.from_iterable(x)))
    preceding_events_df['ocel:type'] = column_list

    if atomic_evs:
        preceding_events_df = preceding_events_df.sort_values(by=event_timestamp_column, ignore_index=True)
        event_id_arr = preceding_events_df[event_id_column].values.tolist()
        event_timestamp_arr = preceding_events_df[event_timestamp_column].values.tolist()
        related_objects_alltypes_arr = preceding_events_df[object_type_column].values.tolist()
        related_objects_by_type_arr_dict = {}
        preceding_events_alltypes_arr = [None] * len(preceding_events_df)
        preceding_events_time_alltypes_arr = [None] * len(preceding_events_df)
        preceding_events_by_type_arr_dict = {}
        preceding_events_time_by_type_arr_dict = {}
        preceding_events_excluding_type_arr_dict = {}
        preceding_events_time_excluding_type_arr_dict = {}
        for object_type in object_types:
            preceding_events_by_type_arr_dict[object_type] = [None] * len(preceding_events_df)
            preceding_events_time_by_type_arr_dict[object_type] = [None] * len(preceding_events_df)
            preceding_events_excluding_type_arr_dict[object_type] = [None] * len(preceding_events_df)
            preceding_events_time_excluding_type_arr_dict[object_type] = [None] * len(preceding_events_df)
            related_objects_by_type_arr_dict[object_type] = preceding_events_df[f'{object_type_column}:{object_type}'].values

        for i in range(0, len(preceding_events_df)):
            related_objects_alltypes = set(related_objects_alltypes_arr[i])
            if not related_objects_alltypes:
                continue
            related_objects_by_type_dict = {object_type: [None] * len(preceding_events_df) for object_type in object_types}
            preceding_events_alltypes_arr[i] = []
            preceding_events_time_alltypes_arr[i] = []
            for object_type in object_types:
                related_objects_by_type_dict[object_type] = set(related_objects_by_type_arr_dict[object_type][i])
                preceding_events_by_type_arr_dict[object_type][i] = []
                preceding_events_time_by_type_arr_dict[object_type][i] = []
                preceding_events_excluding_type_arr_dict[object_type][i] = []
                preceding_events_time_excluding_type_arr_dict[object_type][i] = []
            for j in range(i-1, -1, -1):
                if not related_objects_alltypes:
                    break
                common_objects_alltypes = related_objects_alltypes.intersection(set(related_objects_alltypes_arr[j]))
                if common_objects_alltypes:
                    preceding_events_alltypes_arr[i].append(event_id_arr[j])
                    preceding_events_time_alltypes_arr[i].append(event_timestamp_arr[j])
                    for object_type in object_types:
                        common_objects_by_type = related_objects_by_type_dict[object_type].intersection(common_objects_alltypes)
                        if common_objects_by_type:
                            preceding_events_by_type_arr_dict[object_type][i].append(event_id_arr[j])
                            preceding_events_time_by_type_arr_dict[object_type][i].append(event_timestamp_arr[j])
                        else:
                            preceding_events_excluding_type_arr_dict[object_type][i].append(event_id_arr[j])
                            preceding_events_time_excluding_type_arr_dict[object_type][i].append(event_timestamp_arr[j])
                    related_objects_alltypes = related_objects_alltypes - common_objects_alltypes

        preceding_events_df['preceding_events_alltypes'] = preceding_events_alltypes_arr
        preceding_events_df['preceding_events_time_alltypes'] = preceding_events_time_alltypes_arr
        for object_type in object_types:
            preceding_events_df[f'preceding_events_{object_type}'] = preceding_events_by_type_arr_dict[object_type]
            preceding_events_df[f'preceding_events_time_{object_type}'] = preceding_events_time_by_type_arr_dict[object_type]
            preceding_events_df[f'preceding_events_excluding_{object_type}'] = preceding_events_excluding_type_arr_dict[object_type]
            preceding_events_df[f'preceding_events_time_excluding_{object_type}'] = preceding_events_time_excluding_type_arr_dict[object_type]
    else:
        preceding_events_df = preceding_events_df.sort_values(by=[event_endtime_column, event_timestamp_column], ignore_index=True)
        event_id_arr = preceding_events_df[event_id_column].values.tolist()
        event_starttime_arr = preceding_events_df[event_timestamp_column].values.tolist()
        event_endtime_arr = preceding_events_df[event_endtime_column].values.tolist()
        related_objects_alltypes_arr = preceding_events_df[object_type_column].values.tolist()
        related_objects_by_type_arr_dict = {}
        preceding_events_alltypes_arr = [None] * len(preceding_events_df)
        preceding_events_endtime_alltypes_arr = [None] * len(preceding_events_df)
        preceding_events_by_type_arr_dict = {}
        preceding_events_excluding_type_arr_dict = {}
        preceding_events_endtime_by_type_arr_dict = {}
        preceding_events_endtime_excluding_type_arr_dict = {}
        for object_type in object_types:
            preceding_events_by_type_arr_dict[object_type] = [None] * len(preceding_events_df)
            preceding_events_excluding_type_arr_dict[object_type] = [None] * len(preceding_events_df)
            preceding_events_endtime_by_type_arr_dict[object_type] = [None] * len(preceding_events_df)
            preceding_events_endtime_excluding_type_arr_dict[object_type] = [None] * len(preceding_events_df)
            related_objects_by_type_arr_dict[object_type] = preceding_events_df[f'{object_type_column}:{object_type}'].values

        for i in range(0, len(preceding_events_df)):
            related_objects_alltypes = set(related_objects_alltypes_arr[i])
            event_starttime = event_starttime_arr[i]
            if not related_objects_alltypes:
                continue
            related_objects_by_type_dict = {object_type: [None] * len(preceding_events_df) for object_type in object_types}
            preceding_events_alltypes_arr[i] = []
            preceding_events_endtime_alltypes_arr[i] = []
            for object_type in object_types:
                related_objects_by_type_dict[object_type] = set(related_objects_by_type_arr_dict[object_type][i])
                preceding_events_by_type_arr_dict[object_type][i] = []
                preceding_events_endtime_by_type_arr_dict[object_type][i] = []
                preceding_events_excluding_type_arr_dict[object_type][i] = []
                preceding_events_endtime_excluding_type_arr_dict[object_type][i] = []
            for j in range(i-1, -1, -1):
                if not related_objects_alltypes:
                    break
                if event_starttime < event_endtime_arr[j]:
                    continue
                common_objects_alltypes = related_objects_alltypes.intersection(set(related_objects_alltypes_arr[j]))
                if common_objects_alltypes:
                    preceding_events_alltypes_arr[i].append(event_id_arr[j])
                    preceding_events_endtime_alltypes_arr[i].append(event_endtime_arr[j])
                    
                    for object_type in object_types:
                        common_objects_by_type = related_objects_by_type_dict[object_type].intersection(common_objects_alltypes)
                        if common_objects_by_type:
                            preceding_events_by_type_arr_dict[object_type][i].append(event_id_arr[j])
                            preceding_events_endtime_by_type_arr_dict[object_type][i].append(event_endtime_arr[j])
                        else:
                            preceding_events_excluding_type_arr_dict[object_type][i].append(event_id_arr[j])
                            preceding_events_endtime_excluding_type_arr_dict[object_type][i].append(event_endtime_arr[j])
                            
                    related_objects_alltypes = related_objects_alltypes - common_objects_alltypes


        preceding_events_df['preceding_events_alltypes'] = preceding_events_alltypes_arr
        preceding_events_df['preceding_events_time_alltypes'] = preceding_events_endtime_alltypes_arr
        for object_type in object_types:
            preceding_events_df[f'preceding_events_{object_type}'] = preceding_events_by_type_arr_dict[object_type]
            preceding_events_df[f'preceding_events_time_{object_type}'] = preceding_events_endtime_by_type_arr_dict[object_type]
            preceding_events_df[f'preceding_events_excluding_{object_type}'] = preceding_events_excluding_type_arr_dict[object_type]
            preceding_events_df[f'preceding_events_time_excluding_{object_type}'] = preceding_events_endtime_excluding_type_arr_dict[object_type]
    return preceding_events_df

def get_offset_for_sampling_rate(sampling_rate):
    if sampling_rate == 'W':
        offset = pd.tseries.offsets.Week(weekday=6, normalize=True)
    elif sampling_rate == 'ME':
        offset = pd.tseries.offsets.MonthEnd(0, normalize=True)
    elif sampling_rate == 'QE':
        offset = pd.tseries.offsets.QuarterEnd(0, normalize=True)
    elif sampling_rate == 'YE':
        offset = pd.tseries.offsets.YearEnd(0, normalize=True)
    return offset
#get list of time intervals according to the specified time interval and sampling rate
def get_time_intervals(start_time, end_time, sampling_rate, offset):
    start = (start_time - offset).normalize()
    end = (end_time + offset).normalize()
    time_intervals = pd.interval_range(start, end, freq=sampling_rate)
    #time_intervals = list(pd.interval_range(start, end, freq=sampling_rate))
    #correct start of first interval
    #time_intervals[0] = pd.Interval(start_time, time_intervals[0].right, closed='right')
    #correct end of last interval
    #time_intervals[-1] = pd.Interval(time_intervals[-1].left, end_time, closed='right')
    #time_intervals = pd.IntervalIndex(time_intervals)
    return time_intervals

#a cross join of time intervals_df and objects_summary_df
def get_time_intervals_cross_objects_summary_df(objects_summary_df, time_intervals, object_id_column='ocel:oid'):
    
    #Create a dataframe containing the time interval range
    time_interval_df = pd.DataFrame(data = {'time_interval_left' : time_intervals.left, 'time_interval_right': time_intervals.right})

    #get a cross product of relevant columns of the log with the time interval df
    objects_summary_df = objects_summary_df[[object_id_column,'lifecycle_start', 'lifecycle_end']]\
                .sort_values(by=['lifecycle_start','lifecycle_end'])
    cross_df = objects_summary_df.merge(time_interval_df, how='cross')
    return cross_df

#a cross join of time intervals_df and events_df
def get_time_intervals_cross_events_df(events_df, time_intervals, event_endtime_column, event_id_column='ocel:eid', \
                                       event_timestamp_column='ocel:timestamp'):
    #Create a dataframe containing the time interval range
    time_interval_df = pd.DataFrame(data = {'time_interval_left' : time_intervals.left, 'time_interval_right': time_intervals.right})

    #get a cross product of relevant columns of the log with the time interval df
    events_df = events_df[[event_id_column, event_timestamp_column, event_endtime_column]]\
                .sort_values(by=[event_timestamp_column, event_endtime_column])
    cross_df = events_df.merge(time_interval_df, how='cross')
    return cross_df

def update_object_lifecycle_end_for_non_atomic_events(objects_summary_df,event_to_object_relations_df, events_df,\
                                                    event_endtime_column, event_id_column='ocel:eid',\
                                                    object_id_column='ocel:oid'):
    #get all unique object-to-relations
    e2o_df = event_to_object_relations_df[[object_id_column, event_id_column]].drop_duplicates()
    #get endtimes for all related events
    e2o_df = e2o_df.merge(events_df[[event_id_column, event_endtime_column]], on=event_id_column)
    #get maximum end time for each object. This is the lifecycle end time.
    object_lifecycle_end_df = e2o_df[[object_id_column, event_endtime_column]].groupby(object_id_column).max()
    object_lifecycle_end_df = object_lifecycle_end_df.rename\
                                (columns={event_endtime_column:'lifecycle_end'})
    objects_summary_df = objects_summary_df.drop(columns=['lifecycle_end'])
    objects_summary_df = object_lifecycle_end_df.merge(objects_summary_df, on= object_id_column)
    objects_summary_df = update_object_lifecycle_duration_for_non_atomic_events(objects_summary_df)
    return objects_summary_df

def update_object_lifecycle_duration_for_non_atomic_events(objects_summary_df):
    objects_summary_df['lifecycle_duration'] = objects_summary_df['lifecycle_end'] - objects_summary_df['lifecycle_start']
    objects_summary_df['lifecycle_duration'] = objects_summary_df['lifecycle_duration'].dt.total_seconds()
    return objects_summary_df

#returns a dataframe with rows for only those objects that are contained in some interval
def get_contained_objects(ti_cross_objs_df, object_id_column='ocel:oid'):

    #Match object lifecycles with time intervals to check containment. 
    #Note that the intervals are consider to left open and right closed
    ti_cross_objs_df.loc[(ti_cross_objs_df['lifecycle_start'] > ti_cross_objs_df['time_interval_left']) \
                        & (ti_cross_objs_df['lifecycle_end'] <= ti_cross_objs_df['time_interval_right']), \
                            'contains'] = 1
    
    #Drop all rows where containment in an interval is not found
    ti_cross_objs_df = ti_cross_objs_df.dropna(subset=['contains'])

    #Keep only usable columns.
    ti_cross_objs_df = ti_cross_objs_df[[object_id_column, 'lifecycle_start', 'lifecycle_end']]
    return ti_cross_objs_df

#returns a dataframe with rows for each time an object overlaps with some interval
def get_overlapping_objects(ti_cross_objs_df, object_id_column='ocel:oid'):

    #Match object lifecycles with time intervals to check overlap. 
    #An object must overlap with atleast one interval and may overlap with more than one interval.
    #Note that the intervals are consider to left open and right closed
    ti_cross_objs_df.loc[(ti_cross_objs_df['lifecycle_start'] <= ti_cross_objs_df['time_interval_right']) \
                        & (ti_cross_objs_df['lifecycle_end'] > ti_cross_objs_df['time_interval_left']), \
                            'overlaps'] = 1
    
    #Drop all rows where overlap with an interval is not found.
    ti_cross_objs_df = ti_cross_objs_df.dropna(subset=['overlaps'])

    #Keep only usable columns.
    #We pass time_interval_right as this will be the timestamp used for time series aggregation as an object may
    #overlap with more than time interval. Hence it's own lifecyle start or end timestamp is insufficient
    #for aggregation.
    ti_cross_objs_df = ti_cross_objs_df[[object_id_column, 'lifecycle_start', 'lifecycle_end', 'time_interval_right']]
    
    return ti_cross_objs_df

#returns a dataframe with rows for only those events that are contained in some interval
def get_contained_events(ti_cross_evs_df, event_endtime_column, event_id_column='ocel:eid',\
                          event_timestamp_column='ocel:timestamp'):
    
    #Match event start and end with time intervals to check containment. 
    # The intervals are treated as left open and right closed.
    ti_cross_evs_df.loc[(ti_cross_evs_df[event_timestamp_column] > ti_cross_evs_df['time_interval_left']) \
                        & (ti_cross_evs_df[event_endtime_column] <= ti_cross_evs_df['time_interval_right']), \
                            'contains'] = 1
        
    #Drop all rows where containment in an interval is not found
    ti_cross_evs_df = ti_cross_evs_df.dropna(subset=['contains'])
    
    #Keep only usable columns
    ti_cross_evs_df = ti_cross_evs_df[[event_id_column, event_timestamp_column, event_endtime_column]]

    return ti_cross_evs_df

#returns a dataframe with rows for each time an event overlaps with some interval
def get_overlapping_events(ti_cross_evs_df, event_endtime_column, event_id_column='ocel:eid',\
                            event_timestamp_column='ocel:timestamp'):
    
    #Match event start and end with time intervals to check overlap. An event must overlap with atleast one interval and
    #may overlap with more than one interval.
    ti_cross_evs_df.loc[(ti_cross_evs_df[event_timestamp_column] <= ti_cross_evs_df['time_interval_right']) \
                        & (ti_cross_evs_df[event_endtime_column] > ti_cross_evs_df['time_interval_left']), \
                            'overlaps'] = 1
    
    #Drop all rows where overlap with an interval is not found
    ti_cross_evs_df = ti_cross_evs_df.dropna(subset=['overlaps'])

    #Keep only usable columns
    #We pass time_interval_right as this will be the timestamp used for time series aggregation as a (non-atomic) event may
    #overlap with more than time interval. Hence it's own timestamp (whether starting or ending) is insufficient
    #for aggregation.
    ti_cross_evs_df = ti_cross_evs_df[[event_id_column, event_timestamp_column, event_endtime_column, 'time_interval_right']]
    
    return ti_cross_evs_df

#returns a dataframe with a column for objects and another for a timestamp representing the assigned interval. 
# The choice of the timestamp is different for each assignment mechanism such that it it suitable for resampling/aggregation
# at the time series level. 
def get_objects_to_time_df(objects_summary_df, time_intervals, assignment_mechanism, object_id_column='ocel:oid'):
    
    ti_cross_objs_df = get_time_intervals_cross_objects_summary_df(objects_summary_df, time_intervals)

    if assignment_mechanism == 'starting':
        objs_to_time_df = objects_summary_df[[object_id_column, 'lifecycle_start']]
        objs_to_time_df = objs_to_time_df\
            .rename(columns={'lifecycle_start': 'assignment_mechanism_time'})

    elif assignment_mechanism == 'ending':
        objs_to_time_df = objects_summary_df[[object_id_column, 'lifecycle_end']]
        objs_to_time_df = objs_to_time_df\
            .rename(columns={'lifecycle_end': 'assignment_mechanism_time'})

    elif assignment_mechanism == 'contains':
        objs_to_time_df = get_contained_objects(ti_cross_objs_df)
        objs_to_time_df = objs_to_time_df[[object_id_column, 'lifecycle_end']]
        objs_to_time_df = objs_to_time_df\
            .rename(columns={'lifecycle_end': 'assignment_mechanism_time'})

    elif assignment_mechanism == 'overlaps':
        objs_to_time_df = get_overlapping_objects(ti_cross_objs_df)
        objs_to_time_df = objs_to_time_df[[object_id_column, 'time_interval_right']]
        objs_to_time_df['time_interval_right'] = objs_to_time_df['time_interval_right']
        objs_to_time_df = objs_to_time_df\
            .rename(columns={'time_interval_right': 'assignment_mechanism_time'})

    else:
        raise ValueError('Invalid assignment mechasism selection')
    
    return objs_to_time_df

def get_events_to_time_df(events_df, time_intervals, assignment_mechanism, event_endtime_column, atomic_evs, \
                        event_id_column='ocel:eid', event_timestamp_column='ocel:timestamp'):
    #if all events are atomic then assignment mechanism has no effect on the assignment of events
    #to time periods/intervals and we can return a dataframe of events and their timestamps
    if atomic_evs:
        evs_to_time_df = events_df[[event_id_column, event_timestamp_column]]
        evs_to_time_df = evs_to_time_df[(evs_to_time_df[event_timestamp_column] > time_intervals[0].left) \
            & (evs_to_time_df[event_timestamp_column] <= time_intervals[-1].right)]
        evs_to_time_df = evs_to_time_df.rename(columns={event_timestamp_column: 'assignment_mechanism_time'})
    else:
        #if all events are not atomic then we need to use the respective strategy for assigning
        #events to time periods/intervals as per the selected assignment mechanism
        ti_cross_evs_df = get_time_intervals_cross_events_df(events_df, time_intervals, event_endtime_column)

        if assignment_mechanism == 'starting':
            evs_to_time_df = events_df[[event_id_column, event_timestamp_column]]
            evs_to_time_df = evs_to_time_df.rename(columns={event_timestamp_column: 'assignment_mechanism_time'})

        elif assignment_mechanism == 'ending':
            evs_to_time_df = events_df[[event_id_column, event_endtime_column]]
            evs_to_time_df = evs_to_time_df.rename(columns={event_endtime_column: 'assignment_mechanism_time'})

        elif assignment_mechanism == 'contains':
            evs_to_time_df = get_contained_events(ti_cross_evs_df, event_endtime_column)
            evs_to_time_df = evs_to_time_df[[event_id_column, event_endtime_column]]
            evs_to_time_df = evs_to_time_df.rename(columns={event_endtime_column: 'assignment_mechanism_time'})

        elif assignment_mechanism == 'overlaps':
            evs_to_time_df = get_overlapping_events(ti_cross_evs_df, event_endtime_column)
            evs_to_time_df = evs_to_time_df[[event_id_column, 'time_interval_right']]
            evs_to_time_df['time_interval_right'] = evs_to_time_df['time_interval_right']
            evs_to_time_df = evs_to_time_df.rename(columns={'time_interval_right': 'assignment_mechanism_time'})

        else:
            raise ValueError('Invalid assignment mechasism selection')
    
    return evs_to_time_df

def create_plots_for_ts_collection(ts_collection, property_names_dict):
    for tsid, ts in ts_collection.items():
        property_id = tsid[0].replace('\"','').replace("{", '_').replace('}', '_').replace(':','_')
        if property_id in property_names_dict.keys():
            property_name = property_names_dict[property_id]
        else:
            property_name = ''
        non_temporal_parameters = tsid[1]
        if isinstance(non_temporal_parameters, tuple):
            non_temporal_parameters = ', '.join(non_temporal_parameters)
        chart = px.line(ts, color_discrete_sequence=['blue']).update_layout(xaxis_title='time', yaxis_title=None, showlegend=False)
        with st.container(border=True):
            st.markdown(f'{property_name} ({property_id}), parameters: ({non_temporal_parameters})')
            st.plotly_chart(chart, key=tsid)


def remap_keys(mapping):
    return [{'tsid':k, 'ar': v} for k, v in mapping.items()]

def save_ar_to_json(ar_collection, technique_name):
    ar_file_path = str(Path(f'backend/assets/analysis_results/{technique_name}.json').resolve())
    if technique_name in ['Change Point Detection', 'Forecasting', 'Threshold Based Point Detection']:
        if technique_name == 'Forecasting':
            processed_ar_collection = {}
            for tsid, ar in ar_collection.items():
                ar_series = ar.copy()
                ar_series.index = ar_series.index.map(lambda x: x.isoformat().replace("+00:00", ".000Z"))
                ar_series = ar_series.to_dict()
                processed_ar_collection[tsid] = ar_series
        else:
            processed_ar_collection = ar_collection

        with open(ar_file_path, 'w', encoding='utf-8') as f:
            json.dump(remap_keys(processed_ar_collection), f, indent=4, ensure_ascii=False)

    elif technique_name == 'Granger Causality':
        df = pd.DataFrame(ar_collection[['caused']].values.tolist()).rename(columns = {0 : 'tsid' })
        df['ar'] = ar_collection[['causing','lag']].values.tolist()
        df = df.groupby('tsid').agg(list).reset_index()
        df.to_json(ar_file_path, orient='records', indent=4, force_ascii= False)
    return ar_file_path

def convert_ar_to_json(ar_collection, technique_name):
    if technique_name in ['Change Point Detection', 'Forecasting', 'Threshold Based Point Detection']:
        if technique_name == 'Forecasting':
            processed_ar_collection = {}
            for tsid, ar in ar_collection.items():
                ar_series = ar.copy()
                ar_series.index = ar_series.index.map(lambda x: x.isoformat().replace("+00:00", ".000Z"))
                ar_series = ar_series.to_dict()
                processed_ar_collection[tsid] = ar_series
        else:
            processed_ar_collection = ar_collection
        
        json_ar_collection = json.dumps(remap_keys(processed_ar_collection), indent=4, ensure_ascii=False)

    elif technique_name == 'Granger Causality':
        df = pd.DataFrame(ar_collection[['caused']].values.tolist()).rename(columns = {0 : 'tsid' })
        df['ar'] = ar_collection[['causing','lag']].values.tolist()
        df = df.groupby('tsid').agg(list).reset_index()
        json_ar_collection = df.to_json(orient='records', indent=4, force_ascii= False)
    
    return json_ar_collection

def visualize_analysis_results(ts_collection, ar_collection, technique_name, property_names_dict):
    if technique_name in ['Change Point Detection', 'Threshold Based Point Detection']:
        for tsid, ts in ts_collection.items():
            non_temporal_parameters = tsid[1]
            property_id = tsid[0].replace('\"','').replace("{", '_').replace('}', '_').replace(':','_')
            if property_id in property_names_dict.keys():
                property_name = property_names_dict[property_id]
            else:
                property_name = ''
            if isinstance(non_temporal_parameters, tuple):
                non_temporal_parameters = ', '.join(non_temporal_parameters)
            ar = ar_collection[tsid].copy()
            chart = px.line(ts, color_discrete_sequence=['blue']).update_layout(xaxis_title='time', yaxis_title=None, showlegend=False)
            for index in ar:
                chart = chart.add_vline(x=ts.index[index], line_width=2, line_dash="dash", line_color="green")
            with st.container(border=True):
                if technique_name == 'Change Point Detection':
                    st.markdown(f'Change points for timeseries of {property_name}({property_id}) with parameters: {non_temporal_parameters}')
                else:
                    st.markdown(f'Threshold based points for timeseries of {property_name} ({property_id}) with parameters: {non_temporal_parameters}')
                st.plotly_chart(chart)
    
    elif technique_name == 'Forecasting':
        for tsid, ts in ts_collection.items():
            property_id = tsid[0].replace('\"','').replace("{", '_').replace('}', '_').replace(':','_')
            if property_id in property_names_dict.keys():
                property_name = property_names_dict[property_id]
            else:
                property_name = ''
            non_temporal_parameters = tsid[1]
            if isinstance(non_temporal_parameters, tuple):
                non_temporal_parameters = ', '.join(non_temporal_parameters)
            ar_df = ar_collection[tsid].copy()
            ts_df = ts.copy()
            ts_df = ts_df.rename('values').to_frame()
            ar_df = ar_df.rename('values').to_frame()
            ts_df['category'] = 'historic values'
            ar_df['category'] = 'forecasts'
            joined_df = pd.concat([ts_df,ar_df])
            joined_df.index.name = 'time'
            joined_df = joined_df.reset_index()
            chart = px.line(joined_df, x='time', y='values', color='category', color_discrete_sequence=['blue', 'darkred'], render_mode='svg').update_layout(yaxis_title=None)
            with st.container(border=True):
                st.markdown(f'Forecasts for timeseries of {property_name} ({property_id}) with parameters: {non_temporal_parameters}')
                st.plotly_chart(chart)

    
    elif technique_name == 'Granger Causality':
        gc_df = ar_collection
        caused_tsid_list = gc_df['caused'].unique()

        for caused_tsid in caused_tsid_list:
            property_id = caused_tsid[0].replace('\"','').replace("{", '_').replace('}', '_').replace(':','_')
            if property_id in property_names_dict.keys():
                property_name = property_names_dict[property_id]
            else:
                property_name = ''
            non_temporal_parameters = caused_tsid[1]
            if isinstance(non_temporal_parameters, tuple):
                non_temporal_parameters = ', '.join(non_temporal_parameters)
            graph = graphviz.Digraph(graph_attr={'rankdir': 'LR'})
            caused_df = gc_df[gc_df['caused'] == caused_tsid]
            causing_arr = caused_df['causing'].values.tolist()
            lag_dict = dict(zip(caused_df['causing'], caused_df['lag']))
            graph.node(str(caused_tsid), style='filled', fillcolor = 'lightblue')
            for causing_tsid in causing_arr:
                lag_arr = lag_dict[causing_tsid]
                lag_str = ', '.join(str(x) for x in lag_arr)
                graph.node(str(causing_tsid), style='filled', fillcolor = 'lightgray')
                graph.edge(str(causing_tsid), str(caused_tsid), lag_str)
            with st.container(border=True):
                st.markdown(f'Granger Causality for timeseries of {property_name} ({property_id}) with parameters: {non_temporal_parameters}')
                st.graphviz_chart(graph)
