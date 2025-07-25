# api/admin.py
from django.contrib import admin
from .models import Produto, Venda, ItemVenda, Caixa

admin.site.register(Produto)
admin.site.register(Venda)
admin.site.register(ItemVenda)
admin.site.register(Caixa)