# api/models.py
from django.db import models
from django.contrib.auth.models import User

class Produto(models.Model):
    nome = models.CharField(max_length=100)
    categoria = models.CharField(max_length=50)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    estoque = models.IntegerField()
    foto = models.TextField(blank=True, null=True)
    def __str__(self): return self.nome

class Venda(models.Model):
    METODO_PAGAMENTO_CHOICES = [
        ('Dinheiro', 'Dinheiro'),
        ('PIX', 'PIX'),
        ('Cartao', 'Cartão'),
    ]
    BANDEIRA_CARTAO_CHOICES = [
        ('ELO', 'Elo'),
        ('VISA', 'Visa'),
        ('MASTERCARD', 'Mastercard'),
        ('AMEX', 'Amex'), # Corrigido para Amex
        ('OUTRO', 'Outro'),
    ]

    vendedor = models.ForeignKey(User, on_delete=models.PROTECT, null=True)
    data_venda = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    metodo_pagamento = models.CharField(max_length=20, choices=METODO_PAGAMENTO_CHOICES)
    bandeira_cartao = models.CharField(max_length=20, choices=BANDEIRA_CARTAO_CHOICES, null=True, blank=True)
    nsu = models.CharField(max_length=100, null=True, blank=True)
    codigo_autorizacao = models.CharField(max_length=100, null=True, blank=True)
    foto_notinha = models.TextField(null=True, blank=True)  # Campo para a foto da notinha (Base64)
    observacoes = models.TextField(null=True, blank=True)

def __str__(self):
    return f"Venda #{self.id}"

class ItemVenda(models.Model):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField()
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    def __str__(self): return f"{self.quantidade}x {self.produto.nome}"

# Altere APENAS a classe Caixa em api/models.py

class Caixa(models.Model):
    STATUS_CHOICES = [('ABERTO', 'Aberto'), ('FECHADO', 'Fechado')]
    responsavel = models.CharField(max_length=100)
    data_abertura = models.DateTimeField(auto_now_add=True)
    data_fechamento = models.DateTimeField(null=True, blank=True)
    valor_abertura = models.DecimalField(max_digits=10, decimal_places=2)

    # --- ADIÇÃO DOS NOVOS CAMPOS PARA O FECHAMENTO ---
    dinheiro_apurado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    credito_apurado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    debito_apurado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pix_apurado = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    valor_fechamento_apurado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ABERTO')

    def __str__(self): return f"Caixa de {self.responsavel} - {self.data_abertura.strftime('%d/%m/%Y')}"