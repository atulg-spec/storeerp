import re
from decimal import Decimal, InvalidOperation
from datetime import datetime, date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from openpyxl import load_workbook

from expenses.models import expenses


class Command(BaseCommand):
    help = "Import expenses from an Excel (.xlsx) file"

    def add_arguments(self, parser):
        parser.add_argument(
            "file",
            type=str,
            help="Path to the Excel file"
        )

        parser.add_argument(
            "--skip-header",
            action="store_true",
            help="Skip the first row of the Excel file"
        )

    def clean_amount(self, value):
        """
        Convert Excel amount values into Decimal.

        Supported examples:
            ₹4,000.00
            ₹ 4,000.00
            4000
            4,000
            4000.50
        """

        if value is None:
            return None

        # Excel may already give us a number
        if isinstance(value, Decimal):
            return value

        if isinstance(value, (int, float)):
            return Decimal(str(value))

        value = str(value).strip()

        if not value:
            return None

        # Remove currency symbol and commas
        value = value.replace("₹", "")
        value = value.replace(",", "")
        value = value.strip()

        # Keep only digits, decimal point and minus sign
        value = re.sub(r"[^\d.-]", "", value)

        if not value:
            return None

        try:
            return Decimal(value)
        except InvalidOperation:
            raise ValueError(
                f"Invalid amount: {value}"
            )

    def clean_date(self, value):
        """
        Convert Excel date values into Python date.

        Supported examples:
            22/June/2026
            22/June/26
            22 June 2026
            22/06/2026
            22-06-2026

        Also supports native Excel date/datetime values.
        """

        if value is None:
            return None

        # Native Excel datetime
        if isinstance(value, datetime):
            return value.date()

        # Native Python date
        if isinstance(value, date):
            return value

        value = str(value).strip()

        if not value:
            return None

        date_formats = [
            "%d/%B/%Y",
            "%d/%b/%Y",
            "%d/%m/%Y",
            "%d/%y/%m",
            "%d-%B-%Y",
            "%d-%b-%Y",
            "%d-%m-%Y",
            "%d %B %Y",
            "%d %b %Y",
            "%d/%B/%y",
            "%d/%b/%y",
            "%d/%m/%y",
            "%d-%B-%y",
            "%d-%b-%y",
            "%d-%m-%y",
            "%d %B %y",
            "%d %b %y",
        ]

        for date_format in date_formats:
            try:
                return datetime.strptime(
                    value,
                    date_format
                ).date()
            except ValueError:
                continue

        raise ValueError(
            f"Invalid date format: {value}"
        )

    def handle(self, *args, **options):

        file_path = options["file"]
        skip_header = options["skip_header"]

        # ---------------------------------------------------------
        # OPEN EXCEL FILE
        # ---------------------------------------------------------

        try:
            workbook = load_workbook(
                filename=file_path,
                data_only=True
            )
        except Exception as e:
            raise CommandError(
                f"Could not open Excel file: {e}"
            )

        worksheet = workbook.active

        self.stdout.write(
            self.style.NOTICE(
                f"\nReading: {file_path}"
            )
        )

        # ---------------------------------------------------------
        # READ AND VALIDATE DATA
        # ---------------------------------------------------------

        valid_expenses = []
        skipped = 0
        errors = []

        for row_number, row in enumerate(
            worksheet.iter_rows(values_only=True),
            start=1
        ):

            # Skip header
            if row_number == 1 and skip_header:
                continue

            # We need:
            # Column A = Date
            # Column B = Transaction For
            # Column C = Amount

            if len(row) < 3:
                skipped += 1
                errors.append(
                    f"Row {row_number}: "
                    f"Less than 3 columns"
                )
                continue

            date_value = row[0]
            transaction_value = row[1]
            amount_value = row[2]

            # Ignore completely empty rows
            if (
                not date_value
                and not transaction_value
                and not amount_value
            ):
                skipped += 1
                continue

            try:

                # -------------------------
                # DATE
                # -------------------------

                expense_date = self.clean_date(
                    date_value
                )

                if expense_date is None:
                    raise ValueError(
                        "Date is empty"
                    )

                # -------------------------
                # TRANSACTION FOR
                # -------------------------

                transaction_for = str(
                    transaction_value or ""
                ).strip()

                if not transaction_for:
                    raise ValueError(
                        "Transaction For is empty"
                    )

                # Django field limit
                if len(transaction_for) > 100:
                    transaction_for = (
                        transaction_for[:100]
                    )

                # -------------------------
                # AMOUNT
                # -------------------------

                amount = self.clean_amount(
                    amount_value
                )

                if amount is None:
                    raise ValueError(
                        "Amount is empty"
                    )

                if amount < 0:
                    raise ValueError(
                        "Amount cannot be negative"
                    )

                # -------------------------
                # PREPARE OBJECT
                # -------------------------

                expense = expenses(
                    date=expense_date,
                    transaction_for=transaction_for,
                    amount=amount,
                    remarks=None,
                )

                valid_expenses.append(
                    expense
                )

            except Exception as e:

                skipped += 1

                errors.append(
                    f"Row {row_number}: {e}"
                )

        # ---------------------------------------------------------
        # NOTHING TO IMPORT
        # ---------------------------------------------------------

        if not valid_expenses:

            self.stdout.write(
                self.style.WARNING(
                    "\nNo valid expenses found."
                )
            )

            if errors:
                self.stdout.write(
                    self.style.ERROR(
                        "\nErrors:"
                    )
                )

                for error in errors:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  {error}"
                        )
                    )

            return

        # ---------------------------------------------------------
        # SHOW IMPORT SUMMARY
        # ---------------------------------------------------------

        self.stdout.write(
            self.style.NOTICE(
                f"\nValid expenses found: "
                f"{len(valid_expenses)}"
            )
        )

        self.stdout.write(
            self.style.NOTICE(
                f"Rows skipped: {skipped}"
            )
        )

        self.stdout.write(
            self.style.NOTICE(
                "\nImporting expenses..."
            )
        )

        # ---------------------------------------------------------
        # SAVE USING MODEL.save()
        # ---------------------------------------------------------
        #
        # IMPORTANT:
        #
        # We deliberately DO NOT use bulk_create().
        #
        # bulk_create() bypasses Model.save().
        #
        # Your expenses.save() contains:
        #
        #     credit("Expense", self.amount)
        #
        # Therefore every expense must be saved individually.
        #
        # ---------------------------------------------------------

        imported = 0

        try:

            with transaction.atomic():

                for expense in valid_expenses:

                    expense.save()

                    imported += 1

        except Exception as e:

            raise CommandError(
                f"\nDatabase import failed. "
                f"All changes have been rolled back.\n"
                f"Error: {e}"
            )

        # ---------------------------------------------------------
        # SUCCESS
        # ---------------------------------------------------------

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully imported "
                f"{imported} expenses."
            )
        )

        # ---------------------------------------------------------
        # DISPLAY ERRORS
        # ---------------------------------------------------------

        if errors:

            self.stdout.write(
                self.style.WARNING(
                    "\nSome rows were skipped:"
                )
            )

            for error in errors:

                self.stdout.write(
                    self.style.ERROR(
                        f"  {error}"
                    )
                )