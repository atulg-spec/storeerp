from django.contrib import admin
from django.utils.html import format_html
from .models import expenses


@admin.register(expenses)
class ExpensesAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "transaction_for",
        "amount_display",
        "remarks",
    )

    list_filter = (
        "date",
    )

    search_fields = (
        "transaction_for",
        "remarks",
    )

    ordering = (
        "-date",
        "-id",
    )

    date_hierarchy = "date"

    list_per_page = 25

    @admin.display(description="Amount", ordering="amount")
    def amount_display(self, obj):
        return format_html(
            '<span style="color: #dc2626; font-weight: 700;">− ₹{}</span>',
            obj.amount,
        )

    fieldsets = (
        (
            "Expense Details",
            {
                "fields": (
                    "date",
                    "transaction_for",
                    "amount",
                    "remarks",
                )
            },
        ),
    )