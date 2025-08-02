from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProdutoViewSet,
    VendaViewSet,
    CaixaViewSet,
    CurrentUserView,
    DashboardAdminAPIView,
    DashboardFuncionarioAPIView
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

router = DefaultRouter()
router.register(r'produtos', ProdutoViewSet, basename='produto')
router.register(r'vendas', VendaViewSet, basename='venda')
router.register(r'caixas', CaixaViewSet, basename='caixa')

urlpatterns = [
    path('', include(router.urls)),
    path('users/me/', CurrentUserView.as_view(), name='current-user'),
    path('dashboard/admin/', DashboardAdminAPIView.as_view(), name='dashboard-admin'),
    path('dashboard/funcionario/', DashboardFuncionarioAPIView.as_view(), name='dashboard-funcionario'),

    # ROTAS DE AUTENTICAÇÃO
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]