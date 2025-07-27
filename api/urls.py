from django.urls import path, include
from rest_framework.routers import DefaultRouter
# Agora a importação vai funcionar pois a classe existe no views.py
from .views import ProdutoViewSet, VendaViewSet, CaixaViewSet, CurrentUserView

router = DefaultRouter()
router.register(r'produtos', ProdutoViewSet, basename='produto')
router.register(r'vendas', VendaViewSet, basename='venda')
router.register(r'caixas', CaixaViewSet, basename='caixa')

urlpatterns = [
    path('', include(router.urls)),
    # --- PEÇA QUE FALTAVA ---
    path('users/me/', CurrentUserView.as_view(), name='current-user'),
]