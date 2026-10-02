from django.contrib import admin
from django.utils.html import format_html

from .models import CashFlow, Cash


@admin.register(CashFlow)
class CashFlowAdmin(admin.ModelAdmin):

    list_display = (
        "date",
        "transaction_for",
        "transaction_type_badge",
        "formatted_amount",
    )

    list_display_links = (
        "transaction_for",
    )

    list_filter = (
        "transaction_type",
        "date",
    )

    search_fields = (
        "transaction_for",
    )

    date_hierarchy = "date"

    ordering = (
        "-date",
        "-id",
    )

    fieldsets = (
        (
            "Transaction Details",
            {
                "fields": (
                    "date",
                    "transaction_for",
                    "transaction_type",
                    "amount",
                    "remarks"
                )
            },
        ),
    )

    @admin.display(description="Type")
    def transaction_type_badge(self, obj):
        if obj.transaction_type == "Debit":
            return format_html(
                '<span style="'
                'background:#dcfce7;'
                'color:#15803d;'
                'padding:5px 11px;'
                'border-radius:20px;'
                'font-weight:600;'
                'font-size:12px;'
                '">'
                '↑ Debit'
                '</span>'
            )

        return format_html(
            '<span style="'
            'background:#fee2e2;'
            'color:#b91c1c;'
            'padding:5px 11px;'
            'border-radius:20px;'
            'font-weight:600;'
            'font-size:12px;'
            '">'
            '↓ Credit'
            '</span>'
        )


    @admin.display(description="Amount", ordering="amount")
    def formatted_amount(self, obj):
        if obj.transaction_type == "Debit":
            return format_html(
                '<strong style="color:#16a34a;">+ ₹{}</strong>',
                f"{obj.amount:,.2f}",
            )

        return format_html(
            '<strong style="color:#dc2626;">− ₹{}</strong>',
            f"{obj.amount:,.2f}",
        )

    def has_change_permission(self, request, obj=None):
        # Allow opening/viewing the record,
        # but don't allow saving changes.
        return False



@admin.register(Cash)
class CashAdmin(admin.ModelAdmin):

    list_display = (
        "cash_balance",
        "date",
        "last_updated",
    )

    list_display_links = ("cash_balance",)

    readonly_fields = (
        "updated_at",
        "cash_preview",
    )

    fields = (
        "date",
        "amount",
        "cash_preview",
        "updated_at",
    )

    ordering = ("-updated_at",)

    @admin.display(description="Cash Balance")
    def cash_balance(self, obj):
        amount = f"{obj.amount:,.2f}"

        return format_html(
            '<strong style="color:#16a34a; font-size:16px;">₹{}</strong>',
            amount
        )

    @admin.display(description="Last Updated")
    def last_updated(self, obj):
        return obj.updated_at.strftime("%d %b %Y, %I:%M %p")

    @admin.display(description="Current Cash")
    def cash_preview(self, obj):
        amount = f"{obj.amount}"

        return format_html(
            '''
            <div style="
                background:#f0fdf4;
                border:1px solid #bbf7d0;
                border-radius:10px;
                padding:14px 18px;
                margin:5px 0 10px;
            ">
                <div style="
                    color:#166534;
                    font-size:12px;
                    font-weight:600;
                    text-transform:uppercase;
                    letter-spacing:0.5px;
                ">
                    Current Cash Balance
                </div>

                <div style="
                    color:#15803d;
                    font-size:24px;
                    font-weight:700;
                    margin-top:4px;
                ">
                    ₹{}
                </div>
            </div>
            ''',
            amount
        )

    def has_add_permission(self, request):
        # Only one Cash record is allowed.
        return not Cash.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Don't allow the cash balance to be deleted.
        return False