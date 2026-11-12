from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Stock


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    list_display_links = ('name',)
    ordering = ('name',)

    fieldsets = (
        ("Category Details", {
            "fields": ("name",)
        }),
    )


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'quantity', 'selling_price', 'category_name', 'user', 'last_updated')
    list_filter = ('category__name', 'user', 'last_updated', 'last_updated')
    search_fields = ('category__name','name', 'id')
    readonly_fields = ('cost_price', 'selling_price', 'quantity', 'user','last_updated',)
    date_hierarchy = 'last_updated'
    ordering = ('-last_updated',)

    def get_fieldsets(self, request, obj=None):
        fields = ["category", "name"]

        if request.user.is_superuser:
            fields.append("cost_price")

        fields.extend(["selling_price", "quantity", "user"])

        return (
            ("Stock Details", {
                "fields": tuple(fields)
            }),
        )

    def save_model(self, request, obj, form, change):
        if not change or not obj.user:  # When creating a new stock entry
            obj.user = request.user
        super().save_model(request, obj, form, change)

    def category_name(self, obj):
        return obj.category.name

    category_name.short_description = "Category"



# Optional: Customize Admin Site Branding
admin.site.site_header = "ERP"
admin.site.site_title = "ERP Dashboard"
admin.site.index_title = "Welcome to the ERP Admin Panel"
