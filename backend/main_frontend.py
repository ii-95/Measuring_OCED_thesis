import pm4py
import numpy as np
import pandas as pd
from pathlib import Path
from setup import *
from EP_measurable_properties import *
from OP_measurable_properties import *
from PP_measurable_properties import *
from RP_measurable_properties import *
from time_series_analysis import *
from tsa_to_oced import *
from dotenv import load_dotenv
import os
import math
from statsmodels.tools.sm_exceptions import InterpolationWarning, ValueWarning
import warnings
from jsonschema import validate
import json
import datetime
import streamlit as st
import zipfile
from streamlit_js_eval import streamlit_js_eval
pd.options.mode.copy_on_write = True
warnings.simplefilter('ignore', InterpolationWarning)
warnings.simplefilter('ignore', ValueWarning)
load_dotenv(dotenv_path="inputs.env")
st.set_page_config(layout="wide")
st.set_page_config(page_title="Measuring OCED")

if st.sidebar.button("Reset", width='stretch', type='primary', icon=":material/refresh:"):
    streamlit_js_eval(js_expressions="parent.window.location.reload()")

# Disable the submit button after it is clicked
def disable(form_key):
    st.session_state[form_key] = True

# Initialize disabled for form_submit_button to False
form_keys = ['ocel_file_form_disable', 'atomic_evs_form_disable', 'events_endtime_column_form_disable', 'ocel_input_details_form_disable','resource_object_type_form_disable', 'tsa_form_disable', 'tsa_params_form_disable', 'append_forecasts_form_disable']
for form_key in form_keys:
    if form_key not in st.session_state:
        st.session_state[form_key] = False

session_state_variables = {'ocel_file_path':{}, 'non_atomic_evs_str':'', 'resource_obj_str': '', 'event_endtime_column':'', 'ocel_json_dict': {},  'events_df' : '', \
                            'event_types' : '', 'object_types' : '', 'event_object_combinations' : [], 'objects_summary_df' : '', 'event_to_object_relations_df' : '', \
                            'objects_df' : '', 'object_changes_df' : '', 'first_event_timestamp':'', 'last_event_timestamp':'', 'aggregation_mode':'', 'sampling_rate':'',\
                            'assignment_mechanism':'', 'int_start':'', 'time_intervals':'', 'events_to_time_df':'', 'objects_to_time_df':'', 'overlapping_objects_to_time_df':'', 'object_types_to_df_map':{},\
                            'event_types_to_df_map':{}, 'min_seasonal_period':'', 'max_seasonal_period':'', 'TS_collection':{}, 'prev_iterations_data':{},\
                            'change_point_indices_dict' : {}, 'ts_causal_factors_dict' : {}, 'change_point_idx_ts_dict' : {}, 'threshold_based_ts_dict' : {}, 'ts_forecasts_df' : '',\
                            'granger_df':'', 'forecast_column':'', 'ar_collection':{}, 'ts_mod_ocel_json_dict': {}, 'mod_ocel_json_dict' : {}, 'mod_ocel':'',\
                            'int_end':'', 'selected_properties':'', 'selected_object_types':'', 'selected_event_types':'', 'resource_object_type':'', 'tsa_params': {}, 'tsa_technique':'',\
                            'mode':'', 'comparison_operator':'', 'threshold_1':'', 'threshold_2':'', 'use_change_point_difference_as_lag':'No', 'use_tbpd_results_as_ts_for_granger_causality':'No', \
                            'only_compare_threshold_ts':'No', 'use_granger_causal_ts_as_exogenous_variables':'No', 'append_forecasts_to_ts':'', 'granger_additional_option':'', \
                            'p_value_threshold':'', 'periods_to_predict':'', 'edit_advanced_arima_settings':'', 'edit_advanced_pelt_settings':'', 'ar_history':{}, 'ar_ts_history':{}, 'ar_params_history':{}, \
                            'ar_json_history':{}, 'tbpd_params_list': [], 'ts_related_events_and_objects_dfs': {}, 'is_ar_empty':False}

for variable, init_value in session_state_variables.items():
    if variable not in st.session_state:
        st.session_state[variable] = init_value

def file_selector(folder_path='input_logs'):
    filenames = os.listdir(folder_path)
    accepted_filenames = ['']
    for filename in filenames:
        if filename.endswith('.json'):
            accepted_filenames.append(filename)
    selected_filename = st.selectbox('Select a file', accepted_filenames)
    if selected_filename:
        return os.path.join(folder_path, selected_filename)

ocel_file_path = st.session_state['ocel_file_path']
if not ocel_file_path:
    with st.sidebar.form('ocel_file_form'):
        selected_ocel_file_path = file_selector()
        disable_form_key = 'ocel_file_form_disable'
        st.form_submit_button('Confirm Selection', on_click=disable, args=(disable_form_key, ), disabled=st.session_state[disable_form_key])

    if not selected_ocel_file_path:
        st.stop()
    else:
        ocel_file_path = selected_ocel_file_path
        st.session_state['ocel_file_path'] = selected_ocel_file_path
        st.rerun()
else:
    st.sidebar.write(f'**OCEL**: :blue[{ocel_file_path}]')

if not ocel_file_path:
    st.stop()

non_atomic_evs_str = st.session_state['non_atomic_evs_str']
resource_obj_str = st.session_state['resource_obj_str']

if not non_atomic_evs_str or not resource_obj_str:
    with st.sidebar.form('atomic_evs_form'):
        selected_non_atomic_evs_str = st.selectbox('Does the log contain non-atomic events?', ['', 'No', 'Yes'])
        selected_resource_obj_str = st.selectbox('Does the log contain an object type representing resources/employees?', ['', 'No', 'Yes'])
        st.form_submit_button('Confirm Selection')

        if not selected_non_atomic_evs_str or not selected_resource_obj_str:
            st.stop()
        else:
            non_atomic_evs_str = selected_non_atomic_evs_str
            resource_obj_str = selected_resource_obj_str
            st.session_state['non_atomic_evs_str'] = selected_non_atomic_evs_str
            st.session_state['resource_obj_str'] = selected_resource_obj_str
            st.rerun()
else:
    st.sidebar.markdown(f'**Contains non-atomic events**: :blue[{non_atomic_evs_str}]')
    st.sidebar.markdown(f'**Contains object type representing resources/employees**: :blue[{resource_obj_str}]')

event_endtime_column = st.session_state['event_endtime_column']
if non_atomic_evs_str == 'Yes':
        if not event_endtime_column:
            with st.sidebar.form('events_endtime_column_form'):
                selected_event_endtime_column = st.text_input('Please enter the event attribute containing the endtime for non-atomic events')
                disable_form_key = 'events_endtime_column_form_disable'
                st.form_submit_button('Confirm Selection', on_click=disable, args=(disable_form_key, ), disabled=st.session_state[disable_form_key])
            
            if not selected_event_endtime_column:
                st.stop()
            else:
                event_endtime_column = selected_event_endtime_column
                st.session_state['event_endtime_column'] = selected_event_endtime_column
                st.rerun()
        else:
            st.sidebar.write(f'**Event endtime column**: :blue[{event_endtime_column}]')
else:
    st.session_state['event_endtime_column'] = ''
    event_endtime_column = ''


path_to_ocel = Path(ocel_file_path).resolve()


def read_ocel_from_path(path_to_ocel):
    format = path_to_ocel.suffix
    if format == '.json':
        ocel = pm4py.read_ocel2_json(path_to_ocel)
    elif format == '.sqlite':
        ocel = pm4py.read_ocel2_sqlite(path_to_ocel)
    else:
        raise TypeError('Invalid or unsupported OCEL 2.0 format. Please provide a json or sqlite file.')
    return ocel


if 'ocel' not in st.session_state:
    ocel = read_ocel_from_path(path_to_ocel)
    st.session_state['ocel'] = ocel
else:
    ocel = st.session_state['ocel']


input_ocel_filename = ''.join(path_to_ocel.name.split('.')[:-1])
#for conversion of timeseries and analysis results to ocel, we need to convert the log into json format.
#This is also done even if the original ocel file was in json format as pm4py performs some cleanup activities that are helpful
#in maintaining a uniform structure of the input log and hence result in stable functionality of this tool.
#e.g. resetting initial values of object attributes to timestamp 0 ("1970-01-01T00:00:00Z") or removing objects that are not
#related to any events.
ocel_json_dict = st.session_state['ocel_json_dict']

if not ocel_json_dict:
    converted_ocel_file_path =  str(Path('backend/assets/temp/convert_ocel.json').resolve())
    try:
        os.remove(converted_ocel_file_path)
    except OSError:
        pass
    pm4py.write_ocel2_json(ocel, converted_ocel_file_path)
    with open('backend/assets/temp/convert_ocel.json') as f:
        ocel_json_dict = json.load(f)
        st.session_state['ocel_json_dict'] = ocel_json_dict

#get ocel column and variable names
event_id_column = ocel.event_id_column
event_timestamp_column = ocel.event_timestamp
event_type_column = ocel.event_activity
object_id_column = ocel.object_id_column
object_type_column = ocel.object_type_column
changed_field_column = ocel.changed_field
qualifier_column = ocel.qualifier

attribute_names = pm4py.ocel.ocel_get_attribute_names(ocel)

if 'tsvalues' in attribute_names:
    first_iteration = False
else:
    first_iteration = True
    
#setup essential tables(dataframes) and variables
events_df = st.session_state['events_df']
if (isinstance(events_df, pd.DataFrame) and events_df.empty) or not isinstance(events_df, pd.DataFrame):
    events_df = get_events_df(ocel)
    st.session_state['events_df'] = events_df

event_types = st.session_state['event_types']
if not event_types:
    event_types = list(events_df[event_type_column].unique())
    st.session_state['event_types'] = event_types
    if non_atomic_evs_str == 'Yes' and event_endtime_column in events_df.columns:
        #for all atomic events (where endtime column has empty/null values, replace with value in ocel:timestamp column)
        events_df = adjust_events_end_time(events_df.copy(), event_endtime_column)

object_types = st.session_state['object_types']
if not object_types:
    object_types = pm4py.ocel.ocel_get_object_types(ocel)
    st.session_state['object_types'] = object_types


event_object_combinations =  st.session_state['event_object_combinations']
if not event_object_combinations:
    event_object_combinations = get_event_object_combinations(ocel, event_type_column, object_type_column)
    st.session_state['event_object_combinations'] = event_object_combinations

event_to_object_relations_df = st.session_state['event_to_object_relations_df']
if not isinstance(event_to_object_relations_df, pd.DataFrame):
    event_to_object_relations_df = get_event_to_object_relations_df(ocel)
    st.session_state['event_to_object_relations_df'] = event_to_object_relations_df

objects_summary_df = st.session_state['objects_summary_df']
if not isinstance(objects_summary_df, pd.DataFrame):
    objects_summary_df = get_objects_summary_df(ocel)
    st.session_state['objects_summary_df'] = objects_summary_df
    if non_atomic_evs_str == 'Yes' and event_endtime_column in events_df.columns:
        # calculate lifecycle end time for objects to be calculated based on the maximum endtime of all events associated with
        # an object. By default, pm4py calculates this assuming atomic events which can not be used if non-atomic events exist.
        objects_summary_df = update_object_lifecycle_end_for_non_atomic_events(objects_summary_df.copy(), event_to_object_relations_df.copy(),\
                                                                        events_df.copy(), event_endtime_column)
        
objects_df = st.session_state['objects_df']
if not isinstance(objects_df, pd.DataFrame):
    objects_df = get_objects_df(ocel)
    st.session_state['objects_df'] = objects_df

object_changes_df = st.session_state['object_changes_df']
if not isinstance(object_changes_df, pd.DataFrame):
    object_changes_df = get_object_changes_df(ocel)
    st.session_state['object_changes_df'] = object_changes_df


if non_atomic_evs_str == 'Yes':
    if event_endtime_column in events_df.columns:
        atomic_evs = False
    else:
        st.sidebar.warning('The event attribute specified for the endtime of non-atomic events was not found in the log and hence will not be considered i.e., the events will be treated as atomic. ')
        atomic_evs = True
else:
    atomic_evs = True

first_event_timestamp = st.session_state['first_event_timestamp']
if not first_event_timestamp:
    first_event_timestamp = pd.to_datetime(events_df[event_timestamp_column].min(), utc = True)
    st.session_state['first_event_timestamp'] = first_event_timestamp

last_event_timestamp = st.session_state['last_event_timestamp']
if not last_event_timestamp:
    if not atomic_evs:
        last_event_timestamp = pd.to_datetime(events_df[event_endtime_column].max(), utc = True)
    else:
        last_event_timestamp = pd.to_datetime(events_df[event_timestamp_column].max(), utc = True)
    st.session_state['last_event_timestamp'] = last_event_timestamp

property_names_dict = {
                    'ep1': 'Event Frequency',\
                    'ep2': 'Event Attribute Value', \
                    'ep3': 'Number of Objects per Event', \
                    'ep4': 'Number of Objects of a type per Event' , \
                    'op1': 'Object Frequency',\
                    'op2': 'Object Attribute Value', \
                    'op3': 'Number of Events per Object', \
                    'op4': 'Number of Events of a Type per Object', \
                    'op5': 'Lifecycle Duration (Hours)', \
                    'op6': 'Number of Object Interactions per Event', \
                    'pp1': 'Waiting Time (Hours)', \
                    'pp2': 'Synchronization Time (Hours)', \
                    'pp3': 'Service Time (Hours)', \
                    'pp4': 'Soujourn Time (Hours)', \
                    'pp5': 'Flow Time (Hours)', \
                    'pp6': 'Pooling Time(Hours)',\
                    'pp7': 'Lagging Time(Hours)', \
                    'rp1': 'Number of Involved Resources per Event',\
                    'rp2': 'Number of Active Resources',\
                    'rp3': 'Resource Attribute'
                    }


property_parameters_map = {
                    'ep1': ['event type'],\
                    'ep2': ['event type', 'event attribute'], \
                    'ep3': ['event type'], \
                    'ep4': ['event type', 'object type'], \
                    'op1': ['object type'],\
                    'op2': ['object type', 'object attribute'], \
                    'op3': ['object type'], \
                    'op4': ['object type', 'event type'], \
                    'op5': ['object type'], \
                    'op6': ['object type', 'object type'], \
                    'pp1': ['event type'], \
                    'pp2': ['event type'], \
                    'pp3': ['event type'], \
                    'pp4': ['event type'], \
                    'pp5': ['event type'], \
                    'pp6': ['event type', 'object type'],\
                    'pp7': ['event type', 'object type'], \
                    'rp1': ['event type', 'object type'],\
                    'rp2': ['object type'],\
                    'rp3': ['object type', 'object attribute']
                    }

if resource_obj_str == 'Yes':
    property_names_list = [ value + '-' + key for key,value in property_names_dict.items()]
else:
    property_names_list = [ value + '-' + key for key,value in property_names_dict.items() if not key.startswith('rp')]

sampling_rates = ['Daily', 'Weekly', 'Monthly', 'Quarterly', 'Yearly']
aggregation_modes = ['mean', 'min', 'max', 'sum']
assignment_mechanisms = ['overlaps', 'contains', 'starting', 'ending']

aggregation_mode = st.session_state['aggregation_mode']
sampling_rate = st.session_state['sampling_rate']
assignment_mechanism = st.session_state['assignment_mechanism']
int_start = st.session_state['int_start']
int_end = st.session_state['int_end']
selected_properties = st.session_state['selected_properties']
selected_object_types = st.session_state['selected_object_types']
selected_event_types = st.session_state['selected_event_types']
resource_object_type = st.session_state['resource_object_type']
selected_time_interval = None
if not aggregation_mode or not sampling_rate or not assignment_mechanism or not int_start or not int_end or not selected_properties or not selected_object_types or not selected_event_types:
    with st.sidebar.form("ocel_input_details_form"):
        selected_aggregation_mode = st.selectbox('Aggregation Function', aggregation_modes)
        selected_sampling_rate = st.selectbox('Sampling Rate', sampling_rates)
        selected_assignment_mechanism = st.selectbox('Assignment Mechanism', assignment_mechanisms)
        selected_time_interval = st.date_input(
            label = "Timeframe",
            value= (first_event_timestamp,last_event_timestamp),
            min_value = first_event_timestamp,
            max_value = last_event_timestamp,
            format= "YYYY-MM-DD"
            )
        if selected_time_interval:
            selected_int_start = pd.to_datetime(selected_time_interval[0], utc=True) + pd.Timedelta('1s') 
            selected_int_end = pd.to_datetime(selected_time_interval[1], utc=True) + pd.Timedelta('1D') -  pd.Timedelta('1s')
        selected_selected_object_types = st.multiselect('Select one or more object type(s) to analyze',  object_types)
        selected_selected_event_types = st.multiselect('Select one or more event type(s) to analyze',  event_types)
        selected_selected_properties = st.multiselect('Select one or more properties to analyze', property_names_list)
        disable_form_key = 'ocel_input_details_form_disable'
        st.form_submit_button('Confirm Selection', on_click=disable, args=(disable_form_key, ), disabled=st.session_state[disable_form_key])

    if not selected_aggregation_mode or not selected_sampling_rate or not selected_assignment_mechanism or not selected_int_start or not selected_int_end or not selected_selected_properties or not selected_selected_object_types or not selected_selected_event_types:
        st.stop()
    else:
        aggregation_mode = selected_aggregation_mode
        sampling_rate = selected_sampling_rate
        assignment_mechanism = selected_assignment_mechanism
        #int_start = selected_int_start
        #int_end = selected_int_end
        selected_properties = selected_selected_properties
        selected_object_types = selected_selected_object_types
        selected_event_types = selected_selected_event_types
        st.session_state['aggregation_mode'] = selected_aggregation_mode
        st.session_state['sampling_rate'] = selected_sampling_rate
        st.session_state['assignment_mechanism'] = selected_assignment_mechanism
        st.session_state['int_start'] = selected_int_start
        st.session_state['int_end'] = selected_int_end
        st.session_state['selected_properties'] = selected_selected_properties
        st.session_state['selected_object_types'] = selected_selected_object_types
        st.session_state['selected_event_types'] = selected_selected_event_types
        st.rerun()
        
else:
    st.sidebar.write(f'**Aggregation Function**: :blue[{aggregation_mode}]')
    st.sidebar.write(f'**Sampling Rate**: :blue[{sampling_rate}]')
    st.sidebar.write(f'**Assignment Mechanism**: :blue[{assignment_mechanism}]')
    st.sidebar.write(f'**Selected Object Types**: :blue[{selected_object_types}]')
    st.sidebar.write(f'**Selected Event Types**: :blue[{selected_event_types}]')
    st.sidebar.write(f'**Selected Properties**: :blue[{selected_properties}]')

    a, b, c = st.columns(3)
    e, f = st.columns(2)

    a.metric("Aggregation Function", aggregation_mode, border=True)
    b.metric("Sampling Rate", sampling_rate, border=True)
    c.metric("Assignment Mechanism", assignment_mechanism, border=True)
resource_properties_selected = False
for property in selected_properties:
    if 'Resource' in property:
        resource_properties_selected = True
        break
if resource_properties_selected:
    if not resource_object_type:
        with st.sidebar.form("resource_object_type_form"):
            selected_resource_object_type = st.selectbox('Select resource object type', [''] + selected_object_types)
            disable_form_key = 'resource_object_type_form_disable'
            st.form_submit_button('Confirm Selection', on_click=disable, args=(disable_form_key, ), disabled=st.session_state[disable_form_key])
        
        if not selected_resource_object_type:
            st.stop()
        else:
            resource_object_type = selected_resource_object_type
            st.session_state['resource_object_type'] = selected_resource_object_type
            st.rerun()
    else:
        st.sidebar.write(f'**Selected Resource Object Type**: :blue[{resource_object_type}]')

#map user input to backend variables
selected_property_ids= []
for property in selected_properties:
    selected_property_ids.append(property.split('-')[-1])



if sampling_rate == 'Weekly':
    if int_start.weekday() == 6:
        start_offset_n = 0
    else:
        start_offset_n = 1
elif sampling_rate == 'Monthly':
    if int_start.day == 1 or check_if_last_day_of_month(int_start):
        start_offset_n = 1
    else:
        start_offset_n = 2
elif sampling_rate == 'Yearly':
    if (int_start.day == 1 and int_start.month ==1) or check_if_last_day_of_year(int_start):
        start_offset_n = 1
    else:
        start_offset_n = 2
else:
    start_offset_n = 0


if sampling_rate == 'Daily':
    sampling_rate = 'D'
elif sampling_rate == 'Weekly':
    sampling_rate = 'W'
elif sampling_rate == 'Monthly':
    sampling_rate = 'ME'
elif sampling_rate == 'Quarterly':
    sampling_rate = 'QE'
elif sampling_rate == 'Yearly':
    sampling_rate = 'YE'

starting_offset = get_starting_offset_for_sampling_rate(start_offset_n, sampling_rate)
ending_offset = get_ending_offset_for_sampling_rate(sampling_rate)
offset = get_offset_for_sampling_rate(sampling_rate)

#The time periods according to sampling rates are as follows:
#If sampling rate is 'Daily' then the time period ranges from midnight to midnight
#If sampling rate is 'Weekly' then the time period ranges from midnight of Sunday till the midnight of next Sunday.
#If sampling rate is 'Monthly' then the time period ranges from the midnight of last day of a month till the end of 2nd last day of the next month.
#If sampling rate is 'Quarterly' then the time period ranges from the midnight of last day of a quarter till the end of the 2nd last day of the next quarter.
#If sampling rate is 'Yearly' then the time period ranges from the midnight of last day of a year till the end of the 2nd last day of the next year.

#get time intervals given the sampling rate and total interval. The start and end are first adjusted by an offset 
#(depending on the sampling rate) such that int_start is offset to the midnight of the first day of its respective time interval 
# and int_end to the midnight of the first day of the next time interval.
#e.g. if sampling rate is Monthly (ME) then int_start = 2023-03-02 12:23:44+00:00 becomes 2023-02-29 00:00:00+00:00
#and int_end = 2024-05-28 12:23:56+00:00 becomes 2024-06-30 00:00:00
#The intervals represent the division of the total interval into time intervals of length equal to the sampling rate.

time_intervals = st.session_state['time_intervals']
if not isinstance(time_intervals, pd.IntervalIndex):
    time_intervals = get_time_intervals(int_start, int_end, sampling_rate, starting_offset, ending_offset)
    st.session_state['time_intervals'] = time_intervals
if len(time_intervals) < 4:
    st.error(f'The specified sampling rate and/or time interval range leads to time series containing too few ({len(time_intervals)}) data points. \n A minimum of 4 data points per timeseries are needed for the tool to function whereas atleast 30 points are recommended for viable results. \n Consider using a finer sampling rate or expanding the time period.')
    st.stop()
elif len(time_intervals) <= 12:
    st.warning(f'The specified sampling rate and/or time interval range leads to time series containing too few ({len(time_intervals)}) data points whereas a minimum of 30 data points is recommended. \n This will lead to unreliable analysis results and in extreme cases, failure to execute the analysis altogether. \n For timeseries of less than or equal to 12 data points, \'Granger Causality\' and \'Forecasting\' cannot be performed. \n Consider using a finer sampling rate or expanding the time period.')
#update start and end according to the time intervals calculated
int_start = time_intervals[0].left
int_end = time_intervals[-1].right
st.session_state['int_start'] = int_start
st.session_state['int_end'] = int_end
st.sidebar.write(f'**Analysis Time Period**: :blue[{int_start.isoformat()} - {int_end.isoformat()}]')
e.metric("Starting Time", str(int_start.date()), border=True)
f.metric("Ending Time", str(int_end.date()), border=True)

#get a cross product of objects and events df with the time intervals
#ti_cross_objs_df = get_time_intervals_cross_objects_summary_df(objects_summary_df, time_intervals)
#ti_cross_evs_df = get_time_intervals_cross_events_df(events_df, time_intervals, event_endtime_column)

#get list of events and objects assigned to a time interval 
#if assign_mech = overlap then we get duplicate events/objects
#if assign_mech = contains then a lot of events/objects are usually discarded
#if assign_mech = starting or assign_mech = ending then we get the same number of events/objects as in the original ocel
#atomic events remain unaffected by assign_mech and are neither duplicated nor discarded.
events_to_time_df = st.session_state['events_to_time_df']
if not isinstance(events_to_time_df, pd.DataFrame):
    events_to_time_df = get_events_to_time_df(events_df.copy(), time_intervals, assignment_mechanism, event_endtime_column, atomic_evs)
    st.session_state['events_to_time_df'] = events_to_time_df

objects_to_time_df = st.session_state['objects_to_time_df']
overlapping_objects_to_time_df = st.session_state['overlapping_objects_to_time_df']
if not isinstance(objects_to_time_df, pd.DataFrame):
    objects_to_time_df = get_objects_to_time_df(objects_summary_df.copy(), time_intervals, assignment_mechanism)
    st.session_state['objects_to_time_df'] = objects_to_time_df
    if assignment_mechanism == 'overlaps':
        overlapping_objects_to_time_df = objects_to_time_df.copy()
    else:
        overlapping_objects_to_time_df = get_objects_to_time_df(objects_summary_df.copy(), time_intervals, 'overlaps')
    st.session_state['overlapping_objects_to_time_df'] = overlapping_objects_to_time_df


object_types_to_df_map = st.session_state['object_types_to_df_map']
if not object_types_to_df_map:
    object_types_to_df_map = get_object_types_to_df_map(objects_df.copy(), object_changes_df.copy(), object_types)
    st.session_state['object_types_to_df_map'] = object_types_to_df_map

event_types_to_df_map = st.session_state['event_types_to_df_map']
if not event_types_to_df_map:
    event_types_to_df_map = get_event_types_to_df_map(events_df.copy(), event_types, atomic_evs, event_endtime_column)
    st.session_state['event_types_to_df_map'] = event_types_to_df_map

#determine range of possible seasonal periods
#minimum seasonal period for each sampling rate is selected manually considering the shortest possible repitive pattern
#that can probably occur in event data.
#Maximum seasonal period is selected as 1/3rd of the time series length because a time series must contain atleast
#a few cycles of the season to be detected. 
#The decisions for minimum and maximum periods were taken based on a review of time series literature and discussions
#Nevertheless, there is no absolutely 'correct' choice.
min_seasonal_period = st.session_state['min_seasonal_period']
max_seasonal_period = st.session_state['max_seasonal_period']
if not max_seasonal_period or not min_seasonal_period:
    series_length = len(time_intervals)
    if sampling_rate == 'D':
        min_seasonal_period = 7
        max_seasonal_period = math.floor(series_length/4)
    elif sampling_rate == 'W':
        min_seasonal_period = 4
        max_seasonal_period = math.floor(series_length/4)
    elif sampling_rate == 'ME':
        min_seasonal_period = 3
        max_seasonal_period = math.floor(series_length/4)
    elif sampling_rate == 'QE':
        min_seasonal_period = 2
        max_seasonal_period = math.floor(series_length/4)
    elif sampling_rate == 'YE':
        min_seasonal_period = 2
        max_seasonal_period = math.floor(series_length/4)
    elif max_seasonal_period < min_seasonal_period:
        max_seasonal_period = min_seasonal_period
    st.session_state['min_seasonal_period'] = min_seasonal_period
    st.session_state['max_seasonal_period'] = max_seasonal_period

if first_iteration:
    TS_collection = st.session_state['TS_collection']
    if not TS_collection:
        event_to_object_relations_df_map = get_event_to_object_type_relations_df_map(event_to_object_relations_df.copy(), event_object_combinations)
        object_interactions_df = get_object_interactions_df(ocel)
        ocel_extended_df = get_ocel_extended_df(ocel)
        #check if the specified endtime attribute for events exists. If yes then we assume the presence of 
        # non-atomic events in the log.
        if event_endtime_column in events_df.columns:
            ocel_extended_df[event_endtime_column] = events_df.merge(ocel_extended_df, on=event_id_column, how='inner')[event_endtime_column]

        event_object_count_df_map = get_event_object_count_df_map(ocel, event_types_to_df_map.copy())
        object_type_summary_df_map = get_object_type_summary_df_map(objects_summary_df.copy(), object_types_to_df_map)

        performance_properties_selected = False
        for property_id in selected_property_ids:
            if property_id.startswith('pp') and property_id!= 'pp3':
                performance_properties_selected = True
        
        #get preceding events df for performance perspective properties if atleast one performance property other than service time is selected for analysis
        if performance_properties_selected:        
            preceding_events_df = get_preceding_events_df(ocel_extended_df, object_types, atomic_evs, event_endtime_column)

        property_val_dicts_map = {property:{} for property in property_names_dict.keys()}
        #get all properties of the event perspective
        if 'ep1' in selected_property_ids:
            property_val_dicts_map['ep1'] = ep1(selected_event_types, event_types_to_df_map, events_to_time_df, sampling_rate)
        if 'ep2' in selected_property_ids:
            property_val_dicts_map['ep2'] = ep2(selected_event_types, event_types_to_df_map, events_to_time_df, aggregation_mode, sampling_rate, atomic_evs, event_endtime_column)
        if 'ep3' in selected_property_ids:
            property_val_dicts_map['ep3'] = ep3(selected_event_types, event_object_count_df_map, events_to_time_df, aggregation_mode, sampling_rate)
        if 'ep4' in selected_property_ids and event_object_combinations:
            property_val_dicts_map['ep4'] = ep4(selected_event_types, selected_object_types, event_object_combinations, event_object_count_df_map, events_to_time_df, aggregation_mode, sampling_rate)

        if 'op1' in selected_property_ids:
            property_val_dicts_map['op1'] = op1(selected_object_types, object_types_to_df_map, objects_to_time_df, sampling_rate)
        if 'op2' in selected_property_ids:
            property_val_dicts_map['op2'] = op2(selected_object_types, object_types_to_df_map, objects_to_time_df, aggregation_mode, sampling_rate)
        if 'op3' in selected_property_ids:
            property_val_dicts_map['op3'] = op3(selected_object_types, object_type_summary_df_map, objects_to_time_df, aggregation_mode, sampling_rate)
        if 'op4' in selected_property_ids and event_object_combinations:
            property_val_dicts_map['op4'] = op4(selected_event_types, selected_object_types, objects_df, event_to_object_relations_df_map, objects_to_time_df, aggregation_mode, sampling_rate)
        if 'op5' in selected_property_ids:
            property_val_dicts_map['op5'] = op5(selected_object_types, object_type_summary_df_map, objects_to_time_df, aggregation_mode, sampling_rate)
        if 'op6' in selected_property_ids and not object_interactions_df.empty:
            property_val_dicts_map['op6'] = op6(selected_object_types, object_interactions_df, events_to_time_df, aggregation_mode, sampling_rate)

        if 'pp1' in selected_property_ids:
            property_val_dicts_map['pp1'] = pp1(selected_event_types, preceding_events_df, event_types, events_to_time_df, aggregation_mode, sampling_rate)
        if 'pp2' in selected_property_ids:
            property_val_dicts_map['pp2'] = pp2(selected_event_types, preceding_events_df, event_types, events_to_time_df, aggregation_mode, sampling_rate)
        #service time (pp3) for atomic events is always 0 and  
        #soujourn time (pp4) is equal to waiting time for atomic events
        #so we don't generate any time series for these properties if all events in the log are atomic.  
        if not atomic_evs:
            if 'pp3' in selected_property_ids:
                property_val_dicts_map['pp3'] = pp3(selected_event_types, event_types_to_df_map, events_to_time_df, aggregation_mode, sampling_rate, event_endtime_column)
            if 'pp4' in selected_property_ids:
                property_val_dicts_map['pp4'] = pp4(selected_event_types, property_val_dicts_map['pp1'], preceding_events_df, event_types, event_endtime_column, atomic_evs, events_to_time_df,\
                            aggregation_mode, sampling_rate)
        if 'pp5' in selected_property_ids:
            property_val_dicts_map['pp5'] = pp5(selected_event_types, preceding_events_df, event_types, event_endtime_column, atomic_evs, events_to_time_df,\
                        aggregation_mode, sampling_rate)
        if 'pp6' in selected_property_ids and event_object_combinations:
            property_val_dicts_map['pp6'] = pp6(selected_event_types, selected_object_types, preceding_events_df, event_object_combinations, events_to_time_df, aggregation_mode, sampling_rate)
        if 'pp7' in selected_property_ids and event_object_combinations:
            property_val_dicts_map['pp7'] = pp7(selected_event_types, selected_object_types, preceding_events_df, event_object_combinations, events_to_time_df, aggregation_mode, sampling_rate)

        if resource_object_type:
            if 'rp1' in selected_property_ids:
                property_val_dicts_map['rp1'] = rp1(property_val_dicts_map['ep4'], resource_object_type)
            if 'rp2' in selected_property_ids:
                property_val_dicts_map['rp2'] = rp2(event_to_object_relations_df, events_to_time_df, resource_object_type, sampling_rate)
            if 'rp3' in selected_property_ids:
                property_val_dicts_map['rp3'] = rp3(property_val_dicts_map['op2'], resource_object_type)


        fill_limit = math.floor(len(time_intervals)/10)
        #process time series by padding on both ends with null values to represent missing values 
        #then discard any time series with any null values (not only on the ends but anywhere) and assign remaining
        #to a dict called 'TS_collection' which is then used ahead. 
        #Plot all series being assigned to 'TS_collection'. Plots will be saved to 'backend/assets/plots'.
        for property, property_dict in property_val_dicts_map.items():
            if property_dict:
                for non_temporal_parameters, ts in property_dict.items():
                    if not ts.empty:
                        #padding the timeseries on both ends to align with specified intervals.
                        processed_ts = time_intervals.right.to_frame().merge(ts, left_index=True, right_index=True, how='left')\
                            .drop(columns=0).iloc[:,0]
                        if property in ['ep1','op1','rp2']:
                            processed_ts = processed_ts.replace(np.nan, 0.0)
                        if not processed_ts.isna().any():
                            TS_collection[(property, non_temporal_parameters)] = processed_ts
        st.session_state['TS_collection'] = TS_collection
else:
    prev_iterations_data = st.session_state['prev_iterations_data']
    if not prev_iterations_data:
        #extract time series values and time series for results for 'change point detection' and 'threshold based point detection'
        #from previous iterations
        prev_iterations_data = {}
        object_type_df = object_types_to_df_map['time series']
        ts_obj_ids = list(object_type_df['ocel:oid'].unique())
        for ts_obj_id in ts_obj_ids:
            ts_obj_df = object_type_df[object_type_df[object_id_column] == ts_obj_id]
            tsvalues = ts_obj_df[ts_obj_df[changed_field_column] == 'tsvalues']\
                [[event_timestamp_column, 'tsvalues']].set_index(event_timestamp_column)['tsvalues']
            prev_iterations_data[(ts_obj_id, 'tsvalues')] = tsvalues
            for pdt in ['Change Point Detection', 'Threshold Based Point Detection']:
                for column in ts_obj_df.columns:
                    if column.startswith(pdt):
                        points_df = ts_obj_df[(ts_obj_df[changed_field_column].fillna('') == column) & (ts_obj_df[column] == 1)][[event_timestamp_column, column]]
                        points_df[event_timestamp_column] = points_df[event_timestamp_column] + pd.Timedelta('1s')
                        merged_df = time_intervals.right.to_frame().merge(points_df, right_on=event_timestamp_column, left_index=True, how='left')
                        merged_df[column] = merged_df[column].fillna(0)
                        pd_ts = merged_df[[event_timestamp_column,column]].set_index(event_timestamp_column)
                        prev_iterations_data[(ts_obj_id, column)] = pd_ts[column]
        st.session_state['prev_iterations_data'] = prev_iterations_data

if "tabs" not in st.session_state:
    st.session_state["tabs"] = ["Timeseries"]

tabs = st.tabs(st.session_state["tabs"])

TS_collection = st.session_state['TS_collection']
ts_causal_factors_dict = st.session_state['ts_causal_factors_dict']
change_point_idx_ts_dict = st.session_state['change_point_idx_ts_dict']
threshold_based_ts_dict = st.session_state['threshold_based_ts_dict']
ts_forecasts_df = st.session_state['ts_forecasts_df']
granger_df = st.session_state['granger_df']
forecast_column = st.session_state['forecast_column']
tbpd_params_list = st.session_state['tbpd_params_list']
#retrieve time series and tsa results from previous iterations
if not first_iteration:
    if not TS_collection:
        TS_collection = {}
        ts_causal_factors_dict = {}
        change_point_idx_ts_dict = {}
        threshold_based_ts_dict = {}
        for key, value in prev_iterations_data.items():
            if key[0].startswith('ts'):
                name_list = key[0].split('&')
                property = name_list[1]
                non_temporal_parameters_str = name_list[2]
                non_temporal_parameters_list = non_temporal_parameters_str.split('|')
                if len(non_temporal_parameters_list) > 1:
                    non_temporal_parameters = tuple(non_temporal_parameters_list)
                else:
                    non_temporal_parameters = non_temporal_parameters_list[0]
                if key[1] == 'tsvalues':
                    ts = value
                    ts.index.name = None
                    TS_collection[(property, non_temporal_parameters)] = ts
                if key[1].startswith('Change Point Detection'):
                    cpd_property = f'Change Points for {property}'
                    change_point_idx_ts_dict[(property, non_temporal_parameters)] = value
                if key[1].startswith('Threshold Based Point Detection'):
                    tbpd_params = key[1].removeprefix('Threshold Based Point Detection')
                    if tbpd_params not in tbpd_params_list:
                        tbpd_params_list.append(tbpd_params)
                    tbpd_property = f'Threshold Based Points {tbpd_params} for {property}'
                    threshold_based_ts_dict[(tbpd_property, non_temporal_parameters)] = value

        o2o_df = ocel.o2o.copy()
        granger_df = o2o_df[o2o_df['ocel:qualifier'].str.startswith('Granger')].reset_index(drop=True)
        if not granger_df.empty:
            granger_df = granger_df[['ocel:oid','ocel:oid_2']].rename(columns={'ocel:oid':'caused', 'ocel:oid_2':'causing'})\
                .groupby('caused').agg(list).reset_index()
            ts_causal_factors_list = granger_df.to_dict('records')
            for ts_factors in ts_causal_factors_list:
                causing_tsid_list = []
                caused_ts = ts_factors['caused']
                causing_ts_list = ts_factors['causing']
                caused_ts_str = caused_ts.split('&')
                caused_ts_property = caused_ts_str[1]
                caused_ts_non_temporal_parameters_str = caused_ts_str[2]
                caused_non_temporal_parameters_list = caused_ts_non_temporal_parameters_str.split('|')
                if len(caused_non_temporal_parameters_list) > 1:
                    caused_non_temporal_parameters = tuple(caused_non_temporal_parameters_list)
                else:
                    caused_non_temporal_parameters = caused_non_temporal_parameters_list[0]
                for causing_ts in causing_ts_list:
                    causing_ts_str = causing_ts.split('&')
                    causing_ts_property = causing_ts_str[1]
                    causing_ts_non_temporal_parameters_str = causing_ts_str[2]
                    causing_non_temporal_parameters_list = causing_ts_non_temporal_parameters_str.split('|')
                    if len(causing_non_temporal_parameters_list) > 1:
                        causing_non_temporal_parameters = tuple(causing_non_temporal_parameters_list)
                    else:
                        causing_non_temporal_parameters = causing_non_temporal_parameters_list[0]
                    causing_tsid_list.append((causing_ts_property, causing_non_temporal_parameters))
                ts_causal_factors_dict[(caused_ts_property, caused_non_temporal_parameters)] = causing_tsid_list
            


        ts_forecasts_df = ocel.object_changes[ocel.object_changes['ocel:field'].str.startswith('Forecasting')]    
        if not ts_forecasts_df.empty:
            for column in ts_forecasts_df.columns:
                if column.startswith('Forecasting'):
                    forecast_column = column
            ts_forecasts_df = ts_forecasts_df[['ocel:oid', 'ocel:timestamp', forecast_column]].sort_values(by=['ocel:oid','ocel:timestamp'],ignore_index=True)
            ts_forecasts_df['property'] = ts_forecasts_df['ocel:oid'].str.split(pat='&').str[1]
            ts_forecasts_df['non_temporal_parameters'] = ts_forecasts_df['ocel:oid'].str.split(pat='&').str[-1].str.split(pat='|').apply(lambda x: tuple(x) if len(x) > 1 else x[0])
            ts_forecasts_df['tsid'] = ts_forecasts_df.apply(lambda x: tuple((x['property'], x['non_temporal_parameters'])), axis=1)
            ts_forecasts_df = ts_forecasts_df[['tsid', event_timestamp_column, forecast_column]]

        st.session_state['TS_collection'] = TS_collection
        st.session_state['ts_causal_factors_dict'] = ts_causal_factors_dict
        st.session_state['change_point_idx_ts_dict'] = change_point_idx_ts_dict
        st.session_state['threshold_based_ts_dict'] = threshold_based_ts_dict
        st.session_state['ts_forecasts_df'] = ts_forecasts_df
        st.session_state['granger_df'] = granger_df
        st.session_state['forecast_column'] = forecast_column
        st.session_state['tbpd_params_list'] = tbpd_params_list

if first_iteration:
    generate_related_events_and_objects(TS_collection, property_parameters_map, events_to_time_df, objects_to_time_df, overlapping_objects_to_time_df, event_types_to_df_map, object_types_to_df_map, atomic_evs, event_endtime_column, objects_summary_df)

    with zipfile.ZipFile(f"backend/assets/temp/timeseriesdata_{input_ocel_filename}.zip", "w") as ts_zf:
        for tsid, ts in TS_collection.items():
            with ts_zf.open(f"{tsid}.csv", "w") as buffer:
                ts.to_csv(buffer)


with tabs[0]:
    with open(f"backend/assets/temp/timeseriesdata_{input_ocel_filename}.zip", "rb") as file:
        st.download_button(
                label="Download Time Series",
                data=file,
                file_name=f'timeseries_{input_ocel_filename}.zip',
                mime="application/zip",
                on_click = 'ignore',
                width='stretch',
                type='primary',
                icon=":material/download:"
            )
    create_plots_for_ts_collection(TS_collection, property_names_dict, property_parameters_map, aggregation_mode, assignment_mechanism)

i = 1
for arname, arcollection in st.session_state['ar_history'].items():
    with tabs[i]:
        tsatechnique=arname.split('(')[0]
        params = st.session_state['ar_params_history'][arname]
        param_keys = list(params.keys())
        param_vals = list(params.values())
        num_of_params = len(params)
        num_of_rows = math.ceil(num_of_params/2)
        remaining_num_of_params = num_of_params
        for row in range(0,num_of_rows):
            if remaining_num_of_params > 0:
                if remaining_num_of_params < 2:
                    num_of_cols = remaining_num_of_params
                else:
                    num_of_cols = 2
                cols = st.columns(num_of_cols)
                for j, col in enumerate(cols):
                    key = param_keys[(row)*2 + j]
                    value = param_vals[(row)*2 + j]
                    if isinstance(value,list):
                        value = str([str(x) for x in value]).replace('\'','')
                    if not key in ['threshold_1', 'threshold_2', 'use_change_point_difference_as_lag', 'use_granger_causal_ts_as_exogenous_variables']:
                        key = key.replace('_',' ')
                        key = key[0].upper() + key[1:]
                    elif key == 'threshold_1':
                        if params['mode'] == 'between':
                            key='Lower Threshold'
                        else:
                            key='Threshold'
                    elif key == 'threshold_2' and params['mode'] == 'between':
                        key = 'Upper Threshold'
                    elif key == 'threshold_2' and params['mode'] != 'between':
                        continue
                    elif tsatechnique == 'Forecasting' and not first_iteration and key =='use_granger_causal_ts_as_exogenous_variables':
                        key = 'Use Granger Causal Timeseries as Exogenous Variables'
                    elif tsatechnique == 'Granger Causality' and not first_iteration and key == 'use_change_point_difference_as_lag':
                        key = 'Additional Option for Granger Causality' 
                        value = st.session_state['granger_additional_option']
                    elif tsatechnique == 'Granger Causality' and first_iteration and key == 'use_change_point_difference_as_lag':
                        continue
                    col.metric(key, value, border=True)
                remaining_num_of_params = remaining_num_of_params - num_of_cols
                if remaining_num_of_params <= 0:
                    break
                    


        st.download_button(
                label='Download Analysis results',
                file_name=f'{arname}_results.json',
                mime='application/json',
                data= st.session_state['ar_json_history'][arname],
                on_click = 'ignore',
                width='stretch',
                type='primary',
                icon=":material/download:"
            )
        visualize_analysis_results(st.session_state['ar_ts_history'][arname], arcollection, tsatechnique, property_names_dict, params, property_parameters_map, aggregation_mode, assignment_mechanism)
    i = i + 1

tsa_technique = st.session_state['tsa_technique']
if len(time_intervals) <= 12:
    tsa_techniques = ['', 'Change Point Detection', 'Threshold Based Point Detection']
else:
    tsa_techniques = ['', 'Change Point Detection', 'Threshold Based Point Detection', 'Forecasting', 'Granger Causality']


if not tsa_technique:
    with st.sidebar.form("tsa_form"):
        selected_tsa_technique = st.selectbox('TSA technique', tsa_techniques)
        st.form_submit_button('Confirm Selection')

    if not selected_tsa_technique:
        st.stop()
    else:
        st.session_state['tsa_technique'] = selected_tsa_technique
        tsa_technique = selected_tsa_technique
        st.rerun()
else:
    st.sidebar.write(f'**TSA technique**: :blue[{tsa_technique}]')

if not first_iteration:
    if change_point_idx_ts_dict and tsa_technique == 'Change Point Detection':
        st.sidebar.error('Cannot run change point detection on the same log twice.')
        st.stop()
    if (isinstance(ts_forecasts_df, pd.DataFrame) and not granger_df.empty) and tsa_technique == 'Granger Causality':
        st.sidebar.error('Cannot run granger causality on the same log twice.')
        st.stop()
    if (isinstance(ts_forecasts_df, pd.DataFrame) and not ts_forecasts_df.empty) and tsa_technique == 'Forecasting':
        st.sidebar.error('Cannot run forecasting on the same log twice.')
        st.stop()
    tsa_params_form_complete = False

append_forecasts_to_ts = st.session_state['append_forecasts_to_ts']
if tsa_technique != 'Forecasting' and not first_iteration and (isinstance(ts_forecasts_df, pd.DataFrame) and not ts_forecasts_df.empty):
    if not append_forecasts_to_ts:
        with st.sidebar.form('append_forecasts_form'):
            selected_append_forecasts_to_ts = st.selectbox('Do you wish to append Forecasts from previous iterations to the respective timeseries for current analysis?', ['', 'Yes', 'No'])
            disable_form_key = 'append_forecasts_form_disable'
            st.form_submit_button('Confirm Selection', on_click=disable, args=(disable_form_key, ), disabled=st.session_state[disable_form_key])    
        if not selected_append_forecasts_to_ts:
            st.stop()
        else:
            append_forecasts_to_ts = selected_append_forecasts_to_ts
            st.session_state['append_forecasts_to_ts'] = selected_append_forecasts_to_ts
            st.rerun()
    else:
        st.sidebar.write(f'**Append forecasts to timeseries**: :blue[{append_forecasts_to_ts}]')
else:
    append_forecasts_to_ts = 'No'

use_change_point_difference_as_lag = st.session_state['use_change_point_difference_as_lag']
use_tbpd_results_as_ts_for_granger_causality = st.session_state['use_tbpd_results_as_ts_for_granger_causality']
only_compare_threshold_ts = st.session_state['only_compare_threshold_ts']
use_granger_causal_ts_as_exogenous_variables = st.session_state['use_granger_causal_ts_as_exogenous_variables']

tsa_params = st.session_state['tsa_params']
mode = st.session_state['mode'] 
comparison_operator = st.session_state['comparison_operator'] 
threshold_1 = st.session_state['threshold_1'] 
threshold_2 = st.session_state['threshold_2'] 
granger_additional_option = st.session_state['granger_additional_option']
p_value_threshold = st.session_state['p_value_threshold']
periods_to_predict = st.session_state['periods_to_predict']
edit_advanced_arima_settings = st.session_state['edit_advanced_arima_settings']
edit_advanced_pelt_settings = st.session_state['edit_advanced_pelt_settings']

if not tsa_params:
    if tsa_technique == 'Change Point Detection' and not edit_advanced_pelt_settings:
        with st.sidebar.form("tsa_params_form"):
            selected_edit_advanced_pelt_settings = st.selectbox('Do you wish to edit the parameters passed to the PELT algorithm for Change Point Detection \
                                                                (Only recommended if you are well-versed with PELT. \n Passing unsuitable parameters may cause errors.)', ['','Yes', 'No'])
            st.form_submit_button('Confirm Selection')
        if not selected_edit_advanced_pelt_settings:
            st.stop()
        else:
            st.session_state['edit_advanced_pelt_settings'] = selected_edit_advanced_pelt_settings
            edit_advanced_pelt_settings = selected_edit_advanced_pelt_settings
            st.rerun()
    elif tsa_technique == 'Threshold Based Point Detection':
        if not mode:
            with st.sidebar.form("tsa_params_form"):
                modes = ['','quantile', 'relative change', 'nsmallest', 'nlargest']
                selected_mode = st.selectbox('Measure', modes)
                st.form_submit_button('Confirm Selection')
            
            if selected_mode:
                st.session_state['mode'] = selected_mode
                mode = selected_mode
                st.rerun()
            else:
                st.stop()
        else:
            st.sidebar.write(f'**Mode**: :blue[{mode}]')
    elif tsa_technique == 'Granger Causality':
        additional_options = ['', 'None']
        if not first_iteration and (change_point_idx_ts_dict or threshold_based_ts_dict) and append_forecasts_to_ts == 'No':
            lag = None
            if change_point_idx_ts_dict:
                additional_options.append('Use change point differences as lags')
            if threshold_based_ts_dict:
                #additional_options.append('Add time series generated from threshold based points to the collection of time series')
                additional_options.append('Only use time series generated from threshold based points')
            if not granger_additional_option:
                with st.sidebar.form('tsa_params_form'):
                    selected_granger_additional_option = st.selectbox('Please select the previous analysis results to be used', additional_options)
                    selected_p_value_threshold = st.number_input('P-Value Threshold', min_value=0.01, max_value = 0.10, step=0.01,format="%.2f")
                    st.form_submit_button('Confirm Selection')
                if not selected_granger_additional_option:
                    st.stop()
                else:
                    granger_additional_option = selected_granger_additional_option
                    st.session_state['granger_additional_option'] = selected_granger_additional_option
                    p_value_threshold = selected_p_value_threshold
                    st.session_state['p_value_threshold'] = selected_p_value_threshold
                    st.rerun()
            else:
                st.sidebar.write(f'**P Value Threshold**: :blue[{p_value_threshold}]')
                st.sidebar.write(f'**Additional Option for Granger Causality:** :blue[{granger_additional_option}]')

            if granger_additional_option.startswith('Use'):
                use_change_point_difference_as_lag = 'Yes'
                use_tbpd_results_as_ts_for_granger_causality = 'No'
                only_compare_threshold_ts = 'No'
            elif granger_additional_option.startswith('Add'):
                use_tbpd_results_as_ts_for_granger_causality = 'Yes'
                use_change_point_difference_as_lag = 'No'
                only_compare_threshold_ts = 'No'
            elif granger_additional_option.startswith('Only'):
                only_compare_threshold_ts = 'Yes'
                use_change_point_difference_as_lag = 'No'
                use_tbpd_results_as_ts_for_granger_causality = 'No'
            elif granger_additional_option == 'None':
                use_change_point_difference_as_lag = 'No'
                use_tbpd_results_as_ts_for_granger_causality = 'No'
                only_compare_threshold_ts = 'No'
        else:
            use_change_point_difference_as_lag = 'No'
            use_tbpd_results_as_ts_for_granger_causality = 'No'
            only_compare_threshold_ts = 'No'
            with st.sidebar.form('tsa_params_form'):
                lag = st.multiselect('Lags', list(range(1,math.floor((len(time_intervals)-1) / 3 - 1))))
                p_value_threshold = st.number_input('P-Value Threshold', min_value=0.01, max_value = 0.10, step=0.01,format="%.2f")
                st.form_submit_button('Confirm Selection')
            if not lag:
                st.stop()
            else:
                tsa_params = {'lag': lag, 'p_value_threshold': p_value_threshold, 'use_change_point_difference_as_lag': 'No'}

        st.session_state['use_change_point_difference_as_lag'] = use_change_point_difference_as_lag
        st.session_state['use_tbpd_results_as_ts_for_granger_causality'] = use_tbpd_results_as_ts_for_granger_causality
        st.session_state['only_compare_threshold_ts'] = only_compare_threshold_ts

    elif tsa_technique == 'Forecasting':
        if not use_granger_causal_ts_as_exogenous_variables or not edit_advanced_arima_settings:
            with st.sidebar.form("tsa_params_form"):
                selected_periods_to_predict = st.number_input('Forecasting Horizon (Number of periods to predict)', min_value=1, max_value=math.floor(len(time_intervals)/3), step=1, value=4)
                if not first_iteration and ts_causal_factors_dict:
                    selected_use_granger_causal_ts_as_exogenous_variables = st.selectbox('Do you wish to use previously detected granger causal timeseries as exogenous variables?', ['','Yes', 'No'])
                else:
                    use_granger_causal_ts_as_exogenous_variables = 'No'
                selected_edit_advanced_arima_settings = st.selectbox('Do you wish to edit the parameters passed to AutoARIMA \
                                                                (Only recommended if you are well-versed with AutoARIMA. \n Passing unsuitable parameters may cause errors.)', ['','Yes', 'No'])
                st.form_submit_button('Confirm Selection')

            if (not first_iteration and ts_causal_factors_dict and not selected_use_granger_causal_ts_as_exogenous_variables) or not selected_edit_advanced_arima_settings:
                    st.stop()
            else:
                if not first_iteration and ts_causal_factors_dict:
                    st.session_state['use_granger_causal_ts_as_exogenous_variables'] = selected_use_granger_causal_ts_as_exogenous_variables
                    use_granger_causal_ts_as_exogenous_variables = selected_use_granger_causal_ts_as_exogenous_variables
                st.session_state['periods_to_predict'] = selected_periods_to_predict
                periods_to_predict = selected_periods_to_predict
                st.session_state['edit_advanced_arima_settings'] = selected_edit_advanced_arima_settings
                edit_advanced_arima_settings = selected_edit_advanced_arima_settings
                st.rerun()
        else:
            st.sidebar.write(f'**Periods to predict**: :blue[{periods_to_predict}]')
            st.sidebar.write(f'**Use granger causal timeseries as exogenous variables**: :blue[{use_granger_causal_ts_as_exogenous_variables}]')
    if tsa_technique == 'Threshold Based Point Detection' and mode:

        if mode in ['quantile', 'relative change']:
            if not comparison_operator:
                with st.sidebar.form('threshold_based_comparison_operator_form'):
                    comparison_operators = ['', 'between', 'greater or equal to', 'lesser or equal to']
                    selected_comparison_operator = st.selectbox('Comparison operator', comparison_operators)
                    st.form_submit_button('Confirm Selection')

                if selected_comparison_operator:
                    st.session_state['comparison_operator'] = selected_comparison_operator
                    comparison_operator = selected_comparison_operator
                    st.rerun()
                else:
                    st.stop()
            else:
                st.sidebar.write(f'**Comparison operator**: :blue[{comparison_operator}]')
        else:
            comparison_operator = None


        if not threshold_1:
            with st.sidebar.form('threshold_based_thresholds_form'):
                if not mode:
                    st.stop()
                elif mode in ['nsmallest', 'nlargest']:
                    selected_threshold_1 = st.number_input('Threshold', min_value=1, max_value = len(time_intervals), step=1)
                    selected_threshold_2 = None
                elif mode == 'quantile':
                    if comparison_operator == 'between':
                        selected_threshold_1 = st.number_input('Lower Threshold', min_value=0.0, max_value = 1.0, step=0.001,format="%.3f")
                        selected_threshold_2 = st.number_input('Upper Threshold', min_value=0.0, max_value = 1.0, step=0.001,format="%.3f")
                    else:
                        selected_threshold_1 = st.number_input('Threshold', min_value=0.0, max_value = 1.0, step=0.001,format="%.3f")
                        selected_threshold_2 = None
                elif mode == 'relative change':
                    if comparison_operator == 'between':
                        selected_threshold_1 = st.number_input('Lower Threshold', step=0.001,format="%.3f")
                        selected_threshold_2 = st.number_input('Upper Threshold', step=0.001,format="%.3f")
                    else:
                        selected_threshold_1 = st.number_input('Threshold', step=0.001,format="%.3f")
                        selected_threshold_2 = None

                st.form_submit_button('Confirm Selection')

            if selected_threshold_1:
                st.session_state['threshold_1'] = selected_threshold_1
                threshold_1 = selected_threshold_1
            else:
                st.stop()

            if comparison_operator == 'between':
                if selected_threshold_2: 
                    st.session_state['threshold_2'] = selected_threshold_2
                    threshold_2 = selected_threshold_2
                    st.rerun()
                else:
                    st.stop()
            else:
                st.rerun()
            
        else:
            if comparison_operator != 'between':
                st.sidebar.write(f'**Threshold**: {threshold_1}')
            else:
                st.sidebar.write(f'**Lower Threshold**: :blue[{threshold_1}]')
                st.sidebar.write(f'**Upper Threshold**: :blue[{threshold_2}]')

        if comparison_operator == 'between' and threshold_1 > threshold_2:
            st.sidebar.warning('Upper Threshold must be strictly greater than Lower Threshold')
            st.stop()
        if (comparison_operator != 'between' and threshold_1) or (threshold_2 and threshold_2 > threshold_1):
            tsa_params = {'mode': mode, 'comparison_operator' : comparison_operator, 'threshold_1': threshold_1, 'threshold_2': threshold_2 }

    elif tsa_technique == 'Forecasting' and edit_advanced_arima_settings:
        if edit_advanced_arima_settings == 'Yes':
            with st.sidebar.form('forecasting_arima_config_form'):
                start_p = st.number_input('Starting value for order of AR model of non-seasonal component', min_value=0, max_value = len(time_intervals), step=1, value=2)
                start_q = st.number_input('Starting value for order of MA model of non-seasonal component', min_value=0, max_value = len(time_intervals), step=1, value=2)
                start_P = st.number_input('Starting value for order of AR model of seasonal component', min_value=0, max_value = len(time_intervals), step=1, value=1)
                start_Q = st.number_input('Starting value for order of MA model of seasonal component', min_value=0, max_value = len(time_intervals), step=1, value=1)
                max_p = st.number_input('Maximum value for order of AR model of non-seasonal component', min_value=0, max_value = len(time_intervals), step=1, value=5)
                max_q = st.number_input('Maximum value for order of MA model of non-seasonal component', min_value=0, max_value = len(time_intervals), step=1, value=5)
                max_P = st.number_input('Maximum value for order of AR model of seasonal component', min_value=0, max_value = len(time_intervals), step=1, value=2)
                max_Q = st.number_input('Maximum value for order of MA model of seasonal component', min_value=0, max_value = len(time_intervals), step=1, value=2)
                information_criterion_list = ['','aicc', 'aic', 'bic', 'hqic', 'oob']
                information_criterion = st.selectbox('Information Criteria by which to evaluate the model', information_criterion_list)
                stationarity_tests = ['','kpss', 'adf', 'pp']
                test = st.selectbox('Stationarity test for timeseries', stationarity_tests)
                maxiter = st.number_input('Maximum Number of iterations per timeseries for model evaluation', min_value=50, max_value=500, step=1, value=100)
                st.form_submit_button('Confirm Selection')
            if not information_criterion or not test:
                st.stop()
        else:
            start_p = 2
            start_q = 2
            start_P = 1
            start_Q = 1
            max_p = 5
            max_q = 5
            max_P = 2
            max_Q = 2
            information_criterion = 'aicc'
            test = 'kpss'
            maxiter = 100

        tsa_params = {'periods_to_predict': periods_to_predict, 'use_granger_causal_ts_as_exogenous_variables': use_granger_causal_ts_as_exogenous_variables, 'start_p': start_p, \
                      'start_q': start_q, 'start_P': start_P, 'start_Q': start_Q, 'max_p': max_p, 'max_q': max_q, 'max_P': max_P, 'max_Q': max_Q, \
                    'information_criterion': information_criterion, 'test': test, 'maxiter': maxiter}
    elif tsa_technique == 'Change Point Detection' and edit_advanced_pelt_settings:
        if edit_advanced_pelt_settings == 'Yes':
            with st.sidebar.form('cp_pelt_config_form'):
                cost_models = ['','rbf', 'l1', 'l2']
                model = st.selectbox('Cost Model', cost_models)
                min_size_options = list(range(1, math.floor(len(time_intervals)/2)))
                min_size = st.selectbox('Minimum Segment Length', min_size_options, index=min((len(min_size_options)-1),2))
                jump = st.selectbox('Jump', list(range(1, math.floor(len(time_intervals)/2))))
                penalty = st.selectbox('Penalty', [1,1.5,2,2.5,3], index=1)
                st.form_submit_button('Confirm Selection')
            if not model:
                st.stop()
        else:
            model = 'rbf'
            min_size = 3
            jump = 1
            penalty = 1.5
            
        tsa_params = {'model': model, 'min_size': min_size, 'jump': jump, 'penalty': penalty}

    elif tsa_technique == 'Granger Causality' and not first_iteration:
        if lag or use_change_point_difference_as_lag=='Yes':
            tsa_params = {'lag': lag, 'p_value_threshold': p_value_threshold, 'use_change_point_difference_as_lag': use_change_point_difference_as_lag}
        if not tsa_params:
            with st.sidebar.form('granger additional form'):
                lag = st.multiselect('Lags', list(range(1,math.floor((len(time_intervals)-1) / 3 - 1))))
                p_value_threshold = st.number_input('P-Value Threshold', min_value=0.01, max_value = 0.10, step=0.01,format="%.2f")
                st.form_submit_button('Confirm Selection')
            if lag:
                tsa_params = {'lag': lag, 'p_value_threshold': p_value_threshold, 'use_change_point_difference_as_lag': 'No'}


    if tsa_params:
        st.session_state['tsa_params'] = tsa_params
        st.rerun()
else:
    for key,value in tsa_params.items():
        if not key in ['threshold_1', 'threshold_2', 'use_change_point_difference_as_lag', 'use_granger_causal_ts_as_exogenous_variables']:
            mod_key = key.replace('_',' ')
            mod_key = mod_key[0].upper() + mod_key[1:]
            st.sidebar.write(f'**{mod_key}**: :blue[{value}]')
        elif key == 'threshold_1':
            if comparison_operator == 'between':
                st.sidebar.write(f'**Lower Threshold**: :blue[{value}]')
            else:
                st.sidebar.write(f'**Threshold**: :blue[{value}]')
        elif key == 'threshold_2' and comparison_operator == 'between':
             st.sidebar.write(f'**Upper Threshold**: :blue[{value}]')
    if tsa_technique == 'Forecasting' and not first_iteration:
        st.sidebar.write(f'**Use granger causal timeseries as exogenous variables**: :blue[{use_granger_causal_ts_as_exogenous_variables}]')
    elif tsa_technique == 'Granger Causality' and not first_iteration:
        st.sidebar.write(f'**Additional Option for Granger Causality**: :blue[{granger_additional_option}]')
if not tsa_params:
    st.stop()

if not first_iteration and threshold_based_ts_dict and tsa_technique == 'Threshold Based Point Detection':
    for params in tbpd_params_list:
        if params == '(' + ', '.join(str(x) for x in tsa_params.values() if x != None) + ')':
            st.error('Cannot run threshold based point detection using the same parameters twice on the same log.')
            st.stop()
#constant time series i.e. where all time periods have the same value will not be considered for further analysis.
#so we discard all such time series and assign remaining to a dict 'ar_ts_collection'.
#We round the values to 3 decimal places before checking for constant values since they trigger errors in performing tsa ahead
#especially for granger causality and forecasting.
ar_ts_collection = {}
for tsid, ts in TS_collection.items():
    if not len(ts.round(3).unique()) == 1:
        ar_ts_collection[tsid] = ts.round(3).copy()


change_point_indices_dict = st.session_state['change_point_indices_dict']
#Handle selected options for using analysis results from previous iterations in current iteration's analysis
if not first_iteration:
    #create lists of change points for each time series
    if not change_point_indices_dict and tsa_technique == 'Granger Causality' and use_change_point_difference_as_lag == 'Yes':
        for tsid, cp_ts in change_point_idx_ts_dict.items():
            cp_df = cp_ts.copy()
            cp_df = cp_df.rename('cp').reset_index()
            change_point_indices_dict[tsid] = cp_df[cp_df['cp']==1].index.values.tolist()
        st.session_state['change_point_indices_dict'] = change_point_indices_dict

    #append forecasts to time series is selected if option is selected
    if append_forecasts_to_ts == 'Yes':
        ar_ts_collection_with_forecasts = {}
        for tsid, ts in ar_ts_collection.items():
            forecast_ts = ts_forecasts_df[ts_forecasts_df['tsid'] == tsid][[event_timestamp_column, forecast_column]]
            forecast_ts = forecast_ts.set_index(event_timestamp_column)
            forecast_ts = forecast_ts[forecast_ts.columns[-1]]
            forecast_ts.name = tsid
            ts.name = tsid
            ar_ts_collection_with_forecasts[tsid] = pd.concat([ts, forecast_ts])
        ar_ts_collection = ar_ts_collection_with_forecasts

    #use threshold based point detection results as time series for granger causality, if selected.
    if tsa_technique == 'Granger Causality':
        if use_tbpd_results_as_ts_for_granger_causality == 'Yes':
            with tabs[0]:
                create_plots_for_ts_collection(threshold_based_ts_dict, property_names_dict, property_parameters_map, aggregation_mode, assignment_mechanism)
            for tbp_tsid, tbp_ts in threshold_based_ts_dict.items():
                if not len(tbp_ts.unique()) == 1 and len(tbp_ts[tbp_ts==1]) > 1:
                    ar_ts_collection[tbp_tsid] = tbp_ts
        elif only_compare_threshold_ts == 'Yes':
            with tabs[0]:
                create_plots_for_ts_collection(threshold_based_ts_dict, property_names_dict, property_parameters_map, aggregation_mode, assignment_mechanism)
            processed_threshold_based_ts_dict = {}
            for tbp_tsid, tbp_ts in threshold_based_ts_dict.items():
                if not len(tbp_ts.unique()) == 1 and len(tbp_ts[tbp_ts==1]) > 1 :
                    processed_threshold_based_ts_dict[tbp_tsid] = tbp_ts
            ar_ts_collection = processed_threshold_based_ts_dict

#perform time series analysis and save the results to a json file available in 'backend/assets/analysis_results'
if tsa_technique:
    if ar_ts_collection:
        ar_collection = st.session_state['ar_collection']
        if (isinstance(ar_collection,pd.DataFrame) and ar_collection.empty) or (not isinstance(ar_collection, pd.DataFrame) and not ar_collection):
            ar_collection = time_series_analysis(ar_ts_collection, tsa_technique, min_seasonal_period,\
                                                    max_seasonal_period, sampling_rate, offset, change_point_indices_dict, \
                                                    ts_causal_factors_dict, time_intervals, tsa_params)
            if (tsa_technique in ['Change Point Detection', 'Threshold Based Point Detection'] and ar_collection and any(ar_collection.values())) or (tsa_technique == 'Forecasting') or (isinstance(ar_collection, pd.DataFrame) and not ar_collection.empty):
                st.session_state['ar_collection'] = ar_collection
                if tsa_technique == 'Threshold Based Point Detection':
                    ar_name = tsa_technique + '(' + ', '.join(str(x) for x in tsa_params.values() if x != None) + ')'
                else:
                    ar_name = tsa_technique
                ar_json = convert_ar_to_json(ar_collection, tsa_technique)
                st.session_state['ar_json_history'][ar_name] = ar_json
                st.session_state['ar_history'][ar_name] = ar_collection
                st.session_state['ar_ts_history'][ar_name] = ar_ts_collection
                st.session_state['ar_params_history'][ar_name] = tsa_params
                if not ar_name in st.session_state['tabs']:
                    st.session_state["tabs"].append(ar_name)
                    st.rerun()
            else:
                    st.sidebar.warning('No analysis results produced')
                    st.toast('No analysis results produced')
                    st.session_state['is_ar_empty'] = True

    else:
        st.sidebar.warning('None of the time series qualify for analysis. \n Any timeseries with one or more null values over the analysis time period is not qualified for analysis and hence discarded.')

if append_forecasts_to_ts == 'No' and use_tbpd_results_as_ts_for_granger_causality == 'No' and only_compare_threshold_ts == 'No':
    ts_mod_ocel_json_dict = st.session_state['ts_mod_ocel_json_dict']
    if not ts_mod_ocel_json_dict:
        if first_iteration:
            ts_mod_ocel_json_dict = insert_time_series_into_ocel(TS_collection, ocel_json_dict, int_start, int_end, aggregation_mode, sampling_rate, \
                                                property_names_dict, property_parameters_map, events_to_time_df.copy(), objects_to_time_df.copy(),\
                                                overlapping_objects_to_time_df.copy(), event_types_to_df_map, object_types_to_df_map)
        else:
            ts_mod_ocel_json_dict = ocel_json_dict
        st.session_state['ts_mod_ocel_json_dict'] = ts_mod_ocel_json_dict

    mod_ocel_json_dict = st.session_state['mod_ocel_json_dict']
    if not mod_ocel_json_dict:
        if tsa_technique and not st.session_state['is_ar_empty']:
            ar_mod_ocel_json_dict = insert_ar_into_ocel(ar_collection, tsa_technique, tsa_params, ts_mod_ocel_json_dict, property_names_dict, time_intervals, offset)
            mod_ocel_json_dict = ar_mod_ocel_json_dict
        else:
            mod_ocel_json_dict = ts_mod_ocel_json_dict
        validate(mod_ocel_json_dict, json_schema)
        st.session_state['mod_ocel_json_dict'] = mod_ocel_json_dict
    #write modified ocel to file in specified format. append timestamp to filename to avoid overwriting logs from previous runs
    current_timestamp = str(datetime.datetime.now())
    mod_ocel = st.session_state['mod_ocel']
    if not mod_ocel:
        mod_ocel_json_dict_file_path = str(Path('backend/assets/temp/mod_ocel_json_dict.json').resolve())
        with open(mod_ocel_json_dict_file_path, 'w', encoding='utf-8') as f:
            json.dump(mod_ocel_json_dict, f)
        mod_ocel = pm4py.read_ocel2_json(mod_ocel_json_dict_file_path)
        st.session_state['mod_ocel'] = mod_ocel


    mod_ocel_file_path = str(Path(f'backend/assets/logs/mod_ocel_{input_ocel_filename}_{current_timestamp}'.split('.')[0] + f'.json'))\
        .replace(' ', '-').replace(':','-')
    
    pm4py.write_ocel2_json(mod_ocel, mod_ocel_file_path)
    with open(mod_ocel_file_path, 'rb') as f:
        st.sidebar.download_button(
            label="Download modified ocel",
            data=f,
            file_name=f'mod_ocel_{input_ocel_filename}_{current_timestamp}'.split('.')[0] + '.json',
            mime="application/json",
            on_click = 'ignore',
            width='stretch',
            type='primary',
            icon=":material/download:"
        )
    with st.sidebar.form('next_iteration'):
        next_iteration = st.selectbox('Do you wish to perform another round of analysis?', ['','Yes', 'No'])
        st.form_submit_button('Confirm Selection')
    if next_iteration == 'Yes':
        st.session_state['ocel'] = mod_ocel
        reset_values_dict = {'ocel_json_dict': {}, 'tsa_params' : {}, 'tsa_technique' : '', 'mode' : '', 'comparison_operator' : '', 'threshold_1' : '', 'threshold_2' : '', 'events_df' : '', \
                            'event_types' : '', 'object_types' : '', 'event_object_combinations' : [], 'objects_summary_df' : '', 'event_to_object_relations_df' : '', \
                            'objects_df' : '', 'object_changes_df' : '', 'first_event_timestamp':'', 'last_event_timestamp':'', 'events_to_time_df':'',\
                            'objects_to_time_df':'', 'object_types_to_df_map':{}, 'event_types_to_df_map':{}, 'TS_collection':{},\
                            'prev_iterations_data':{}, 'change_point_indices_dict' : {}, 'ts_causal_factors_dict' : {}, 'change_point_idx_ts_dict' : {},\
                            'threshold_based_ts_dict' : {}, 'ts_forecasts_df' : '', 'granger_df':'', 'forecast_column':'', 'ar_collection':{}, 'ts_mod_ocel_json_dict': {}, \
                            'mod_ocel_json_dict' : {}, 'mod_ocel':'', 'tbpd_params_list': [], 'is_ar_empty':False}
        for key,value in reset_values_dict.items():
            st.session_state[key] = value
        st.rerun()
    else:
        st.stop()
else:
    if append_forecasts_to_ts == 'Yes':
        st.sidebar.markdown('Further iterations or modification of the OCEL is not possible after appending forecasts to timeseries. For further analysis please start again with a fresh copy of the OCEL.')
    elif only_compare_threshold_ts == 'Yes' or use_tbpd_results_as_ts_for_granger_causality == 'Yes':
        st.sidebar.markdown('Further iterations or modification of the OCEL is not possible after conducting analysis using the timeseries derived from threshold based points. For further analysis please start again with a fresh copy of the OCEL.')