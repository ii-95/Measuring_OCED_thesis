import pm4py
import pandas as pd
import numpy as np
import pandas as pd
from pandas.api.types import is_any_real_numeric_dtype
from setup import agg
from collections import Counter

def op1(object_types_to_df_map, objects_to_time_df, sampling_rate, object_id_column = 'ocel:oid'):
    
    # Function to produce time series of count/frequency of objects for a given object type
    # Input: object type, dataframe containing all objects of the specified type 
    # (with attributes and timestamps)
    def op1_iter(object_type, df):
            ts_id = f'{object_type}'
            df[ts_id] = 1
            df = df[['assignment_mechanism_time', ts_id]]
            df = df.set_index('assignment_mechanism_time')
            ts = df[ts_id]
            ts = ts.resample(sampling_rate).sum()
            return ts
    
    # Call function 'op1_iter' for each object type to produce respective count/frequency timeseries.
    # Map object type to time series in dictionary 'op1_dict'
    op1_dict = {}
    for object_type, object_type_df in object_types_to_df_map.items():
        df = objects_to_time_df.merge(object_type_df[object_id_column], on = object_id_column,\
                                        how='right', suffixes=('_2', None))\
            .drop_duplicates()
        op1_dict[object_type] = op1_iter(object_type, df)
    return op1_dict

def op2(object_types_to_df_map, objects_to_time_df, aggregation_mode, sampling_rate, \
        object_id_column='ocel:oid', timestamp_column='ocel:timestamp', 
        changed_field_column='ocel:field'):

    # Function to produce time series of attribute values for a given attribute and object type
    # Input: object type, object attribute, dataframe containing value of the attribute at the end of each interval
    # along with timestamps representing the interval.

    def op2_iter(object_type, object_attribute, df):
        ts_id = f'{object_type}_{object_attribute}'
        attr_df = df[['assignment_mechanism_time', object_attribute]]
        attr_df = attr_df.rename(columns={object_attribute: ts_id})
        attr_df = attr_df.set_index('assignment_mechanism_time')
        ts = attr_df[ts_id]
        ts = agg(ts, aggregation_mode, sampling_rate)
        return ts

    op2_dict = {}

    for object_type, object_type_df in object_types_to_df_map.items():
        #get all attributes associated with object type
        object_attributes = list(set(object_type_df.columns.values) - \
                                 set([object_id_column, timestamp_column, changed_field_column]))
        for object_attribute in object_attributes:
            #get rows which contain attribute's initial value or attribute changes
            attr_df = object_type_df[object_type_df[changed_field_column].isin([None, object_attribute])]
            #check if attribute has values assigned
            if not attr_df.empty:
                #merge with object's time assignment df
                attr_df = attr_df.merge(objects_to_time_df, on = object_id_column, how='inner')
                #only keep those rows where attribute to object assignment timestamp is less than object to time period
                #assignment timestamp
                attr_df = attr_df[attr_df[timestamp_column] < attr_df['assignment_mechanism_time']]
                #get latest value of attribute for each object at end of each time interval
                attr_df = attr_df.groupby([object_id_column, 'assignment_mechanism_time']).max(timestamp_column)
                attr_df = attr_df.reset_index()
                # Call function 'op2_iter' for each combination of an object type and one of it's numerical attributes
                # to produce a dictionary that maps the time series attribute values. 
                op2_dict[(object_type, object_attribute)] = op2_iter(object_type, object_attribute, attr_df)
    return op2_dict

def op3(object_type_summary_df_map, objects_to_time_df, aggregation_mode, sampling_rate, object_id_column = 'ocel:oid'):


    # Function to produce time series of (total) number of events per object of a given object type
    # Input: object type, dataframe containing all objects of the specified type including the list of
    # events in the lifecycle of that object and timestamps according to the assignment mechanism
    def op3_iter(object_type, df):
            ts_id = f'{object_type}'
            #compute the number of activities in an object's lifecycle
            df[ts_id] = df['activities_lifecycle'].str.len()
            df = df[['assignment_mechanism_time', ts_id]]
            df = df.set_index('assignment_mechanism_time')
            ts = df[ts_id]
            ts = agg(ts, aggregation_mode, sampling_rate)
            return ts

 
    op3_dict = {}

    #'object_type_summary_df' contains rows of objects of 'object type' from 'objects_summary_df'
    for object_type, object_type_summary_df in object_type_summary_df_map.items():
        #get timestamps that represent interval/time-period assignment for objects i.e. 'objects_to_time_df' and 
        #merge with object_type_summary_df which contains information regarding the events in each
        #objects lifecycle in column 'activities_lifecycle' and hence the number of events per object
        #can be determined using this information.
        df = objects_to_time_df.merge(object_type_summary_df, on=object_id_column, \
                                      how='inner', suffixes=('_2', None))
        # Call function 'op3_iter' for each object type to produce respective timeseries for (total) 
        # number of events per object.
        # Map event type to time series in dictionary 'op3_dict'   
        op3_dict[object_type] = op3_iter(object_type, df)
    return op3_dict


def op4(event_to_object_relations_df_map, objects_to_time_df, aggregation_mode, sampling_rate, \
        event_id_column = 'ocel:eid', object_id_column= 'ocel:oid', event_type_column = 'ocel:activity', \
        object_type_column = 'ocel:type'):
    
    # Function to produce time series of (total) number of events per object of a given object type
    # Input: object type, dataframe containing all objects of the specified type along with the count of related events
    # of the specified type and timestamps according to the assignment mechanism
    def op4_iter(object_type, event_type, df):
            ts_id = f'{object_type}_{event_type}'
            df = df.rename(columns={'event_count': ts_id})
            df = df[['assignment_mechanism_time', ts_id]]
            df = df.set_index('assignment_mechanism_time')
            ts = df[ts_id]
            ts = agg(ts, aggregation_mode, sampling_rate)
            return ts

    op4_dict = {}
    for (event_type, object_type), event_to_object_relations_df in event_to_object_relations_df_map.items():
        #For this property, we only wish to retain unique combinations of related events and objects 
        # of the specified types, irrespective of qualifiers and timestamps.
        df = event_to_object_relations_df[[event_id_column, event_type_column, 
                                                                    object_id_column, object_type_column]] \
                                                                    .drop_duplicates()
        #  Subsequently we count the number of events per object
        df = df.groupby(object_id_column).count().reset_index()[[object_id_column,object_type_column]]\
                                                        .rename(columns={object_type_column: 'event_count'})
        #get timestamps that represent interval/time-period assignment for objects i.e. 'objects_to_time_df' and 
        #merge with 'event_to_object_relations_df' which contains all related events and objects of the specified types.
        df = objects_to_time_df.merge(df, on= object_id_column, how='inner', suffixes=('_2', None))
        # Call function 'op4_iter' for each combination of object type and event type in the log 
        # to produce respective timeseries for number of events of the type per object of the type.
        # Map event type to time series in dictionary 'op4_dict'   
        op4_dict[(object_type, event_type)] = op4_iter(object_type, event_type, df)
    return op4_dict

def op5(object_type_summary_df_map, objects_to_time_df, aggregation_mode, sampling_rate, object_id_column = 'ocel:oid'):

    # Function to produce time series of lifecycle duration of objects of a given object type
    # Input: object type, dataframe containing all objects of the specified type along with their
    # lifecycle duration and timestamps according to the assignment mechanism
    def op5_iter(object_type, df):
            df['lifecycle_duration'] = df['lifecycle_duration']/3600
            ts_id = f'{object_type}'
            df = df.rename(columns={'lifecycle_duration': ts_id})
            df = df[['assignment_mechanism_time', ts_id]]
            df = df.set_index('assignment_mechanism_time')
            ts = df[ts_id]
            ts = agg(ts, aggregation_mode, sampling_rate)
            return ts

 
    op5_dict = {}

    #'object_type_summary_df' contains rows of objects of 'object type' from 'objects_summary_df'
    for object_type, object_type_summary_df in object_type_summary_df_map.items():
        #get timestamps that represent interval/time-period assignment for objects i.e. 'objects_to_time_df' and 
        #merge with object_type_summary_df which contains lifecycle duration of objects
        df = objects_to_time_df.merge(object_type_summary_df, on=object_id_column,\
                                       how='inner', suffixes=('_2', None))
        # Call function 'op5_iter' for each object type to produce respective timeseries for lifecycle duration
        # of objects of the specified type.
        # Map event type to time series in dictionary 'op5_dict'   
        op5_dict[object_type] = op5_iter(object_type, df)
    return op5_dict

def op6(object_interactions_df, events_to_time_df, aggregation_mode, sampling_rate,\
         object_id_column='ocel:oid', event_id_column='ocel:eid', object_type_column='ocel:type'):
    
    # Function to produce time series of number of object interactions per event between objects of two given 
    # (not necessarily different) object types.
    # Input: a combination of two object types, dataframe containing events and count of object interactions for each event
    # between objects of the two specified types along timestamps of events according to the assignment mechanism.
    def op6_iter(object_to_object_combination, df):
            ts_id = f'{object_to_object_combination[0]}_{object_to_object_combination[1]}'
            df = df.rename(columns={'object_type_pairs': ts_id})
            df = df[['assignment_mechanism_time', ts_id]]
            df = df.set_index('assignment_mechanism_time')
            ts = df[ts_id]
            ts = agg(ts, aggregation_mode, sampling_rate)
            return ts
    
    op6_dict = {}
    obj_intr_df = object_interactions_df
    #remove all duplicate interactions from obj_intr_df
    obj_intr_df['object_type_pairs'] = [(tuple(sorted(filter(None, x)))) for x in obj_intr_df\
                                                   [[object_type_column, f'{object_type_column}_2']].to_numpy()]
    obj_intr_df['object_id_pairs'] = [(tuple(sorted(filter(None, x)))) for x in obj_intr_df\
                                                 [[object_id_column, f'{object_id_column}_2']].to_numpy()]
    obj_intr_df = obj_intr_df[[event_id_column, 'object_id_pairs', 'object_type_pairs']]
    obj_intr_df = obj_intr_df.drop_duplicates()
    #get all unique object type combinations in the log whose objects interact via events i.e. the objects are
    # related to the same event
    object_to_object_type_combinations= obj_intr_df['object_type_pairs'].drop_duplicates()
    for object_to_object_type_combination in object_to_object_type_combinations:
        #filter rows for the specified object type combination 
        combination_df = obj_intr_df[obj_intr_df['object_type_pairs']==object_to_object_type_combination]
        #get count of interactions per event
        interaction_count_df = combination_df.groupby(event_id_column).count().reset_index()
        #get timestamps of events according to assignment mechanism
        df = interaction_count_df.merge(events_to_time_df, on=event_id_column, how='inner')
        #generate time series for each combination
        op6_dict[object_to_object_type_combination] = op6_iter(object_to_object_type_combination, df)
    return op6_dict
