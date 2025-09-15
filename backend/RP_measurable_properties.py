import pm4py
import pandas as pd
import numpy as np
import pandas as pd
from setup import agg

def rp1(ep4_dict, resource_object_type):

    rp1_dict = {}
    for (event_type, object_type), ts in ep4_dict.items():
        if object_type == resource_object_type:
            rp1_dict[(event_type, resource_object_type)] = ts
    return rp1_dict


def rp2(event_to_object_relations_df, events_to_time_df, resource_object_type, sampling_rate,  \
        event_id_column = 'ocel:eid', object_type_column = 'ocel:type'):
     
    df = event_to_object_relations_df[event_to_object_relations_df[object_type_column] == resource_object_type]
    df = df.merge(events_to_time_df, on = event_id_column, how='inner')
    rp2_dict = {}
    ts_id= resource_object_type
    df[ts_id] = 1
    df = df[['assignment_mechanism_time', ts_id]]
    df = df.set_index('assignment_mechanism_time')
    ts = df[ts_id]
    ts = ts.resample(sampling_rate).sum()
    rp2_dict[resource_object_type] = ts
    return rp2_dict

def rp3(op2_dict, resource_object_type):

    rp3_dict = {}
    for (object_type, object_attribute), ts in op2_dict.items():
        if object_type == resource_object_type:
            rp3_dict[object_type, object_attribute] = ts
    return rp3_dict
