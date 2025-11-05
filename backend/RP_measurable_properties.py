import pandas as pd
import numpy as np
import pandas as pd
from setup import agg

#For each event type, provides time series for number of involved resource 
#related to events. Since we consider resources to specified as objects in the log, it is a subset of the 
#time series collection for ep4 i.e. number of objects of a type per event. We get all ep4 time series where the object type is
#equal to the resource object type.
def rp1(ep4_dict, resource_object_type):

    rp1_dict = {}
    for (event_type, object_type), ts in ep4_dict.items():
        if object_type == resource_object_type:
            rp1_dict[(event_type, resource_object_type)] = ts
    return rp1_dict


#Generates a single time series for the number of active resource per time period (regardless of event type).
#Time series is stored in a dict nevertheless to maintain consistent interfacing with external functions.
def rp2(event_to_object_relations_df, events_to_time_df, resource_object_type, sampling_rate,  \
        event_id_column = 'ocel:eid', object_type_column = 'ocel:type', object_id_column = 'ocel:oid'):
     
    df = event_to_object_relations_df[event_to_object_relations_df[object_type_column] == resource_object_type]
    df = df.merge(events_to_time_df, on = event_id_column, how='inner')
    rp2_dict = {}
    if not df.empty:
        ts_id= object_id_column
        df = df[['assignment_mechanism_time', ts_id]]
        df = df.set_index('assignment_mechanism_time')
        ts = df[ts_id]
        ts = ts.resample(sampling_rate, label='right', closed='right').agg(set).str.len()
        rp2_dict[resource_object_type] = ts
    return rp2_dict

#For each resource attribute, provides time series for the value of the attribute. 
#Since we consider resources to specified as objects in the log, it is a subset of the 
#time series collection for op2 i.e. object attribute values. We get all op2 time series where the object type is
#equal to the resource object type.
def rp3(op2_dict, resource_object_type):

    rp3_dict = {}
    for (object_type, object_attribute), ts in op2_dict.items():
        if object_type == resource_object_type:
            rp3_dict[object_type, object_attribute] = ts
    return rp3_dict
