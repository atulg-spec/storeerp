import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from openpyxl import load_workbook

from inventory.models import Stock
from sales.models import Sales


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def normalize_header(value):
    """Normalize column names for flexible matching."""
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def parse_date(value):
    """Convert Excel dates or supported date strings to datetime."""
    if isinstance(value, datetime):
        result = value

    elif isinstance(value, date):
        result = datetime.combine(value, datetime.min.time())

    elif isinstance(value, str):
        value = value.strip()
        result = None

        formats = (
            "%d-%m-%Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%Y-%m-%d",
            "%m/%d/%Y",
        )

        for fmt in formats:
            try:
                result = datetime.strptime(value, fmt)
                break
            except ValueError:
                continue

        if result is None:
            raise ValueError(
                f"Unsupported date format: {value!r}"
            )

    else:
        raise ValueError(
            f"Missing or invalid date: {value!r}"
        )

    if timezone.is_aware(result):
        return result

    if timezone.is_aware(timezone.now()):
        return timezone.make_aware(
            result,
            timezone.get_current_timezone(),
        )

    return result


def parse_number(value, field_name):
    """Parse a numeric Excel value safely."""
    if value is None or str(value).strip() == "":
        raise ValueError(f"Missing {field_name}")

    try:
        number = Decimal(
            str(value).replace(",", "").strip()
        )
    except (InvalidOperation, ValueError):
        raise ValueError(
            f"Invalid {field_name}: {value!r}"
        )

    if not number.is_finite():
        raise ValueError(
            f"Invalid {field_name}: {value!r}"
        )

    return number


def parse_verified(value):
    """Convert common Excel values to a Boolean."""
    if isinstance(value, bool):
        return value

    return str(value or "").strip().lower() in {
        "true",
        "1",
        "yes",
        "y",
        "verified",
    }


# --------------------------------------------------
# DJANGO MANAGEMENT COMMAND
# --------------------------------------------------

class Command(BaseCommand):
    help = (
        "Import historical sales from Excel without "
        "skipping duplicate transactions."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default="sales.xlsx",
            help="Path to the Excel file.",
        )

        parser.add_argument(
            "--sheet",
            default=None,
            help="Worksheet name; defaults to the active sheet.",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate all rows without saving sales.",
        )

    # --------------------------------------------------
    # MAIN IMPORT PROCESS
    # --------------------------------------------------

    def handle(self, *args, **options):
        file_path = Path(options["file"])

        if not file_path.is_absolute():
            file_path = Path.cwd() / file_path

        if not file_path.exists():
            raise CommandError(
                f"Excel file not found: {file_path}"
            )

        if file_path.suffix.lower() not in {".xlsx", ".xlsm"}:
            raise CommandError(
                "Please provide an .xlsx or .xlsm Excel file."
            )

        try:
            workbook = load_workbook(
                file_path,
                read_only=True,
                data_only=True,
            )
        except Exception as exc:
            raise CommandError(
                f"Could not open Excel file: {exc}"
            )

        imported = 0
        errors = []
        blank_rows = 0
        total_rows = 0

        try:
            # Select worksheet
            if options["sheet"]:
                if options["sheet"] not in workbook.sheetnames:
                    raise CommandError(
                        f"Sheet not found. Available sheets: "
                        f"{', '.join(workbook.sheetnames)}"
                    )

                sheet = workbook[options["sheet"]]
            else:
                sheet = workbook.active

            rows = sheet.iter_rows(values_only=True)
            headers = next(rows, None)

            if not headers:
                raise CommandError(
                    "The worksheet is empty."
                )

            # Map normalized headers to column indexes
            columns = {}

            for index, header in enumerate(headers):
                if header is not None:
                    columns[normalize_header(header)] = index

            def find_column(*aliases, required=True):
                for alias in aliases:
                    key = normalize_header(alias)

                    if key in columns:
                        return columns[key]

                if required:
                    raise CommandError(
                        f"Missing column. Expected one of: "
                        f"{', '.join(aliases)}. "
                        f"Found: {list(columns.keys())}"
                    )

                return None

            # Excel column mapping
            date_col = find_column(
                "Date",
                "Sale Date",
                "Sold On",
                "Sold Date",
            )

            product_col = find_column(
                "Product",
                "Product Name",
                "Stock",
                "Item",
                "Item Name",
                "Name",
                "Particulars",
            )

            quantity_col = find_column(
                "Quantity Sold",
                "Quantity",
                "Qty",
                "Units Sold",
            )

            price_col = find_column(
                "Selling Price",
                "Sale Price",
                "Price",
                "Unit Selling Price",
            )

            verified_col = find_column(
                "Is Verified",
                "Verified",
                required=False,
            )

            # Amount is optional because Sales calculates
            # total_amount = quantity_sold * selling_price.
            amount_col = find_column(
                "Amount",
                "Total Amount",
                "Total",
                required=False,
            )

            if options["dry_run"]:
                self.stdout.write(
                    self.style.WARNING(
                        "DRY RUN: validating rows only; "
                        "no sales will be saved."
                    )
                )

            self.stdout.write(
                f"Reading file: {file_path}"
            )
            self.stdout.write(
                f"Worksheet: {sheet.title}"
            )
            self.stdout.write("Starting import...\n")

            # Process every data row.
            # Duplicate transactions are NOT skipped.
            for row_number, row in enumerate(rows, start=2):
                total_rows += 1

                # Blank rows cannot represent a sale.
                if not row or all(
                    value is None
                    or (
                        isinstance(value, str)
                        and not value.strip()
                    )
                    for value in row
                ):
                    blank_rows += 1
                    continue

                try:
                    # Read and validate date
                    sold_on = parse_date(row[date_col])

                    # Read product name
                    product_name = str(
                        row[product_col] or ""
                    ).strip()

                    if not product_name:
                        raise ValueError(
                            "Missing product name"
                        )

                    # Read quantity
                    quantity_decimal = parse_number(
                        row[quantity_col],
                        "quantity",
                    )

                    if (
                        quantity_decimal <= 0
                        or quantity_decimal
                        != quantity_decimal.to_integral_value()
                    ):
                        raise ValueError(
                            "Quantity must be a positive integer"
                        )

                    quantity = int(quantity_decimal)

                    # Read unit selling price
                    price = parse_number(
                        row[price_col],
                        "selling price",
                    )

                    if price < 0:
                        raise ValueError(
                            "Selling price cannot be negative"
                        )

                    # Find the corresponding inventory item
                    try:
                        stock = Stock.objects.get(
                            name__iexact=product_name
                        )
                    except Stock.DoesNotExist:
                        raise ValueError(
                            f"Stock item not found for "
                            f"{product_name!r}"
                        )
                    except Stock.MultipleObjectsReturned:
                        raise ValueError(
                            f"Multiple stock records matched "
                            f"{product_name!r}"
                        )

                    # Verification flag, if provided
                    verified = False

                    if verified_col is not None:
                        verified = parse_verified(
                            row[verified_col]
                        )

                    # Optional amount validation.
                    # The model calculates the actual total
                    # from quantity multiplied by unit price.
                    if amount_col is not None:
                        raw_amount = row[amount_col]

                        if (
                            raw_amount is not None
                            and str(raw_amount).strip() != ""
                        ):
                            amount = parse_number(
                                raw_amount,
                                "amount",
                            )

                            expected_amount = (
                                quantity_decimal * price
                            )

                            if amount != expected_amount:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"Row {row_number}: Excel "
                                        f"amount ₹{amount} differs "
                                        f"from quantity × price "
                                        f"(₹{expected_amount}). "
                                        f"Using quantity × price."
                                    )
                                )

                    # Dry run: validate without saving
                    if options["dry_run"]:
                        imported += 1

                        self.stdout.write(
                            self.style.SUCCESS(
                                f"VALID: Row {row_number} | "
                                f"{product_name} | "
                                f"{quantity} pcs | "
                                f"₹{price} | {sold_on}"
                            )
                        )
                        continue

                    # Create a new sale for EVERY valid row.
                    # There is deliberately no duplicate check.
                    with transaction.atomic():
                        sale = Sales(
                            stock=stock,
                            quantity_sold=quantity,
                            selling_price=float(price),
                            is_verified=verified,
                        )

                        sale.save()

                        # Sales.sold_on uses auto_now_add=True,
                        # so restore the historical Excel date
                        # directly in the database.
                        Sales.objects.filter(
                            pk=sale.pk
                        ).update(
                            sold_on=sold_on
                        )

                    imported += 1

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"IMPORTED: Row {row_number} | "
                            f"{product_name} | "
                            f"{quantity} pcs | "
                            f"₹{price} | {sold_on}"
                        )
                    )

                except (ValueError, TypeError, IndexError) as exc:
                    message = (
                        f"Row {row_number}: {exc}"
                    )
                    errors.append(message)

                    self.stderr.write(
                        self.style.ERROR(
                            f"ERROR: {message}"
                        )
                    )

            # --------------------------------------------------
            # FINAL REPORT
            # --------------------------------------------------

            self.stdout.write("\n" + "=" * 55)
            self.stdout.write("SALES IMPORT SUMMARY")
            self.stdout.write("=" * 55)

            self.stdout.write(
                f"Non-header rows examined: {total_rows}"
            )
            self.stdout.write(
                f"Successfully imported/validated: {imported}"
            )
            self.stdout.write(
                f"Blank rows: {blank_rows}"
            )
            self.stdout.write(
                f"Rows with errors: {len(errors)}"
            )

            if errors:
                self.stdout.write(
                    self.style.ERROR(
                        "\nSome rows need correction. "
                        "Review the ERROR messages above."
                    )
                )

            elif options["dry_run"]:
                self.stdout.write(
                    self.style.WARNING(
                        "\nDry run complete. No sales were saved. "
                        "Run without --dry-run to import."
                    )
                )

            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        "\nImport completed. All non-empty rows "
                        "were processed without duplicate skipping."
                    )
                )

        finally:
            workbook.close()