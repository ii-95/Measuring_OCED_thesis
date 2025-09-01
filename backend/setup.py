import pm4py
import pandas as pd
import numpy as np
import pandas as pd

def agg(series, agg_mode, samp_rate):
    if type(series) == pd.Series:
        if agg_mode == 'mean':
            return series.resample(samp_rate).mean()
        elif agg_mode == 'sum':
            return series.resample(samp_rate).sum()
        elif agg_mode == 'min':
            return series.resample(samp_rate).min()
        elif agg_mode == 'max':
            return series.resample(samp_rate).max()
        
def get_events_df(ocel_obj):
    events_df = ocel_obj.get_extended_table()
    return events_df

def get_objects_df(ocel_obj):
    object_df = pm4py.ocel_objects_summary(ocel_obj)
    return object_df

#returns a dictionary that maps each event type to the respective table in the ocel's sql db (converted to dataframe).
def get_event_types_to_table_df_map(ocel_db_engine):

    # read table 'event_map_type' in ocel sql db
    event_map_type_df = pd.read_sql("SELECT * FROM event_map_type", con=ocel_db_engine)


    # append 'event_' to the 'ocel_type_map' column of the 'event_map_type' table (dataframe) in 
    # ocel to get the actual name table
    event_map_type_df['ocel_type_map'] = 'event_' + event_map_type_df['ocel_type_map'].astype(str) 
    # convert the two column dataframe to a dict to use ahead
    event_types_to_table_name_map = dict(zip(event_map_type_df.ocel_type, event_map_type_df.ocel_type_map))


    # initilize and populate the dictionary that maps each event type 
    # to respective table (converted to dataframe) in ocel sql db.
    # convert the 'ocel_time' column in the event type table to datetime format
    event_types_to_table_df_map = {}
    for key,value in event_types_to_table_name_map.items():
        df = pd.read_sql(f"SELECT * FROM {value}", con=ocel_db_engine)
        df['ocel_time'] = pd.to_datetime(df['ocel_time'])
        event_types_to_table_df_map[key] = df

    return event_types_to_table_df_map

#returns a dictionary that  maps each object type to the respective table in the ocel's sql db.
def get_object_types_to_table_df_map(ocel_db_engine):
     
    # read table 'object_map_type' in ocel sql db
    object_map_type_df = pd.read_sql("SELECT * FROM object_map_type", con=ocel_db_engine)

    # append 'object_' to the 'ocel_type_map' column of the 'object_map_type' table (dataframe) in 
    # ocel to get the actual name table
    object_map_type_df['ocel_type_map'] = 'object_' + object_map_type_df['ocel_type_map'].astype(str) 
    # convert the two column dataframe to a dict to use ahead
    object_types_to_table_name_map = dict(zip(object_map_type_df.ocel_type, object_map_type_df.ocel_type_map))

    # initilize and populate the dictionary that maps each object type
    # to it's table (converted to dataframes) in the ocel's sql db
    # convert the 'ocel_time' column to datetime format
    object_types_to_table_df_map = {}

    for key,value in object_types_to_table_name_map.items():
        df = pd.read_sql(f"SELECT * FROM {value}", con=ocel_db_engine)
        df['ocel_time'] = pd.to_datetime(df['ocel_time'])
        object_types_to_table_df_map[key] = df

    return object_types_to_table_df_map



# returns a dictionary mapping each event type to a dataframe containing the number of objects of each object type 
# per event of the specified event type
def get_event_object_count_df_map(ocel, event_types_to_table_df_map):
    event_object_count_df = pd.DataFrame.from_dict(pm4py.ocel_objects_ot_count(ocel)).transpose()
    event_object_count_df = event_object_count_df.replace(np.nan, 0)
    event_object_count_df_map = {}

    for event_type, event_type_df in event_types_to_table_df_map.items():
        event_df = event_type_df[['ocel_id', 'ocel_time']].copy()
        event_df = event_df.set_index('ocel_id')
        event_object_count_df_map[event_type] = event_df.join(event_object_count_df)
    return event_object_count_df_map


# get all existing combinations of event types and object types in the ocel
# returns an array of  lists where each list is a combination => [object type, event type] that occurs in the log
def get_event_object_combinations(ocel):
    event_object_combinations = pm4py.ocel_objects_interactions_summary(ocel)[['ocel:activity','ocel:type']].drop_duplicates() \
    .values
    return event_object_combinations

#get list of time intervals according to the specified time interval and sampling rate
def get_time_intervals(start_time, end_time, samp_rate):
    offset = pd.tseries.frequencies.to_offset(samp_rate)
    start = (start_time - offset).normalize()
    end = (end_time + offset).normalize()
    time_intervals = list(pd.interval_range(start, end, freq=samp_rate).to_tuples())
    #correct start of first interval
    time_intervals[0] = list(time_intervals[0])
    time_intervals[0][0] = start_time
    time_intervals[0] = tuple(time_intervals[0])
    #correct end of last interval
    time_intervals[-1] = list(time_intervals[-1])
    time_intervals[-1][1] = end_time
    time_intervals[-1] = tuple(time_intervals[-1])
    time_intervals = pd.Index(time_intervals)
    return time_intervals
    
def get_time_intervals_cross_objects_df(objects_df, time_intervals):
    
    #Create a dataframe containing the time interval range
    time_interval_df = pd.DataFrame(time_intervals, columns = ['time_interval'])

    #get a cross product of relevant columns of the log with the time interval df
    objects_df = objects_df[['ocel:oid','lifecycle_start', 'lifecycle_end']].sort_values(by=['lifecycle_start','lifecycle_end'])
    cross_df = objects_df.merge(time_interval_df, how='cross')
    return cross_df

def get_time_intervals_cross_events_df(events_df, time_intervals, endtime):
    #Create a dataframe containing the time interval range
    time_interval_df = pd.DataFrame(time_intervals, columns = ['time_interval'])

    #get a cross product of relevant columns of the log with the time interval df
    events_df = events_df[['ocel:eid', 'ocel:timestamp', endtime]].sort_values(by=['ocel:timestamp', endtime])
    cross_df = events_df.merge(time_interval_df, how='cross')
    return cross_df

def get_contained_objects(ti_cross_objs_df):
    #Match object lifecycles with time intervals to check containment. Containment is an interval is left open and right closed.
    ti_cross_objs_df['count'] = ti_cross_objs_df.apply(lambda x: 1 if (x['lifecycle_start'] > x['time_interval'][0]) \
                                                       and (x['lifecycle_end'] <= x['time_interval'][1]) else None, axis=1)
    #Drop all rows where containment in an interval is not found
    ti_cross_objs_df = ti_cross_objs_df.dropna(subset=['count'])

    #Keep only usable columns.
    ti_cross_objs_df = ti_cross_objs_df[['ocel:oid', 'lifecycle_start', 'lifecycle_end']]
    return ti_cross_objs_df

def get_overlapping_objects(ti_cross_objs_df):
    #Match object lifecycles with time intervals to check overlap. An object must overlap with atleast one interval and
    #may overlap with more than one interval.
    ti_cross_objs_df['count'] = ti_cross_objs_df.apply(lambda x: 1 if (x['lifecycle_start'] <= x['time_interval'][1]) \
                                                       and (x['lifecycle_end'] >= x['time_interval'][0]) else None, axis=1)
    #Drop all rows where overlap with an interval is not found.
    ti_cross_objs_df = ti_cross_objs_df.dropna(subset=['count'])

    #Add column for the end of each time interval
    ti_cross_objs_df['time_interval_end'] = ti_cross_objs_df.apply(lambda x: x['time_interval'][0], axis=1)

    #Keep only usable columns.
    ti_cross_objs_df = ti_cross_objs_df[['ocel:oid', 'lifecycle_start', 'lifecycle_end', 'time_interval_end']]
    
    return ti_cross_objs_df

def get_contained_events(ti_cross_evs_df, endtime):
    #Match event start and end with time intervals to check containment. The intervals are treated as left open and right closed.
    ti_cross_evs_df['count'] = ti_cross_evs_df.apply(lambda x: 1 if (x['ocel:timestamp'] > x['time_interval'][0]) \
                                                     and (x[endtime] <= x['time_interval'][1]) else None, axis=1)
    
    #Drop all rows where containment in an interval is not found
    ti_cross_evs_df = ti_cross_evs_df.dropna(subset=['count'])
    
    #Keep only usable columns
    ti_cross_evs_df = ti_cross_evs_df[['ocel:eid', 'ocel:timestamp', endtime]]

    return ti_cross_evs_df

def get_overlapping_events(ti_cross_evs_df, endtime):
    #Match event start and end with time intervals to check overlap. An event must overlap with atleast one interval and
    #may overlap with more than one interval.
    ti_cross_evs_df['count'] = ti_cross_evs_df.apply(lambda x: 1 if (x['ocel:timestamp'] <= x['time_interval'][1]) \
                                                     and (x[endtime] >= x['time_interval'][0]) else None, axis=1)
    
    #Drop all rows where overlap with an interval is not found
    ti_cross_evs_df = ti_cross_evs_df.dropna(subset=['count'])
    
    #Add column for the end of each time interval
    ti_cross_evs_df['time_interval_end'] = ti_cross_evs_df.apply(lambda x: x['time_interval'][0], axis =1)

    #Keep only usable columns
    ti_cross_evs_df = ti_cross_evs_df[['ocel:eid', 'ocel:timestamp', endtime, 'time_interval_end']]
    
    return ti_cross_evs_df

def get_objects_to_time_df(objects_df, time_intervals, assign_mech):
    ti_cross_objs_df = get_time_intervals_cross_objects_df(objects_df, time_intervals)

    if assign_mech == 'starting':
        objs_to_time_df = objects_df[['ocel:oid', 'lifecycle_start']]
        objs_to_time_df = objs_to_time_df.rename(columns={'ocel:oid' : 'ocel_id', 'lifecycle_start': 'assign_mech_time'})

    elif assign_mech == 'ending':
        objs_to_time_df = objects_df[['ocel:oid', 'lifecycle_end']]
        objs_to_time_df = objs_to_time_df.rename(columns={'ocel:oid' : 'ocel_id', 'lifecycle_end': 'assign_mech_time'})

    elif assign_mech == 'contains':
        objs_to_time_df = get_contained_objects(ti_cross_objs_df)
        objs_to_time_df = objs_to_time_df[['ocel:oid', 'lifecycle_end']]
        objs_to_time_df = objs_to_time_df.rename(columns={'ocel:oid' : 'ocel_id', 'lifecycle_end': 'assign_mech_time'})

    elif assign_mech == 'overlaps':
        objs_to_time_df = get_overlapping_objects(ti_cross_objs_df)
        objs_to_time_df = objs_to_time_df[['ocel:oid', 'time_interval_end']]
        objs_to_time_df = objs_to_time_df.rename(columns={'ocel:oid' : 'ocel_id', 'time_interval_end': 'assign_mech_time'})

    else:
        raise ValueError('Invalid assignment mechasism selection')
    
    return objs_to_time_df

def get_events_to_time_df(events_df, time_intervals, assign_mech, endtime):

    ti_cross_evs_df = get_time_intervals_cross_events_df(events_df, time_intervals, endtime)

    if assign_mech == 'starting':
        evs_to_time_df = events_df[['ocel:eid', 'ocel:timestamp']]
        evs_to_time_df = evs_to_time_df.rename(columns={'ocel:eid' : 'ocel_id', 'ocel:timestamp': 'assign_mech_time'})

    elif assign_mech == 'ending':
        evs_to_time_df = events_df[['ocel:eid', endtime]]
        evs_to_time_df = evs_to_time_df.rename(columns={'ocel:eid' : 'ocel_id', endtime: 'assign_mech_time'})

    elif assign_mech == 'contains':
        evs_to_time_df = get_contained_events(ti_cross_evs_df, endtime)
        evs_to_time_df = evs_to_time_df[['ocel:eid', endtime]]
        evs_to_time_df = evs_to_time_df.rename(columns={'ocel:eid' : 'ocel_id', endtime: 'assign_mech_time'})

    elif assign_mech == 'overlaps':
        evs_to_time_df = get_overlapping_events(ti_cross_evs_df, endtime)
        evs_to_time_df = evs_to_time_df[['ocel:eid', 'time_interval_end']]
        evs_to_time_df = evs_to_time_df.rename(columns={'ocel:eid' : 'ocel_id', 'time_interval_end': 'assign_mech_time'})

    else:
        raise ValueError('Invalid assignment mechasism selection')
    
    return evs_to_time_df
