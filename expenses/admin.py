from django.contrib import admin
from expenses.models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'category', 'created_at')
    list_filter = ('category', 'created_at', 'user')
    search_fields = ('category', 'user__username')
    ordering = ('-created_at',)
