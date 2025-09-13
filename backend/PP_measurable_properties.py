import pm4py
import pandas as pd
import numpy as np
import pandas as pd
from setup import agg

def pp1(preceding_events_df, event_types, events_to_time_df, aggregation_mode, sampling_rate,\
         event_id_column = 'ocel:eid', event_timestamp_column = 'ocel:timestamp', event_type_column = 'ocel:activity'):

    def pp1_iter(event_type, df):
        ts_id = event_type
        df['waiting_time'] = df['waiting_time'].dt.total_seconds()/3600
        df = df.rename(columns={'waiting_time': ts_id})
        df = df[['assignment_mechanism_time', ts_id]]
        df = df.set_index('assignment_mechanism_time')
        ts = df[ts_id]
        ts = agg(ts, aggregation_mode, sampling_rate)
        return ts

    pp1_dict = {}
    wt_df = preceding_events_df
    wt_df['time_latest_preceding_event'] = wt_df['preceding_events_timestamps'].str[0]
    wt_df['time_latest_preceding_event'] = pd.to_datetime(wt_df['time_latest_preceding_event'], utc=True)
    wt_df.loc[wt_df['time_latest_preceding_event'].isnull(), 'time_latest_preceding_event'] = wt_df[event_timestamp_column]
    wt_df['waiting_time'] = wt_df[event_timestamp_column] -  wt_df['time_latest_preceding_event']

    for event_type in event_types:
        type_wt_df = wt_df[wt_df[event_type_column] == event_type]
        type_wt_df = type_wt_df.merge(events_to_time_df, left_on = event_id_column, right_on = 'ocel_id', how = 'inner')
        pp1_dict[event_type] = pp1_iter(event_type, type_wt_df)

    return pp1_dict

def pp2(preceding_events_df, event_types, events_to_time_df, aggregation_mode, sampling_rate,\
         event_id_column = 'ocel:eid', event_timestamp_column = 'ocel:timestamp', event_type_column = 'ocel:activity'):

    def pp2_iter(event_type, df):
        ts_id = event_type
        df['synchronization_time'] = df['synchronization_time'].dt.total_seconds()/3600
        df = df.rename(columns={'synchronization_time': ts_id})
        df = df[['assignment_mechanism_time', ts_id]]
        df = df.set_index('assignment_mechanism_time')
        ts = df[ts_id]
        ts = agg(ts, aggregation_mode, sampling_rate)
        return ts

    pp2_dict = {}
    wt_df = preceding_events_df
    wt_df['time_latest_preceding_event'] = wt_df['preceding_events_timestamps'].str[0]
    wt_df['time_earliest_preceding_event'] = wt_df['preceding_events_timestamps'].str[-1]
    wt_df['time_latest_preceding_event'] = pd.to_datetime(wt_df['time_latest_preceding_event'], utc=True)
    wt_df['time_earliest_preceding_event'] = pd.to_datetime(wt_df['time_earliest_preceding_event'], utc=True)
    wt_df.loc[wt_df['time_latest_preceding_event'].isnull(), 'time_latest_preceding_event'] = wt_df[event_timestamp_column]
    wt_df.loc[wt_df['time_earliest_preceding_event'].isnull(), 'time_earliest_preceding_event'] = wt_df[event_timestamp_column]
    wt_df['synchronization_time'] = wt_df['time_latest_preceding_event'] - wt_df['time_earliest_preceding_event']

    for event_type in event_types:
        type_wt_df = wt_df[wt_df[event_type_column] == event_type]
        type_wt_df = type_wt_df.merge(events_to_time_df, left_on = event_id_column, right_on = 'ocel_id', how = 'inner')
        pp2_dict[event_type] = pp2_iter(event_type, type_wt_df)
        
    return pp2_dict

def pp3(events_df, event_types, events_to_time_df, aggregation_mode, sampling_rate, event_endtime_column,\
        event_id_column = 'ocel:eid', event_timestamp_column = 'ocel:timestamp', event_type_column = 'ocel:activity'):

    def pp3_iter(event_type, df):
        ts_id = event_type
        df['service_time'] = df['service_time'].dt.total_seconds()/3600
        df = df.rename(columns={'service_time': ts_id})
        df = df[['assignment_mechanism_time', ts_id]]
        df = df.set_index('assignment_mechanism_time')
        ts = df[ts_id]
        ts = agg(ts, aggregation_mode, sampling_rate)
                
        return ts
 
    pp3_dict = {}
    for event_type in event_types:
        event_type_df = events_df[events_df[event_type_column] == event_type]
        event_type_df['service_time'] = event_type_df[event_endtime_column] - event_type_df[event_timestamp_column]
        df = events_to_time_df.merge(event_type_df, left_on='ocel_id', right_on=event_id_column, how='inner', suffixes=('_2', None))
        pp3_dict[event_type] = pp3_iter(event_type, df)
    return pp3_dict