from django.contrib.auth.models import User
from django.db import models


class Expense(models.Model):
    """"Модель для отслеживания расходов пользователя."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='expenses'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category}: {self.amount}"
