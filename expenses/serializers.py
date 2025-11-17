from rest_framework import serializers
from expenses.models import Expense


class ExpenseSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Expense."""

    class Meta:
        model = Expense
        fields = ['id', 'user', 'amount', 'category', 'created_at']
        read_only_fields = ['user', 'created_at']
