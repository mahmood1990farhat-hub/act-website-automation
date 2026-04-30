from django.db import models


class BankDetails(models.Model):
    bank_account_number = models.CharField(max_length=20)
    sort_code = models.CharField(max_length=10)
    registered_address = models.TextField()


