import numpy as np
import pandas as pd
from setup import *
pd.options.mode.copy_on_write = True



#Convert timeseries to OCED and plug back into original OCEL
def insert_time_series_into_ocel(TS_collection, ocel_json_dict, int_start, int_end, aggregation_mode, sampling_rate, \
                                 property_names_dict, property_parameters_map, events_to_time_df, objects_to_time_df, overlapping_objects_to_time_df,
                                 event_types_to_df_map, object_types_to_df_map, event_id_column = 'ocel:eid', object_id_column = 'ocel:oid'):
    #load ocel components into dataframes
    json_objects_df = pd.DataFrame(ocel_json_dict['objects'])
    json_events_df = pd.DataFrame(ocel_json_dict['events'])
    json_object_types_df = pd.DataFrame(ocel_json_dict['objectTypes'])
    json_event_types_df = pd.DataFrame(ocel_json_dict['eventTypes'])
    #below code is needed in case if no events or objects have any attributes in the log
    if not 'attributes' in json_events_df.columns.values:
        column_list = [[]] * len(json_events_df)
        json_events_df['attributes'] = column_list
    if not 'attributes' in json_objects_df.columns.values:
        column_list = [[]] * len(json_objects_df)
        json_objects_df['attributes'] = column_list
    #initialize dataframe for time series objects
    #also initialize lists that will hold the values that are to be plugged into the relevant dataframe columns, post data processing
    ts_objs_df = pd.DataFrame(columns=json_objects_df.columns.values.tolist())
    ts_obj_id_list = [None] * len(TS_collection)
    ts_obj_type_list = ['time series'] * len(TS_collection)
    attributes_list = [[]] * len(TS_collection)
    relationships_list = [[]] * len(TS_collection)

    #purpose of dummy events is explained later when they are used
    json_event_types_df.loc[len(json_event_types_df)] = {'name':'dummy',  'attributes':[]}
    json_events_df.loc[len(json_events_df)] = {'type': 'dummy', 'relationships': [], 'attributes': [], 'id': 'start_dummy_event', 'time': (int_start + pd.Timedelta('1s')).isoformat().replace("+00:00", ".000Z")}
    json_events_df.loc[len(json_events_df)] = {'type': 'dummy', 'relationships': [], 'attributes': [], 'id': 'end_dummy_event', 'time': (int_end - pd.Timedelta('1s')).isoformat().replace("+00:00", ".000Z")}

    #create new object type for time series
    json_object_types_df.loc[len(json_object_types_df)] = {'name':'time series',  'attributes':[{'name': 'tsvalues', 'type': 'float'}]}
    i=0
    for tsid, ts in TS_collection.items():
        #get all relevant variable values
        property_id = tsid[0]
        property_name = property_names_dict[property_id]
        non_temporal_parameters = tsid[1]
        if isinstance(non_temporal_parameters, tuple):
            non_temporal_parameters_str = '_'.join(non_temporal_parameters)
        else:
            non_temporal_parameters_str = str(non_temporal_parameters)
        qualifer_str = 'ts' + '-' + sampling_rate + '-' + aggregation_mode + '-' + property_name + '-' + non_temporal_parameters_str
        ts_obj_id = 'ts-' + property_id + '-' + non_temporal_parameters_str
        #set time series object id
        ts_obj_id_list[i] = ts_obj_id
        #all time series object attributes except 'tsvalues' are static
        """ attributes = [{'name': 'sampling_rate', 'value': sampling_rate, 'time': '1970-01-01T00:00:00.000Z'}, \
                    {'name': 'aggregation_mode', 'value': aggregation_mode, 'time': '1970-01-01T00:00:00.000Z'},\
                        {'name': 'property_id', 'value': property_id, 'time': '1970-01-01T00:00:00.000Z'},\
                        {'name': 'property_name', 'value': property_name, 'time': '1970-01-01T00:00:00.000Z'},\
                        {'name': 'non_temporal_parameters', 'value': non_temporal_parameters_str, 'time': '1970-01-01T00:00:00.000Z'}] """
        attributes = []
        #get time series values, convert to iso string format and add to attributes dict of the time series object
        ts_df = ts.rename('value').to_frame()
        ts_df.index.name = 'time'
        ts_df = ts_df.reset_index()
        ts_df['time'] = ts_df['time'].map(lambda x: x.isoformat().replace("+00:00", ".000Z"))
        ts_df['name'] = 'tsvalues'
        ts_df = ts_df[['name', 'value', 'time']]
        ts_df.loc[len(ts_df)] = {'name':'tsvalues', 'value':0, 'time':'1970-01-01T00:00:00.000Z'}
        ts_df = ts_df.sort_values(by='time', ignore_index= True)
        tsvalues = ts_df.to_dict('records')
        attributes = tsvalues.copy()
        attributes_list[i] = attributes

        #for the first parameter (either an event type or an object type) in the non temporal parameters of the time series, connect the time series object
        #to the original events or object of that type in the OCEL by adding a e2o or o2o qualifier containing the pertinent
        #information regarding the time series i.e., sampling rate, agg mode, property name and non temporal parameters.
        primary_parameter_type = property_parameters_map[property_id][0]
        if primary_parameter_type == 'event type':
            if isinstance(non_temporal_parameters, tuple):
                et = non_temporal_parameters[0]
            else:
                et = non_temporal_parameters
            et_events_in_time_interval = event_types_to_df_map[et].merge(events_to_time_df, how='inner', on = event_id_column)[event_id_column].values
            related_evs_json = json_events_df[json_events_df['id'].isin(et_events_in_time_interval)]['relationships']
            if related_evs_json.isna().all():
                empty_column = pd.Series([[]] * len(related_evs_json), index=related_evs_json.index, name = 'relationships')
                related_evs_json = empty_column
            related_evs_json = related_evs_json + pd.Series([[{'objectId': ts_obj_id, 'qualifier': qualifer_str}]] * len(related_evs_json), related_evs_json.index.values.tolist(), name='relationships')
            json_events_df.loc[related_evs_json.index, 'relationships'] = related_evs_json
        elif primary_parameter_type == 'object type':
            if isinstance(non_temporal_parameters, tuple):
                ot = non_temporal_parameters[0]
            else:
                ot = non_temporal_parameters
            
            if property_id not in ['op6', 'rp2']:
                ot_objects_in_time_interval = objects_to_time_df.merge(object_types_to_df_map[ot][object_id_column], how='inner', on = object_id_column).drop_duplicates()[object_id_column].drop_duplicates()
            else:
                ot_objects_in_time_interval = overlapping_objects_to_time_df.merge(object_types_to_df_map[ot][object_id_column], how='inner', on = object_id_column).drop_duplicates()[object_id_column].drop_duplicates()
            if property_id == 'op6':
                ot_2 = non_temporal_parameters[1]
                if ot != ot_2:
                    ot_2_objects_in_time_interval = overlapping_objects_to_time_df.merge(object_types_to_df_map[ot_2][object_id_column], how='inner', on = object_id_column).drop_duplicates()[object_id_column].drop_duplicates()
                    ot_objects_in_time_interval = pd.concat([ot_objects_in_time_interval, ot_2_objects_in_time_interval], ignore_index=True)

            ts_related_objects_df = ot_objects_in_time_interval.rename('objectId').to_frame()
            ts_related_objects_df['qualifier'] = qualifer_str
            ts_related_objects_json = ts_related_objects_df.to_dict('records')
            relationships_list[i] = ts_related_objects_json

            """  related_objs_json = json_objects_df[json_objects_df['id'].isin(ot_objects_in_time_interval.values)]['relationships']
            if related_objs_json.isna().all():
                empty_column = pd.Series([[]] * len(related_objs_json), index=related_objs_json.index, name = 'relationships')
                related_objs_json = empty_column
            related_objs_json = related_objs_json + pd.Series([[{'objectId': ts_obj_id, 'qualifier': qualifer_str}]] * len(related_objs_json), related_objs_json.index.values.tolist(), name='relationships')
            json_objects_df.loc[related_objs_json.index, 'relationships'] = related_objs_json """
            #connect time series that are only linked to objects (e.g. time series for object frequency)
            #to a dummy event. This is done to preserve these time series in the log during future iterations
            #as pm4py discards any objects that are not related to a event when reading a log.

            start_dummy_ev_idx = json_events_df.loc[json_events_df['id']=='start_dummy_event'].index.values[0]
            end_dummy_ev_idx = json_events_df.loc[json_events_df['id']=='end_dummy_event'].index.values[0]
            start_dummy_ev_relationships = json_events_df.loc[json_events_df['id']=='start_dummy_event', 'relationships'].iloc[0]
            end_dummy_ev_relationships = json_events_df.loc[json_events_df['id']=='end_dummy_event', 'relationships'].iloc[0]
            
            if not start_dummy_ev_relationships:
                start_dummy_ev_relationships = []
            elif isinstance(start_dummy_ev_relationships, dict):
                start_dummy_ev_relationships = [start_dummy_ev_relationships]

            if not end_dummy_ev_relationships:
                end_dummy_ev_relationships = []
            elif isinstance(end_dummy_ev_relationships, dict):
                end_dummy_ev_relationships = [end_dummy_ev_relationships]
                
            start_dummy_ev_relationships = start_dummy_ev_relationships + [{'objectId': ts_obj_id, 'qualifier': 'dummy_relationship'}]
            end_dummy_ev_relationships = end_dummy_ev_relationships + [{'objectId': ts_obj_id, 'qualifier': 'dummy_relationship'}]

            json_events_df.at[start_dummy_ev_idx, 'relationships'] = start_dummy_ev_relationships
            json_events_df.at[end_dummy_ev_idx, 'relationships'] = end_dummy_ev_relationships

        i = i + 1
    #set time series dataframe columns
    ts_objs_df['id'] = ts_obj_id_list
    ts_objs_df['type'] = ts_obj_type_list
    ts_objs_df['attributes'] = attributes_list
    ts_objs_df['relationships'] = relationships_list
    json_objects_df = pd.concat([json_objects_df, ts_objs_df], ignore_index= True)
    #some cleanup
    json_objects_df['relationships'] = json_objects_df['relationships'].fillna('').apply(list)
    json_objects_df['attributes'] = json_objects_df['attributes'].fillna('').apply(list)
    json_events_df['relationships'] = json_events_df['relationships'].fillna('').apply(list)
    json_events_df['attributes'] = json_events_df['attributes'].fillna('').apply(list)

    ocel_json_dict_mod = {}
    ocel_json_dict_mod['objects'] = json_objects_df.to_dict('records')
    ocel_json_dict_mod['events'] = json_events_df.to_dict('records')
    ocel_json_dict_mod['eventTypes'] = json_event_types_df.to_dict('records')
    ocel_json_dict_mod['objectTypes'] = json_object_types_df.to_dict('records')
    return ocel_json_dict_mod


#Convert ar to OCED and plug back into original OCEL
def insert_ar_into_ocel(ar_collection, tsa_technique, tsa_params, ocel_json_dict, property_names_dict, time_intervals, offset):

    #load ocel components into dataframes
    json_objects_df = pd.DataFrame(ocel_json_dict['objects'])
    json_events_df = pd.DataFrame(ocel_json_dict['events'])
    json_object_types_df = pd.DataFrame(ocel_json_dict['objectTypes'])
    json_event_types_df = pd.DataFrame(ocel_json_dict['eventTypes'])

    #below code is needed in case if no events or objects have any attributes in the log
    if not 'attributes' in json_events_df.columns.values:
        column_list = [[]] * len(json_events_df)
        json_events_df['attributes'] = column_list
    if not 'attributes' in json_objects_df.columns.values:
        column_list = [[]] * len(json_objects_df)
        json_objects_df['attributes'] = column_list

    #some cleanup
    json_objects_df['relationships'] = json_objects_df['relationships'].fillna('').apply(list)
    json_objects_df['attributes'] = json_objects_df['attributes'].fillna('').apply(list)
    json_events_df['relationships'] = json_events_df['relationships'].fillna('').apply(list)
    json_events_df['attributes'] = json_events_df['attributes'].fillna('').apply(list)

#attribute name contains the tsa technique name and a dictionary (converted to string) of all associated parameters
    attr_name = tsa_technique + '(' + ', '.join(str(x) for x in tsa_params.values() if x != None) + ')'
    if tsa_technique != 'Granger Causality':

        #create object attribute for 'time series' object type to store analysis results of type other than granger causality
        ts_obj_type_attributes = json_object_types_df.loc[json_object_types_df['name'] == 'time series', 'attributes'].iloc[0]
        ts_obj_type_idx = json_object_types_df[json_object_types_df['name'] == 'time series'].index.values[0]
        if not ts_obj_type_attributes:
            ts_obj_type_attributes = []
        elif isinstance(ts_obj_type_attributes, dict):
            ts_obj_type_attributes = [ts_obj_type_attributes]

        ts_obj_type_attributes_mod = ts_obj_type_attributes + [{'name': attr_name, 'type': 'float'}]
        json_object_types_df.at[ts_obj_type_idx, 'attributes'] = ts_obj_type_attributes_mod

        for tsid, ar in ar_collection.items():
            #get all relevant variable values
            property_id = tsid[0]
            property_name = property_names_dict[property_id]
            non_temporal_parameters = tsid[1]
            if isinstance(non_temporal_parameters, tuple):
                non_temporal_parameters_str = '_'.join(non_temporal_parameters)
            else:
                non_temporal_parameters_str = str(non_temporal_parameters)
            ts_obj_id = 'ts-' + property_id + '-' + non_temporal_parameters_str

            #we create an object attribute for the ar that will have an initial value of 0.
            # Then for each index in ar, we set the attribute value as 1 with the timestamp set at the end of that interval.
            # We set the attribute value to 0 for the next interval, unless the index for the next interval is also in ar in which case it will 
            #also be set as 1 and so on and so forth.

            ts_obj_attributes = json_objects_df[json_objects_df['id'] == ts_obj_id]['attributes'].iloc[0]
            ts_obj_idx = json_objects_df[json_objects_df['id'] == ts_obj_id].index.values[0]
            if not ts_obj_attributes:
                ts_obj_attributes = []
            elif isinstance(ts_obj_attributes, dict):
                ts_obj_attributes = [ts_obj_attributes]

            if tsa_technique == 'Change Point Detection' or tsa_technique == 'Threshold Based Point Detection':
                ts_obj_attributes = ts_obj_attributes + [{'name': attr_name, 'value': 0, 'time': '1970-01-01T00:00:00.000Z'}]
                for index in ar:
                    if not index+1 in ar:
                        if index+1 != len(time_intervals):
                            ts_obj_attributes = ts_obj_attributes + \
                                [{'name': attr_name, 'value': 1, 'time': (time_intervals[index].right - pd.Timedelta('1s')).isoformat().replace("+00:00", ".000Z")}, \
                                            {'name': attr_name, 'value': 0, 'time': (time_intervals[index + 1].right - pd.Timedelta('1s')).isoformat().replace("+00:00", ".000Z")}]
                        else:
                            ts_obj_attributes = ts_obj_attributes + \
                                [{'name': attr_name, 'value': 1, 'time': (time_intervals[index].right - pd.Timedelta('1s')).isoformat().replace("+00:00", ".000Z")}, \
                                            {'name': attr_name, 'value': 0, 'time': ((time_intervals[index].right + offset)  - pd.Timedelta('1s')).isoformat().replace("+00:00", ".000Z")}]
                    else:
                        ts_obj_attributes = ts_obj_attributes + \
                        [{'name': attr_name, 'value': 1, 'time': (time_intervals[index].right - pd.Timedelta('1s')).isoformat().replace("+00:00", ".000Z")}]
                json_objects_df.at[ts_obj_idx, 'attributes'] = ts_obj_attributes
            elif tsa_technique == 'Forecasting':
                fc_df = ar_collection[tsid]
                if not fc_df.empty:
                    fc_df = fc_df.rename('value').to_frame().reset_index().rename(columns={'index': 'time'})
                    fc_df['time'] = fc_df['time'].map(lambda x: x.isoformat().replace("+00:00", ".000Z"))
                    fc_df['name'] = attr_name
                    fc_df = fc_df[['name', 'value', 'time']]
                    fc_df.loc[len(fc_df)] = {'name':attr_name, 'value':0, 'time':'1970-01-01T00:00:00.000Z'}
                    fc_df = fc_df.sort_values(by='time', ignore_index= True)
                    fc_dict = fc_df.to_dict('records')
                    ts_obj_attributes = ts_obj_attributes + fc_dict
                    json_objects_df.at[ts_obj_idx, 'attributes'] = ts_obj_attributes
    else:
        ar_collection_list = ar_collection.groupby('caused').agg(list).reset_index().to_dict('records')
        for ar in ar_collection_list:
            caused_tsid = ar['caused']
            caused_ts_property_id = caused_tsid[0]
            caused_ts_non_temporal_parameters = caused_tsid[1]
            if isinstance(caused_ts_non_temporal_parameters, tuple):
                caused_ts_non_temporal_parameters_str = '_'.join(caused_ts_non_temporal_parameters)
            else:
                caused_ts_non_temporal_parameters_str = str(caused_ts_non_temporal_parameters)
            caused_ts_obj_id = 'ts-' + caused_ts_property_id + '-' + caused_ts_non_temporal_parameters_str

            caused_ts_obj_relationships = json_objects_df[json_objects_df['id'] == caused_ts_obj_id]['relationships'].iloc[0]
            caused_ts_obj_idx = json_objects_df[json_objects_df['id'] == caused_ts_obj_id].index.values[0]
            if not caused_ts_obj_relationships:
                caused_ts_obj_relationships = []
            elif isinstance(caused_ts_obj_relationships, dict):
                caused_ts_obj_relationships = [caused_ts_obj_relationships]

            causing_ts_list = ar['causing']
            lag_list = ar['lag']
            for i in range(0, len(causing_ts_list)):
                causing_tsid = causing_ts_list[i]
                causing_ts_property_id = causing_tsid[0]
                causing_ts_non_temporal_parameters = causing_tsid[1]
                if isinstance(causing_ts_non_temporal_parameters, tuple):
                    causing_ts_non_temporal_parameters_str = '_'.join(causing_ts_non_temporal_parameters)
                else:
                    causing_ts_non_temporal_parameters_str = str(causing_ts_non_temporal_parameters)
                causing_ts_obj_id = 'ts-' + causing_ts_property_id + '-' + causing_ts_non_temporal_parameters_str
                lag = lag_list[i]
                caused_ts_obj_relationships = caused_ts_obj_relationships + [{'objectId': causing_ts_obj_id, 'qualifier': f'Granger caused by (with lags: {lag})'}]
            json_objects_df.at[caused_ts_obj_idx, 'relationships'] = caused_ts_obj_relationships

    ocel_json_dict_mod = {}
    ocel_json_dict_mod['objects'] = json_objects_df.to_dict('records')
    ocel_json_dict_mod['events'] = json_events_df.to_dict('records')
    ocel_json_dict_mod['eventTypes'] = json_event_types_df.to_dict('records')
    ocel_json_dict_mod['objectTypes'] = json_object_types_df.to_dict('records')
    return ocel_json_dict_mod


json_schema= {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "eventTypes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": { "type": "string" },
                    "attributes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": { "type": "string" },
                                "type": { "type": "string" }
                            },
                            "required": ["name", "type"]
                        }
                    }
                },
                "required": ["name", "attributes"]
            }
        },
        "objectTypes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": { "type": "string" },
                    "attributes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": { "type": "string" },
                                "type": { "type": "string" }
                            },
                            "required": ["name", "type"]
                        }
                    }
                },
                "required": ["name", "attributes"]
            }
        },
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": { "type": "string" },
                    "type": { "type": "string" },
                    "time": { "type": "string", "format": "date-time" },
                    "attributes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": { "type": "string" },
                                "value": { "type": ["string", "number"] }
                            },
                            "required": ["name", "value"]
                        }
                    },
                    "relationships": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "objectId": { "type": "string" },
                                "qualifier": { "type": "string" }
                            },
                            "required": ["objectId", "qualifier"]
                        }
                    }
                },
                "required": ["id", "type", "time"]
            }
        },
        "objects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": { "type": "string" },
                    "type": { "type": "string" },
                    "relationships": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "objectId": { "type": "string" },
                                "qualifier": { "type": "string" }
                            },
                            "required": ["objectId", "qualifier"]
                        }
                    },
                    "attributes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": { "type": "string" },
                                "value": { "type": ["string","number"] },
                                "time": { "type": "string", "format": "date-time" }
                            },
                            "required": ["name", "value", "time"]
                        }
                    }
                },
                "required": ["id", "type"]
            }
        }
    },
    "required": ["eventTypes", "objectTypes", "events", "objects"]
}