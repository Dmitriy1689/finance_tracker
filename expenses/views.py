from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from expenses.models import Expense
from expenses.serializers import ExpenseSerializer


class ExpenseViewSet(viewsets.ModelViewSet):
    """ViewSet для управления расходами пользователя."""

    permission_classes = [IsAuthenticated]
    serializer_class = ExpenseSerializer

    def get_queryset(self):
        """Фильтрация расходов по текущему пользователю."""
        return Expense.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """
        Автоматическое назначение текущего пользователя при создании расхода.
        """
        serializer.save(user=self.request.user)
