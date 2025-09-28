import pm4py
import pandas as pd
import numpy as np
import pandas as pd
from setup import agg

#Generates time series for Waiting Time for each event type in the log.
#Gets the ending time (or timestamp if atomic) of the preceding event that ends (or occurs if atomic) the latest amongst
# all its preceding events for each event and stores in the column 'time_latest_preceding_event'.
#Preceding events are formally defined in the Thesis as well as described in the comments above the function
#'preceding_events_df' in 'setup.py'.
#Waiting time is then determined for each event by taking a difference of 'time_latest_preceding_event' and 
#the starting time of the event. For an event with no preceding events, it's waiting time is 0.
#It then iterates over events of each type and generates a time series for them by calling 'pp1_iter'. 
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
    wt_df = preceding_events_df.copy()
    wt_df['time_latest_preceding_event'] = wt_df['preceding_events_time_alltypes'].str[0]
    wt_df['time_latest_preceding_event'] = pd.to_datetime(wt_df['time_latest_preceding_event'], utc=True)
    wt_df['waiting_time'] = wt_df[event_timestamp_column] -  wt_df['time_latest_preceding_event']
    wt_df.loc[wt_df['waiting_time'].isnull(), 'waiting_time'] = pd.Timedelta(0)


    for event_type in event_types:
        type_wt_df = wt_df[wt_df[event_type_column] == event_type]
        type_wt_df = type_wt_df.merge(events_to_time_df, on = event_id_column, how = 'inner')
        pp1_dict[event_type] = pp1_iter(event_type, type_wt_df)

    return pp1_dict

#Generates time series for Synchronization Time for each event type in the log.
#Gets the ending time (or timestamp if atomic) of two preceding events for each event, one that ends (or occurs if atomic) 
#the earliest and another that ends the latest amongst all its preceding events and stores them in the columns
#'time_earliest_preceding_event' and 'time_latest_preceding_event'.
#Preceding events are formally defined in the Thesis as well as described in the comments above the function
#'preceding_events_df' in 'setup.py'.
#Synchronization time is then determined for each event by taking a difference of 'time_latest_preceding_event' and 
#'time_earliest_preceding_event' of the event. For an event with no preceding events, it's synchronization time is 0.
#It then iterates over events of each type and generates a time series for them by calling 'pp2_iter'. 
def pp2(preceding_events_df, event_types, events_to_time_df, aggregation_mode, sampling_rate,\
         event_id_column = 'ocel:eid', event_type_column = 'ocel:activity'):

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
    st_df = preceding_events_df.copy()
    st_df['time_latest_preceding_event'] = st_df['preceding_events_time_alltypes'].str[0]
    st_df['time_earliest_preceding_event'] = st_df['preceding_events_time_alltypes'].str[-1]
    st_df['time_latest_preceding_event'] = pd.to_datetime(st_df['time_latest_preceding_event'], utc=True)
    st_df['time_earliest_preceding_event'] = pd.to_datetime(st_df['time_earliest_preceding_event'], utc=True)
    st_df['synchronization_time'] = st_df['time_latest_preceding_event'] - st_df['time_earliest_preceding_event']
    st_df.loc[st_df['synchronization_time'].isnull(), 'synchronization_time'] = pd.Timedelta(0)

    for event_type in event_types:
        type_st_df = st_df[st_df[event_type_column] == event_type]
        type_st_df = type_st_df.merge(events_to_time_df, on = event_id_column, how = 'inner')
        pp2_dict[event_type] = pp2_iter(event_type, type_st_df)
        
    return pp2_dict

#Generates time series for Service Time for each event type in the log. 
#Only called if the event log contains non-atomic events.
#Service time is determined for each event by taking a difference of the starting and ending timestamps of the event. 
#It then iterates over events of each type and generates a time series for them by calling 'pp3_iter'. 
def pp3(event_types_to_df_map, events_to_time_df, aggregation_mode, sampling_rate, event_endtime_column,\
        event_id_column = 'ocel:eid', event_timestamp_column = 'ocel:timestamp'):

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
        svt_df = event_type_df.copy()
        svt_df['service_time'] = svt_df[event_endtime_column] - event_type_df[event_timestamp_column]
        svt_df = events_to_time_df.merge(svt_df, on=event_id_column, how='inner', suffixes=('_2', None))
        pp3_dict[event_type] = pp3_iter(event_type, svt_df)
    return pp3_dict

#Generates time series for Soujourn Time for each event type in the log.
#If the log only contains atomic events then this is exactly the same as Waiting Time i.e. pp1.
#Else if the log contain non-atomic events then it is the sum of its service time and waiting time.
#It gets the ending time of the preceding event that ends the latest amongst
#all its preceding events for each event and stores in the column 'time_latest_preceding_event'.
#Preceding events are formally defined in the Thesis as well as described in the comments above the function
#'preceding_events_df' in 'setup.py'.
#Soujourn is then determined for each event by taking a difference of 'time_latest_preceding_event' and 
#the ending time of the event. For an event with no preceding events, its soujourn time is
#difference between its own ending and starting timestamps i.e. its service time.
#It then iterates over events of each type and generates a time series for them by calling 'pp4_iter'. 
def pp4(pp1_dict, preceding_events_df, event_types, event_endtime_column, atomic_evs, events_to_time_df,\
        aggregation_mode, sampling_rate, event_id_column = 'ocel:eid', event_timestamp_column = 'ocel:timestamp',\
        event_type_column = 'ocel:activity'):

    def pp4_iter(event_type, df):
        ts_id = event_type
        df['soujourn_time'] = df['soujourn_time'].dt.total_seconds()/3600
        df = df.rename(columns={'soujourn_time': ts_id})
        df = df[['assignment_mechanism_time', ts_id]]
        df = df.set_index('assignment_mechanism_time')
        ts = df[ts_id]
        ts = agg(ts, aggregation_mode, sampling_rate)
        return ts

    pp4_dict = {}
    
    if atomic_evs:
        for event_type in event_types:
            pp4_dict[event_type] = pp1_dict[event_type]
    else:
        sjt_df = preceding_events_df.copy()
        sjt_df['time_latest_preceding_event'] = sjt_df['preceding_events_time_alltypes'].str[0]
        sjt_df['time_latest_preceding_event'] = pd.to_datetime(sjt_df['time_latest_preceding_event'], utc=True)
        sjt_df['soujourn_time'] = sjt_df[event_endtime_column] -  sjt_df['time_latest_preceding_event']
        sjt_df.loc[sjt_df['time_latest_preceding_event'].isnull(), 'soujourn_time'] =\
                                                sjt_df[event_endtime_column] -  sjt_df[event_timestamp_column]

        for event_type in event_types:
            type_sjt_df = sjt_df[sjt_df[event_type_column] == event_type]
            type_sjt_df = type_sjt_df.merge(events_to_time_df, on = event_id_column, how = 'inner')
            pp4_dict[event_type] = pp4_iter(event_type, type_sjt_df)

    return pp4_dict

#Generates time series for Flow Time for each event type in the log.
#It gets the ending time of the preceding event that ends the earliest amongst
#all its preceding events for each event and stores in the column 'time_earliest_preceding_event'.
#Preceding events are formally defined in the Thesis as well as described in the comments above the function
#'preceding_events_df' in 'setup.py'.
#Flow is then determined for each event by taking a difference of 'time_latest_preceding_event' and 
#the ending time of the event (if events are non-atomic) or timestamp of the event (if events are atomic). 
#For an event with no preceding events, its flow time is difference between its own ending and starting timestamps 
#i.e., its service time if events are non-atomic else flow time is zero if atomic.
#It then iterates over events of each type and generates a time series for them by calling 'pp5_iter'. 
def pp5(preceding_events_df, event_types, event_endtime_column, atomic_evs, events_to_time_df,\
        aggregation_mode, sampling_rate, event_id_column = 'ocel:eid', event_timestamp_column = 'ocel:timestamp',\
        event_type_column = 'ocel:activity'):

    def pp5_iter(event_type, df):
        ts_id = event_type
        df['flow_time'] = df['flow_time'].dt.total_seconds()/3600
        df = df.rename(columns={'flow_time': ts_id})
        df = df[['assignment_mechanism_time', ts_id]]
        df = df.set_index('assignment_mechanism_time')
        ts = df[ts_id]
        ts = agg(ts, aggregation_mode, sampling_rate)
        return ts
    
    pp5_dict = {}
    
    if atomic_evs:
        event_time_column = event_timestamp_column
    else:
        event_time_column = event_endtime_column


    ft_df = preceding_events_df.copy()
    ft_df['time_earliest_preceding_event'] = ft_df['preceding_events_time_alltypes'].str[-1]
    ft_df['time_earliest_preceding_event'] = pd.to_datetime(ft_df['time_earliest_preceding_event'], utc=True)
    ft_df['flow_time'] = ft_df[event_time_column] -  ft_df['time_earliest_preceding_event']

    if atomic_evs:
        ft_df.loc[ft_df['time_earliest_preceding_event'].isnull(), 'flow_time'] = pd.Timedelta(0)
    else:
        ft_df.loc[ft_df['time_earliest_preceding_event'].isnull(), 'flow_time'] =\
                                            ft_df[event_endtime_column] -  ft_df[event_timestamp_column]

    for event_type in event_types:
        type_ft_df = ft_df[ft_df[event_type_column] == event_type]
        type_ft_df = type_ft_df.merge(events_to_time_df, on = event_id_column, how = 'inner')
        pp5_dict[event_type] = pp5_iter(event_type, type_ft_df)

    return pp5_dict

#Generates time series for Pooling Time for each combination of event type, object type that occurs in the log.
#For each combination (event type, object type), it filters the events of that event type and gets 
#the ending time (or timestamp if atomic) of two of the preceding events, one that ends (or occurs if atomic) the latest 
# and another that ends (or occurs) the earliest among all its preceding events (related via objects of that object type) 
#for each event and stores them  in the columns 'time_latest_preceding_event_obj type' and 
#'time_earliest_preceding_event_obj type'. Pooling time is then determined for each event by taking a difference of the two
#aforementioned timestamps. For an event with no preceding events related by the object type of the combination, 
#it's pooling time is 0.
def pp6(preceding_events_df, event_object_combinations, events_to_time_df, aggregation_mode, sampling_rate,\
        event_id_column = 'ocel:eid', event_type_column = 'ocel:activity'):

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
    pt_df = preceding_events_df.copy()


    for (event_type,object_type) in event_object_combinations:
        combo_pt_df = pt_df[(pt_df[event_type_column] == event_type)]
        combo_pt_df['time_latest_preceding_event_obj_type'] \
            = combo_pt_df[f'preceding_events_time_{object_type}'].str[0]
        
        combo_pt_df['time_earliest_preceding_event_obj_type'] \
            = combo_pt_df[f'preceding_events_time_{object_type}'].str[-1]
        
        combo_pt_df['time_latest_preceding_event_obj_type'] \
            = pd.to_datetime(combo_pt_df['time_latest_preceding_event_obj_type'], utc=True)
        
        combo_pt_df['time_earliest_preceding_event_obj_type'] \
            = pd.to_datetime(combo_pt_df['time_earliest_preceding_event_obj_type'], utc=True)
        
        combo_pt_df['pooling_time'] = combo_pt_df['time_latest_preceding_event_obj_type'] \
            - combo_pt_df['time_earliest_preceding_event_obj_type']
        
        combo_pt_df.loc[combo_pt_df['pooling_time'].isnull(), 'pooling_time'] = pd.Timedelta(0)
        combo_pt_df = combo_pt_df.merge(events_to_time_df, on = event_id_column, how = 'inner')
        pp6_dict[(event_type,object_type)] = pp6_iter(event_type, combo_pt_df)
        
    return pp6_dict

#Generates time series for Lagging Time for each combination of event type, object type that occurs in the log.
#For each combination (event type, object type), it filters the events of that event type and gets 
#the ending time (or timestamp if atomic) of two of the preceding events, one for the event that ends 
#(or occurs if atomic) the latest among all its preceding events, related via objects of the combination's object type 
# and another for the event that ends the earliest among all its preceding events, related via objects of 
#any object type excluding the one in the combination and stores them  in the columns 
#'time_latest_preceding_event_obj type' and 'time_earliest_preceding_event_excluding_obj type', respectively. 
#Lagging time is then determined for each event by taking a difference of the two aforementioned timestamps. 
#For an event with no preceding events related by objects of either the object type of the combination or any other type,
#its lagging time is 0. If the calculated lagging time is negative, it's set to zero.
def pp7(preceding_events_df, event_object_combinations, events_to_time_df, aggregation_mode, sampling_rate, \
        event_id_column = 'ocel:eid', event_type_column = 'ocel:activity'):

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

    lt_df = preceding_events_df.copy()


    for (event_type,object_type) in event_object_combinations:
        combo_lt_df = lt_df[(lt_df[event_type_column] == event_type)]

        combo_lt_df['time_latest_preceding_event_obj_type'] = \
            combo_lt_df[f'preceding_events_time_{object_type}'].str[0]
        
        combo_lt_df['time_earliest_preceding_event_excluding_obj_type']\
              = combo_lt_df[f'preceding_events_time_excluding_{object_type}'].str[-1]
        
        combo_lt_df['time_latest_preceding_event_obj_type'] = \
            pd.to_datetime(combo_lt_df['time_latest_preceding_event_obj_type'], utc=True)
        
        combo_lt_df['time_earliest_preceding_event_excluding_obj_type'] \
            = pd.to_datetime(combo_lt_df['time_earliest_preceding_event_excluding_obj_type'], utc=True)
        
        combo_lt_df['lagging_time'] = combo_lt_df['time_latest_preceding_event_obj_type'] \
            - combo_lt_df['time_earliest_preceding_event_excluding_obj_type']
        
        combo_lt_df.loc[combo_lt_df['lagging_time'].isnull(), 'lagging_time'] = pd.Timedelta(0)
        combo_lt_df.loc[combo_lt_df['lagging_time'] < pd.Timedelta(0), 'lagging_time'] = pd.Timedelta(0)
        combo_lt_df = combo_lt_df.merge(events_to_time_df, on = event_id_column, how = 'inner')
        pp7_dict[(event_type,object_type)] = pp7_iter(event_type, combo_lt_df)
        
    return pp7_dict