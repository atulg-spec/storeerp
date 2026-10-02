from django.contrib import admin
from .models import Bills, Extortion
from sales.models import Sales
from django.utils import timezone
from django.db.models import Sum
from django.utils.html import format_html
from django.contrib import messages

@admin.register(Bills)
class BillsAdmin(admin.ModelAdmin):
    list_display = ('date', 'file_link')
    list_filter = ('date',)
    
    @admin.display(description="Bill File")
    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">View File</a>', obj.file.url)
        return "-"


@admin.register(Extortion)
class ExtortionAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "transaction_for",
        "formatted_amount",
        "remarks",
    )

    list_display_links = (
        "transaction_for",
    )

    list_filter = (
        "date",
    )

    search_fields = (
        "transaction_for",
        "remarks",
    )

    date_hierarchy = "date"

    ordering = (
        "-date",
        "-id",
    )

    list_per_page = 25

    @admin.display(
        description="Amount",
        ordering="amount",
    )
    def formatted_amount(self, obj):
        amount = f"₹{obj.amount:,.2f}"

        return format_html(
            '<span style="color: #16a34a; font-weight: 700;">{}</span>',
            amount,
        )