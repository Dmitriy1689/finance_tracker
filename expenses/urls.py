from expenses.views import ExpenseViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'expenses', ExpenseViewSet, basename='expense')

urlpatterns = list(router.urls)
