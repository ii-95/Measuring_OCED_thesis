import pm4py
import pandas as pd
import numpy as np
import pandas as pd


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

def get_objects_df(ocel):
    object_df = pm4py.ocel_objects_summary(ocel)
    return object_df

def get_event_to_object_relations_df(ocel):
    event_to_object_relations_df = ocel.relations
    return event_to_object_relations_df

#if non-atomic events exist in the log, then fill in endtimes for any possible atomic events 
# in the log (those with null/empty values in endtine column) with their starting time.
def adjust_events_end_time(events_df, event_endtime_column, event_timestamp_column = 'ocel:timestamp'):
    #replaces all null and empty values with pd.NaT
    events_df[event_endtime_column] = pd.to_datetime(events_df[event_endtime_column])
    #replaces all pd.NaT values with value in ocel:timestamp column
    events_df.loc[events_df[event_endtime_column].isnull(), event_endtime_column] = events_df[event_timestamp_column]
    return events_df

#returns a dictionary that maps each event type to the respective table in the ocel's sql db (converted to dataframe).
def get_event_types_to_db_table_map(ocel_db_engine):

    # read table 'event_map_type' in ocel sql db
    event_map_type_df = pd.read_sql("SELECT * FROM event_map_type", con=ocel_db_engine)


    # append 'event_' to the 'ocel_type_map' column of the 'event_map_type' table (dataframe) in 
    # ocel to get the actual name table
    event_map_type_df['ocel_type_map'] = 'event_' + event_map_type_df['ocel_type_map'].astype(str) 
    # convert the two column dataframe to a dict to use ahead
    event_types_to_db_table_name_map = dict(zip(event_map_type_df.ocel_type, event_map_type_df.ocel_type_map))


    # initilize and populate the dictionary that maps each event type 
    # to respective table (converted to dataframe) in ocel sql db.
    # convert the 'ocel_time' column in the event type table to datetime format
    event_types_to_db_table_map = {}
    for key,value in event_types_to_db_table_name_map.items():
        df = pd.read_sql(f"SELECT * FROM {value}", con=ocel_db_engine)
        df['ocel_time'] = pd.to_datetime(df['ocel_time'])
        event_types_to_db_table_map[key] = df

    return event_types_to_db_table_map

#returns a dictionary that  maps each object type to the respective table in the ocel's sql db.
def get_object_types_to_db_table_map(ocel_db_engine):
     
    # read table 'object_map_type' in ocel sql db
    object_map_type_df = pd.read_sql("SELECT * FROM object_map_type", con=ocel_db_engine)

    # append 'object_' to the 'ocel_type_map' column of the 'object_map_type' table (dataframe) in 
    # ocel to get the actual name table
    object_map_type_df['ocel_type_map'] = 'object_' + object_map_type_df['ocel_type_map'].astype(str) 
    # convert the two column dataframe to a dict to use ahead
    object_types_to_db_table_name_map = dict(zip(object_map_type_df.ocel_type, object_map_type_df.ocel_type_map))

    # initilize and populate the dictionary that maps each object type
    # to it's table (converted to dataframes) in the ocel's sql db
    # convert the 'ocel_time' column to datetime format
    object_types_to_db_table_map = {}

    for key,value in object_types_to_db_table_name_map.items():
        df = pd.read_sql(f"SELECT * FROM {value}", con=ocel_db_engine)
        df['ocel_time'] = pd.to_datetime(df['ocel_time'])
        object_types_to_db_table_map[key] = df

    return object_types_to_db_table_map



# returns a dictionary mapping each event type to a dataframe containing the number of objects of each object type 
# per event of the specified event type
def get_event_object_count_df_map(ocel, event_types_to_db_table_map):
    event_object_count_df = pd.DataFrame.from_dict(pm4py.ocel_objects_ot_count(ocel)).transpose()
    event_object_count_df = event_object_count_df.replace(np.nan, 0)
    event_object_count_df_map = {}

    for event_type, event_type_df in event_types_to_db_table_map.items():
        event_df = event_type_df[['ocel_id', 'ocel_time']].copy()
        event_df = event_df.set_index('ocel_id')
        event_object_count_df_map[event_type] = event_df.join(event_object_count_df)
    return event_object_count_df_map


# get all existing combinations of event types and object types in the ocel
# returns an array of  lists where each list is a combination => [object type, event type] that occurs in the log
def get_event_object_combinations(ocel, event_type_column='ocel:eid', object_type_column='ocel:oid'):
    event_object_combinations = pm4py.ocel_objects_interactions_summary(ocel)[[event_type_column, object_type_column]]\
                                .drop_duplicates().values
    return event_object_combinations

#get list of time intervals according to the specified time interval and sampling rate
def get_time_intervals(start_time, end_time, sampling_rate):
    offset = pd.tseries.frequencies.to_offset(sampling_rate)
    start = (start_time - offset).normalize()
    end = (end_time + offset).normalize()
    time_intervals = list(pd.interval_range(start, end, freq=sampling_rate).to_tuples())
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

#a cross join of time intervals_df and objects_df
def get_time_intervals_cross_objects_df(objects_df, time_intervals, object_id_column='ocel:oid'):
    
    #Create a dataframe containing the time interval range
    time_interval_df = pd.DataFrame(time_intervals, columns = ['time_interval'])

    #get a cross product of relevant columns of the log with the time interval df
    objects_df = objects_df[[object_id_column,'lifecycle_start', 'lifecycle_end']]\
                .sort_values(by=['lifecycle_start','lifecycle_end'])
    cross_df = objects_df.merge(time_interval_df, how='cross')
    return cross_df

#a cross join of time intervals_df and events_df
def get_time_intervals_cross_events_df(events_df, time_intervals, event_endtime_column, event_id_column='ocel:eid', \
                                       event_timestamp_column='ocel:timestamp'):
    #Create a dataframe containing the time interval range
    time_interval_df = pd.DataFrame(time_intervals, columns = ['time_interval'])

    #get a cross product of relevant columns of the log with the time interval df
    events_df = events_df[[event_id_column, event_timestamp_column, event_endtime_column]]\
                .sort_values(by=[event_timestamp_column, event_endtime_column])
    cross_df = events_df.merge(time_interval_df, how='cross')
    return cross_df

def update_object_lifecycle_end_for_non_atomic_events(objects_df,event_to_object_relations_df, events_df,\
                                                    event_endtime_column, event_id_column='ocel:eid',\
                                                    object_id_column='ocel:oid'):
    #get all unique object-to-relations
    e2o_df = event_to_object_relations_df[[object_id_column, event_id_column]].drop_duplicates()
    #get endtimes for all related events
    e2o_df = e2o_df.merge(events_df[[event_id_column, event_endtime_column]], on=event_id_column)
    #get maximum end time for each object. This is the lifecycle end time.
    object_lifecycle_end_df = e2o_df[[object_id_column, event_endtime_column]].groupby(object_id_column).max()
    object_lifecycle_end_df = object_lifecycle_end_df.rename\
                                (columns={event_id_column:'lifecycle_end'})
    objects_df = objects_df.drop(columns=['lifecycle_end'])
    objects_df = object_lifecycle_end_df.merge(objects_df, on= object_id_column)
    objects_df = update_object_lifecycle_end_for_non_atomic_events(objects_df)
    return objects_df

#returns a dataframe with rows for only those objects that are contained in some interval
def get_contained_objects(ti_cross_objs_df, object_id_column='ocel:oid'):
    #Match object lifecycles with time intervals to check containment. 
    #Containment is an interval is left open and right closed.
    ti_cross_objs_df['count'] = ti_cross_objs_df.apply(lambda x: 1 if (x['lifecycle_start'] > x['time_interval'][0]) \
                                                       and (x['lifecycle_end'] <= x['time_interval'][1]) else None, axis=1)
    #Drop all rows where containment in an interval is not found
    ti_cross_objs_df = ti_cross_objs_df.dropna(subset=['count'])

    #Keep only usable columns.
    ti_cross_objs_df = ti_cross_objs_df[[object_id_column, 'lifecycle_start', 'lifecycle_end']]
    return ti_cross_objs_df

#returns a dataframe with rows for each time an object overlaps with some interval
def get_overlapping_objects(ti_cross_objs_df, object_id_column='ocel:oid'):
    #Match object lifecycles with time intervals to check overlap. 
    #An object must overlap with atleast one interval and may overlap with more than one interval.
    ti_cross_objs_df['count'] = ti_cross_objs_df.apply(lambda x: 1 if (x['lifecycle_start'] <= x['time_interval'][1]) \
                                                       and (x['lifecycle_end'] >= x['time_interval'][0]) else None, axis=1)
    #Drop all rows where overlap with an interval is not found.
    ti_cross_objs_df = ti_cross_objs_df.dropna(subset=['count'])

    #Add column for the end of each time interval
    ti_cross_objs_df['time_interval_end'] = ti_cross_objs_df.apply(lambda x: x['time_interval'][0], axis=1)

    #Keep only usable columns.
    ti_cross_objs_df = ti_cross_objs_df[[object_id_column, 'lifecycle_start', 'lifecycle_end', 'time_interval_end']]
    
    return ti_cross_objs_df

#returns a dataframe with rows for only those events that are contained in some interval
def get_contained_events(ti_cross_evs_df, event_endtime_column, event_id_column='ocel:eid',\
                          event_timestamp_column='ocel:timestamp'):
    #Match event start and end with time intervals to check containment. 
    # The intervals are treated as left open and right closed.
    ti_cross_evs_df['count'] = ti_cross_evs_df.apply(lambda x: 1 if (x[event_timestamp_column] > x['time_interval'][0]) \
                                                    and (x[event_endtime_column] <= x['time_interval'][1]) else None, axis=1)
    
    #Drop all rows where containment in an interval is not found
    ti_cross_evs_df = ti_cross_evs_df.dropna(subset=['count'])
    
    #Keep only usable columns
    ti_cross_evs_df = ti_cross_evs_df[[event_id_column, event_timestamp_column, event_endtime_column]]

    return ti_cross_evs_df

#returns a dataframe with rows for each time an event overlaps with some interval
def get_overlapping_events(ti_cross_evs_df, event_endtime_column, event_id_column='ocel:eid',\
                            event_timestamp_column='ocel:timestamp'):
    #Match event start and end with time intervals to check overlap. An event must overlap with atleast one interval and
    #may overlap with more than one interval.
    ti_cross_evs_df['count'] = ti_cross_evs_df.apply(lambda x: 1 if (x[event_timestamp_column] <= x['time_interval'][1]) \
                                                    and (x[event_endtime_column] >= x['time_interval'][0]) else None, axis=1)
    
    #Drop all rows where overlap with an interval is not found
    ti_cross_evs_df = ti_cross_evs_df.dropna(subset=['count'])
    
    #Add column for the end of each time interval
    ti_cross_evs_df['time_interval_end'] = ti_cross_evs_df.apply(lambda x: x['time_interval'][0], axis =1)

    #Keep only usable columns
    ti_cross_evs_df = ti_cross_evs_df[[event_id_column, event_timestamp_column, event_endtime_column, 'time_interval_end']]
    
    return ti_cross_evs_df

#returns a dataframe with a column for objects and another for a timestamp representing the assigned interval. 
# The choice of the timestamp is different for each assignment mechanism such that it it suitable for resampling/aggregation
# at the time series level. 
def get_objects_to_time_df(objects_df, time_intervals, assignment_mechanism, object_id_column='ocel:oid'):
    
    ti_cross_objs_df = get_time_intervals_cross_objects_df(objects_df, time_intervals)

    if assignment_mechanism == 'starting':
        objs_to_time_df = objects_df[[object_id_column, 'lifecycle_start']]
        objs_to_time_df = objs_to_time_df\
            .rename(columns={object_id_column : 'ocel_id', 'lifecycle_start': 'assignment_mechanism_time'})

    elif assignment_mechanism == 'ending':
        objs_to_time_df = objects_df[[object_id_column, 'lifecycle_end']]
        objs_to_time_df = objs_to_time_df\
            .rename(columns={object_id_column : 'ocel_id', 'lifecycle_end': 'assignment_mechanism_time'})

    elif assignment_mechanism == 'contains':
        objs_to_time_df = get_contained_objects(ti_cross_objs_df)
        objs_to_time_df = objs_to_time_df[[object_id_column, 'lifecycle_end']]
        objs_to_time_df = objs_to_time_df\
            .rename(columns={object_id_column : 'ocel_id', 'lifecycle_end': 'assignment_mechanism_time'})

    elif assignment_mechanism == 'overlaps':
        objs_to_time_df = get_overlapping_objects(ti_cross_objs_df)
        objs_to_time_df = objs_to_time_df[[object_id_column, 'time_interval_end']]
        objs_to_time_df = objs_to_time_df\
            .rename(columns={object_id_column : 'ocel_id', 'time_interval_end': 'assignment_mechanism_time'})

    else:
        raise ValueError('Invalid assignment mechasism selection')
    
    return objs_to_time_df

def get_events_to_time_df(events_df, time_intervals, assignment_mechanism, event_endtime_column, atomic_evs, \
                        event_id_column='ocel:eid', event_timestamp_column='ocel:timestamp'):
    #if all events are atomic then assignment mechanism has no effect on the assignment of events
    #to time periods/intervals and we can return a dataframe of events and their timestamps
    if atomic_evs:
        evs_to_time_df = events_df[[event_id_column, event_timestamp_column]]
        evs_to_time_df = evs_to_time_df.rename(columns={event_id_column : 'ocel_id',\
                                                         event_timestamp_column: 'assignment_mechanism_time'})
    else:
        #if all events are not atomic then we need to use the respective strategy for assigning
        #events to time periods/intervals as per the selected assignment mechanism
        ti_cross_evs_df = get_time_intervals_cross_events_df(events_df, time_intervals, event_endtime_column)

        if assignment_mechanism == 'starting':
            evs_to_time_df = events_df[[event_id_column, event_timestamp_column]]
            evs_to_time_df = evs_to_time_df.rename(columns={event_id_column : 'ocel_id',\
                                                             event_timestamp_column: 'assignment_mechanism_time'})

        elif assignment_mechanism == 'ending':
            evs_to_time_df = events_df[[event_id_column, event_endtime_column]]
            evs_to_time_df = evs_to_time_df.rename(columns={event_id_column : 'ocel_id',\
                                                             event_endtime_column: 'assignment_mechanism_time'})

        elif assignment_mechanism == 'contains':
            evs_to_time_df = get_contained_events(ti_cross_evs_df, event_endtime_column)
            evs_to_time_df = evs_to_time_df[[event_id_column, event_endtime_column]]
            evs_to_time_df = evs_to_time_df.rename(columns={event_id_column : 'ocel_id',\
                                                            event_endtime_column: 'assignment_mechanism_time'})

        elif assignment_mechanism == 'overlaps':
            evs_to_time_df = get_overlapping_events(ti_cross_evs_df, event_endtime_column)
            evs_to_time_df = evs_to_time_df[[event_id_column, 'time_interval_end']]
            evs_to_time_df = evs_to_time_df.rename(columns={event_id_column : 'ocel_id',\
                                                             'time_interval_end': 'assignment_mechanism_time'})

        else:
            raise ValueError('Invalid assignment mechasism selection')
    
    return evs_to_time_df
