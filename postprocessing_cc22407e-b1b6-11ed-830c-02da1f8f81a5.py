import json
import traceback
import pandas as pd
from nameparser import HumanName
from date_format_updated import transform_date


def get_annotation_value(extracted_df, annotation):
    return extracted_df.loc[annotation]['value']


def general_fields(pvi_json, extracted_df):
    final_list = []
    if pvi_json["senderCaseVersion"] and pvi_json["senderCaseVersion"] == '2':
        pvi_json['mostRecentReceiptDate'] = None
    if pvi_json['senderCaseVersion_acc'] and pvi_json['senderCaseVersion_acc'] == '1':
        pvi_json['sourceType'][0]['value'] = 'Solicited - Post Mkt Surv'
    elif pvi_json['senderCaseVersion_acc'] and pvi_json['senderCaseVersion_acc'] == '2':
        pvi_json['sourceType'][0]['value'] = 'Spontaneous'
    pvi_json['senderCaseVersion_acc'] = None
    if pvi_json["senderCaseVersion"]:
        pvi_json["senderCaseVersion"] = int(pvi_json["senderCaseVersion"])
    #pat_data = get_annotation_value(extracted_df, 'PMMPATIENT')
    #pvi_json['patient']['name'] = pat_data[0][3].strip()
    if pvi_json['patient']['age']['inputValue'] and '/' in pvi_json['patient']['age']['inputValue']:
        pvi_json['patient']['age']['inputValue'] = transform_date(pvi_json['patient']['age']['inputValue'], 'dd/mm/yyyy', '%d-%b-%Y')
    if pvi_json['patient']['name']:
        pvi_json['patient']['name'] = '/' + pvi_json['patient']['name']
    for med_his in pvi_json['patient']['medicalHistories']:
        if med_his['reportedReaction']:
            final_list.append(med_his)
    pvi_json['patient']['medicalHistories'] = final_list
    return pvi_json


def parse_reporter_details(pvi_json):
    final_reporter_list = []
    for reporter in pvi_json['reporters']:
        reporter['faxNumber'], reporter['fax'] = reporter['fax'], None
        reporter['consentForFU'], reporter['country_acc'] = reporter['country_acc'], None
        if reporter['department_acc'] and 'patient' in reporter['department_acc'].lower().strip():
            reporter['contactType'], reporter['department_acc'] = reporter['department_acc'], None
        if reporter['contactType_acc']:
            parsed_name_dict = HumanName(reporter['firstName'])
            reporter['title'] = parsed_name_dict['title'].title().upper()
            reporter['firstName'] = parsed_name_dict['first'].title().upper()
            reporter['middleName'] = parsed_name_dict['middle'].title().upper()
            reporter['lastName'] = parsed_name_dict['last'].title().upper()
        if reporter['firstName'] or reporter['lastName'] or reporter['middleName']:
            final_reporter_list.append(reporter)
    pvi_json['reporters'] = final_reporter_list
    found_intermediary = False
    for reporter in pvi_json['reporters']:
        if reporter['Intermediary']:
            if not found_intermediary:
                reporter['primary'] = 'Yes'
                found_intermediary = True
            reporter['Intermediary'] = None
    return pvi_json


def date_validator(pvi_json):
    if isinstance(pvi_json, dict):
        for key, value in pvi_json.items():
            if isinstance(value, dict):
                date_validator(value)
            elif isinstance(value, list):
                for val in value:
                    date_validator(val)
            else:
                if key.lower().endswith("date") and value:
                    pvi_json.update({key: transform_date(value, 'dd/mm/yyyy', '%d-%b-%Y')})
    elif isinstance(pvi_json, list):
        for list_element in pvi_json:
            date_validator(list_element)
    return pvi_json


def product_seq_num(pvi_json):
    freq_list = ['bid', 'prn', 'q10h', 'q2h', 'q3h', 'q4h', 'qd', 'qh', 'qid', 'qod', 'qom', 'qow', 'qw', 'single', 'tid']
    for prod in pvi_json['products']:
        prod['seq_num'] = pvi_json['products'].index(prod) + 1
        for dose_info in prod['doseInformations']:
            if dose_info['dose_inputValue']:
                dose_info['dose_inputValue'] = ' '.join(dose_info['dose_inputValue'].split()[:2])
            if dose_info['frequency_value']:
                if dose_info['frequency_value'].strip().lower() in freq_list:
                    pass
                else:
                    if dose_info['description']:
                        dose_info['description'] = dose_info['description'] + ' Frequency: ' + dose_info['frequency_value']
                    else:
                        dose_info['description'] = 'Frequency: ' + dose_info['frequency_value']
    return pvi_json


def get_postprocessed_json(pvi_json, extracted_data_json):
    extracted_df = pd.DataFrame(extracted_data_json)
    extracted_df.set_index("class", inplace=True)
    try:
        pvi_json = general_fields(pvi_json, extracted_df)
    except:
        traceback.print_exc()
    try:
        pvi_json = parse_reporter_details(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = product_seq_num(pvi_json)
    except:
        traceback.print_exc()
    try:
        pvi_json = date_validator(pvi_json)
    except:
        traceback.print_exc()
    return pvi_json
