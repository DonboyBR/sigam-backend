from django.db import models
from django.contrib.auth.models import User


class Produto(models.Model):
    nome = models.CharField(max_length=100)
    categoria = models.CharField(max_length=50)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    estoque = models.IntegerField()
    foto = models.TextField(blank=True, null=True)

    def __str__(self): return self.nome


class Caixa(models.Model):
    STATUS_CHOICES = [('ABERTO', 'Aberto'), ('FECHADO', 'Fechado')]
    responsavel = models.ForeignKey(User, on_delete=models.PROTECT, related_name='caixas_operados')
    data_abertura = models.DateTimeField(auto_now_add=True)
    data_fechamento = models.DateTimeField(null=True, blank=True)
    valor_abertura = models.DecimalField(max_digits=10, decimal_places=2)
    dinheiro_apurado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    credito_apurado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    debito_apurado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pix_apurado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valor_fechamento_apurado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valor_fechamento_sistema = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    dinheiro_sistema_ajustado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    credito_sistema_ajustado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    debito_sistema_ajustado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    pix_sistema_ajustado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ABERTO')
    anexo_filipeta = models.ImageField(upload_to='filipetas/', blank=True, null=True)

    def __str__(self):
        return f"Caixa de {self.responsavel.username} - {self.data_abertura.strftime('%d/%m/%Y')}"


class Venda(models.Model):
    METODO_PAGAMENTO_CHOICES = [('Dinheiro', 'Dinheiro'), ('PIX', 'PIX'), ('Cartao', 'Cartão'), ]
    TIPO_CARTAO_CHOICES = [('Debito', 'Débito'), ('Credito', 'Crédito'), ]
    BANDEIRA_CARTAO_CHOICES = [('ELO', 'Elo'), ('VISA', 'Visa'), ('MASTERCARD', 'Mastercard'), ('AMEX', 'Amex'),
                               ('OUTRO', 'Outro'), ]
    caixa = models.ForeignKey(Caixa, on_delete=models.SET_NULL, null=True, blank=True, related_name='vendas')
    vendedor = models.ForeignKey(User, on_delete=models.PROTECT, null=True)
    data_venda = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pagamento = models.CharField(max_length=20, choices=METODO_PAGAMENTO_CHOICES)
    tipo_cartao = models.CharField(max_length=10, choices=TIPO_CARTAO_CHOICES, null=True, blank=True)
    bandeira_cartao = models.CharField(max_length=20, choices=BANDEIRA_CARTAO_CHOICES, null=True, blank=True)
    nsu = models.CharField(max_length=100, null=True, blank=True)
    codigo_autorizacao = models.CharField(max_length=100, null=True, blank=True)
    foto_notinha = models.ImageField(upload_to='notinhas/', blank=True, null=True)
    observacoes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Venda #{self.id}"


class ItemVenda(models.Model):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField()
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self): return f"{self.quantidade}x {self.produto.nome}"

class Configuracoes(models.Model):
    id_fixo = models.IntegerField(primary_key=True, default=1, editable=False)
    unidade = models.CharField(max_length=100, default="Unidade Centro")
    cnpj = models.CharField(max_length=20, default="12.345.678/0001-90")
    endereco = models.CharField(max_length=255, default="Rua das Flores, 123")
    telefone = models.CharField(max_length=20, default="(11) 99999-9999")
    email = models.EmailField(default="contato@skyfit.com")
    gympass = models.CharField(max_length=100, default="senha123", verbose_name="Senha Gympass")
    radioSenha = models.CharField(max_length=100, default="senha456", verbose_name="Senha Rádio")
    instagram = models.URLField(default="https://instagram.com/skyfit")

    def __str__(self):
        return f"Configurações da Empresa ({self.unidade})"

    class Meta:
        verbose_name_plural = "Configurações"
