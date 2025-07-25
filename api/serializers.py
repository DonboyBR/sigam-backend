# api/serializers.py - VERSÃO COM INDENTAÇÃO CORRIGIDA
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

        # Usando a lógica que já tínhamos para pegar o vendedor logado (ou o admin como fallback)
        vendedor = self.context.get('request').user if self.context.get('request') and self.context.get(
            'request').user.is_authenticated else User.objects.filter(is_superuser=True).first()

        total_venda = sum(item['quantidade'] * item['preco_unitario'] for item in itens_data)

        # Cria a Venda principal com todos os novos campos
        venda = Venda.objects.create(vendedor=vendedor, total=total_venda, **validated_data)

        # Cria cada Item de Venda e dá baixa no estoque
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
    class Meta:
        model = Caixa
        # --- AJUSTE AQUI ---
        # Adicionamos os novos campos de valores apurados
        fields = [
            'id', 'responsavel', 'data_abertura', 'data_fechamento',
            'valor_abertura', 'valor_fechamento_apurado', 'status',
            'dinheiro_apurado', 'credito_apurado', 'debito_apurado', 'pix_apurado'
        ]

class CaixaAberturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Caixa
        fields = ['responsavel', 'valor_abertura']