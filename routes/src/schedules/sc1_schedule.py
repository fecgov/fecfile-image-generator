import os
import pypdftk

from flask import current_app
from os import path


def print_sc1_line(
    f3x_data, md5_directory, sc1, sc1_start_page, total_no_of_pages, image_num=None
):
    sc1_start_page += 1

    # is_memo_page = 0
    sc1_schedule_page_dict = {}

    if image_num:
        sc1_schedule_page_dict["IMGNO"] = image_num
        image_num += 1

    sc1_schedule_page_dict["PAGENO"] = sc1_start_page
    sc1_schedule_page_dict["TRANSACTION_ID"] = sc1.get("transactionId")
    sc1_schedule_page_dict["TOTALPAGES"] = total_no_of_pages
    sc1_schedule_page_dict["committeeName"] = f3x_data.get("committeeName")
    sc1_schedule_page_dict["committeeId"] = f3x_data.get("committeeId")
    sc1_schedule_page_dict["lenderName"] = sc1.get("lenderOrganizationName")
    for i in [
        "lenderStreet1",
        "lenderStreet2",
        "lenderCity",
        "lenderState",
        "lenderZipCode",
        "loanInterestRate",
        "isLoanRestructured",
        "otherPartiesLiable",
        "pledgedCollateralIndicator",
        "pledgeCollateralDescription",
        "perfectedInterestIndicator",
        "futureIncomeIndicator",
        "SCPageNo",
    ]:
        sc1_schedule_page_dict[i] = sc1.get(i)
    if sc1.get("loanIncurredDate") != "":
        date_array = sc1.get("loanIncurredDate").split("/")
        sc1_schedule_page_dict["loanIncurredDateMonth"] = date_array[0]
        sc1_schedule_page_dict["loanIncurredDateDay"] = date_array[1]
        sc1_schedule_page_dict["loanIncurredDateYear"] = date_array[2]

    if sc1.get("loanDueDate") not in ["none", "null", " ", "", None]:
        if "-" in sc1.get("loanDueDate"):
            date_array = sc1.get("loanDueDate").split("-")
            if len(date_array) == 3:
                sc1_schedule_page_dict["loanDueDateMonth"] = date_array[1]
                sc1_schedule_page_dict["loanDueDateDay"] = date_array[2]
                sc1_schedule_page_dict["loanDueDateYear"] = date_array[0]
            else:
                sc1_schedule_page_dict["loanDueDateYear"] = sc1.get("loanDueDate")
        elif "/" in sc1.get("loanDueDate"):
            date_array = sc1.get("loanDueDate").split("/")
            if len(date_array) == 3:
                sc1_schedule_page_dict["loanDueDateMonth"] = date_array[0]
                sc1_schedule_page_dict["loanDueDateDay"] = date_array[1]
                sc1_schedule_page_dict["loanDueDateYear"] = date_array[2]
            else:
                sc1_schedule_page_dict["loanDueDateYear"] = sc1.get("loanDueDate")
        else:
            sc1_schedule_page_dict["loanDueDateYear"] = sc1.get("loanDueDate")
    if sc1.get("originalLoanDate") != "":
        date_array = sc1.get("originalLoanDate").split("/")
        sc1_schedule_page_dict["originalLoanDateMonth"] = date_array[0]
        sc1_schedule_page_dict["originalLoanDateDay"] = date_array[1]
        sc1_schedule_page_dict["originalLoanDateYear"] = date_array[2]
    if sc1.get("depositoryAccountEstablishedDate") != "":
        date_array = sc1.get("depositoryAccountEstablishedDate").split("/")
        sc1_schedule_page_dict["ACCOUNT_EST_DATE_MM"] = date_array[0]
        sc1_schedule_page_dict["ACCOUNT_EST_DATE_DD"] = date_array[1]
        sc1_schedule_page_dict["ACCOUNT_EST_DATE_YY"] = date_array[2]
    sc1_schedule_page_dict["loanAmount"] = "{0:.2f}".format(
        float(sc1.get("loanAmount"))
    )
    sc1_schedule_page_dict["creditAmountThisDraw"] = "{0:.2f}".format(
        float(sc1.get("creditAmountThisDraw"))
    )
    sc1_schedule_page_dict["totalOutstandingBalance"] = "{0:.2f}".format(
        float(sc1.get("totalOutstandingBalance"))
    )
    sc1_schedule_page_dict["BACK_REF_TRAN_ID"] = sc1.get(
        "backReferenceTransactionIdNumber"
    )
    sc1_schedule_page_dict["pledgeCollateralAmount"] = "{0:.2f}".format(
        float(sc1.get("pledgeCollateralAmount"))
    )
    sc1_schedule_page_dict["PLEDGE_DESC"] = sc1.get("futureIncomeDescription")
    sc1_schedule_page_dict["PLEDGE_ESTIMATED_AMOUNT"] = "{0:.2f}".format(
        float(sc1.get("futureIncomeEstimate"))
    )
    treasurerName = ""
    for i in [
        "treasurerPrefix",
        "treasurerLastName",
        "treasurerFirstName",
        "treasurerMiddleName",
        "treasurerSuffix",
    ]:
        if sc1.get(i) != "":
            treasurerName += sc1.get(i) + " "
    sc1_schedule_page_dict["COMMITTEE_TREASURER_NAME"] = treasurerName[0:-1]
    sc1_schedule_page_dict["DEPOSITORY_NAME"] = sc1.get("depositoryAccountLocation")
    sc1_schedule_page_dict["DEPOSITORY_STREET1"] = sc1.get("depositoryAccountStreet1")
    sc1_schedule_page_dict["DEPOSITORY_STREET2"] = sc1.get("depositoryAccountStreet2")
    sc1_schedule_page_dict["DEPOSITORY_CITY"] = sc1.get("depositoryAccountCity")
    sc1_schedule_page_dict["DEPOSITORY_STATE"] = sc1.get("depositoryAccountState")
    sc1_schedule_page_dict["DEPOSITORY_ZIP"] = sc1.get("depositoryAccountZipCode")
    sc1_schedule_page_dict["BASIS"] = sc1.get("basisOfLoanDescription")
    if sc1.get("treasurerSignedDate") != "":
        date_array = sc1.get("treasurerSignedDate").split("/")
        sc1_schedule_page_dict["TREASUER_SIGN_DATE_MM"] = date_array[0]
        sc1_schedule_page_dict["TREASUER_SIGN_DATE_DD"] = date_array[1]
        sc1_schedule_page_dict["TREASUER_SIGN_DATE_YY"] = date_array[2]
    authorizedName = ""
    for i in [
        "authorizedPrefix",
        "authorizedLastName",
        "authorizedFirstName",
        "authorizedMiddleName",
        "authorizedSuffix",
    ]:
        if sc1.get(i) != "":
            authorizedName += sc1.get(i) + " "
    sc1_schedule_page_dict["AUTH_REP_NAME"] = authorizedName[0:-1]
    sc1_schedule_page_dict["AUTH_REP_TITLE"] = sc1.get("authorizedTitle")
    if sc1.get("authorizedSignedDate") != "":
        date_array = sc1.get("authorizedSignedDate").split("/")
        sc1_schedule_page_dict["AUTH_REP_SIGN_MM"] = date_array[0]
        sc1_schedule_page_dict["AUTH_REP_SIGN_DD"] = date_array[1]
        sc1_schedule_page_dict["AUTH_REP_SIGN_YY"] = date_array[2]
    sc1_infile = current_app.config["FORM_TEMPLATES_LOCATION"].format("SC1")
    sc1_outfile = md5_directory + "SC" + "/page_" + str(sc1_start_page) + ".pdf"
    pypdftk.fill_form(sc1_infile, sc1_schedule_page_dict, sc1_outfile)

    # Memo text changes
    if sc1_schedule_page_dict.get("memoDescription"):
        # is_memo_page = 1
        memo_dict = {}
        temp_memo_outfile = md5_directory + "SC/page_memo_temp.pdf"
        memo_infile = current_app.config["FORM_TEMPLATES_LOCATION"].format("TEXT")
        memo_outfile = md5_directory + "SC/page_memo_" + str(sc1_start_page) + ".pdf"
        memo_dict["scheduleName_1"] = "SC1"
        memo_dict["memoDescription_1"] = sc1_schedule_page_dict["memoDescription"]
        memo_dict["PAGESTR"] = (
            "PAGE " + str(sc1_start_page + 1) + " / " + str(total_no_of_pages)
        )
        if (
            "transactionId" in sc1_schedule_page_dict
            and sc1_schedule_page_dict["transactionId"]
        ):
            memo_dict["transactionId_1"] = sc1_schedule_page_dict["transactionId"]

        if image_num:
            memo_dict["IMGNO"] = image_num
            image_num += 1

        # build page
        pypdftk.fill_form(memo_infile, memo_dict, memo_outfile)
        pypdftk.concat([sc1_outfile, memo_outfile], temp_memo_outfile)
        os.remove(memo_outfile)
        os.rename(temp_memo_outfile, sc1_outfile)
    if path.isfile(md5_directory + "SC/all_pages.pdf"):
        pypdftk.concat(
            [
                md5_directory + "SC/all_pages.pdf",
                md5_directory + "SC" + "/page_" + str(sc1_start_page) + ".pdf",
            ],
            md5_directory + "SC/temp_all_pages.pdf",
        )
        os.rename(
            md5_directory + "SC/temp_all_pages.pdf", md5_directory + "SC/all_pages.pdf"
        )
    else:
        os.rename(
            md5_directory + "SC/all_pages.pdf",
            md5_directory + "SC" + "/page_" + str(sc1_start_page) + ".pdf",
        )

    return image_num
