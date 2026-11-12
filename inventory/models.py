from django.db import models
from accounts.models import CustomUser
from django.db.models import Max


def generate_stock_id():
    last_id = Stock.objects.aggregate(
        max_id=Max('id')
    )['max_id']

    next_id = 1000 if last_id is None else last_id + 1

    while '7' in str(next_id):
        next_id += 1

    return next_id


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Stock(models.Model):
    id = models.PositiveIntegerField(
        unique=True,
        editable=False,
        default=generate_stock_id,
        primary_key=True
    )
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='user')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='stocks')
    name = models.CharField(max_length=100, unique=True, default="")
    cost_price = models.FloatField(default=0)
    selling_price = models.FloatField(default=0, verbose_name="Minimum Selling Price")
    quantity = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)  # ✅ FIXED
    description = models.TextField(blank=True, null=True)
    short_description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.category.name}"

    class Meta:
        ordering = ['-last_updated']

    def save_model(self, request, obj, form, change):
        if not change or not obj.user:   # If creating new object
            obj.user = request.user
        super().save_model(request, obj, form, change)
