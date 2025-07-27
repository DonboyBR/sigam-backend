# api/urls.py - VERSÃO COM IMPORT CORRIGIDO
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProdutoViewSet, VendaViewSet, CaixaViewSet,
    DashboardAdminAPIView, DashboardFuncionarioAPIView
)

router = DefaultRouter()
router.register(r'produtos', ProdutoViewSet, basename='produto')
router.register(r'vendas', VendaViewSet, basename='venda')
router.register(r'caixas', CaixaViewSet, basename='caixa')

# A lista de URLs padrão do router
urlpatterns = router.urls

# Adicionando as rotas customizadas
urlpatterns += [
    path('dashboard/admin/', DashboardAdminAPIView.as_view(), name='dashboard-admin'),
    path('caixas/<int:pk>/details/', CaixaViewSet.as_view({'get': 'get_details'}), name='caixa-details'),
    path('dashboard/funcionario/', DashboardFuncionarioAPIView.as_view(), name='dashboard-funcionario'),
]