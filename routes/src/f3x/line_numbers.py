# Below method builds line number array for different schedules

def process_sa_line_numbers(sa_line_numbers_dict, sa_obj):
    line_num_val = '11A1' if sa_obj.get('lineNumber') in ['11A', '11AI', '11AII'] else sa_obj.get('lineNumber')
    if line_num_val and line_num_val in sa_line_numbers_dict:
        sa_line_numbers_dict[line_num_val]['data'].append(sa_obj)


def process_sf_line_numbers(sf_crd, sf_non_crd, sf_empty_ord, sf_empty_non_ord, sf_empty_none, sf_empty_sub,
                            sf_crd_memo, sf_non_crd_memo, sf_empty_ord_memo, sf_empty_non_ord_memo,
                            sf_empty_none_memo, sf_empty_sub_memo,
                            sf_obj):
    if sf_obj["coordinateExpenditure"] ==  "Y":
        sf_crd.append(sf_obj)
        if sf_obj['memoDescription']:
            sf_crd_memo.append(
                {'scheduleName': 'SF' + sf_obj['lineNumber'], 'memoDescription': sf_obj['memoDescription'],
                 'transactionId': sf_obj['transactionId']})
    elif sf_obj["coordinateExpenditure"] ==  "N" and sf_obj['subordinateCommitteeName']:
        sf_non_crd.append(sf_obj)
        if sf_obj['memoDescription']:
            sf_non_crd_memo.append(
                {'scheduleName': 'SF' + sf_obj['lineNumber'], 'memoDescription': sf_obj['memoDescription'],
                 'transactionId': sf_obj['transactionId']})
    elif sf_obj["coordinateExpenditure"] == '' and sf_obj['designatingCommitteeName']:
        sf_empty_ord.append(sf_obj)
        if sf_obj['memoDescription']:
            sf_empty_ord_memo.append(
                {'scheduleName': 'SF' + sf_obj['lineNumber'], 'memoDescription': sf_obj['memoDescription'],
                 'transactionId': sf_obj['transactionId']})
    elif sf_obj["coordinateExpenditure"] == '' and sf_obj['subordinateCommitteeName']: 
        sf_empty_non_ord.append(sf_obj)
        if sf_obj['memoDescription']:
            sf_crd_memo.append(
                {'scheduleName': 'SF' + sf_obj['lineNumber'], 'memoDescription': sf_obj['memoDescription'],
                 'transactionId': sf_obj['transactionId']})
    elif sf_obj["coordinateExpenditure"] == '' and sf_obj['subordinateCommitteeName'] == '' and sf_obj['designatingCommitteeName'] == '':
        sf_empty_none.append(sf_obj)
        if sf_obj['memoDescription']:
            sf_empty_none_memo.append(
                {'scheduleName': 'SF' + sf_obj['lineNumber'], 'memoDescription': sf_obj['memoDescription'],
                 'transactionId': sf_obj['transactionId']})
    elif sf_obj["coordinateExpenditure"] == 'N' and sf_obj['subordinateCommitteeName'] == '':
        sf_empty_sub.append(sf_obj)
        if sf_obj['memoDescription']:
            sf_empty_sub_memo.append(
                {'scheduleName': 'SF' + sf_obj['lineNumber'], 'memoDescription': sf_obj['memoDescription'],
                 'transactionId': sf_obj['transactionId']})


def process_sh_line_numbers(sh_line_numbers_dict, sh_obj):

    if sh_obj['transactionTypeIdentifier'] == 'ALLOC_H1':
        sh_line_numbers_dict['H1']['data'].append(sh_obj)

    elif sh_obj['transactionTypeIdentifier'] == 'ALLOC_H2_RATIO':
        sh_line_numbers_dict['H2']['data'].append(sh_obj)

    else:
        line_num_val = sh_obj.get('lineNumber')
        if line_num_val and sh_line_numbers_dict.get(line_num_val):
            sh_line_numbers_dict[line_num_val]['data'].append(sh_obj)


def process_line_numbers(line_numbers_dict, obj):
    line_num_val = obj.get('lineNumber')
    if line_num_val and line_num_val in line_numbers_dict:
        line_numbers_dict[line_num_val]['data'].append(obj)
