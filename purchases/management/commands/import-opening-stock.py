from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import CustomUser
from inventory.models import Stock, Category

# Change "purchases.models" if Purchase belongs to another app.
from purchases.models import Purchase

from openpyxl import load_workbook


class Command(BaseCommand):
    help = "Import opening stock and create pending purchase records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-id",
            type=int,
            required=True,
            help="ID of the user who owns these stock items.",
        )
        parser.add_argument(
            "--file",
            type=str,
            default="Opening Stock.xlsx",
            help="Path to the Excel file.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        file_path = Path(options["file"])

        if not file_path.is_absolute():
            file_path = Path.cwd() / file_path

        if not file_path.exists():
            raise CommandError(
                f"Excel file not found: {file_path}"
            )

        try:
            user = CustomUser.objects.get(
                pk=options["user_id"]
            )
        except CustomUser.DoesNotExist:
            raise CommandError("The specified user does not exist.")

        try:
            category = Category.objects.get(name="Men's Wear")
        except Category.DoesNotExist:
            raise CommandError(
                "Category 'Men's Wear' does not exist."
            )

        workbook = load_workbook(
            file_path,
            read_only=True,
            data_only=True,
        )
        worksheet = workbook.active

        # Read and normalize the Excel header row.
        headers = [
            str(cell).strip().lower()
            if cell is not None else ""
            for cell in next(worksheet.iter_rows(
                min_row=1,
                max_row=1,
                values_only=True,
            ))
        ]

        required_headers = {
            "name": "name",
            "cost price": "cost_price",
            "opening stock quantity": "quantity",
        }

        missing = [
            header for header in required_headers
            if header not in headers
        ]

        if missing:
            workbook.close()
            raise CommandError(
                f"Missing Excel columns: {', '.join(missing)}"
            )

        columns = {
            field: headers.index(header)
            for header, field in required_headers.items()
        }

        stocks_created = 0
        purchases_created = 0
        skipped = 0

        try:
            for row_number, row in enumerate(
                worksheet.iter_rows(
                    min_row=2,
                    values_only=True,
                ),
                start=2,
            ):
                name = row[columns["name"]]

                if name is None or not str(name).strip():
                    continue

                name = str(name).strip()

                try:
                    cost_price = float(
                        row[columns["cost_price"]]
                    )
                    quantity = int(
                        row[columns["quantity"]]
                    )
                except (TypeError, ValueError):
                    raise CommandError(
                        f"Invalid cost or quantity at Excel "
                        f"row {row_number}: {name}"
                    )

                if cost_price < 0 or quantity < 0:
                    raise CommandError(
                        f"Negative cost or quantity at row "
                        f"{row_number}: {name}"
                    )

                # Stock.name is globally unique in your model.
                stock, stock_created = Stock.objects.get_or_create(
                    name=name,
                    defaults={
                        "user": user,
                        "category": category,
                    },
                )

                if stock_created:
                    stocks_created += 1
                elif stock.category_id != category.id:
                    raise CommandError(
                        f"'{name}' already exists under a "
                        f"different category."
                    )

                # Do not create duplicate opening purchases
                # when this command is run again.
                purchase_exists = Purchase.objects.filter(
                    stock_item=stock,
                    quantity_purchased=quantity,
                    cost_price_per_unit=cost_price,
                    is_received=False,
                ).exists()

                if purchase_exists:
                    skipped += 1
                    continue

                Purchase.objects.create(
                    stock_item=stock,
                    quantity_purchased=quantity,
                    cost_price_per_unit=cost_price,
                    is_received=False,
                )

                purchases_created += 1

        finally:
            workbook.close()

        self.stdout.write(
            self.style.SUCCESS(
                "\nOpening stock import completed!\n"
                f"Stock items created: {stocks_created}\n"
                f"Pending purchases created: {purchases_created}\n"
                f"Purchases skipped: {skipped}\n"
                "All newly created purchases have "
                "is_received=False."
            )
        )
