import pm4py
import pandas as pd
import numpy as np
import pandas as pd
from pandas.api.types import is_any_real_numeric_dtype
from setup import agg


def ep1(event_types_to_db_table_map, events_to_time_df, sampling_rate):
    
    # Function to produce time series of count/frequency of events for a given event type
    # Input: event type, dataframe containing all events of the specified type 
    # (with attributes and timestamps)
    def ep1_iter(event_type, df):
            ts_id = f'event-frequency_{event_type}'
            df[ts_id] = 1
            df = df[['assignment_mechanism_time', ts_id]]
            df = df.set_index('assignment_mechanism_time')
            ts = df[ts_id]
            ts = ts.resample(sampling_rate).sum()
            return ts
    
    # Call function 'ep1_iter' for each event type to produce respective count/frequency timeseries.
    # Map event type to time series in dictionary 'ep1_dict'
    ep1_dict = {}
    for event_type, event_type_df in event_types_to_db_table_map.items():
        df = events_to_time_df.merge(event_type_df, on='ocel_id', how='inner', suffixes=('_2', None))
        ep1_dict[event_type] = ep1_iter(event_type, df)
    return ep1_dict

def ep2(event_types_to_db_table_map, events_to_time_df, aggregation_mode, sampling_rate):

    # Function to produce time series of attribute values for all numerical attributes of a given event type
    # Input: event type, dataframe containing all events of the specified type 
    # (with attributes and timestamps)
    def ep2_iter(event_type, df):
        attr_ts_dict = {}
        event_attributes = list(set(df.columns.values) - set(['ocel_id', 'ocel_time']))
        for event_attribute in event_attributes:
            if is_any_real_numeric_dtype(df[event_attribute]):
                ts_id = f'event-attribute_{event_type}_{event_attribute}'
                attr_df = df[['assignment_mechanism_time', event_attribute]]
                attr_df = attr_df.rename(columns={event_attribute: ts_id})
                attr_df = attr_df.set_index('assignment_mechanism_time')
                ts = attr_df[ts_id]
                attr_ts_dict[event_attribute] = agg(ts, aggregation_mode, sampling_rate)
                
        return attr_ts_dict

    # Call function 'ep2_iter' for each event type to produce a dictionary that maps the time series 
    # of attribute values for each of it's numerical attributes to the respective attribute. 
    # Map each such dictionary to the event type in 'ep2_dict'.
    ep2_dict = {event_type:{} for event_type in event_types_to_db_table_map.keys()}
    for event_type, event_type_df in event_types_to_db_table_map.items():
        #<-----------Remove in prod----------->
        #dummy attribute for testing
        event_type_df['test_attribute'] = np.random.randint(1, 100, event_type_df.shape[0])
        #<------------------------------------>
        df = events_to_time_df.merge(event_type_df, on='ocel_id', how='inner', suffixes=('_2', None))
        ep2_dict[event_type] = ep2_iter(event_type, df)
    return ep2_dict

def ep3(event_object_count_df_map, events_to_time_df, aggregation_mode, sampling_rate):

    # Function to produce time series of (total) number of objects per event of a given event type
    # Input: event type, dataframe containing all events of the specified type and the count of
    # objects of each type for the event
    def ep3_iter(event_type, df):
            ts_id = f'number-of-objects-per-event_{event_type}'

            #numeric_only option set as True excludes the only non-numeric and hence 
            #non-object-type-frequency column in the dataframe
            df[ts_id] = df.sum(axis=1, numeric_only=True)
            df = df[['assignment_mechanism_time', ts_id]]
            df = df.set_index('assignment_mechanism_time')
            ts = df[ts_id]
            ts = agg(ts, aggregation_mode, sampling_rate)
            return ts

    # Call function 'ep3_iter' for each event type to produce respective timeseries for (total) 
    # number of objects per event.
    # Map event type to time series in dictionary 'ep3_dict'    
    ep3_dict = {}
    for event_type, event_object_count_df in event_object_count_df_map.items():
        df = events_to_time_df.merge(event_object_count_df, on='ocel_id', how='inner', suffixes=('_2', None))
        ep3_dict[event_type] = ep3_iter(event_type, df)
    return ep3_dict

def ep4(event_object_combinations, event_object_count_df_map, events_to_time_df, aggregation_mode, sampling_rate):

    # Function to produce time series of number of objects of a given object type per event of a given event type.
    # Input: event type, object type, dataframe containing all events of the specified event type 
    # and a count of objects of the specified object type.
    def ep4_iter(event_type, object_type, df):
            ts_id = f'number-of-objects-of-a-type-per-event_{event_type}_{object_type}'
            df = df.rename(columns={object_type: ts_id})
            df = df[['assignment_mechanism_time', ts_id]]
            df = df.set_index('assignment_mechanism_time')
            ts = df[ts_id]
            ts = agg(ts, aggregation_mode, sampling_rate)
            return ts

    # Call function 'ep4_iter' for each combination (that exists in the log)  of an event type and object type to 
    # produce respective timeseries for number of objects of each object type per event.
    # Map combination of event type and object type to a time series in dictionary 'ep4_dict'.
    ep4_dict = {}
    for combination in event_object_combinations:
        event_type = combination[0]
        object_type = combination[1]
        event_object_count_df = event_object_count_df_map[event_type][['ocel_time', object_type]]
        df = events_to_time_df.merge(event_object_count_df, on='ocel_id', how='inner', suffixes=('_2', None))
        ep4_dict[(event_type,object_type)] = ep4_iter(event_type, object_type, df)
    return ep4_dict