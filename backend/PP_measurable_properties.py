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
    wt_df['waiting_time'] = wt_df[event_timestamp_column] -  wt_df['time_latest_preceding_event']
    wt_df.loc[wt_df['waiting_time'].isnull(), 'waiting_time'] = pd.Timedelta(0)


    for event_type in event_types:
        type_wt_df = wt_df[wt_df[event_type_column] == event_type]
        type_wt_df = type_wt_df.merge(events_to_time_df, on = event_id_column, how = 'inner')
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
    st_df = preceding_events_df
    st_df['time_latest_preceding_event'] = st_df['preceding_events_timestamps'].str[0]
    st_df['time_earliest_preceding_event'] = st_df['preceding_events_timestamps'].str[-1]
    st_df['time_latest_preceding_event'] = pd.to_datetime(st_df['time_latest_preceding_event'], utc=True)
    st_df['time_earliest_preceding_event'] = pd.to_datetime(st_df['time_earliest_preceding_event'], utc=True)
    st_df['synchronization_time'] = st_df['time_latest_preceding_event'] - st_df['time_earliest_preceding_event']
    st_df.loc[st_df['synchronization_time'].isnull(), 'synchronization_time'] = pd.Timedelta(0)

    for event_type in event_types:
        type_st_df = st_df[st_df[event_type_column] == event_type]
        type_st_df = type_st_df.merge(events_to_time_df, on = event_id_column, how = 'inner')
        pp2_dict[event_type] = pp2_iter(event_type, type_st_df)
        
    return pp2_dict

def pp3(event_types_to_df_map, events_to_time_df, aggregation_mode, sampling_rate, event_endtime_column,\
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
    for event_type, event_type_df in event_types_to_df_map.items():
        svt_df = event_type_df
        svt_df['service_time'] = svt_df[event_endtime_column] - event_type_df[event_timestamp_column]
        svt_df = events_to_time_df.merge(svt_df, on=event_id_column, how='inner', suffixes=('_2', None))
        pp3_dict[event_type] = pp3_iter(event_type, svt_df)
    return pp3_dict

def pp4(pp1_dict, pp3_dict, event_types, atomic_evs):
    pp4_dict = {}
    if atomic_evs:
        for event_type in event_types:
            pp4_dict[event_type] = pp1_dict[event_type]
    else:
        for event_type in event_types:
            pp4_dict[event_type] = pp1_dict[event_type].add(pp3_dict[event_type])
    return pp4_dict

def pp5(pp2_dict, pp4_dict, event_types):
    pp5_dict = {}
    for event_type in event_types:
        pp5_dict[event_type] = pp2_dict[event_type].add(pp4_dict[event_type])
    return pp5_dict

def pp6(preceding_events_by_object_type_df, event_object_combinations, events_to_time_df, aggregation_mode, sampling_rate,\
        event_id_column = 'ocel:eid', event_timestamp_column = 'ocel:timestamp', event_type_column = 'ocel:activity', \
        object_type_column = 'ocel:type'):

    def pp6_iter(event_type, df):
        ts_id = event_type
        df['pooling_time'] = df['pooling_time'].dt.total_seconds()/3600
        df = df.rename(columns={'pooling_time': ts_id})
        df = df[['assignment_mechanism_time', ts_id]]
        df = df.set_index('assignment_mechanism_time')
        ts = df[ts_id]
        ts = agg(ts, aggregation_mode, sampling_rate)
        return ts

    pp6_dict = {}
    pt_df = preceding_events_by_object_type_df
    pt_df['time_latest_preceding_event'] = pt_df['preceding_events_timestamps_obj_type'].str[0]
    pt_df['time_earliest_preceding_event'] = pt_df['preceding_events_timestamps_obj_type'].str[-1]
    pt_df['time_latest_preceding_event'] = pd.to_datetime(pt_df['time_latest_preceding_event'], utc=True)
    pt_df['time_earliest_preceding_event'] = pd.to_datetime(pt_df['time_earliest_preceding_event'], utc=True)
    pt_df['pooling_time'] = pt_df['time_latest_preceding_event'] - pt_df['time_earliest_preceding_event']
    pt_df.loc[pt_df['pooling_time'].isnull(), 'pooling_time'] = pd.Timedelta(0)


    for (event_type,object_type) in event_object_combinations:
        combination_pt_df = pt_df[(pt_df[event_type_column] == event_type) & (pt_df[object_type_column] == object_type)]
        combination_pt_df = combination_pt_df.merge(events_to_time_df, on = event_id_column, how = 'inner')
        pp6_dict[(event_type,object_type)] = pp6_iter(event_type, combination_pt_df)
        
    return pp6_dict

def pp7(preceding_events_df, preceding_events_by_object_type_df, event_object_combinations, events_to_time_df, atomic_evs,\
        event_endtime_column, aggregation_mode, sampling_rate, event_id_column = 'ocel:eid',\
        event_timestamp_column = 'ocel:timestamp', event_type_column = 'ocel:activity', object_type_column = 'ocel:type'):

    def pp7_iter(event_type, df):
        ts_id = event_type
        df['lagging_time'] = df['lagging_time'].dt.total_seconds()/3600
        df = df.rename(columns={'lagging_time': ts_id})
        df = df[['assignment_mechanism_time', ts_id]]
        df = df.set_index('assignment_mechanism_time')
        ts = df[ts_id]
        ts = agg(ts, aggregation_mode, sampling_rate)
        return ts

    pp7_dict = {}
    if atomic_evs:
        lt_df = preceding_events_by_object_type_df.merge(preceding_events_df,\
                on = [event_id_column, event_timestamp_column, event_type_column], how='inner',  suffixes=('_2', None))
    else: 
        lt_df = preceding_events_by_object_type_df.merge(preceding_events_df,\
                 on = [event_id_column, event_timestamp_column, event_endtime_column, event_type_column], \
                 how='inner',  suffixes=('_2', None))

    lt_df['time_latest_preceding_event_obj_type'] = lt_df['preceding_events_timestamps_obj_type'].str[0]
    lt_df['time_earliest_preceding_event'] = lt_df['preceding_events_timestamps'].str[-1]
    lt_df['time_latest_preceding_event_obj_type'] = pd.to_datetime(lt_df['time_latest_preceding_event_obj_type'], utc=True)
    lt_df['time_earliest_preceding_event'] = pd.to_datetime(lt_df['time_earliest_preceding_event'], utc=True)
    lt_df['lagging_time'] = lt_df['time_latest_preceding_event_obj_type'] - lt_df['time_earliest_preceding_event']
    lt_df.loc[lt_df['lagging_time'].isnull(), 'lagging_time'] = pd.Timedelta(0)

    for (event_type,object_type) in event_object_combinations:
        combination_lt_df = lt_df[(lt_df[event_type_column] == event_type) & (lt_df[object_type_column] == object_type)]
        combination_lt_df = combination_lt_df.merge(events_to_time_df, on = event_id_column, how = 'inner')
        pp7_dict[(event_type,object_type)] = pp7_iter(event_type, combination_lt_df)
        
    return pp7_dict