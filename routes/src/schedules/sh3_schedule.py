import os
import pypdftk

from flask import current_app
from os import path
from routes.src.utils import directory_files
from routes.src.f3x.helper import get_sh3_page_count, make_sh3_dict


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

        sh3_dict = make_sh3_dict(sh3_list)

        current_page_num = 0

        for hash_check, hash_check_value in sh3_dict.items():
            hash_check_total_pages = get_sh3_page_count(hash_check_value)
            account_name = hash_check.split("@@")[0]
            receipt_date = None

            if len(hash_check.split("@@")[0]) > 1:
                receipt_date = hash_check.split("@@")[1]

            event_type_dict = {
                "AD": {"current_index": 0, "amount": 0},
                "GV": {"current_index": 0, "amount": 0},
                "EA": {"current_index": 0, "amount": 0},
                "DC": {"current_index": 0, "amount": 0},
                "DF": {"current_index": 0, "amount": 0},
                "PC": {"current_index": 0, "amount": 0},
            }

            total_amount = 0
            while hash_check_total_pages:
                hash_check_total_pages -= 1
                current_page_total_amount = 0

                current_page_num += 1

                sh3_schedule_page_dict = {}

                sh3_schedule_page_dict["lineNumber"] = line_number
                sh3_schedule_page_dict["pageNo"] = (
                    sh3_line_start_page + current_page_num
                )
                sh3_schedule_page_dict["totalPages"] = total_no_of_pages

                if image_num:
                    sh3_schedule_page_dict["IMGNO"] = image_num
                    image_num += 1

                sh3_schedule_page_dict["accountName"] = account_name

                if receipt_date:
                    date_array = receipt_date.split("/")
                    sh3_schedule_page_dict["receiptDateMonth"] = date_array[0]
                    sh3_schedule_page_dict["receiptDateDay"] = date_array[1]
                    sh3_schedule_page_dict["receiptDateYear"] = date_array[2]

                for event_type, value_list in hash_check_value.items():
                    current_index = event_type_dict[event_type]["current_index"]

                    if current_index < len(value_list):
                        sh3_schedule_page_dict[
                            event_type.lower() + "transactionId"
                        ] = value_list[current_index]["transactionId"]
                        sh3_schedule_page_dict[
                            event_type.lower() + "transferredAmount"
                        ] = "{0:.2f}".format(
                            float(value_list[current_index]["transferredAmount"])
                        )
                        current_page_total_amount += float(
                            sh3_schedule_page_dict[
                                event_type.lower() + "transferredAmount"
                            ]
                        )

                        event_type_dict[event_type]["current_index"] += 1

                        if event_type in ["DC", "DF"]:
                            sub_transferred_amount = float(
                                sh3_schedule_page_dict[
                                    event_type.lower() + "transferredAmount"
                                ]
                            )
                            event_type_dict[event_type]["amount"] += float(
                                sh3_schedule_page_dict[
                                    event_type.lower() + "transferredAmount"
                                ]
                            )

                            sh3_schedule_page_dict[
                                event_type.lower() + "activityEventName"
                            ] = value_list[current_index]["activityEventName"]

                            if current_index + 1 < len(value_list):
                                current_index += 1
                                sh3_schedule_page_dict[
                                    event_type.lower() + "transactionId_1"
                                ] = value_list[current_index]["transactionId"]
                                sh3_schedule_page_dict[
                                    event_type.lower() + "transferredAmount_1"
                                ] = "{0:.2f}".format(
                                    float(
                                        value_list[current_index]["transferredAmount"]
                                    )
                                )
                                sh3_schedule_page_dict[
                                    event_type.lower() + "activityEventName_1"
                                ] = value_list[current_index]["activityEventName"]

                                sub_transferred_amount += float(
                                    sh3_schedule_page_dict[
                                        event_type.lower() + "transferredAmount_1"
                                    ]
                                )
                                current_page_total_amount += float(
                                    sh3_schedule_page_dict[
                                        event_type.lower() + "transferredAmount_1"
                                    ]
                                )

                                event_type_dict[event_type]["current_index"] += 1
                                event_type_dict[event_type]["amount"] += float(
                                    sh3_schedule_page_dict[
                                        event_type.lower() + "transferredAmount_1"
                                    ]
                                )

                            sh3_schedule_page_dict[
                                event_type.lower() + "subtransferredAmount"
                            ] = "{0:.2f}".format(float(sub_transferred_amount))
                        else:
                            event_type_dict[event_type]["amount"] += float(
                                sh3_schedule_page_dict[
                                    event_type.lower() + "transferredAmount"
                                ]
                            )

                sh3_schedule_page_dict["totalAmountTransferred"] = "{0:.2f}".format(
                    float(current_page_total_amount)
                )
                total_amount += current_page_total_amount

                # condition for last page
                if not hash_check_total_pages:
                    sh3_schedule_page_dict["totalAmountPeriod"] = "{0:.2f}".format(
                        float(total_amount)
                    )
                    for key, value in event_type_dict.items():
                        sh3_schedule_page_dict[
                            key.lower() + "total"
                        ] = "{0:.2f}".format(float(value["amount"]))

                sh3_outfile = (
                    md5_directory
                    + "SH3/"
                    + line_number
                    + "/page_"
                    + str(current_page_num - 1)
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
