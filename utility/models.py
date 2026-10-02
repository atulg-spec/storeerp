from django.db import models
from django.utils import timezone

class Bills(models.Model):
    file = models.FileField(upload_to='bills/')
    date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"Bill - {self.date}"

    class Meta:
        verbose_name = "Bill"
        verbose_name_plural = "Bills"


class Extortion(models.Model):
    date = models.DateField(default=timezone.now)
    transaction_for = models.CharField(max_length=100, default="")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    remarks = models.TextField(null=True,blank=True)

    def __str__(self):
        return f"Cash received - {self.amount} for {self.transaction_for} at {self.date}"

    class Meta:
        verbose_name = "Extortion"
        verbose_name_plural = "Extortion Rent"

    def save(self, *args, **kwargs):
        if not self.pk:
            from accounting.utility.calculations import debit
            debit('Extortion Rent', self.amount)
            super().save(*args, **kwargs)