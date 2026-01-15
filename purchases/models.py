from django.db import models
from django.utils import timezone
from inventory.models import Stock

class Purchase(models.Model):
    stock_item = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='purchases')
    purchase_date = models.DateField(default=timezone.now)

    quantity_purchased = models.PositiveIntegerField()
    cost_price_per_unit = models.FloatField(help_text="Cost per unit at purchase time")
    selling_price = models.FloatField(blank=True, null=True, editable=False, verbose_name="Minimum Selling Price")

    total_cost = models.FloatField(editable=False)
    is_received = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-purchase_date']
        verbose_name = "Add Purchase"
        verbose_name_plural = "Add Purchases"

    def __str__(self):
        return f"{self.stock_item.category.name} - {self.quantity_purchased} pcs"

    def save(self, *args, **kwargs):
        # Only calculate total_cost, do NOT update stock here
        self.total_cost = self.quantity_purchased * self.cost_price_per_unit
        self.selling_price = round(self.cost_price_per_unit / 0.8, 2)
        super().save(*args, **kwargs)
