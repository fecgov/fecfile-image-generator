import os
import pypdftk
import sys
import traceback

from flask import current_app
from os import path


def print_sc_line(
    f3x_data,
    md5_directory,
    sc_schedules,
    sc_start_page,
    total_no_of_pages,
    image_num=None,
):
    try:
        sc_schedule_total = 0
        os.makedirs(md5_directory + "SC/", exist_ok=True)
        sc_infile = current_app.config["FORM_TEMPLATES_LOCATION"].format("SC")
        sc1_list = []
        totalOutstandingLoans = "0.00"

        page_num = 0
        for sc in sc_schedules:
            page_subtotal = "{0:.2f}".format(float(sc.get("loanBalance")))

            # memo_array = []
            sc_schedule_total += float(page_subtotal)
            sc_schedule_page_dict = {}
            sc_schedule_page_dict["TRANSACTION_ID"] = sc.get("transactionId")
            sc_schedule_page_dict["totalPages"] = total_no_of_pages
            sc_schedule_page_dict["committeeName"] = f3x_data.get("committeeName")
            sc_schedule_page_dict["pageSubtotal"] = page_subtotal

            for item in [
                "memoCode",
                "memoDescription",
                "lenderStreet1",
                "lenderStreet2",
                "lenderCity",
                "lenderState",
                "lenderZipCode",
                "electionOtherDescription",
                "isLoanSecured",
            ]:
                sc_schedule_page_dict[item] = sc.get(item)

            for item in [
                "loanAmountOriginal",
                "loanPaymentToDate",
                "loanBalance",
                "loanInterestRate",
            ]:
                sc_schedule_page_dict[item] = "{0:.2f}".format(float(sc.get(item)))

            if "electionCode" in sc and sc.get("electionCode") != "":
                sc_schedule_page_dict["electionType"] = sc.get("electionCode")[0:1]
                sc_schedule_page_dict["electionYear"] = sc.get("electionCode")[1:5]

            # if sc.get('lenderOrganizationName') == "":
            if not sc.get("lenderOrganizationName"):
                lenderName = ""
                for item in [
                    "lenderLastName",
                    "lenderFirstName",
                    "lenderMiddleName",
                    "lenderPrefix",
                    "lenderSuffix",
                ]:
                    if sc.get(item):
                        lenderName += sc.get(item) + " "
                sc_schedule_page_dict["lenderName"] = lenderName[0:-1]
            else:
                sc_schedule_page_dict["lenderName"] = sc.get("lenderOrganizationName")

            if sc.get("loanIncurredDate"):
                date_array = sc.get("loanIncurredDate").split("/")
                sc_schedule_page_dict["loanIncurredDateMonth"] = date_array[0]
                sc_schedule_page_dict["loanIncurredDateDay"] = date_array[1]
                sc_schedule_page_dict["loanIncurredDateYear"] = date_array[2]

            if sc.get("loanDueDate"):
                if "-" in sc.get("loanDueDate"):
                    date_array = sc.get("loanDueDate").split("-")
                    if len(date_array) == 3:
                        sc_schedule_page_dict["loanDueDateMonth"] = date_array[1]
                        sc_schedule_page_dict["loanDueDateDay"] = date_array[2]
                        sc_schedule_page_dict["loanDueDateYear"] = date_array[0]
                    else:
                        sc_schedule_page_dict["loanDueDateYear"] = sc.get("loanDueDate")
                elif "/" in sc.get("loanDueDate"):
                    date_array = sc.get("loanDueDate").split("/")
                    if len(date_array) == 3:
                        sc_schedule_page_dict["loanDueDateMonth"] = date_array[0]
                        sc_schedule_page_dict["loanDueDateDay"] = date_array[1]
                        sc_schedule_page_dict["loanDueDateYear"] = date_array[2]
                    else:
                        sc_schedule_page_dict["loanDueDateYear"] = sc.get("loanDueDate")
                else:
                    sc_schedule_page_dict["loanDueDateYear"] = sc.get("loanDueDate")

            if sc.get("child"):
                sc2 = []
                for sc_child in sc.get("child"):
                    if sc_child.get("transactionTypeIdentifier") == "SC2":
                        sc2.append(sc_child)
                    elif sc_child.get("transactionTypeIdentifier") == "SC1":
                        # sc_child['SCPageNo'] = sc_start_page
                        sc1_list.append(sc_child)
                if sc2:
                    sc2_list = []
                    temp_sc2 = []
                    for i in range(len(sc2)):
                        temp_sc2.append(sc2[i])
                        if i % 4 == 3 or i == len(sc2) - 1:
                            sc2_list.append(temp_sc2)
                            temp_sc2 = []

                    for i in range(len(sc2_list)):
                        sc_schedule_single_page_dict = {}
                        sc_schedule_single_page_dict = sc_schedule_page_dict
                        for j in range(len(sc2_list[i])):
                            sc2_name = ""
                            for k in [
                                "prefix",
                                "lastName",
                                "firstName",
                                "middleName",
                                "suffix",
                            ]:
                                if sc2_list[i][j].get(k) != "":
                                    sc2_name += sc2_list[i][j].get(k) + ","

                            sc_schedule_single_page_dict[
                                "name_{}".format(j + 1)
                            ] = sc2_name[0:-1]
                            sc_schedule_single_page_dict[
                                "street1_{}".format(j + 1)
                            ] = sc2_list[i][j].get("street1")
                            sc_schedule_single_page_dict[
                                "street2_{}".format(j + 1)
                            ] = sc2_list[i][j].get("street2")
                            sc_schedule_single_page_dict[
                                "city_{}".format(j + 1)
                            ] = sc2_list[i][j].get("city")
                            sc_schedule_single_page_dict[
                                "state_{}".format(j + 1)
                            ] = sc2_list[i][j].get("state")
                            sc_schedule_single_page_dict[
                                "zipCode_{}".format(j + 1)
                            ] = sc2_list[i][j].get("zipCode")
                            sc_schedule_single_page_dict[
                                "employer_{}".format(j + 1)
                            ] = sc2_list[i][j].get("employer")
                            sc_schedule_single_page_dict[
                                "occupation_{}".format(j + 1)
                            ] = sc2_list[i][j].get("occupation")
                            sc_schedule_single_page_dict[
                                "guaranteedAmount_{}".format(j + 1)
                            ] = "{0:.2f}".format(
                                float(sc2_list[i][j].get("guaranteedAmount"))
                            )

                        sc_schedule_single_page_dict["pageNo"] = (
                            sc_start_page + page_num
                        )
                        page_num += 1

                        if image_num:
                            sc_schedule_single_page_dict["IMGNO"] = image_num
                            image_num += 1

                        if (
                            sc_schedules[len(sc_schedules) - 1].get("transactionId")
                            == sc_schedule_single_page_dict.get("TRANSACTION_ID")
                            and i == len(sc2_list) - 1
                        ):
                            totalOutstandingLoans = sc_schedule_single_page_dict[
                                "scheduleTotal"
                            ] = "{0:.2f}".format(sc_schedule_total)
                        sc_outfile = (
                            md5_directory
                            + "SC"
                            + "/page_"
                            + str(sc_start_page)
                            + ".pdf"
                        )
                        pypdftk.fill_form(
                            sc_infile, sc_schedule_single_page_dict, sc_outfile
                        )

                        # Memo text changes
                        if sc_schedule_page_dict.get("memoDescription"):
                            memo_dict = {}
                            temp_memo_outfile = md5_directory + "SC/page_memo_temp.pdf"
                            memo_infile = current_app.config[
                                "FORM_TEMPLATES_LOCATION"
                            ].format("TEXT")
                            memo_outfile = (
                                md5_directory
                                + "SC/page_memo_"
                                + str(sc_start_page)
                                + ".pdf"
                            )
                            memo_dict["scheduleName_1"] = "SC13"
                            memo_dict["PAGESTR"] = (
                                "PAGE "
                                + str(sc_start_page + page_num)
                                + " / "
                                + str(total_no_of_pages)
                            )
                            memo_dict["memoDescription_1"] = sc_schedule_page_dict[
                                "memoDescription"
                            ]
                            if (
                                "TRANSACTION_ID" in sc_schedule_page_dict
                                and sc_schedule_page_dict["TRANSACTION_ID"]
                            ):
                                memo_dict["transactionId_1"] = sc_schedule_page_dict[
                                    "TRANSACTION_ID"
                                ]

                            page_num += 1

                            if image_num:
                                memo_dict["IMGNO"] = image_num
                                image_num += 1

                            # build memo page
                            pypdftk.fill_form(memo_infile, memo_dict, memo_outfile)
                            pypdftk.concat(
                                [sc_outfile, memo_outfile], temp_memo_outfile
                            )
                            os.remove(memo_outfile)
                            os.rename(temp_memo_outfile, sc_outfile)

                        for j in range(len(sc2_list[i])):
                            del sc_schedule_single_page_dict["name{}".format(j + 1)]
                            del sc_schedule_single_page_dict["street1_{}".format(j + 1)]
                            del sc_schedule_single_page_dict["street2_{}".format(j + 1)]
                            del sc_schedule_single_page_dict["city_{}".format(j + 1)]
                            del sc_schedule_single_page_dict["state_{}".format(j + 1)]
                            del sc_schedule_single_page_dict["zipCode_{}".format(j + 1)]
                            del sc_schedule_single_page_dict[
                                "employer_{}".format(j + 1)
                            ]
                            del sc_schedule_single_page_dict[
                                "occupation_{}".format(j + 1)
                            ]
                            del sc_schedule_single_page_dict[
                                "guaranteedAmount_{}".format(j + 1)
                            ]
                        if path.isfile(md5_directory + "SC/all_pages.pdf"):
                            pypdftk.concat(
                                [
                                    md5_directory + "SC/all_pages.pdf",
                                    md5_directory
                                    + "SC"
                                    + "/page_"
                                    + str(sc_start_page)
                                    + ".pdf",
                                ],
                                md5_directory + "SC/temp_all_pages.pdf",
                            )
                            os.rename(
                                md5_directory + "SC/temp_all_pages.pdf",
                                md5_directory + "SC/all_pages.pdf",
                            )
                        else:
                            os.rename(
                                md5_directory
                                + "SC"
                                + "/page_"
                                + str(sc_start_page)
                                + ".pdf",
                                md5_directory + "SC/all_pages.pdf",
                            )
                else:
                    sc_schedule_page_dict["pageNo"] = sc_start_page + page_num
                    page_num += 1

                    if image_num:
                        sc_schedule_page_dict["IMGNO"] = image_num
                        image_num += 1

                    if sc_schedules[len(sc_schedules) - 1].get(
                        "transactionId"
                    ) == sc_schedule_page_dict.get("TRANSACTION_ID"):
                        totalOutstandingLoans = sc_schedule_page_dict[
                            "scheduleTotal"
                        ] = "{0:.2f}".format(sc_schedule_total)
                    sc_outfile = (
                        md5_directory + "SC" + "/page_" + str(sc_start_page) + ".pdf"
                    )
                    pypdftk.fill_form(sc_infile, sc_schedule_page_dict, sc_outfile)

                    # Memo text changes
                    if sc_schedule_page_dict.get("memoDescription"):
                        memo_dict = {}
                        temp_memo_outfile = md5_directory + "SC/page_memo_temp.pdf"
                        memo_infile = current_app.config[
                            "FORM_TEMPLATES_LOCATION"
                        ].format("TEXT")
                        memo_outfile = (
                            md5_directory
                            + "SC/page_memo_"
                            + str(sc_start_page)
                            + ".pdf"
                        )
                        memo_dict["scheduleName_1"] = "SC13"
                        memo_dict["PAGESTR"] = (
                            "PAGE "
                            + str(sc_start_page + page_num)
                            + " / "
                            + str(total_no_of_pages)
                        )
                        memo_dict["memoDescription_1"] = sc_schedule_page_dict[
                            "memoDescription"
                        ]
                        if (
                            "TRANSACTION_ID" in sc_schedule_page_dict
                            and sc_schedule_page_dict["TRANSACTION_ID"]
                        ):
                            memo_dict["transactionId_1"] = sc_schedule_page_dict[
                                "TRANSACTION_ID"
                            ]

                        page_num += 1

                        if image_num:
                            memo_dict["IMGNO"] = image_num
                            image_num += 1

                        # build page
                        pypdftk.fill_form(memo_infile, memo_dict, memo_outfile)
                        pypdftk.concat([sc_outfile, memo_outfile], temp_memo_outfile)
                        os.remove(memo_outfile)
                        os.rename(temp_memo_outfile, sc_outfile)

                    if path.isfile(md5_directory + "SC/all_pages.pdf"):
                        pypdftk.concat(
                            [
                                md5_directory + "SC/all_pages.pdf",
                                md5_directory
                                + "SC"
                                + "/page_"
                                + str(sc_start_page)
                                + ".pdf",
                            ],
                            md5_directory + "SC/temp_all_pages.pdf",
                        )
                        os.rename(
                            md5_directory + "SC/temp_all_pages.pdf",
                            md5_directory + "SC/all_pages.pdf",
                        )
                    else:
                        os.rename(
                            md5_directory
                            + "SC"
                            + "/page_"
                            + str(sc_start_page)
                            + ".pdf",
                            md5_directory + "SC/all_pages.pdf",
                        )
            else:
                sc_schedule_page_dict["pageNo"] = sc_start_page + page_num
                page_num += 1

                if image_num:
                    sc_schedule_page_dict["IMGNO"] = image_num
                    print("Bug", image_num)
                    image_num += 1

                if sc_schedules[len(sc_schedules) - 1].get(
                    "transactionId"
                ) == sc_schedule_page_dict.get("TRANSACTION_ID"):
                    totalOutstandingLoans = sc_schedule_page_dict[
                        "scheduleTotal"
                    ] = "{0:.2f}".format(sc_schedule_total)
                sc_outfile = (
                    md5_directory + "SC" + "/page_" + str(sc_start_page) + ".pdf"
                )
                pypdftk.fill_form(sc_infile, sc_schedule_page_dict, sc_outfile)

                # Memo text changes
                if sc_schedule_page_dict.get("memoDescription"):
                    memo_dict = {}
                    temp_memo_outfile = md5_directory + "SC/page_memo_temp.pdf"
                    memo_infile = current_app.config["FORM_TEMPLATES_LOCATION"].format(
                        "TEXT"
                    )
                    memo_outfile = (
                        md5_directory + "SC/page_memo_" + str(sc_start_page) + ".pdf"
                    )
                    memo_dict["scheduleName_1"] = "SC13"
                    memo_dict["PAGESTR"] = (
                        "PAGE "
                        + str(sc_start_page + page_num)
                        + " / "
                        + str(total_no_of_pages)
                    )
                    memo_dict["memoDescription_1"] = sc_schedule_page_dict[
                        "memoDescription"
                    ]
                    if (
                        "TRANSACTION_ID" in sc_schedule_page_dict
                        and sc_schedule_page_dict["TRANSACTION_ID"]
                    ):
                        memo_dict["transactionId_1"] = sc_schedule_page_dict[
                            "TRANSACTION_ID"
                        ]

                    page_num += 1

                    if image_num:
                        memo_dict["IMGNO"] = image_num
                        image_num += 1

                    # build page
                    pypdftk.fill_form(memo_infile, memo_dict, memo_outfile)
                    pypdftk.concat([sc_outfile, memo_outfile], temp_memo_outfile)
                    os.remove(memo_outfile)
                    os.rename(temp_memo_outfile, sc_outfile)

                if path.isfile(md5_directory + "SC/all_pages.pdf"):
                    pypdftk.concat(
                        [
                            md5_directory + "SC/all_pages.pdf",
                            md5_directory
                            + "SC"
                            + "/page_"
                            + str(sc_start_page)
                            + ".pdf",
                        ],
                        md5_directory + "SC/temp_all_pages.pdf",
                    )
                    os.rename(
                        md5_directory + "SC/temp_all_pages.pdf",
                        md5_directory + "SC/all_pages.pdf",
                    )
                else:
                    os.rename(
                        md5_directory + "SC" + "/page_" + str(sc_start_page) + ".pdf",
                        md5_directory + "SC/all_pages.pdf",
                    )
        return sc1_list, sc_start_page + page_num - 1, totalOutstandingLoans, image_num
    except:
        # printing stack trace
        traceback.print_exception(*sys.exc_info())
