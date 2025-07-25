# api/urls.py - VERSÃO COM A ROTA DE DETALHES CORRIGIDA
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProdutoViewSet, VendaViewSet, CaixaViewSet, DashboardAdminAPIView

router = DefaultRouter()
router.register(r'produtos', ProdutoViewSet, basename='produto')
router.register(r'vendas', VendaViewSet, basename='venda')
router.register(r'caixas', CaixaViewSet, basename='caixa')

# A lista de URLs padrão do router
urlpatterns = router.urls

# --- ADIÇÃO PRECISA AQUI ---
# Adicionamos a rota específica para os detalhes do caixa, que o router não cria sozinho.
# O <int:pk> significa que ele espera um número (o ID do caixa) no meio do endereço.
urlpatterns += [
    path('dashboard/admin/', DashboardAdminAPIView.as_view(), name='dashboard-admin'),
    path('caixas/<int:pk>/details/', CaixaViewSet.as_view({'get': 'get_details'}), name='caixa-details'),
]