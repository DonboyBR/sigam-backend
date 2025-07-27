from rest_framework import serializers
from .models import Produto, Venda, ItemVenda, Caixa
from django.contrib.auth.models import User

class ProdutoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Produto
        fields = '__all__'

class ItemVendaSerializer(serializers.ModelSerializer):
    produto_id = serializers.IntegerField(write_only=True)
    class Meta:
        model = ItemVenda
        fields = ['produto_id', 'quantidade', 'preco_unitario']

class VendaSerializer(serializers.ModelSerializer):
    itens = ItemVendaSerializer(many=True)
    class Meta:
        model = Venda
        fields = [
            'id', 'vendedor', 'data_venda', 'total',
            'metodo_pagamento', 'bandeira_cartao', 'nsu',
            'codigo_autorizacao', 'foto_notinha', 'observacoes',
            'itens'
        ]
        read_only_fields = ['id', 'vendedor', 'data_venda', 'total']

    def create(self, validated_data):
        itens_data = validated_data.pop('itens')
        vendedor = self.context['request'].user
        total_venda = sum(item['quantidade'] * item['preco_unitario'] for item in itens_data)
        venda = Venda.objects.create(vendedor=vendedor, total=total_venda, **validated_data)
        for item_data in itens_data:
            produto = Produto.objects.get(id=item_data['produto_id'])
            ItemVenda.objects.create(
                venda=venda,
                produto=produto,
                quantidade=item_data['quantidade'],
                preco_unitario=item_data['preco_unitario']
            )
            produto.estoque -= item_data['quantidade']
            produto.save()
        return venda

class CaixaSerializer(serializers.ModelSerializer):
    responsavel = serializers.CharField(source='responsavel.username', read_only=True)
    class Meta:
        model = Caixa
        fields = [
            'id', 'responsavel', 'data_abertura', 'data_fechamento',
            'valor_abertura', 'valor_fechamento_apurado', 'status',
            'dinheiro_apurado', 'credito_apurado', 'debito_apurado', 'pix_apurado'
        ]

class CaixaAberturaSerializer(serializers.ModelSerializer):
    responsavel = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Caixa
        fields = ['id', 'valor_abertura', 'responsavel', 'data_abertura', 'status']
        read_only_fields = ['responsavel', 'data_abertura', 'status', 'id']

# --- PEÇAS QUE FALTAVAM ---
class CaixaHistorySerializer(serializers.ModelSerializer):
    responsavel_nome = serializers.CharField(source='responsavel.username', read_only=True)
    class Meta:
        model = Caixa
        fields = [
            'id', 'responsavel_nome', 'data_abertura', 'data_fechamento',
            'valor_abertura', 'valor_fechamento_sistema',
        ]

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']