from django.db import models
from django.utils import timezone


class CashFlow(models.Model):
    TRANSACTION_TYPE = (
        ("Debit", "Debit"),
        ("Credit", "Credit"),
    )

    date = models.DateField(default=timezone.now)
    transaction_for = models.CharField(max_length=100, default="")
    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPE
    )
    remarks = models.TextField(null=True,blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.transaction_type} - ₹{self.amount} - {self.transaction_for}"

    def save(self, *args, **kwargs):
        if not self.pk:
            cash = Cash.objects.all().first()
            if self.transaction_type == "Debit":
                cash.amount = cash.amount + self.amount
            else:
                cash.amount = cash.amount - self.amount
            cash.save()
            super().save(*args, **kwargs)



class Cash(models.Model):
    date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cash"
        verbose_name_plural = "Cash"

    def __str__(self):
        return f"₹{self.amount}"