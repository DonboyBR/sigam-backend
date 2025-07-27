from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Sum, Count, DecimalField, IntegerField
from django.db.models.functions import Coalesce
from rest_framework.views import APIView
from django.contrib.auth.models import User
from .models import Produto, Venda, ItemVenda, Caixa
from .serializers import ProdutoSerializer, VendaSerializer, CaixaSerializer, CaixaAberturaSerializer


class ProdutoViewSet(viewsets.ModelViewSet):
    queryset = Produto.objects.all()
    serializer_class = ProdutoSerializer
    permission_classes = [permissions.IsAuthenticated]


class VendaViewSet(viewsets.ModelViewSet):
    queryset = Venda.objects.all()
    serializer_class = VendaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        return {'request': self.request}


class CaixaViewSet(viewsets.ModelViewSet):
    queryset = Caixa.objects.all().order_by('-data_abertura')
    serializer_class = CaixaSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='aberto')
    def get_caixa_aberto(self, request):
        try:
            # Tenta encontrar um caixa aberto associado ao usuário logado
            caixa_aberto = Caixa.objects.get(responsavel=request.user, status='ABERTO')
            serializer = self.get_serializer(caixa_aberto)
            return Response(serializer.data)
        except Caixa.DoesNotExist:
            return Response(None, status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='aberto/totais')
    def get_totals(self, request):
        try:
            caixa_aberto = Caixa.objects.get(responsavel=request.user, status='ABERTO')
            vendas_no_periodo = Venda.objects.filter(data_venda__gte=caixa_aberto.data_abertura)
            totais = vendas_no_periodo.values('metodo_pagamento').annotate(
                total_metodo=Coalesce(Sum('total'), 0, output_field=DecimalField()))
            resultado = {'dinheiro': 0, 'credito': 0, 'debito': 0, 'pix': 0, 'total': 0}
            for item in totais:
                metodo = item['metodo_pagamento'].lower().replace('cartao de ', '').replace('cartão', 'credito')
                if metodo in resultado:
                    resultado[metodo] = item['total_metodo']
            resultado['total'] = sum(resultado.values())
            return Response(resultado)
        except Caixa.DoesNotExist:
            return Response({'detail': 'Nenhum caixa aberto para este usuário.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], url_path='abrir')
    def abrir_caixa(self, request):
        if Caixa.objects.filter(responsavel=request.user, status='ABERTO').exists():
            return Response({'detail': 'Você já possui um caixa aberto.'}, status=status.HTTP_400_BAD_REQUEST)

        # ALTERAÇÃO: Remove a linha que sobrescreve request.data['responsavel']
        # O serializer deve pegar o responsavel do request.user

        serializer = CaixaAberturaSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            # No serializer, garanta que o responsável seja atribuído como request.user
            serializer.save(responsavel=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='fechar')
    def fechar_caixa(self, request, pk=None):
        caixa = self.get_object()
        if caixa.status == 'FECHADO':
            return Response({'detail': 'Este caixa já está fechado.'}, status=status.HTTP_400_BAD_REQUEST)

        totais_apurados = request.data.get('totais', {})
        caixa.dinheiro_apurado = totais_apurados.get('dinheiro', 0)
        caixa.credito_apurado = totais_apurados.get('credito', 0)
        caixa.debito_apurado = totais_apurados.get('debito', 0)
        caixa.pix_apurado = totais_apurados.get('pix', 0)
        caixa.valor_fechamento_apurado = totais_apurados.get('total', 0)

        caixa.status = 'FECHADO'
        caixa.data_fechamento = timezone.now()
        caixa.save()
        return Response(self.get_serializer(caixa).data)

    @action(detail=False, methods=['get'], url_path='historico')
    def get_history(self, request):
        queryset = Caixa.objects.filter(status='FECHADO').order_by('-data_fechamento')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='details')
    def get_details(self, request, pk=None):
        try:
            caixa = self.get_object()
            if not caixa.data_fechamento:
                caixa.data_fechamento = timezone.now()

            vendas_no_periodo = Venda.objects.filter(
                data_venda__gte=caixa.data_abertura,
                data_venda__lte=caixa.data_fechamento
            )
            totais_venda = vendas_no_periodo.values('metodo_pagamento').annotate(
                total=Coalesce(Sum('total'), 0, output_field=DecimalField())
            )
            itens_vendidos = ItemVenda.objects.filter(venda__in=vendas_no_periodo).values(
                'produto__nome', 'quantidade', 'preco_unitario', 'venda__metodo_pagamento'
            ).order_by('-venda__data_venda')
            details = {
                'caixa': self.get_serializer(caixa).data,
                'totais_venda': list(totais_venda),
                'itens_vendidos': list(itens_vendidos)
            }
            return Response(details)
        except Caixa.DoesNotExist:
            return Response({'detail': 'Caixa não encontrado.'}, status=status.HTTP_404_NOT_FOUND)


class DashboardAdminAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        data_str = request.query_params.get('data')
        vendedor_id = request.query_params.get('vendedor_id')
        if data_str:
            data_selecionada = timezone.datetime.strptime(data_str, '%Y-%m-%d').date()
        else:
            data_selecionada = timezone.now().date()

        inicio_dia = timezone.make_aware(timezone.datetime.combine(data_selecionada, timezone.datetime.min.time()))
        fim_dia = timezone.make_aware(timezone.datetime.combine(data_selecionada, timezone.datetime.max.time()))
        vendas_do_dia = Venda.objects.filter(data_venda__range=(inicio_dia, fim_dia))
        itens_do_dia = ItemVenda.objects.filter(venda__in=vendas_do_dia)

        if vendedor_id and vendedor_id != 'todos':
            vendas_do_dia = vendas_do_dia.filter(vendedor_id=vendedor_id)
            itens_do_dia = itens_do_dia.filter(venda__vendedor_id=vendedor_id)

        total_geral_vendido = vendas_do_dia.aggregate(total=Coalesce(Sum('total'), 0, output_field=DecimalField()))[
            'total']
        total_produtos_vendidos = \
        itens_do_dia.aggregate(total=Coalesce(Sum('quantidade'), 0, output_field=IntegerField()))['total']

        ranking_produtos = ItemVenda.objects.values('produto__nome').annotate(total_vendido=Sum('quantidade')).order_by(
            '-total_vendido')[:5]
        ranking_vendedores = Venda.objects.values('vendedor__username').annotate(
            valor_total_vendido=Sum('total')).order_by('-valor_total_vendido')[:3]
        vendedores = User.objects.filter(is_staff=True).values('id', 'username')

        data = {
            'total_geral_vendido': total_geral_vendido,
            'total_produtos_vendidos': total_produtos_vendidos,
            'ranking_produtos': list(ranking_produtos),
            'ranking_vendedores': list(ranking_vendedores),
            'vendedores_disponiveis': list(vendedores),
        }
        return Response(data)


class DashboardFuncionarioAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        funcionario = request.user
        total_vendido_turno = 0
        produtos_vendidos_turno = 0
        try:
            caixa_aberto = Caixa.objects.get(responsavel=funcionario, status='ABERTO')
            vendas_no_periodo = Venda.objects.filter(vendedor=funcionario, data_venda__gte=caixa_aberto.data_abertura)
            total_vendido_turno = \
            vendas_no_periodo.aggregate(total=Coalesce(Sum('total'), 0, output_field=DecimalField()))['total']
            produtos_vendidos_turno = \
            vendas_no_periodo.aggregate(total=Coalesce(Sum('itens__quantidade'), 0, output_field=IntegerField()))[
                'total']
        except Caixa.DoesNotExist:
            pass
        data = {
            'totalVendidoTurno': total_vendido_turno,
            'produtosVendidosTurno': produtos_vendidos_turno,
        }
        return Response(data)