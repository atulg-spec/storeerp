def debit(transaction_for, amount, remarks = ""):
    from accounting.models import CashFlow
    if amount <= 0:
        return
    CashFlow.objects.create(
        transaction_for = transaction_for,
        transaction_type = 'Debit',
        amount = amount
        )

def credit(transaction_for, amount, remarks = ""):
    from accounting.models import CashFlow
    if amount <= 0:
        return
    CashFlow.objects.create(
        transaction_for = transaction_for,
        transaction_type = 'Credit',
        amount = amount,
        remarks = remarks
        )


