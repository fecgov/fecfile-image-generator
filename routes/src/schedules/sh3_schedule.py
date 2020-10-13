import os
import pypdftk

from flask import current_app
from os import path
from routes.src.utils import directory_files


def print_sh3_line(
    f3x_data,
    md5_directory,
    line_number,
    sh3_list,
    sh3_line_page_cnt,
    sh3_line_start_page,
    total_no_of_pages,
    image_num=None,
):
    if sh3_list:
        os.makedirs(md5_directory + "SH3/" + line_number, exist_ok=True)
        sh3_infile = current_app.config["FORM_TEMPLATES_LOCATION"].format("SH3")
        sh3_line_dict = []
        sh3_line_transaction = []
        total_dict = {}
        t_transfered = {}
        # dc_subtotal = 0
        # df_subtotal = 0
        for sh3 in sh3_list:
            a_n = sh3["accountName"]
            hash_check = "%s-%s" % (sh3["accountName"], sh3["receiptDate"])
            if hash_check not in sh3_line_transaction:
                sh3_line_transaction.append(hash_check)
            ind = sh3_line_transaction.index(hash_check)

            if len(sh3_line_dict) <= ind:
                sh3_line_dict.insert(ind, sh3)

            if sh3["activityEventType"] == "DF":
                ind = sh3_line_transaction.index(hash_check)
                if sh3_line_dict[ind].get("dfsubs"):
                    sh3_line_dict[ind]["dfsubs"].append(sh3)
                    sh3_line_dict[ind]["dftotal"] += sh3["transferredAmount"]
                else:
                    sh3_line_dict[ind]["dfsubs"] = [sh3]
                    sh3_line_dict[ind]["dftotal"] = sh3["transferredAmount"]
            elif sh3["activityEventType"] == "DC":
                ind = sh3_line_transaction.index(hash_check)
                if sh3_line_dict[ind].get("dcsubs"):
                    sh3_line_dict[ind]["dcsubs"].append(sh3)
                    sh3_line_dict[ind]["dctotal"] += sh3["transferredAmount"]
                else:
                    sh3_line_dict[ind]["dcsubs"] = [sh3]
                    sh3_line_dict[ind]["dctotal"] = sh3["transferredAmount"]
            else:
                ind = sh3_line_transaction.index(hash_check)
                if sh3_line_dict[ind].get("subs"):
                    sh3_line_dict[ind]["subs"].append(sh3)
                else:
                    sh3_line_dict[ind]["subs"] = [sh3]

            if ind in t_transfered:
                t_transfered[ind] += sh3["transferredAmount"]
            else:
                t_transfered[ind] = sh3["transferredAmount"]

            if a_n in total_dict and sh3["activityEventType"] in total_dict[a_n]:
                total_dict[a_n][sh3["activityEventType"]] += sh3["transferredAmount"]
                total_dict[a_n]["lastpage"] = ind
            elif a_n in total_dict:
                total_dict[a_n][sh3["activityEventType"]] = sh3["transferredAmount"]
                total_dict[a_n]["lastpage"] = ind
            else:
                total_dict[a_n] = {
                    sh3["activityEventType"]: sh3["transferredAmount"],
                    "lastpage": ind,
                }

        if sh3_line_page_cnt > 0:
            sh3_line_start_page += 1
            for sh3_page_no, sh3_page in enumerate(sh3_line_dict):
                # page_subtotal = 0.00
                last_page = False
                sh3_schedule_page_dict = {}
                sh3_schedule_page_dict["lineNumber"] = line_number
                sh3_schedule_page_dict["pageNo"] = sh3_line_start_page + sh3_page_no
                sh3_schedule_page_dict["totalPages"] = total_no_of_pages
                acc_name = sh3_page.get("accountName")
                lastpage_c = total_dict[acc_name]["lastpage"]

                if image_num:
                    sh3_schedule_page_dict["IMGNO"] = image_num
                    image_num += 1

                # page_start_index = sh3_page_no * 1
                if sh3_page_no == lastpage_c:
                    last_page = True
                # This call prepares data to render on PDF
                # sh3_schedule_page_dict['adtransactionId'] = sh3_page['transactionId']
                # sh3_schedule_page_dict['adtransferredAmount'] = t_transfered[sh3_page_no]
                sh3_schedule_page_dict["accountName"] = acc_name
                sh3_schedule_page_dict["totalAmountTransferred"] = "{0:.2f}".format(
                    float(t_transfered[sh3_page_no])
                )

                if "receiptDate" in sh3_page:

                    date_array = sh3_page["receiptDate"].split("/")
                    sh3_schedule_page_dict["receiptDateMonth"] = date_array[0]
                    sh3_schedule_page_dict["receiptDateDay"] = date_array[1]
                    sh3_schedule_page_dict["receiptDateYear"] = date_array[2]

                for sub_sh3 in sh3_page.get("subs", []):
                    s_ = sub_sh3["activityEventType"].lower()
                    sh3_schedule_page_dict[s_ + "transactionId"] = sub_sh3[
                        "transactionId"
                    ]
                    sh3_schedule_page_dict[s_ + "transferredAmount"] = "{0:.2f}".format(
                        float(sub_sh3["transferredAmount"])
                    )

                df_inc = ""

                for sub_sh3 in sh3_page.get("dfsubs", []):
                    s_ = sub_sh3["activityEventType"].lower()
                    sh3_schedule_page_dict[s_ + "transactionId" + df_inc] = sub_sh3[
                        "transactionId"
                    ]
                    sh3_schedule_page_dict[
                        s_ + "transferredAmount" + df_inc
                    ] = "{0:.2f}".format(float(sub_sh3["transferredAmount"]))
                    sh3_schedule_page_dict[s_ + "activityEventName" + df_inc] = sub_sh3[
                        "activityEventName"
                    ]
                    sh3_schedule_page_dict[
                        s_ + "subtransferredAmount"
                    ] = "{0:.2f}".format(float(sh3_page.get(s_ + "total", "")))
                    df_inc = "_1"

                dc_inc = ""

                for sub_sh3 in sh3_page.get("dcsubs", []):
                    s_ = sub_sh3["activityEventType"].lower()
                    sh3_schedule_page_dict[s_ + "transactionId" + dc_inc] = sub_sh3[
                        "transactionId"
                    ]
                    sh3_schedule_page_dict[
                        s_ + "transferredAmount" + dc_inc
                    ] = "{0:.2f}".format(float(sub_sh3["transferredAmount"]))
                    sh3_schedule_page_dict[s_ + "activityEventName" + dc_inc] = sub_sh3[
                        "activityEventName"
                    ]
                    sh3_schedule_page_dict[
                        s_ + "subtransferredAmount"
                    ] = "{0:.2f}".format(float(sh3_page.get(s_ + "total", "")))
                    dc_inc = "_1"

                sh3_schedule_page_dict["committeeName"] = f3x_data["committeeName"]
                if last_page:
                    total_dict[acc_name]["lastpage"] = 0
                    sh3_schedule_page_dict["totalAmountPeriod"] = "{0:.2f}".format(
                        float(sum(total_dict[acc_name].values()))
                    )
                    for total_key in total_dict[acc_name]:
                        sh3_schedule_page_dict[
                            total_key.lower() + "total"
                        ] = "{0:.2f}".format(float(total_dict[acc_name][total_key]))

                sh3_outfile = (
                    md5_directory
                    + "SH3/"
                    + line_number
                    + "/page_"
                    + str(sh3_page_no)
                    + ".pdf"
                )
                pypdftk.fill_form(sh3_infile, sh3_schedule_page_dict, sh3_outfile)
        pypdftk.concat(
            directory_files(md5_directory + "SH3/" + line_number + "/"),
            md5_directory + "SH3/" + line_number + "/all_pages.pdf",
        )
        if path.isfile(md5_directory + "SH3/all_pages.pdf"):
            pypdftk.concat(
                [
                    md5_directory + "SH3/all_pages.pdf",
                    md5_directory + "SH3/" + line_number + "/all_pages.pdf",
                ],
                md5_directory + "SH3/temp_allpages.pdf",
            )
            os.rename(
                md5_directory + "SH3/temp_all_pages.pdf",
                md5_directory + "SH3/all_pages.pdf",
            )
        else:
            os.rename(
                md5_directory + "SH3/" + line_number + "/all_pages.pdf",
                md5_directory + "SH3/all_pages.pdf",
            )

    return image_num
