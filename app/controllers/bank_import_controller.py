import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
import io
import re

from flask import flash, g, redirect, render_template, request, url_for

from app.models import (
    add_bank_file_format,
    add_statement,
    add_bank_transaction,
    get_bank_file_format_by_id,
    get_bank_file_formats_for_group,
)
DEFAULT_DELIMITER = ","
MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024
MANAGE_FORMAT_PAGE_SIZE = 5
VALID_TRANSACTION_TYPES = {"Debit", "Credit"}
VALID_BANK_IMPORT_TABS = {"upload-tab-panel", "format-tab-panel", "manage-tab-panel"}
TRANSACTION_TYPE_MAP = {"debit": "Debit", "credit": "Credit"}
BANK_FILE_FORMAT_KEYS = "id format_name delimiter date_format data_start_row date_column name_column amount_column debit_amount_column credit_amount_column transaction_type_column".split()


def bank_import_page():
    group_code = g.current_user["group_code"]
    format_db_rows = get_bank_file_formats_for_group(group_code)
    formats = [dict(zip(BANK_FILE_FORMAT_KEYS, row)) for row in format_db_rows]

    manage_page_raw = request.args.get("manage_page", "").strip()
    manage_page = _parse_positive_int(manage_page_raw) or 1
    total_formats = len(formats)
    total_manage_pages = max(
        1,
        (total_formats + MANAGE_FORMAT_PAGE_SIZE - 1) // MANAGE_FORMAT_PAGE_SIZE,
    )

    manage_page = min(manage_page, total_manage_pages)
    start_index = (manage_page - 1) * MANAGE_FORMAT_PAGE_SIZE
    end_index = start_index + MANAGE_FORMAT_PAGE_SIZE
    manage_formats = formats[start_index:end_index]

    active_tab = request.args.get("tab", "upload-tab-panel")
    if active_tab not in VALID_BANK_IMPORT_TABS:
        active_tab = "upload-tab-panel"

    return render_template(
        "postlogin/bank_import.html",
        formats=formats,
        manage_formats=manage_formats,
        active_tab=active_tab,
        manage_page=manage_page,
        total_manage_pages=total_manage_pages,
    )


def create_bank_file_format():
    user_id = g.current_user["id"]
    group_code = g.current_user["group_code"]

    file_format_data = _read_bank_file_format_data(request.form)
    validation_error = _validate_bank_file_format_data(file_format_data)
    if validation_error:
        flash(validation_error, "error")
        return _redirect_to_bank_import_tab("format-tab-panel")

    format_id = add_bank_file_format(
        user_id,
        group_code,
        file_format_data["format_name"],
        file_format_data["delimiter"],
        file_format_data["date_format"],
        file_format_data["data_start_row"],
        file_format_data["date_column"],
        file_format_data["name_column"],
        file_format_data["amount_column"],
        file_format_data["debit_amount_column"],
        file_format_data["credit_amount_column"],
        file_format_data["transaction_type_column"],
    )

    if format_id is None:
        flash("Could not save bank file format.", "error")
    else:
        flash("Bank file format saved.", "success")

    return _redirect_to_bank_import_tab("manage-tab-panel", manage_page=1)


def upload_bank_file():
    user_id = g.current_user["id"]
    group_code = g.current_user["group_code"]

    format_id_raw = request.form.get("bank_file_format_id", "").strip()
    format_id = _parse_positive_int(format_id_raw)

    if format_id is None:
        flash("Please select a bank file format.", "error")
        return _redirect_to_bank_import_tab("upload-tab-panel")

    selected_format_row = get_bank_file_format_by_id(group_code, format_id)
    if selected_format_row is None:
        flash("Selected bank file format was not found.", "error")
        return _redirect_to_bank_import_tab("upload-tab-panel")

    uploaded_file = request.files.get("bank_csv")
    if uploaded_file is None or not uploaded_file.filename:
        flash("Please choose a CSV file.", "error")
        return _redirect_to_bank_import_tab("upload-tab-panel")

    file_bytes = uploaded_file.read()
    if not file_bytes:
        flash("The selected CSV file is empty.", "error")
        return _redirect_to_bank_import_tab("upload-tab-panel")

    if len(file_bytes) > MAX_UPLOAD_SIZE_BYTES:
        flash("CSV file is too large. Please upload a smaller file.", "error")
        return _redirect_to_bank_import_tab("upload-tab-panel")

    csv_text = file_bytes.decode("utf-8-sig", errors="replace")

    selected_format = dict(zip(BANK_FILE_FORMAT_KEYS, selected_format_row))
    statement_id = add_statement(user_id, format_id, group_code, uploaded_file.filename)
    if statement_id is None:
        flash("Could not save statement.", "error")
        return _redirect_to_bank_import_tab("upload-tab-panel")

    reader = csv.reader(io.StringIO(csv_text), delimiter=selected_format["delimiter"])
    rows_added = 0

    for row_number, row in enumerate(reader, start=1):
        if row_number < selected_format["data_start_row"]:
            continue

        parsed_transaction = _read_transaction_values_from_csv_row(row, selected_format)
        if parsed_transaction is None:
            continue

        name, transaction_date, amount_value, transaction_type = parsed_transaction
        created_bank_transaction_id = add_bank_transaction(
            statement_id,
            group_code,
            name,
            transaction_date,
            amount_value,
            transaction_type,
        )

        if created_bank_transaction_id is not None:
            rows_added += 1

    flash(f"Import finished. Added {rows_added} row(s).", "success")
    return _redirect_to_bank_import_tab("upload-tab-panel")


def _read_bank_file_format_data(form_data):
    delimiter = form_data.get("delimiter", DEFAULT_DELIMITER)
    delimiter = delimiter.strip() or DEFAULT_DELIMITER
    amount_column = form_data.get("amount_column", "").strip()
    debit_amount_column = form_data.get("debit_amount_column", "").strip()
    credit_amount_column = form_data.get("credit_amount_column", "").strip()
    transaction_type_column = form_data.get("transaction_type_column", "").strip()

    return {
        "format_name": form_data.get("format_name", "").strip(),
        "delimiter": delimiter,
        "date_format": form_data.get("date_format", "").strip(),
        "data_start_row": _parse_positive_int(form_data.get("data_start_row", "").strip()),
        "date_column": _parse_positive_int(form_data.get("date_column", "").strip()),
        "name_column": _parse_positive_int(form_data.get("name_column", "").strip()),
        "amount_column": _parse_positive_int(amount_column) if amount_column else None,
        "debit_amount_column": _parse_positive_int(debit_amount_column)
        if debit_amount_column
        else None,
        "credit_amount_column": _parse_positive_int(credit_amount_column)
        if credit_amount_column
        else None,
        "transaction_type_column": _parse_positive_int(transaction_type_column)
        if transaction_type_column
        else None,
    }


def _validate_bank_file_format_data(file_format_data):
    if (
        not file_format_data["format_name"]
        or not file_format_data["date_format"]
        or file_format_data["data_start_row"] is None
        or file_format_data["date_column"] is None
        or file_format_data["name_column"] is None
    ):
        return "Please fill in all required format fields."

    if len(file_format_data["delimiter"]) != 1:
        return "Delimiter must be one character."

    if (
        file_format_data["amount_column"] is None
        and file_format_data["debit_amount_column"] is None
        and file_format_data["credit_amount_column"] is None
    ):
        return "Please provide either an amount column, or debit/credit amount columns."

    return None


def _redirect_to_bank_import_tab(tab_name, manage_page=None):
    url_values = {"tab": tab_name}
    if manage_page is not None:
        url_values["manage_page"] = manage_page
    return redirect(url_for("main.bank_import_page", **url_values))


def _read_transaction_values_from_csv_row(row, bank_file_format):
    date_value = _get_value_from_row(row, bank_file_format["date_column"])
    name_value = _get_value_from_row(row, bank_file_format["name_column"])

    if not date_value or not name_value:
        return None

    transaction_date = _parse_date(date_value, bank_file_format["date_format"])
    if transaction_date is None:
        return None

    amount_and_type = _read_amount_and_type(row, bank_file_format)
    if amount_and_type is None:
        return None

    amount_value, transaction_type = amount_and_type
    if amount_value <= 0 or transaction_type not in VALID_TRANSACTION_TYPES:
        return None

    return name_value, transaction_date, amount_value, transaction_type


def _read_amount_and_type(row, bank_file_format):
    amount_column = bank_file_format["amount_column"]
    debit_amount_column = bank_file_format["debit_amount_column"]
    credit_amount_column = bank_file_format["credit_amount_column"]
    transaction_type_column = bank_file_format["transaction_type_column"]

    if amount_column is not None:
        raw_amount = _get_value_from_row(row, amount_column)
        amount_value = _parse_amount(raw_amount)
        if amount_value is None or amount_value == 0:
            return None

        transaction_type = ""
        if transaction_type_column is not None:
            raw_transaction_type = _get_value_from_row(row, transaction_type_column).lower()
            transaction_type = TRANSACTION_TYPE_MAP.get(raw_transaction_type, "")

        if not transaction_type:
            if amount_value < 0:
                transaction_type = "Debit"
            else:
                transaction_type = "Credit"

        return abs(amount_value), transaction_type

    debit_amount = _parse_amount(_get_value_from_row(row, debit_amount_column))
    credit_amount = _parse_amount(_get_value_from_row(row, credit_amount_column))

    if debit_amount is not None and debit_amount > 0:
        return debit_amount, "Debit"
    if credit_amount is not None and credit_amount > 0:
        return credit_amount, "Credit"

    return None


def _parse_date(raw_value, date_format):
    try:
        return datetime.strptime(raw_value.strip(), date_format).date()
    except ValueError:
        return None


def _parse_amount(raw_amount):
    if raw_amount is None:
        return None

    clean_value = raw_amount.strip()
    if not clean_value:
        return None

    if clean_value.startswith("(") and clean_value.endswith(")"):
        clean_value = "-" + clean_value[1:-1]

    clean_value = clean_value.replace(",", "")
    clean_value = re.sub(r"[^0-9.\-]", "", clean_value)

    if clean_value in {"", "-", ".", "-."}:
        return None

    try:
        return Decimal(clean_value)
    except InvalidOperation:
        return None


def _get_value_from_row(row, column_number):
    if column_number is None:
        return ""

    index = column_number - 1
    if index < 0 or index >= len(row):
        return ""

    return row[index].strip()


def _parse_positive_int(value):
    try:
        parsed_value = int(value)
    except (TypeError, ValueError):
        return None

    if parsed_value < 1:
        return None

    return parsed_value
