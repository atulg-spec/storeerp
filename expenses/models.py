from django.db import models
from django.utils import timezone
from django.db import transaction

# Create your models here.
class expenses(models.Model):
    date = models.DateField(default=timezone.now)
    transaction_for = models.CharField(max_length=100, default="")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    remarks = models.TextField(null=True,blank=True)

    def __str__(self):
        return f"{self.transaction_for} - {self.amount}"

    class Meta:
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        with transaction.atomic():
            super().save(*args, **kwargs)

            if is_new:
                from accounting.utility.calculations import credit
                credit("Expense", self.amount)